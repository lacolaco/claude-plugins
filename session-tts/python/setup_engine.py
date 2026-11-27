"""Bootstrap the local TTS engine (VOICEVOX Engine).

Idempotent: every step checks state first and skips if already done.
Designed to run on every SessionStart so the engine is always available;
typical re-runs do nothing but a port probe.

The VOICEVOX Engine archive bundles its voice models (`model/*.vvm`), so
there is no separate model install step.
"""
from __future__ import annotations

import fcntl
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

# --- configuration ---------------------------------------------------------

ENGINE_VERSION = "0.26.2"
ENGINE_ASSET = (
    f"https://github.com/VOICEVOX/voicevox_engine/releases/download/"
    f"{ENGINE_VERSION}/voicevox_engine-macos-arm64-{ENGINE_VERSION}.7z.001"
)
# Top-level directory inside the release archive.
ENGINE_ARCHIVE_ROOT = "macos-arm64"
# Plugin-specific port: the VOICEVOX desktop app uses 50021, so the plugin
# runs its own engine on a different port to avoid colliding with it.
DEFAULT_ENGINE_URL = "http://127.0.0.1:50121"
ENGINE_BASE_URL = os.environ.get("SESSION_TTS_ENGINE_URL", DEFAULT_ENGINE_URL)
_url = urlsplit(ENGINE_BASE_URL)
ENGINE_HOST = _url.hostname or "127.0.0.1"
ENGINE_PORT = _url.port or 50121
ENGINE_CPU_THREADS = 4

DATA_DIR = Path.home() / ".claude" / "session-tts"
ENGINE_DIR = DATA_DIR / "voicevox-engine"
ENGINE_BIN = ENGINE_DIR / "run"
ENGINE_PID = DATA_DIR / "voicevox-engine.pid"
ENGINE_LOG = DATA_DIR / "engine.log"
SETUP_LOCK = DATA_DIR / "setup.lock"

# Install left behind by session-tts <= 0.13 (AivisSpeech Engine). Both
# paths are fixed constants derived from the home directory, never from
# a variable that could be empty.
LEGACY_ENGINE_DIR = DATA_DIR / "engine"
LEGACY_ENGINE_PID = DATA_DIR / "engine.pid"


def log(msg: str) -> None:
    print(f"[session-tts/setup] {msg}", flush=True)


# --- migration from AivisSpeech Engine -------------------------------------


