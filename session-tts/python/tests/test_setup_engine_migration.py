"""Tests for setup_engine.py migration from the AivisSpeech engine install."""
from __future__ import annotations

import importlib.util
import subprocess
import time
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "setup_engine.py"


@pytest.fixture
def setup_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    spec = importlib.util.spec_from_file_location("setup_engine", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data_dir = tmp_path / "session-tts"
    data_dir.mkdir()
    monkeypatch.setattr(module, "DATA_DIR", data_dir)
    monkeypatch.setattr(module, "LEGACY_ENGINE_DIR", data_dir / "engine")
    monkeypatch.setattr(module, "LEGACY_ENGINE_PID", data_dir / "engine.pid")
    return module


def _start_fake_engine(run: Path) -> subprocess.Popen[bytes]:
    run.parent.mkdir(parents=True, exist_ok=True)
    run.write_text("#!/bin/bash\nsleep 60 &\nwait\n")
    run.chmod(0o755)
    proc = subprocess.Popen(["bash", str(run)], start_new_session=True)
    time.sleep(0.3)
    return proc


def test_stops_legacy_engine_and_removes_its_dir(setup_engine: ModuleType) -> None:
    proc = _start_fake_engine(setup_engine.LEGACY_ENGINE_DIR / "run")
    setup_engine.LEGACY_ENGINE_PID.write_text(str(proc.pid))
    setup_engine.migrate_legacy_engine()
    assert proc.wait(timeout=5) is not None
    assert not setup_engine.LEGACY_ENGINE_PID.exists()
    assert not setup_engine.LEGACY_ENGINE_DIR.exists()


def test_leaves_unrelated_process_with_recycled_pid(
    setup_engine: ModuleType, tmp_path: Path
) -> None:
    other = _start_fake_engine(tmp_path / "elsewhere" / "run")
    try:
        setup_engine.LEGACY_ENGINE_PID.write_text(str(other.pid))
        setup_engine.migrate_legacy_engine()
        assert other.poll() is None
        assert not setup_engine.LEGACY_ENGINE_PID.exists()
    finally:
        other.kill()
        other.wait()


def test_no_legacy_install_is_a_noop(setup_engine: ModuleType) -> None:
    setup_engine.migrate_legacy_engine()
    assert list(setup_engine.DATA_DIR.iterdir()) == []
