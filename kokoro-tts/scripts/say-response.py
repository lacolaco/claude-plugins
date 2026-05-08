"""Read Claude Code responses aloud using Kokoro TTS (mlx-audio, Apple Silicon)."""

import json
import os
import queue
import re
import signal
import subprocess
import sys
import tempfile
import threading
import warnings

import alkana
import soundfile as sf
from mlx_audio.tts.utils import load_model

warnings.filterwarnings("ignore")

MODEL_ID = "mlx-community/Kokoro-82M-bf16"
VOICE = "jf_alpha"
LANG = "j"
MAX_TEXT_LENGTH = 2000
# Kokoro truncates input at 510 phonemes per inference, so we synthesize in
# smaller chunks (split on sentence/clause boundaries) and concatenate the
# audio. Japanese averages around 2 phonemes per character, so cap each chunk
# well under the 510-phoneme ceiling.
MAX_CHARS_PER_CHUNK = 180
# Speed scales linearly with the chunk count so short replies stay natural
# while long multi-chunk responses don't drag.
SPEED_MIN = 1.2
SPEED_MAX = 1.5
SPEED_CHUNKS_FLOOR = 1  # at or below this many chunks: SPEED_MIN
SPEED_CHUNKS_CEILING = 8  # at or above this many chunks: SPEED_MAX

CUSTOM = {
    "API": "エーピーアイ",
    "CLI": "シーエルアイ",
    "SQL": "エスキューエル",
    "SSH": "エスエスエイチ",
    "TTS": "ティーティーエス",
    "CI": "シーアイ",
    "CD": "シーディー",
    "PR": "ピーアール",
    "AI": "エーアイ",
    "git": "ギット",
    "npm": "エヌピーエム",
    "pnpm": "ピーエヌピーエム",
    "GitHub": "ギットハブ",
    "TypeScript": "タイプスクリプト",
    "JavaScript": "ジャバスクリプト",
    "Anthropic": "アンソロピック",
    "Claude": "クロード",
    "lacolaco": "ラコラコ",
    "plugin": "プラグイン",
    "Plugin": "プラグイン",
}
_CUSTOM_SORTED = sorted(CUSTOM.items(), key=lambda x: -len(x[0]))


def clean(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    in_code = False
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
        s = re.sub(r"^[-*+]\s+", "", s)
        s = re.sub(r"^\d+\.\s+", "", s)
        if s:
            cleaned.append(s)
    text = " ".join(cleaned)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    for ch in ["#", "`", ">"]:
        text = text.replace(ch, "")
    text = re.sub(r"（[^）]*）", "", text)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"【[^】]*】", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = " ".join(text.split()).strip()
    return text[:MAX_TEXT_LENGTH]


def en_to_kana(text: str) -> str:
    for k, v in _CUSTOM_SORTED:
        text = text.replace(k, v)

    def replace_word(m: re.Match) -> str:
        word = m.group(0)
        kana = alkana.get_kana(word.lower())
        return kana if kana else word

    return re.sub(r"[A-Za-z]{2,}", replace_word, text)


PIDFILE = os.path.expanduser("~/.claude/kokoro-tts/playback.pid")


def player_worker(play_queue: "queue.Queue[str | None]") -> None:
    """Drain the queue, playing each WAV synchronously and deleting it after."""
    while True:
        path = play_queue.get()
        if path is None:
            return
        subprocess.run(["afplay", path], check=False)
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def kill_previous_playback() -> None:
    """Terminate the previous run's process group, if any, so the latest
    response supersedes earlier playback instead of overlapping with it."""
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
    """Become a process-group leader and record the pgid for the next run."""
    os.setpgrp()
    os.makedirs(os.path.dirname(PIDFILE), exist_ok=True)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))


def clear_self() -> None:
    """Remove the pid file if it still points at us."""
    try:
        with open(PIDFILE) as f:
            recorded = int(f.read().strip())
        if recorded == os.getpid():
            os.unlink(PIDFILE)
    except (FileNotFoundError, ValueError):
        pass


def adaptive_speed(num_chunks: int) -> float:
    """Linear interpolation from SPEED_MIN to SPEED_MAX over the chunk-count range."""
    if num_chunks <= SPEED_CHUNKS_FLOOR:
        return SPEED_MIN
    if num_chunks >= SPEED_CHUNKS_CEILING:
        return SPEED_MAX
    ratio = (num_chunks - SPEED_CHUNKS_FLOOR) / (
        SPEED_CHUNKS_CEILING - SPEED_CHUNKS_FLOOR
    )
    return SPEED_MIN + ratio * (SPEED_MAX - SPEED_MIN)


def split_into_chunks(text: str, max_chars: int) -> list[str]:
    """Split on sentence and clause boundaries, packing as much as fits.

    Falls back to hard-cutting at max_chars when a single clause is still
    longer than the limit, so no chunk ever exceeds max_chars.
    """
    parts = re.split(r"(?<=[。．！？!?、，,])\s*", text)
    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current:
            chunks.append(current)
            current = ""

    for part in parts:
        if not part:
            continue
        if len(part) > max_chars:
            flush()
            for i in range(0, len(part), max_chars):
                chunks.append(part[i : i + max_chars])
            continue
        if not current:
            current = part
        elif len(current) + len(part) <= max_chars:
            current += part
        else:
            flush()
            current = part
    flush()
    return chunks


def main() -> None:
    data = json.load(sys.stdin)
    # Stop / StopFailure carry `last_assistant_message`; Notification carries `message`.
    text = data.get("last_assistant_message") or data.get("message") or ""
    if not text:
        return

    text = clean(text)
    if not text:
        return

    text = en_to_kana(text)

    chunks = split_into_chunks(text, MAX_CHARS_PER_CHUNK)
    if not chunks:
        return

    speed = adaptive_speed(len(chunks))

    # Single-flight: terminate any in-progress playback (including its
    # afplay child) so a fresh response replaces the previous one instead
    # of overlapping. Becoming a pgrp leader bundles us with our subprocess
    # afplay processes so the next run can kill them all with killpg.
    kill_previous_playback()
    register_self()

    try:
        # Pipeline synthesis and playback so audio starts as soon as the
        # first chunk is ready instead of waiting for the full response.
        play_queue: "queue.Queue[str | None]" = queue.Queue()
        player = threading.Thread(
            target=player_worker, args=(play_queue,), daemon=False
        )
        player.start()

        model = load_model(MODEL_ID)
        for chunk in chunks:
            for result in model.generate(
                text=chunk, voice=VOICE, speed=speed, lang_code=LANG
            ):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    sf.write(f.name, result.audio, result.sample_rate)
                    path = f.name
                play_queue.put(path)

        play_queue.put(None)
        player.join()
    finally:
        clear_self()


if __name__ == "__main__":
    main()
