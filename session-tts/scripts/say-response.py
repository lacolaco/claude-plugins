"""Speak text aloud via the local TTS engine.

Core text→audio adapter. Receives the text to speak on stdin (plain UTF-8)
and the per-session voice via the SESSION_TTS_SPEAKER_ID env var. Hook /
notification / skill specifics live in caller-side adapters; this module
knows nothing about hook payload shapes.

Pipeline (synth and playback run in parallel):
  text → strip markdown → split into small chunks
                      → [synth thread]  HTTP /audio_query + /synthesis
                      → [player thread] afplay each WAV in order
The first chunk is intentionally small so the first audible word arrives
quickly even on long responses.
"""
from __future__ import annotations

import os
import queue
import re
import signal
import subprocess
import sys
import tempfile
import threading

import httpx

ENGINE_BASE_URL = os.environ.get("SESSION_TTS_ENGINE_URL", "http://127.0.0.1:10101")
SPEAKER_ID = int(os.environ.get("SESSION_TTS_SPEAKER_ID", "0"))
SESSION_ID = os.environ.get("SESSION_TTS_SESSION_ID", "")

MAX_TEXT_LENGTH = 2000
# Engine docs recommend keeping each /synthesis call under 500 chars and
# splitting at meaning boundaries (paragraphs/sentences) for natural prosody.
# Beyond ~1000 chars per call, prosody collapses into monotone and the engine
# may even leak memory. So: first chunk small for low time-to-first-audio,
# later chunks closer to the engine's sweet spot for prosody.
FIRST_CHUNK_MAX = 60
LATER_CHUNK_MAX = 250

# Long replies get sped up so multi-paragraph answers don't drag. The threshold
# is chunk-count based because chunk size is bounded above, so chunk count is
# a fair proxy for total speaking time.
FAST_SPEED_CHUNK_THRESHOLD = 4
FAST_SPEED_SCALE = 1.2

# Hard cap on how many chunks a single response can produce. Past this, the
# rest of the text is dropped and a truncation notice is appended so the user
# hears the cut instead of an abrupt mid-sentence stop. Without this cap, a
# very long response can play for over a minute and there is no easy way to
# interrupt it once it has started.
MAX_CHUNKS = 8
TRUNCATION_NOTICE = "以下、省略します。"

# Per-session pidfile: a new utterance only preempts a still-playing
# utterance from the SAME session. Other concurrent sessions keep their
# audio. The whole point of the per-session voice rotation is that
# parallel sessions can be told apart by ear; a global single-flight
# would make that pointless by silencing every session except the
# most recent one.
PIDFILE_DIR = os.path.expanduser("~/.claude/session-tts/playback")
PIDFILE = os.path.join(PIDFILE_DIR, SESSION_ID) if SESSION_ID else ""


# --- text cleanup ----------------------------------------------------------


def _strip_inline_markdown(text: str) -> str:
    # Markdown image: drop entirely (alt text rarely speaks well).
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    # Markdown link: keep the label, drop the URL part.
    text = re.sub(r"\[([^\]]+)\]\(([^)]*)\)", r"\1", text)
    # Bold / italic / inline code: keep inner text, drop the markers only.
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Heading and blockquote markers.
    for ch in ["#", ">"]:
        text = text.replace(ch, "")
    # Bare URLs that aren't part of a markdown link.
    text = re.sub(r"https?://\S+", "", text)
    return " ".join(text.split()).strip()


_LIST_ITEM_RE = re.compile(r"^([-*+]\s+|\d+\.\s+)(.*)")
# Endings that already provide a natural pause — no need to append a period.
_TERMINAL_PUNCT = ("。", "．", "！", "？", "!", "?", ".", "、", "，", ",")


def clean(text: str) -> str:
    """Strip Markdown and emit paragraphs separated by `\n\n`.

    List items keep their source paragraph (no extra `\n\n`) so playback
    flows naturally; instead each item gets a trailing `。` if it lacks
    one, which gives the synthesizer a clause-level pause between items
    without the longer paragraph-level gap.
    """
    paragraphs = re.split(r"\n[ \t]*\n+", text)
    out: list[str] = []
    in_code = False
    for paragraph in paragraphs:
        lines = paragraph.split("\n")
        cleaned: list[str] = []
        for line in lines:
            s = line.strip()
            if s.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if s.startswith("$ ") or s.startswith("> "):
                continue
            if line.startswith("    ") and s:
                continue
            if "|" in s:
                continue
            if s.startswith("---") or s.startswith(":--"):
                continue
            list_match = _LIST_ITEM_RE.match(s)
            if list_match:
                item_text = list_match.group(2).strip()
                if not item_text:
                    continue
                if not item_text.endswith(_TERMINAL_PUNCT):
                    item_text += "。"
                cleaned.append(item_text)
            elif s:
                cleaned.append(s)
        if not cleaned:
            continue
        merged = _strip_inline_markdown(" ".join(cleaned))
        if merged:
            out.append(merged)
    return "\n\n".join(out)[:MAX_TEXT_LENGTH]


