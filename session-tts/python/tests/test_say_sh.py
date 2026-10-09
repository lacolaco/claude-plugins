"""Tests for skills/say/say.sh: the phrase is echoed to stdout, then spoken."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_SAY_SH = Path(__file__).resolve().parents[2] / "skills" / "say" / "say.sh"
_SESSION_ID = "test-session"
_PHRASE = "報告です。テストが通りました"


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """Isolated HOME plus a stub `uv` that records stdin and prints noise."""
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "uv"
    stub.write_text(
        "#!/bin/bash\n"
        f'cat > "{tmp_path}/spoken.txt"\n'
        "echo 'stub-engine-noise'\n"
    )
    stub.chmod(0o755)
    e = dict(os.environ)
    e["HOME"] = str(home)
    e["PATH"] = f"{bin_dir}:{e['PATH']}"
    e["CLAUDE_CODE_SESSION_ID"] = _SESSION_ID
    e.pop("CLAUDE_PLUGIN_ROOT", None)
    return e


def _session_dir(env: dict[str, str]) -> Path:
    d = Path(env["HOME"]) / ".claude" / "session-tts" / "sessions" / _SESSION_ID
    d.mkdir(parents=True, exist_ok=True)
    return d


def _run(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_SAY_SH), *args],
        env=env, capture_output=True, text=True, check=False,
    )


def test_echoes_phrase_and_speaks(env: dict[str, str], tmp_path: Path) -> None:
    (_session_dir(env) / "speaker").write_text("3")
    r = _run(env, _PHRASE)
    assert r.returncode == 0
    assert r.stdout == _PHRASE + "\n"
    assert (tmp_path / "spoken.txt").read_text() == _PHRASE


def test_echoes_phrase_when_silenced(env: dict[str, str], tmp_path: Path) -> None:
    d = _session_dir(env)
    (d / "speaker").write_text("3")
    (d / "silenced").write_text("")
    r = _run(env, _PHRASE)
    assert r.returncode == 0
    assert r.stdout == _PHRASE + "\n"
    assert not (tmp_path / "spoken.txt").exists()


def test_echoes_phrase_when_no_speaker(env: dict[str, str], tmp_path: Path) -> None:
    r = _run(env, _PHRASE)
    assert r.returncode == 0
    assert r.stdout == _PHRASE + "\n"
    assert not (tmp_path / "spoken.txt").exists()


def test_empty_argument_prints_nothing(env: dict[str, str]) -> None:
    (_session_dir(env) / "speaker").write_text("3")
    for args in ([], [""]):
        r = _run(env, *args)
        assert r.returncode == 0
        assert r.stdout == ""
