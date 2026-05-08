"""Read Claude Code responses aloud using Kokoro TTS (mlx-audio, Apple Silicon)."""

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import warnings

import alkana
import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model

warnings.filterwarnings("ignore")

MODEL_ID = "mlx-community/Kokoro-82M-bf16"
VOICE = "jf_alpha"
SPEED = 1.2
LANG = "j"
MAX_TEXT_LENGTH = 2000
# Kokoro truncates input at 510 phonemes per inference, so we synthesize in
# smaller chunks (split on sentence/clause boundaries) and concatenate the
# audio. Japanese averages around 2 phonemes per character, so cap each chunk
# well under the 510-phoneme ceiling.
MAX_CHARS_PER_CHUNK = 180

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


def play_and_cleanup(path: str) -> None:
    subprocess.run(["afplay", path], check=False)
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


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

    model = load_model(MODEL_ID)
    audio_pieces: list[np.ndarray] = []
    sample_rate: int | None = None
    for chunk in chunks:
        for result in model.generate(
            text=chunk, voice=VOICE, speed=SPEED, lang_code=LANG
        ):
            audio_pieces.append(result.audio)
            sample_rate = result.sample_rate

    if not audio_pieces or sample_rate is None:
        return

    audio = np.concatenate(audio_pieces)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, sample_rate)
        threading.Thread(
            target=play_and_cleanup, args=(f.name,), daemon=False
        ).start()


if __name__ == "__main__":
    main()
