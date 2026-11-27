"""Tests for voice assignment: session-on.sh, tts.sh on, and resolve_speaker."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

_PLUGIN_ROOT = Path(__file__).resolve().parents[2]
_SESSION_ON = _PLUGIN_ROOT / "scripts" / "session-on.sh"
_TTS_SH = _PLUGIN_ROOT / "skills" / "tts" / "tts.sh"
_SAY_SH = _PLUGIN_ROOT / "skills" / "say" / "say.sh"

# Rotation order: ずんだもん, 四国めたん, 春日部つむぎ, 冥鳴ひまり, 東北きりたん.
_ROTATION = ["3", "2", "8", "14", "108"]


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """Isolated HOME plus a stub `uv` that records the speaker it was given."""
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "uv"
    stub.write_text(
        "#!/bin/bash\n"
        'case "$*" in *say-response.py*) '
        f'echo "$SESSION_TTS_SPEAKER_ID" >> "{tmp_path}/spoken-speakers" ;; esac\n'
        "cat > /dev/null\n"
    )
    stub.chmod(0o755)
    e = dict(os.environ)
    e["HOME"] = str(home)
    e["PATH"] = f"{bin_dir}:{e['PATH']}"
    e["CLAUDE_PLUGIN_ROOT"] = str(_PLUGIN_ROOT)
    e.pop("SESSION_TTS_ENABLED", None)
    return e


def _data_dir(env: dict[str, str]) -> Path:
    return Path(env["HOME"]) / ".claude" / "session-tts"


def _speaker(env: dict[str, str], sid: str) -> str | None:
    f = _data_dir(env) / "sessions" / sid / "speaker"
    return f.read_text().strip() if f.exists() else None


def _session_start(env: dict[str, str], sid: str, enabled: str | None = None) -> None:
    e = dict(env)
    if enabled is not None:
        e["SESSION_TTS_ENABLED"] = enabled
    r = subprocess.run(
        ["bash", str(_SESSION_ON)],
        input=json.dumps({"session_id": sid}),
        env=e, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr


def _tts(env: dict[str, str], sid: str, action: str) -> subprocess.CompletedProcess[str]:
    e = dict(env)
    e["CLAUDE_CODE_SESSION_ID"] = sid
    return subprocess.run(
        ["bash", str(_TTS_SH), action],
        env=e, capture_output=True, text=True, check=False,
    )


def test_rotation_cycles_through_all_voices(env: dict[str, str]) -> None:
    for i in range(len(_ROTATION) + 1):
        _session_start(env, f"s{i}")
    got = [_speaker(env, f"s{i}") for i in range(len(_ROTATION) + 1)]
    assert got == [*_ROTATION, _ROTATION[0]]


def test_refire_keeps_voice(env: dict[str, str]) -> None:
    _session_start(env, "a")
    _session_start(env, "a")
    _session_start(env, "b")
    assert _speaker(env, "a") == _ROTATION[0]
    assert _speaker(env, "b") == _ROTATION[1]


@pytest.mark.parametrize("value", ["0", "false", "no"])
def test_disabled_session_takes_no_slot(env: dict[str, str], value: str) -> None:
    _session_start(env, "lead1")
    _session_start(env, "worker", enabled=value)
    _session_start(env, "lead2")
    assert _speaker(env, "worker") is None
    assert (_data_dir(env) / "sessions" / "worker" / "silenced").exists()
    assert _speaker(env, "lead1") == _ROTATION[0]
    assert _speaker(env, "lead2") == _ROTATION[1]


def test_late_activation_assigns_voice(env: dict[str, str]) -> None:
    _session_start(env, "lead")
    _session_start(env, "late", enabled="0")
    r = _tts(env, "late", "on")
    assert r.returncode == 0, r.stderr
    assert "TTS is enabled for this session" in r.stdout
    assert _speaker(env, "late") == _ROTATION[1]
    assert not (_data_dir(env) / "sessions" / "late" / "silenced").exists()
    # A later off/on keeps the voice.
    _tts(env, "late", "off")
    _tts(env, "late", "on")
    assert _speaker(env, "late") == _ROTATION[1]


def test_legacy_speaker_id_is_replaced_on_speak(env: dict[str, str], tmp_path: Path) -> None:
    d = _data_dir(env) / "sessions" / "old"
    d.mkdir(parents=True)
    (d / "speaker").write_text("888753760\n")
    e = dict(env)
    e["CLAUDE_CODE_SESSION_ID"] = "old"
    r = subprocess.run(
        ["bash", str(_SAY_SH), "報告です"],
        env=e, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr
    assert _speaker(env, "old") == _ROTATION[0]
    assert (tmp_path / "spoken-speakers").read_text().split() == [_ROTATION[0]]


def test_legacy_speaker_id_is_replaced_on_refire(env: dict[str, str]) -> None:
    d = _data_dir(env) / "sessions" / "old"
    d.mkdir(parents=True)
    (d / "speaker").write_text("1431611904\n")
    _session_start(env, "old")
    assert _speaker(env, "old") == _ROTATION[0]


def test_silenced_session_is_not_reassigned(env: dict[str, str], tmp_path: Path) -> None:
    d = _data_dir(env) / "sessions" / "old"
    d.mkdir(parents=True)
    (d / "speaker").write_text("888753760\n")
    (d / "silenced").write_text("")
    e = dict(env)
    e["CLAUDE_CODE_SESSION_ID"] = "old"
    subprocess.run(["bash", str(_SAY_SH), "報告です"], env=e, check=True, capture_output=True)
    assert _speaker(env, "old") == "888753760"
    assert not (tmp_path / "spoken-speakers").exists()


# --- stereo position (sessions/<sid>/pan) ---------------------------------

_PAN_RE = re.compile(r"-?(0(\.[0-9]+)?|1(\.0+)?)")


def _pan(env: dict[str, str], sid: str) -> str | None:
    f = _data_dir(env) / "sessions" / sid / "pan"
    return f.read_text().strip() if f.exists() else None


def _say(env: dict[str, str], sid: str) -> None:
    e = dict(env)
    e["CLAUDE_CODE_SESSION_ID"] = sid
    subprocess.run(["bash", str(_SAY_SH), "報告です"], env=e, check=True, capture_output=True)


def test_session_start_assigns_valid_random_pan(env: dict[str, str]) -> None:
    for i in range(10):
        _session_start(env, f"s{i}")
    pans = [_pan(env, f"s{i}") for i in range(10)]
    assert all(p is not None and _PAN_RE.fullmatch(p) for p in pans), pans
    assert len(set(pans)) > 1, pans


def test_pan_is_stable_across_refire_and_off_on(env: dict[str, str]) -> None:
    _session_start(env, "a")
    first = _pan(env, "a")
    _session_start(env, "a")
    _tts(env, "a", "off")
    _tts(env, "a", "on")
    _say(env, "a")
    assert _pan(env, "a") == first


def test_disabled_session_gets_pan_on_late_activation(env: dict[str, str]) -> None:
    _session_start(env, "late", enabled="0")
    assert _pan(env, "late") is None
    _tts(env, "late", "on")
    assert _PAN_RE.fullmatch(_pan(env, "late") or "")


def test_session_with_voice_but_no_pan_gets_one_on_speech(env: dict[str, str]) -> None:
    d = _data_dir(env) / "sessions" / "old"
    d.mkdir(parents=True)
    (d / "speaker").write_text(_ROTATION[2] + "\n")
    _say(env, "old")
    assert _speaker(env, "old") == _ROTATION[2]
    assert _PAN_RE.fullmatch(_pan(env, "old") or "")


@pytest.mark.parametrize("content", ["", "left", "1.5", "-2", "0.5.1"])
def test_invalid_pan_is_replaced(env: dict[str, str], content: str) -> None:
    _session_start(env, "a")
    (_data_dir(env) / "sessions" / "a" / "pan").write_text(content)
    _say(env, "a")
    assert _PAN_RE.fullmatch(_pan(env, "a") or "")
