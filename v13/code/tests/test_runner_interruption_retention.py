"""Fail-closed warm retention after an interrupted llama-server request."""
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from v13 import runners
from v13.common import Cancelled, Limits


class AliveProcess:
    def __init__(self):
        self.pid = 4321
        self.alive = True

    def poll(self):
        return None if self.alive else 1


def make_runner(tmp_path, monkeypatch):
    runner = runners.LlamaRunner(
        tmp_path,
        "C3_LANGUAGE",
        SimpleNamespace(name="fixture-model"),
        {"answer_tokens": 8},
        purpose="generate",
    )
    runner.proc = AliveProcess()
    runner._loaded_stamp = "fixture-stamp"
    runner._lifecycle_stamp = lambda: "fixture-stamp"
    runner.unload = Mock(return_value={"process_reaped": True})
    monkeypatch.setattr(
        runners,
        "process_memory",
        lambda pid: {"rss_bytes": 1024, "pss_bytes": 512},
    )
    return runner


def interrupt(runner, exc, deadline):
    def fail(*args, **kwargs):
        raise exc
        yield  # pragma: no cover - makes this a generator for yield-from

    runner._generate = fail
    with pytest.raises(type(exc)):
        list(runner.generate([], threading.Event(), deadline))


def test_deadline_retains_only_when_every_server_slot_is_idle(tmp_path, monkeypatch):
    runner = make_runner(tmp_path, monkeypatch)
    calls = []

    def idle_slots(method, path, payload, deadline, timeout_cap=3.0):
        calls.append((method, path))
        # The endpoint can include prompt text; the runtime must not persist it.
        return [{"is_processing": False, "prompt": "PRIVATE_DO_NOT_STORE"}]

    runner._json = idle_slots
    interrupt(runner, Limits("deadline"), time.monotonic() - 0.01)

    decision = runner.last_metrics["interruption_unload"]
    assert calls == [("GET", "/slots")]
    assert decision == {
        "process_reaped": False,
        "retained_warm": True,
        "reason": "SERVER_IDLE",
    }
    assert runner.unload.call_count == 0
    assert runner.last_metrics["warm_process_retained"] is True
    assert "PRIVATE_DO_NOT_STORE" not in repr(runner.last_metrics)


def test_deadline_unloads_when_server_keeps_processing(tmp_path, monkeypatch):
    runner = make_runner(tmp_path, monkeypatch)
    runner._json = lambda method, path, payload, deadline, timeout_cap=3.0: [
        {"is_processing": True}
    ]

    interrupt(runner, Limits("deadline"), time.monotonic() - 0.01)

    assert runner.unload.call_count == 1
    assert runner.last_metrics["interruption_unload"]["process_reaped"] is True
    assert runner.last_metrics["warm_process_retained"] is False


def test_deadline_unloads_when_slots_endpoint_is_unavailable_or_malformed(
    tmp_path, monkeypatch
):
    runner = make_runner(tmp_path, monkeypatch)
    runner._json = Mock(side_effect=RuntimeError("slots endpoint unavailable"))
    interrupt(runner, Limits("deadline"), time.monotonic() - 0.01)
    assert runner.unload.call_count == 1
    assert runner.last_metrics["warm_process_retained"] is False

    malformed = make_runner(tmp_path, monkeypatch)
    malformed._json = lambda method, path, payload, deadline, timeout_cap=3.0: [
        {"is_processing": "false", "prompt": "PRIVATE_DO_NOT_STORE"}
    ]
    interrupt(malformed, Limits("deadline"), time.monotonic() - 0.01)
    assert malformed.unload.call_count == 1
    assert "PRIVATE_DO_NOT_STORE" not in repr(malformed.last_metrics)


def test_user_cancel_and_native_error_still_unload_immediately(tmp_path, monkeypatch):
    cancelled = make_runner(tmp_path, monkeypatch)
    cancelled._json = Mock(side_effect=AssertionError("must not probe after user stop"))
    interrupt(cancelled, Cancelled("user stop"), time.monotonic() + 10)
    assert cancelled.unload.call_count == 1
    cancelled._json.assert_not_called()

    failed = make_runner(tmp_path, monkeypatch)
    failed._json = Mock(side_effect=AssertionError("must not probe after native error"))
    interrupt(failed, RuntimeError("native failure"), time.monotonic() + 10)
    assert failed.unload.call_count == 1
    failed._json.assert_not_called()


def test_deadline_unloads_when_model_lifecycle_changed(tmp_path, monkeypatch):
    runner = make_runner(tmp_path, monkeypatch)
    runner._lifecycle_stamp = lambda: "changed"
    runner._json = Mock(return_value=[{"is_processing": False}])

    interrupt(runner, Limits("deadline"), time.monotonic() - 0.01)

    assert runner.unload.call_count == 1
    runner._json.assert_not_called()
    assert runner.last_metrics["warm_process_retained"] is False



def test_retained_c3_runner_is_reused_by_pool_on_the_next_turn(tmp_path, monkeypatch):
    model_path = tmp_path / "models" / "c3.gguf"
    models = SimpleNamespace(path_for=lambda role: model_path)
    pool = runners.RunnerPool(
        tmp_path, models, {"answer_tokens": 8, "temperature": 0.1}
    )
    runner = pool.get("C3_LANGUAGE")
    runner.proc = AliveProcess()
    runner._loaded_stamp = "fixture-stamp"
    runner._lifecycle_stamp = lambda: "fixture-stamp"
    runner.unload = Mock(return_value={"process_reaped": True})
    monkeypatch.setattr(
        runners,
        "process_memory",
        lambda pid: {"rss_bytes": 1024, "pss_bytes": 512},
    )

    slot_reads = []

    def idle_slots(method, path, payload, deadline, timeout_cap=3.0):
        slot_reads.append((method, path))
        return [{"is_processing": False, "prompt": "PRIVATE_DO_NOT_STORE"}]

    runner._json = idle_slots
    generation_calls = 0

    def interrupted_then_warm(messages, cancel, deadline, *args, **kwargs):
        nonlocal generation_calls
        generation_calls += 1
        if generation_calls == 1:
            raise Limits("deadline")
        runner.load(cancel, deadline)
        yield "warm"

    runner._generate = interrupted_then_warm
    pid_before = runner.proc.pid

    with pytest.raises(Limits):
        list(runner.generate([], threading.Event(), time.monotonic() - 0.01))

    first_metrics = dict(runner.last_metrics)
    assert first_metrics["status"] == "DEADLINE"
    assert first_metrics["warm_process_retained"] is True
    assert first_metrics["interruption_unload"]["reason"] == "SERVER_IDLE"
    assert slot_reads == [("GET", "/slots")]
    assert runner.unload.call_count == 0
    assert runner.proc.pid == pid_before

    # The real Runtime asks RunnerPool for the same C3 role on the next turn.
    reused = pool.get("C3_LANGUAGE")
    assert reused is runner
    assert reused.proc.pid == pid_before
    assert list(reused.generate([], threading.Event(), time.monotonic() + 5)) == ["warm"]
    assert generation_calls == 2
    assert reused.proc.pid == pid_before
    assert reused.unload.call_count == 0
    assert "PRIVATE_DO_NOT_STORE" not in repr(first_metrics)
