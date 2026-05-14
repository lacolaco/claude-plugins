"""Shared fixtures for say-response.py unit tests.

The runtime entry point is `session-tts/scripts/say-response.py`. The hyphen
in the filename prevents `import say-response`, so we load it through
`importlib` once per test session and expose the module as a fixture.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "say-response.py"


@pytest.fixture(scope="session")
def say_response() -> ModuleType:
    spec = importlib.util.spec_from_file_location("say_response", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