def _is_legacy_engine(pid: int) -> bool:
    r = subprocess.run(
        ["ps", "-ww", "-o", "command=", "-p", str(pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    return str(LEGACY_ENGINE_DIR) in r.stdout


def _wait_exit(pid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _is_legacy_engine(pid):
            return True
        time.sleep(0.2)
    return not _is_legacy_engine(pid)


def stop_legacy_engine() -> None:
    """Stop the AivisSpeech engine a previous plugin version started.

    Only the pid recorded in the legacy pid file is signalled, and only if
    that process is still running from the legacy engine directory, so a
    recycled pid never hits an unrelated process.
    """
    if not LEGACY_ENGINE_PID.exists():
        return
    raw = LEGACY_ENGINE_PID.read_text().strip()
    if raw.isdigit():
        pid = int(raw)
        if _is_legacy_engine(pid):
            log(f"stopping legacy AivisSpeech engine (pid={pid})...")
            # The engine was started with start_new_session=True, so it
            # leads its own process group.
            os.killpg(pid, signal.SIGTERM)
            if not _wait_exit(pid, 10.0):
                os.killpg(pid, signal.SIGKILL)
                _wait_exit(pid, 5.0)
    LEGACY_ENGINE_PID.unlink()


def remove_legacy_engine_dir() -> None:
    if LEGACY_ENGINE_DIR.is_dir():
        log(f"removing legacy AivisSpeech engine at {LEGACY_ENGINE_DIR}")
        shutil.rmtree(LEGACY_ENGINE_DIR)


def migrate_legacy_engine() -> None:
    stop_legacy_engine()
    remove_legacy_engine_dir()


# --- engine binary ---------------------------------------------------------


def ensure_engine_binary() -> None:
    if ENGINE_BIN.exists() and os.access(ENGINE_BIN, os.X_OK):
        return
    log(f"downloading VOICEVOX Engine v{ENGINE_VERSION} (~1.8 GB)...")
    # Extract next to the final location so the move is a same-volume rename.
    with tempfile.TemporaryDirectory(dir=DATA_DIR) as tmp:
        archive = Path(tmp) / "engine.7z"
        with httpx.stream("GET", ENGINE_ASSET, follow_redirects=True, timeout=300.0) as r:
            r.raise_for_status()
            with archive.open("wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
        log("extracting engine archive...")
        # Lazy import — py7zr pulls a few transitive deps we'd rather not
        # load when the binary is already in place.
        import py7zr  # type: ignore

        extract_dir = Path(tmp) / "extract"
        with py7zr.SevenZipFile(archive, "r") as z:
            z.extractall(path=extract_dir)
        extracted_root = extract_dir / ENGINE_ARCHIVE_ROOT
        if not (extracted_root / "run").exists():
            raise RuntimeError(f"engine archive layout unexpected: no {ENGINE_ARCHIVE_ROOT}/run")
        if ENGINE_DIR.exists():
            shutil.rmtree(ENGINE_DIR)
        shutil.move(str(extracted_root), str(ENGINE_DIR))
    ENGINE_BIN.chmod(0o755)
    log(f"engine installed at {ENGINE_BIN}")


# --- engine process --------------------------------------------------------


def is_engine_alive(timeout: float = 1.0) -> bool:
    try:
        r = httpx.get(f"{ENGINE_BASE_URL}/version", timeout=timeout)
        return r.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


def ensure_engine_running(boot_timeout: float = 60.0) -> None:
    if is_engine_alive():
        return
    log("starting TTS engine...")
    log_fh = ENGINE_LOG.open("ab")
    cmd = [
        str(ENGINE_BIN),
        "--host",
        ENGINE_HOST,
        "--port",
        str(ENGINE_PORT),
        "--cpu_num_threads",
        str(ENGINE_CPU_THREADS),
    ]
    # Boost the engine's scheduling priority on macOS so CPU pressure from
    # other busy processes doesn't perturb its inference threads. taskpolicy
    # ships with macOS and doesn't need sudo. -t 0 / -l 0 set the highest
    # throughput / latency tiers for the process.
    taskpolicy = shutil.which("taskpolicy")
    if taskpolicy:
        cmd = [taskpolicy, "-t", "0", "-l", "0", *cmd]
    # Detach from this process so the engine outlives the SessionStart hook.
    # `cwd` is the engine dir so the engine resolves its bundled files.
    proc = subprocess.Popen(
        cmd,
        cwd=ENGINE_DIR,
        stdout=log_fh,
        stderr=log_fh,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    ENGINE_PID.write_text(str(proc.pid))
    deadline = time.monotonic() + boot_timeout
    while time.monotonic() < deadline:
        if is_engine_alive(timeout=0.5):
            log(f"engine ready (pid={proc.pid})")
            return
        if proc.poll() is not None:
            raise RuntimeError(
                f"engine exited early (code={proc.returncode}); see {ENGINE_LOG}"
            )
        time.sleep(0.5)
    # Boot timed out — leave the process running, the next SessionStart will
    # probe /version again. Bail loudly so the hook log shows the issue.
    raise TimeoutError(
        f"engine did not respond within {boot_timeout}s; check {ENGINE_LOG}"
    )


# --- entrypoint ------------------------------------------------------------


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        # Concurrent SessionStarts each run this script; serialize them so
        # only one downloads / migrates / spawns, and the rest find the
        # engine ready once they get the lock.
        with SETUP_LOCK.open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            migrate_legacy_engine()
            ensure_engine_binary()
            ensure_engine_running()
    except Exception as e:
        log(f"setup failed: {e!r}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
