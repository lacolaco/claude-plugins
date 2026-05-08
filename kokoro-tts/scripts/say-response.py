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
import soundfile as sf
from mlx_audio.tts.utils import load_model

warnings.filterwarnings("ignore")

MODEL_ID = "mlx-community/Kokoro-82M-bf16"
VOICE = "jf_alpha"
SPEED = 1.2
LANG = "j"
MAX_TEXT_LENGTH = 1000

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

    model = load_model(MODEL_ID)
    result = next(
        model.generate(text=text, voice=VOICE, speed=SPEED, lang_code=LANG), None
    )
    if result is None:
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, result.audio, result.sample_rate)
        threading.Thread(
            target=play_and_cleanup, args=(f.name,), daemon=False
        ).start()


if __name__ == "__main__":
    main()
