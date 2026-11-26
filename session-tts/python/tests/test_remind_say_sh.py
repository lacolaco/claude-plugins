"""Tests for scripts/remind-say.sh: reminders reach only the lead conversation."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_REMIND_SH = Path(__file__).resolve().parents[2] / "scripts" / "remind-say.sh"
_SESSION_ID = "test-session"
_TRIGGERS = ["todo", "monitor", "agent", "prompt"]


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    home = tmp_path / "home"
    home.mkdir()
    e = dict(os.environ)
    # Pin XDG dirs to the real home so shimmed tools on PATH (jq via a
    # version manager) still find their config after HOME is swapped.
    real_home = Path.home()
    for var, sub in (("XDG_CONFIG_HOME", ".config"), ("XDG_DATA_HOME", ".local/share"),
                     ("XDG_CACHE_HOME", ".cache"), ("XDG_STATE_HOME", ".local/state")):
        e.setdefault(var, str(real_home / sub))
    e["HOME"] = str(home)
    e["CLAUDE_PLUGIN_ROOT"] = "/plugin-root"
    return e


def _session_dir(env: dict[str, str]) -> Path:
    d = Path(env["HOME"]) / ".claude" / "session-tts" / "sessions" / _SESSION_ID
    d.mkdir(parents=True, exist_ok=True)
    (d / "speaker").write_text("3")
    return d


def _run(env: dict[str, str], trigger: str, payload: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_REMIND_SH), trigger],
        input=json.dumps(payload), env=env, capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize("trigger", _TRIGGERS)
def test_lead_payload_prints_reminder(env: dict[str, str], trigger: str) -> None:
    _session_dir(env)
    r = _run(env, trigger, {"session_id": _SESSION_ID})
    assert r.returncode == 0
    assert "[session-tts]" in r.stdout
    assert "/plugin-root/skills/say/say.sh" in r.stdout
    if trigger != "prompt":
        assert "additionalContext" in json.loads(r.stdout)["hookSpecificOutput"]


@pytest.mark.parametrize("trigger", _TRIGGERS)
def test_subagent_payload_prints_nothing(env: dict[str, str], trigger: str) -> None:
    _session_dir(env)
    r = _run(env, trigger, {"session_id": _SESSION_ID, "agent_id": "a1b2c3", "agent_type": "general-purpose"})
    assert r.returncode == 0
    assert r.stdout == ""


@pytest.mark.parametrize("trigger", _TRIGGERS)
def test_silenced_lead_prints_nothing(env: dict[str, str], trigger: str) -> None:
    (_session_dir(env) / "silenced").write_text("")
    r = _run(env, trigger, {"session_id": _SESSION_ID})
    assert r.returncode == 0
    assert r.stdout == ""
