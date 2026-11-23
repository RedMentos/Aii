import hashlib
import queue
import threading
from types import SimpleNamespace

from v13 import broker, output_policy, transaction
from v13.contracts import validate
from v13.fast_greeting import match
from v13.runtime import Runtime


def test_exact_greeting_allowlist_and_fallthrough():
    assert match("Hi!")["reply"] == "Hi."
    assert match("  HALLO… ")["reply"] == "Hallo."
    assert match("Guten Morgen.")["reply"] == "Guten Morgen."
    assert match("hi there") is None
    assert match("hi, can you calculate 2+2?") is None
    assert match("hello world") is None
    assert match("") is None
    assert match(None) is None


class _Store:
    def __init__(self, text="hi"):
        self.text = text
        self.packets = []
        self.output = None
        self.finished = None
        self.logs = []

    def read_source(self, _ref):
        return self.text

    def message(self, _session, _event_id, _role):
        return "assistant-message"

    def source(self, text, _kind):
        return {
            "source_id": "src-" + hashlib.sha256(text.encode()).hexdigest()[:12],
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "char_start": 0,
            "char_end": len(text),
            "modality": "text",
        }

    def add_packet(self, kind, value):
        validate(kind, value)
        self.packets.append((kind, value))
        return value

    def append_message(self, _message_id, text):
        self.output = text

    def finish_message(self, message_id, status, metadata):
        self.finished = (message_id, status, dict(metadata))

    def log(self, event, event_id, detail):
        self.logs.append((event, event_id, detail))


class _Executive:
    def __init__(self):
        self.updated = []

    def snapshot(self, _event, _session):
        return {"packet_id": "snapshot-1"}

    def update(self, event, session, *, status):
        self.updated.append((event["event_id"], session, status))


def _runtime_for_fastpath(text):
    runtime = Runtime.__new__(Runtime)
    runtime.store = _Store(text)
    runtime.executive = _Executive()
    runtime.bodies = SimpleNamespace(begin_turn=lambda _event_id: None)
    runtime.session = "session-1"
    runtime.cfg = {"deadline_seconds": 30}
    runtime.notice_messages = []
    runtime.notice = runtime.notice_messages.append
    runtime.turn_event = None
    return runtime


def test_runtime_persists_source_only_greeting_without_loading_native_organs(monkeypatch):
    runtime = _runtime_for_fastpath("hi!")
    broker_calls = []
    monkeypatch.setattr(output_policy, "match", lambda _store, _text: None)
    monkeypatch.setattr(
        transaction,
        "commit_output",
        lambda _store, _mid, _eid, meta: meta.update(output_committed=True) or True,
    )
    monkeypatch.setattr(transaction, "settle_turn", lambda *_args: None)
    monkeypatch.setattr(
        broker.Broker,
        "finalize",
        lambda _self, event, mid, meta, status, output, **kwargs: (
            broker_calls.append((event["event_id"], mid, status, output, kwargs))
            or {"egress_ok": True}
        ),
    )
    event = {
        "event_id": "event-1",
        "brain_generation_id": "generation-1",
        "source_ref": {
            "source_id": "user-source",
            "sha256": "a" * 64,
            "char_start": 0,
            "char_end": 3,
            "modality": "text",
        },
    }

    result = Runtime._turn(runtime, event)

    assert result == {"skip_online_world_update": True, "fastpath": "EXACT_GREETING_ACK"}
    assert runtime.store.output == "Hi."
    assert runtime.store.finished is not None
    _mid, status, metadata = runtime.store.finished
    assert status == "FINAL"
    assert metadata["model_generated"] is False
    assert metadata["output_authority"] == "APPROVED_FIXED_RULE"
    assert metadata["fastpath"]["kind"] == "EXACT_GREETING_ACK"
    assert metadata["fastpath"]["normalized_input"] == "hi"
    assert metadata["skip_online_world_update"] is True
    assert metadata["first_output_monotonic_ns"] is not None
    assert "B1_DETAIL" in metadata["skipped_native_stages"]
    assert "B2_GIST" in metadata["skipped_native_stages"]
    assert "C3_LANGUAGE" in metadata["skipped_native_stages"]
    policy = [value for kind, value in runtime.store.packets if kind == "OutputPolicyDecision"]
    assert len(policy) == 1
    assert policy[0]["rule_id"] == "BUILTIN_GREETING_ACK_V1"
    assert policy[0]["model_generated"] is False
    assert broker_calls and broker_calls[0][2:4] == ("FINAL", "Hi.")
    assert broker_calls[0][4]["direct"] is True
    assert runtime.executive.updated == [("event-1", "session-1", "FINAL")]


class _WorkerStore:
    def __init__(self, stop):
        self.stop = stop

    def one(self, sql, _params):
        if "SELECT session_id FROM events" in sql:
            return {"session_id": "session-1"}
        if "SELECT * FROM messages" in sql:
            return {"status": "FINAL", "text": "Hi.", "metadata": "{}"}
        raise AssertionError(sql)

    def claim_turn(self, _event_id):
        return True

    def finish_turn(self, _event_id, _status):
        self.stop.set()

    def log(self, *_args):
        pass


def _run_worker_with_turn_result(result):
    stop = threading.Event()
    runtime = Runtime.__new__(Runtime)
    runtime.stop = stop
    runtime.paused = False
    runtime.lock = threading.RLock()
    runtime.jobs = queue.Queue()
    runtime.jobs.put(("turn", {"event_id": "event-1"}, 0, 0.0))
    runtime.queued_bytes = 0
    runtime.current = None
    runtime.cancel_event = threading.Event()
    runtime.status = "Bereit"
    runtime._session_local = threading.local()
    runtime.cfg = {"queue_ttl_seconds": 30}
    runtime.store = _WorkerStore(stop)
    runtime._turn = lambda _payload: result
    updates = []
    runtime.online_world_update = lambda limit: updates.append(limit)
    runtime.turn_event = None
    Runtime._worker(runtime)
    return updates


def test_worker_skips_learning_scan_for_no_action_greeting_but_keeps_normal_turn_learning():
    assert _run_worker_with_turn_result({"skip_online_world_update": True}) == []
    assert _run_worker_with_turn_result(None) == [64]
