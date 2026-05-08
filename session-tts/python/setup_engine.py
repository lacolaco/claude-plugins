"""Bootstrap the local TTS engine and required voice models.

Idempotent: every step checks state first and skips if already done.
Designed to run on every SessionStart so the engine is always available;
typical re-runs do nothing but a port probe.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

# --- configuration ---------------------------------------------------------

ENGINE_VERSION = "1.2.0"
ENGINE_ASSET = (
    f"https://github.com/Aivis-Project/AivisSpeech-Engine/releases/download/"
    f"{ENGINE_VERSION}/AivisSpeech-Engine-macOS-arm64-{ENGINE_VERSION}.7z.001"
)
ENGINE_HOST = "127.0.0.1"
ENGINE_PORT = 10101

# Voice UUIDs and the engine-side style_id of each voice's "ノーマル" style.
# Order matters: it defines the rotation order for new sessions.
VOICES = [
    {"uuid": "a59cb814-0083-4369-8542-f51a29e72af7", "name": "まお", "style_id": 888753760},
    {"uuid": "e9339137-2ae3-4d41-9394-fb757a7e61e6", "name": "まい", "style_id": 1431611904},
    {"uuid": "4f281e78-eba6-495a-8e50-5c322d02b5b1", "name": "るな", "style_id": 345585728},
]

DATA_DIR = Path(os.path.expanduser("~/.claude/session-tts"))
ENGINE_DIR = DATA_DIR / "engine"
ENGINE_BIN = ENGINE_DIR / "run"
ENGINE_PID = DATA_DIR / "engine.pid"
ENGINE_LOG = DATA_DIR / "engine.log"

VOICE_LIST = DATA_DIR / "voices.json"

ENGINE_BASE_URL = f"http://{ENGINE_HOST}:{ENGINE_PORT}"


def log(msg: str) -> None:
    print(f"[session-tts/setup] {msg}", flush=True)


# --- engine binary ---------------------------------------------------------


def ensure_engine_binary() -> None:
    if ENGINE_BIN.exists() and os.access(ENGINE_BIN, os.X_OK):
        return
    log(f"downloading TTS engine v{ENGINE_VERSION}...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "engine.7z"
        with httpx.stream("GET", ENGINE_ASSET, follow_redirects=True, timeout=300.0) as r:
            r.raise_for_status()
            with archive.open("wb") as f:
                for chunk in r.iter_bytes(1 << 16):
                    f.write(chunk)
        log("extracting engine archive...")
        # Lazy import — py7zr pulls a few transitive deps we'd rather not
        # load when the binary is already in place.
        import py7zr  # type: ignore

        with py7zr.SevenZipFile(archive, "r") as z:
            z.extractall(path=tmp)
        # The archive contains a top-level "macOS-arm64/" dir; move its
        # contents into ENGINE_DIR so ENGINE_BIN points at the run script.
        extracted_root = Path(tmp) / "macOS-arm64"
        if not extracted_root.exists():
            # Fallback: pick the first directory inside tmp that is not the archive.
            candidates = [p for p in Path(tmp).iterdir() if p.is_dir()]
            if not candidates:
                raise RuntimeError("engine archive layout unexpected")
            extracted_root = candidates[0]
        if ENGINE_DIR.exists():
            shutil.rmtree(ENGINE_DIR)
        shutil.move(str(extracted_root), str(ENGINE_DIR))
    if not ENGINE_BIN.exists():
        raise RuntimeError(f"engine binary not found at {ENGINE_BIN} after extract")
    ENGINE_BIN.chmod(0o755)
    log(f"engine installed at {ENGINE_BIN}")


# --- engine process --------------------------------------------------------


def is_engine_alive(timeout: float = 1.0) -> bool:
    try:
        r = httpx.get(f"{ENGINE_BASE_URL}/version", timeout=timeout)
        return r.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


def ensure_engine_running(boot_timeout: float = 30.0) -> None:
    if is_engine_alive():
        return
    log("starting TTS engine...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_fh = ENGINE_LOG.open("ab")
    # Detach from this process so the engine outlives the SessionStart hook.
    proc = subprocess.Popen(
        [
            str(ENGINE_BIN),
            "--host",
            ENGINE_HOST,
            "--port",
            str(ENGINE_PORT),
            "--no-use_gpu",
            "--output_log_utf8",
            "--disable_sentry",
        ],
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


# --- voice models ----------------------------------------------------------


def installed_model_uuids(client: httpx.Client) -> set[str]:
    r = client.get("/aivm_models")
    r.raise_for_status()
    data = r.json()
    # /aivm_models returns {uuid: {...}, uuid2: {...}}
    if isinstance(data, dict):
        return set(data.keys())
    if isinstance(data, list):
        return {m.get("aivm_model_uuid") for m in data if m.get("aivm_model_uuid")}
    return set()


def install_model(client: httpx.Client, uuid: str) -> None:
    download_url = (
        f"https://api.aivis-project.com/v1/aivm-models/{uuid}/download?model_type=AIVMX"
    )
    r = client.post("/aivm_models/install", data={"url": download_url}, timeout=120.0)
    r.raise_for_status()


def ensure_voices() -> None:
    with httpx.Client(base_url=ENGINE_BASE_URL, timeout=30.0) as client:
        already = installed_model_uuids(client)
        missing = [v for v in VOICES if v["uuid"] not in already]
        if not missing:
            return
        for v in missing:
            log(f"installing voice: {v['name']}")
            install_model(client, v["uuid"])


# --- entrypoint ------------------------------------------------------------


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        ensure_engine_binary()
        ensure_engine_running()
        ensure_voices()
    except Exception as e:
        log(f"setup failed: {e!r}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
