"""Regression: SSE metadata frames must not synchronously re-sample /proc.

Linux synthetic transport only; not native llama-server or Redmi evidence.
"""
import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

from v13.runners import LlamaRunner


class _Response:
    status = 200

    def __init__(self, events):
        self.lines = iter([b"data: " + json.dumps(event).encode() + b"\n" for event in events])

    def readline(self):
        return next(self.lines, b"")


class _Connection:
    events = []

    def __init__(self, *args, **kwargs):
        pass

    def request(self, *args, **kwargs):
        pass

    def getresponse(self):
        return _Response(self.events)

    def close(self):
        pass


def test_zero_token_metadata_does_not_trigger_repeated_sync_procfs(monkeypatch):
    runner = object.__new__(LlamaRunner)
    runner.purpose = "generate"
    runner.role = "C3_LANGUAGE"
    runner.cfg = {"answer_tokens": 32, "temperature": 0.1}
    runner.model = SimpleNamespace(name="synthetic")
    runner.key = "test-only"
    runner.port = 1
    runner.proc = SimpleNamespace(pid=123, poll=lambda: None)
    runner._audit_enabled = False
    runner._audit_begin_window = lambda **kwargs: None
    runner._prompt = lambda *args: ("synthetic", 4, False)
    runner.load = lambda *args: None
    runner.last_metrics = {}
    runner.stage_times = {}
    runner.phase = "load"
    runner.phase_started = time.monotonic()
    # Many metadata frames before and after exactly one token batch.
    _Connection.events = ([{"content": "", "tokens": []}] * 100
                          + [{"content": "ok", "tokens": list(range(16))}]
                          + [{"content": "", "tokens": []}] * 100
                          + [{"stop": True, "tokens": []}])
    reads = []
    def memory(pid):
        reads.append(pid)
        return {"rss_bytes": 1024}
    monkeypatch.setattr("v13.runners.http.client.HTTPConnection", _Connection)
    monkeypatch.setattr("v13.runners.process_memory", memory)
    monkeypatch.setattr("v13.runners.native_sampling_policy", lambda *args: {})
    output = list(runner._generate([{"role": "user", "content": "hi"}],
                                   threading.Event(), time.monotonic() + 5))
    assert output == ["ok"]
    assert runner.last_metrics["generated_tokens"] == 16
    # One synchronous batch sample plus final resource snapshot; metadata
    # frames must not produce 200 redundant procfs reads.
    assert reads == [123, 123]
