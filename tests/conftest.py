"""Keep every test away from the real ~/.rat state, whose index holds a person's files, and from a real model."""
import atexit
import os
import shutil
import tempfile

import pytest

_state = tempfile.mkdtemp(prefix="rat_tests_")
atexit.register(shutil.rmtree, _state, ignore_errors=True)
os.environ.setdefault("RAT_STATE_DIR", _state)


@pytest.fixture(autouse=True)
def _assistant_stays_on_the_patchable_engine(monkeypatch):
    """A developer's installed Ollama models must not route the assistant around tests that patch `slm_engine`."""
    from rat.engine.slm import slm_engine
    monkeypatch.setattr(slm_engine, "list_installed_models", lambda: [])


@pytest.fixture(autouse=True)
def _picking_a_file_does_not_load_a_real_model(monkeypatch):
    """Selecting a file warms the answer model; tests must not make a developer's Ollama load it."""
    from rat.engine.slm import SLMEngine
    monkeypatch.setattr(SLMEngine, "warm_up",
                        lambda self, timeout=60.0: {"error": "tests_do_not_warm", "duration_ms": 0.0})
