import ast
import json
import queue
import struct
import threading

import pytest

from v13.audio_perception_bridge import consume_pcm16_window
from v13.cognition import Cognition
from v13.runtime import Runtime, _validate_audio_window
from v13.store import Store


def _window(consent_check):
    return {
        "pcm16": struct.pack("<160h", *([1000] * 160)),
        "sample_rate": 16000,
        "start_ms": 0,
        "source_id": "mic-test-1",
        "consent_receipt": "opaque-local-receipt",
        "consent_check": consent_check,
    }


def _store(tmp_path):
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session("audio consumer")
    event = store.event(session, "spoken with text")
    return store, event, home


def test_audio_window_is_bounded_and_requires_live_consent_provider():
    valid = _window(lambda source_id, receipt: True)
    assert _validate_audio_window(valid)["pcm16"] == valid["pcm16"]

    for invalid in (
        valid | {"sample_rate": True},
        valid | {"pcm16": b"\x00"},
        valid | {"pcm16": b"\x00\x00" * 16001},
        valid | {"consent_check": None},
        valid | {"unexpected": "field"},
    ):
        with pytest.raises(ValueError):
            _validate_audio_window(invalid)


def test_submit_keeps_pcm_process_local_and_counts_it_against_queue_bytes(monkeypatch):
    class FakeStore:
        accepted = False

        def accept_turn(self, *args):
            self.accepted = True
            event = {
                "event_id": "event-audio-1",
                "brain_generation_id": "generation-1",
                "source_ref": {"source_id": "text-1", "sha256": "a" * 64,
                               "char_start": 0, "char_end": 5, "modality": "text"},
            }
            self.persisted_event = dict(event)
            return event

    runtime = Runtime.__new__(Runtime)
    runtime._session_local = threading.local()
    runtime.session = "session-1"
    runtime.cfg = {"input_bytes": 65536, "queue_count": 16, "queue_bytes": 262144}
    runtime.lock = threading.RLock()
    runtime.stop = threading.Event()
    runtime.current = None
    runtime.jobs = queue.Queue(maxsize=16)
    runtime.queued_bytes = 0
    runtime.store = FakeStore()
    runtime.cancel_event = threading.Event()
    runtime.wake = threading.Event()
    runtime.notice = lambda _message: None
    monkeypatch.setattr("v13.runtime.duplex.on_input", lambda *_args: None)
    monkeypatch.setattr("v13.runtime.duplex.record", lambda *_args: None)

    window = _window(lambda source_id, receipt: True)
    event_id = runtime.submit("hello", audio_window=window)
    kind, payload, queued_bytes, _queued_at = runtime.jobs.get_nowait()

    assert event_id == "event-audio-1"
    assert kind == "turn"
    assert payload["_audio_window"]["pcm16"] == window["pcm16"]
    assert queued_bytes == len(b"hello") + len(window["pcm16"])
    assert "_audio_window" not in runtime.store.persisted_event