# --- chunking --------------------------------------------------------------


def _split_paragraph(text: str, max_chars: int) -> list[str]:
    parts = re.split(r"(?<=[。．！？!?、，,])\s*", text)
    chunks: list[str] = []
    current = ""
    for part in parts:
        if not part:
            continue
        if len(part) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(part), max_chars):
                chunks.append(part[i : i + max_chars])
            continue
        if not current:
            current = part
        elif len(current) + len(part) <= max_chars:
            current += part
        else:
            chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks


def split_into_chunks(text: str) -> list[str]:
    """Split on paragraphs first, then sentence/clause boundaries.

    The first chunk is capped at FIRST_CHUNK_MAX so the engine returns
    something playable as fast as possible; subsequent chunks use
    LATER_CHUNK_MAX to keep the cadence natural.
    """
    chunks: list[str] = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if not chunks:
            head = _split_paragraph(paragraph, FIRST_CHUNK_MAX)
            if head:
                chunks.append(head[0])
                if len(head) > 1:
                    rest = "".join(head[1:])
                    chunks.extend(_split_paragraph(rest, LATER_CHUNK_MAX))
        else:
            chunks.extend(_split_paragraph(paragraph, LATER_CHUNK_MAX))
    return chunks


# --- single-flight playback ------------------------------------------------


def kill_previous_playback() -> None:
    if not PIDFILE:
        return
    try:
        with open(PIDFILE) as f:
            old_pgid = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return
    try:
        os.killpg(old_pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass


def register_self() -> None:
    os.setpgrp()
    if not PIDFILE:
        return
    os.makedirs(os.path.dirname(PIDFILE), exist_ok=True)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))


def clear_self() -> None:
    if not PIDFILE:
        return
    try:
        with open(PIDFILE) as f:
            recorded = int(f.read().strip())
        if recorded == os.getpid():
            os.unlink(PIDFILE)
    except (FileNotFoundError, ValueError):
        pass


# --- synthesis & playback --------------------------------------------------


def synth_chunk(
    client: httpx.Client, text: str, speaker_id: int, speed_scale: float = 1.0
) -> bytes:
    q = client.post("/audio_query", params={"text": text, "speaker": speaker_id})
    q.raise_for_status()
    query = q.json()
    if speed_scale != 1.0:
        query["speedScale"] = speed_scale
    # Pad each chunk's leading silence so afplay's device-open transient lands
    # inside the silence rather than over the first phoneme. Default 0.1s is
    # too short for that on Bluetooth output.
    query["prePhonemeLength"] = 0.5
    s = client.post(
        "/synthesis",
        params={"speaker": speaker_id},
        json=query,
        timeout=120.0,
    )
    s.raise_for_status()
    return s.content


def player_worker(play_queue: "queue.Queue[str | None]") -> None:
    while True:
        path = play_queue.get()
        if path is None:
            return
        subprocess.run(["afplay", path], check=False)
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def synth_worker(
    client: httpx.Client,
    speaker_id: int,
    chunks: list[str],
    play_queue: "queue.Queue[str | None]",
) -> None:
    speed_scale = (
        FAST_SPEED_SCALE if len(chunks) >= FAST_SPEED_CHUNK_THRESHOLD else 1.0
    )
    try:
        for chunk in chunks:
            try:
                wav_bytes = synth_chunk(client, chunk, speaker_id, speed_scale)
            except httpx.HTTPError:
                # Skip a failing chunk rather than aborting the whole reply —
                # better to lose one sentence than to leave the user wondering
                # why nothing is being read.
                continue
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_bytes)
                path = f.name
            play_queue.put(path)
    finally:
        play_queue.put(None)


# --- entrypoint ------------------------------------------------------------


def main() -> None:
    if SPEAKER_ID == 0:
        # No speaker assigned (session was never set up properly).
        return
    text = sys.stdin.read()
    if not text:
        return

    text = clean(text)
    if not text:
        return

    chunks = split_into_chunks(text)
    if not chunks:
        return
    if len(chunks) > MAX_CHUNKS:
        chunks = chunks[:MAX_CHUNKS] + [TRUNCATION_NOTICE]

    kill_previous_playback()
    register_self()
    try:
        with httpx.Client(base_url=ENGINE_BASE_URL, timeout=60.0) as client:
            play_queue: "queue.Queue[str | None]" = queue.Queue()
            synth_thread = threading.Thread(
                target=synth_worker,
                args=(client, SPEAKER_ID, chunks, play_queue),
                daemon=False,
            )
            player_thread = threading.Thread(
                target=player_worker, args=(play_queue,), daemon=False
            )
            synth_thread.start()
            player_thread.start()
            synth_thread.join()
            player_thread.join()
    finally:
        clear_self()


if __name__ == "__main__":
    main()
