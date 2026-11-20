"""Warming the selected-document model when a file is picked; no real Ollama."""
from io import BytesIO
import json
import threading
from types import SimpleNamespace
from unittest.mock import patch

from rat.engine.assistant_runtime import AssistantRuntime
from rat.engine.selected_document_qa import MODEL
from rat.engine.slm import NUM_CTX, SLMEngine

# conftest replaces warm_up in every test so no test loads a real model; keep the real one here.
REAL_WARM_UP = SLMEngine.warm_up


def test_warm_up_loads_without_a_prompt_at_the_answer_context_size():
    reply = {'model': 'fixture', 'done': True, 'done_reason': 'load'}
    with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(reply).encode())) as urlopen:
        result = REAL_WARM_UP(SLMEngine(model='fixture'))
    request = urlopen.call_args.args[0]
    body = json.loads(request.data)
    assert request.full_url.endswith('/api/chat')
    # A different num_ctx would make Ollama load the model again on the first real question.
    assert body == {'model': 'fixture', 'messages': [], 'stream': False, 'options': {'num_ctx': NUM_CTX}}
    assert result['error'] is None and result['duration_ms'] >= 0


def test_warm_up_failure_is_returned_not_raised():
    with patch('urllib.request.urlopen', side_effect=ConnectionRefusedError('fixture offline')):
        result = REAL_WARM_UP(SLMEngine())
    assert 'fixture offline' in result['error']


def test_runtime_warms_the_answer_model_once_while_a_warm_up_runs(monkeypatch):
    entered, release, models = threading.Event(), threading.Event(), []

    def blocked(self, timeout=60.0):
        models.append(self.model)
        entered.set()
        assert release.wait(3)
        return {'error': None, 'duration_ms': 1.0}

    monkeypatch.setattr(SLMEngine, 'warm_up', blocked)
    with AssistantRuntime(active_tool_packs=[]) as runtime:
        first = runtime.warm_selected_document_model()
        assert entered.wait(2)
        assert not first.done(), 'Picking a file must not wait for the model to load'
        assert runtime.warm_selected_document_model() is first
        release.set()
        assert first.result(timeout=3)['error'] is None
        second = runtime.warm_selected_document_model()
        assert second is not first
        second.result(timeout=3)
    assert models == [MODEL, MODEL]


def test_runtime_does_not_warm_without_a_live_local_model(monkeypatch):
    calls = []
    monkeypatch.setattr(SLMEngine, 'warm_up', lambda self, timeout=60.0: calls.append(self.model))
    with AssistantRuntime(active_tool_packs=[], use_live_model=False) as runtime:
        assert runtime.warm_selected_document_model() is None
    remote = SimpleNamespace(ollama_url='http://example.invalid:11434')
    with AssistantRuntime(active_tool_packs=[], model_client=remote) as runtime:
        assert runtime.warm_selected_document_model() is None
    assert calls == []
