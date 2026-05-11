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
# Playback scope. "main" is the default (Stop / Notification hook).
# Mid-turn say.sh sets "say" to get its own pidfile lane and a queue-based
# (wait-then-register) instead of preempt-then-register semantics:
#   - "main" preempts the previous "main" utterance (so a new response
#     replaces the older one) — but does not touch "say".
#   - "say" waits for the previous "say" utterance to finish, then plays.
#     So consecutive mid-turn reports are serialized (no overlap) and the
#     Stop hook that fires right after a mid-turn report no longer kills
#     it (different pidfile lane).
SCOPE = os.environ.get("SESSION_TTS_SCOPE", "main")

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

# afplay --volume coefficient applied to every chunk. Capped below 1.0 so
# TTS doesn't dominate over other audio (notifications, music) when the
# user has system volume up. macOS has no native way to make afplay
# follow the system "alert volume"; this is the simplest substitute.
PLAYBACK_VOLUME = "0.8"

# Per-session, per-scope pidfile. Different scopes for the same session
# never see each other's pidfile, so the Stop hook ("main") and mid-turn
# say.sh ("say") cannot kill each other. Different sessions still have
# independent pidfiles within each scope (concurrent sessions keep their
# audio — that's the whole point of the per-session voice rotation).
PIDFILE_DIR = os.path.expanduser(f"~/.claude/session-tts/playback/{SCOPE}")
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


_HEADING_LINE_RE = re.compile(r"^#{1,6}\s+\S")


def clean(text: str) -> str:
    """Strip Markdown and emit paragraphs separated by `\n\n`.

    List items keep their source paragraph (no extra `\n\n`) so playback
    flows naturally; instead each item gets a trailing `。` if it lacks
    one, which gives the synthesizer a clause-level pause between items
    without the longer paragraph-level gap.

    Markdown headings (a paragraph whose only line starts with `#…#
    `) are NOT emitted as their own paragraph. Instead the heading
    text is held over and prepended to the *next* non-heading
    paragraph (with `。` between them), so a heading like `## 検証`
    does not become a 2-character chunk bookended by audible silence
    (`prePhonemeLength` pad + `afplay` device-open overhead per
    chunk). Regular paragraph boundaries are preserved — only the
    heading-vs-its-section split is collapsed.
    """
    paragraphs = re.split(r"\n[ \t]*\n+", text)
    out: list[str] = []
    in_code = False
    pending_heading = ""
    for paragraph in paragraphs:
        lines = paragraph.split("\n")
        is_heading_only = (
            not in_code
            and len(lines) == 1
            and _HEADING_LINE_RE.match(lines[0].strip()) is not None
        )
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
        if not merged:
            continue
        if is_heading_only:
            if not merged.endswith(_TERMINAL_PUNCT):
                merged += "。"
            pending_heading += merged
            continue
        if pending_heading:
            merged = pending_heading + merged
            pending_heading = ""
        out.append(merged)
    if pending_heading:
        out.append(pending_heading)
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


def wait_for_previous_playback(poll_interval: float = 0.2) -> None:
    """Block until the previous playback in this scope finishes.

    Used by the "say" scope so consecutive mid-turn reports queue up
    rather than overlap. Polls the pidfile + signal-0 instead of using
    fcntl.flock to keep behavior identical to the killpg path (which
    also walks the pidfile contents).
    """
    import time

    if not PIDFILE:
        return
    while True:
        try:
            with open(PIDFILE) as f:
                old_pgid = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return
        try:
            # Signal 0 = "check existence without sending". If the process
            # group leader is gone, we own the slot.
            os.killpg(old_pgid, 0)
        except (ProcessLookupError, PermissionError):
            return
        time.sleep(poll_interval)


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
        subprocess.run(["afplay", "--volume", PLAYBACK_VOLUME, path], check=False)
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

    if SCOPE == "say":
        # mid-turn say.sh: queue up behind the previous mid-turn report
        # so consecutive narrations play in order without overlap.
        wait_for_previous_playback()
    else:
        # main / default: preempt the previous in-flight utterance.
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