def test_real_store_audio_packet_becomes_source_bound_body_and_c3_context(tmp_path):
    store, event, home = _store(tmp_path)
    runtime = Runtime.__new__(Runtime)
    runtime.store = store
    calls = []

    def consent(source_id, receipt):
        calls.append((source_id, receipt))
        return True

    window = _validate_audio_window(_window(consent))
    result = consume_pcm16_window(
        runtime, window["pcm16"], sample_rate=window["sample_rate"],
        start_ms=window["start_ms"], event_id=event["event_id"],
        generation_id=store.generation_id, source_id=window["source_id"],
        consent_receipt=window["consent_receipt"],
        consent_check=window["consent_check"], token_budget=512,
    )
    context = runtime._audio_context_record(event["event_id"], result, window)
    assert context is not None

    body_view = runtime._audio_context_view(event["event_id"], consumer="B1_DETAIL")
    assert body_view is not None
    cognition = Cognition.__new__(Cognition)
    cognition.r = runtime
    body_query, body_refs = cognition._audio_context_query(
        {"event_id": event["event_id"]}, "B1_DETAIL"
    )
    assert body_query == body_view
    assert body_refs == [context["summary_source_ref"]]

    layer, summary_ref = runtime._audio_prompt_layer(event["event_id"])
    assert layer[0] == "RAW_EAR_ACOUSTIC"
    assert summary_ref == context["summary_source_ref"]
    prompt_body = layer[2]
    assert prompt_body["authority"] == "ACOUSTIC_FEATURES_ONLY"
    assert prompt_body["transcript"] is None
    assert prompt_body["learning_authority"] is False
    assert prompt_body["action_authority"] is False
    assert "pcm16" not in json.dumps(prompt_body).lower()
    assert "consent_receipt_ref" not in json.dumps(prompt_body)

    saved = store.read_source(summary_ref)
    decoded = json.loads(saved)
    assert decoded == context["body"]
    assert decoded["audio_packet_id"] == result["packet"]["packet_id"]
    assert decoded["audio_source_ref"]["sha256"] == result["packet"]["source_ref"]["sha256"]
    assert len(calls) >= 7  # bridge, record, B1, and C3 each recheck current consent
    packet_rows = store.rows("SELECT payload FROM packets WHERE kind='PerceptPacket'")
    assert len(packet_rows) == 1
    assert window["pcm16"].hex() not in packet_rows[0]["payload"]
    blobs = list((home / "data" / "blobs").iterdir())
    assert all(blob.read_bytes() != window["pcm16"] for blob in blobs)
    store.close()


def test_c3_layer_is_omitted_when_consent_is_revoked_before_prompt_assembly(tmp_path):
    store, event, _home = _store(tmp_path)
    runtime = Runtime.__new__(Runtime)
    runtime.store = store
    calls = []

    def revoke_on_c3(source_id, receipt):
        calls.append((source_id, receipt))
        return len(calls) <= 5

    window = _validate_audio_window(_window(revoke_on_c3))
    result = consume_pcm16_window(
        runtime, window["pcm16"], sample_rate=window["sample_rate"],
        start_ms=window["start_ms"], event_id=event["event_id"],
        generation_id=store.generation_id, source_id=window["source_id"],
        consent_receipt=window["consent_receipt"],
        consent_check=window["consent_check"], token_budget=512,
    )
    context = runtime._audio_context_record(event["event_id"], result, window)
    assert context is not None
    layer, summary_ref = runtime._audio_prompt_layer(event["event_id"])

    assert len(calls) == 6
    assert layer is None
    assert summary_ref is None
    assert store.rows("SELECT id FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT'") != []
    store.close()


def test_body_offer_and_c3_use_the_same_audio_context_with_separate_provenance():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    runtime_source = (root / "v13" / "runtime.py").read_text(encoding="utf-8")
    cognition_source = (root / "v13" / "cognition.py").read_text(encoding="utf-8")
    runtime_tree = ast.parse(runtime_source)
    cognition_tree = ast.parse(cognition_source)
    turn = next(node for node in ast.walk(runtime_tree)
                if isinstance(node, ast.FunctionDef) and node.name == "_turn")
    offer = next(node for node in ast.walk(cognition_tree)
                 if isinstance(node, ast.FunctionDef) and node.name == "offer")
    calls = {node.func.attr for node in ast.walk(turn)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    offer_calls = {node.func.attr for node in ast.walk(offer)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert "_audio_context_record" in calls
    assert "_audio_prompt_layer" in calls
    assert "_audio_context_query" in offer_calls
    assert "audio_context_refs=audio_context_refs" in cognition_source
    assert "audio_context_refs=query_packet.get('audio_context_refs',[])" in cognition_source
    assert "query.get('audio_context_refs',[])!=offer.get('audio_context_refs',[])" in cognition_source
    assert "volatile.append(audio_layer)" in runtime_source
    assert "provenance=[e['source_ref']]+([audio_source_ref] if audio_source_ref else [])" in runtime_source
