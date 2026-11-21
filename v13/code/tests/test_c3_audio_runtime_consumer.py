import ast
import math
import time
import json
import queue
import struct
import threading
from contextlib import contextmanager

import pytest

from v13.audio_voice_cues import consume_pcm16_voice_window
from v13.cognition import Cognition
from v13.runtime import Runtime, _validate_audio_window
import v13.runtime as runtime_module
from v13.store import Store
from v13.operator import Operator
from unittest.mock import Mock


def _tone(frequency=140, sample_rate=16000, seconds=1.0, amplitude=6000):
    count = int(sample_rate * seconds)
    samples = [int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
               for i in range(count)]
    return struct.pack("<" + "h" * count, *samples)


_CONSENT_LOCK = threading.RLock()


def _consent_guard(source_id, receipt):
    @contextmanager
    def lease():
        with _CONSENT_LOCK:
            yield True
    return lease()


def _window(consent_check, finality="FINAL"):
    return {
        "pcm16": _tone(),
        "sample_rate": 16000,
        "start_ms": 0,
        "source_id": "mic-test-1",
        "finality": finality,
        "consent_receipt": "opaque-local-receipt",
        "consent_check": consent_check,
        "consent_guard": _consent_guard,
    }


def _store(tmp_path):
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    store.ensure_generation_snapshot({}, {})
    session = store.new_session("audio consumer")
    event = store.event(session, "spoken with text")
    return store, event, home


def test_audio_window_is_bounded_and_requires_live_consent_provider():
    valid = _window(lambda source_id, receipt: True)
    assert _validate_audio_window(valid)["pcm16"] == valid["pcm16"]

    missing_finality = dict(valid)
    missing_finality.pop("finality")
    missing_guard = dict(valid)
    missing_guard.pop("consent_guard")
    for invalid in (
        missing_finality,
        missing_guard,
        valid | {"finality": "PARTIAL"},
        valid | {"finality": True},
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
    runtime.home = home
    calls = []

    def consent(source_id, receipt):
        calls.append((source_id, receipt))
        return True

    window = _validate_audio_window(_window(consent))
    result = consume_pcm16_voice_window(
        runtime, window["pcm16"], sample_rate=window["sample_rate"],
        start_ms=window["start_ms"], event_id=event["event_id"],
        generation_id=store.generation_id, source_id=window["source_id"],
        consent_receipt=window["consent_receipt"],
        consent_check=window["consent_check"], consent_guard=window["consent_guard"], token_budget=512,
        finality=window["finality"],
    )
    context = runtime._audio_context_record(event["event_id"], result, window)
    assert context is not None
    cues = result["packet"]["segments"][0]["acoustic"]["voice_cues"]
    assert result["a4"]["voice_activity_hint"] == "VOICED"
    assert context["body"]["voice_cues"] == cues

    body_view = runtime._audio_context_view(event["event_id"], consumer="B1_DETAIL")
    assert body_view is not None
    assert body_view["voice_cues"] == cues
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
    assert prompt_body["voice_cues"] == cues
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



def test_provisional_audio_is_observed_by_a4_but_never_promoted_to_body_or_c3(tmp_path):
    from types import SimpleNamespace

    store, event, home = _store(tmp_path)
    runtime = Runtime.__new__(Runtime)
    runtime.store = store
    runtime.home = home
    calls = []

    def consent(source_id, receipt):
        calls.append((source_id, receipt))
        return True

    window = _validate_audio_window(_window(consent, finality="PROVISIONAL"))
    result = consume_pcm16_voice_window(
        runtime, window["pcm16"], sample_rate=window["sample_rate"],
        start_ms=window["start_ms"], event_id=event["event_id"],
        generation_id=store.generation_id, source_id=window["source_id"],
        consent_receipt=window["consent_receipt"],
        consent_check=window["consent_check"], consent_guard=window["consent_guard"], token_budget=512,
        finality=window["finality"],
    )

    assert result["packet"]["segments"][0]["finality"] == "PROVISIONAL"
    assert result["a4"]["finality"] == "PROVISIONAL"
    assert result["c3_admission"].status == "EMPTY_OR_UNAUTHORIZED"
    assert result["c3_admission"].selected == ()
    assert "mic-test-1" in result["c3_admission"].omitted
    assert runtime._audio_context_record(event["event_id"], result, window) is None

    # Even a malformed upstream admission must not promote a provisional packet.
    fake_percept = SimpleNamespace(
        source_id="mic-test-1", modality="audio", start_ms=0, end_ms=10,
        summary="provisional acoustic fixture", priority=1,
    )
    forced = dict(result, c3_admission=SimpleNamespace(status="ADMITTED", selected=(fake_percept,)))
    assert runtime._audio_context_record(event["event_id"], forced, window) is None
    assert runtime._audio_context_view(event["event_id"], consumer="B1_DETAIL") is None
    assert runtime._audio_prompt_layer(event["event_id"]) == (None, None)
    cognition = Cognition.__new__(Cognition)
    cognition.r = runtime
    assert cognition._audio_context_query({"event_id": event["event_id"]}, "B1_DETAIL") == (None, [])
    assert store.rows("SELECT id FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT'") == []
    assert len(calls) >= 4
    store.close()


def test_c3_layer_is_omitted_when_consent_is_revoked_before_prompt_assembly(tmp_path):
    store, event, home = _store(tmp_path)
    runtime = Runtime.__new__(Runtime)
    runtime.store = store
    runtime.home = home
    revoked = False
    calls = []

    def consent(source_id, receipt):
        calls.append((source_id, receipt))
        return not revoked

    window = _validate_audio_window(_window(consent))
    result = consume_pcm16_voice_window(
        runtime, window["pcm16"], sample_rate=window["sample_rate"],
        start_ms=window["start_ms"], event_id=event["event_id"],
        generation_id=store.generation_id, source_id=window["source_id"],
        consent_receipt=window["consent_receipt"],
        consent_check=window["consent_check"], consent_guard=window["consent_guard"],
        token_budget=512, finality=window["finality"],
    )
    context = runtime._audio_context_record(event["event_id"], result, window)
    assert context is not None
    context_ref = context["summary_source_ref"]
    revoked = True
    layer, summary_ref = runtime._audio_prompt_layer(event["event_id"])

    assert len(calls) >= 2
    assert layer is None
    assert summary_ref is None
    assert event["event_id"] not in getattr(runtime, "_audio_contexts", {})
    assert store.rows(
        "SELECT id FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT' AND deleted=0"
    ) == []
    with pytest.raises(ValueError):
        store.read_source(context_ref)
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
    assert "consume_pcm16_voice_window" in runtime_source
    assert "voice_cues=validate_voice_cues" in runtime_source
    assert "query.get('audio_context_refs',[])!=offer.get('audio_context_refs',[])" in cognition_source
    assert "volatile.append(audio_layer)" in runtime_source
    assert "provenance=[e['source_ref']]+meta.get('source_recall_refs',[])+([audio_source_ref] if audio_source_ref else [])" in runtime_source


def test_normal_runtime_turn_delivers_voice_cues_to_b1_b2_and_c3(tmp_path):
    runtime = Runtime(tmp_path)
    try:
        runtime.sleep.cycle.set_policy("enabled", "off")
        runtime.cfg.update(
            deadline_seconds=90,
            observer_seconds=5,
            max_reentry=0,
            observer_mode="background",
            b2_quote_select="off",
            offer_quote_context_chars=0,
            b2_state_slots=0,
        )
        operator = Operator(runtime)
        operator.run(":effort max")
        operator.run(":ctxos active")
        runtime._route = Mock(return_value=("both", {"source": "SYNTHETIC_AUDIO_E2E"}))
        runtime.learner.output_delta = Mock(return_value=None)
        seen = {}

        class Runner:
            def __init__(self, role):
                self.role = role
                self.last_metrics = {
                    "role": role, "status": "FINAL", "generated_tokens": 5,
                    "synthetic": True,
                }

            def generate(self, messages, cancel, deadline, *args, **kwargs):
                seen[self.role] = messages
                if self.role == "B1_DETAIL":
                    yield json.dumps({
                        "summary": "The rent is 120 euros.",
                        "quotes": ["The rent is 120 euros."],
                        "uncertainty": "low", "needs_reentry": False,
                    })
                elif self.role == "B2_GIST":
                    yield json.dumps({
                        "summary": "A long-term reserve is needed.",
                        "quotes": ["The plan preserves a long-term reserve."],
                        "uncertainty": "low", "needs_reentry": False,
                    })
                else:
                    yield "One combined response."

        runners = {
            role: Runner(role)
            for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
        }
        runtime.pool.get = Mock(side_effect=lambda role: runners[role])
        question = (
            "Compare details with planning. The rent is 120 euros. "
            "The plan preserves a long-term reserve."
        )
        window = _window(lambda source_id, receipt: True)
        runtime.submit(question, audio_window=window)

        deadline = time.monotonic() + 30
        while not runtime.idle() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert runtime.idle(), "synthetic audio Runtime turn did not settle"
        answer = runtime.last_answer()
        metadata = json.loads(answer["metadata"])
        assert answer["status"] == "FINAL", {key: metadata.get(key) for key in ("error", "detail", "failure_stage")}
        metadata = json.loads(answer["metadata"])
        assert metadata["audio_input"]["status"] == "A5_A4_C3_VOICE_CUE_ADMISSION"
        assert metadata["audio_input"]["voice_activity_hint"] == "VOICED"
        assert metadata["audio_admission"]["c3_prompt_included"] is True

        for role in ("B1_DETAIL", "B2_GIST"):
            rendered = json.dumps(seen[role], ensure_ascii=False)
            assert "voice_cues" in rendered and "VOICED" in rendered
        c3_rendered = json.dumps(seen["C3_LANGUAGE"], ensure_ascii=False)
        assert "RAW_EAR_ACOUSTIC" in c3_rendered
        assert "voice_cues" in c3_rendered and "VOICED" in c3_rendered
        assert "The rent is 120 euros." in c3_rendered
        assert "A long-term reserve is needed." in c3_rendered
        query_rows = runtime.store.rows("SELECT payload FROM packets WHERE kind='QueryPacket'")
        query_packets = [json.loads(row["payload"]) for row in query_rows]
        audio_queries = [packet for packet in query_packets if packet.get("audio_context_refs")]
        assert {packet["target_role"] for packet in audio_queries} == {"B1_DETAIL", "B2_GIST"}
        for packet in audio_queries:
            persisted = packet.get("audio_context")
            assert isinstance(persisted, dict)
            assert persisted["summary_source_ref"] == packet["audio_context_refs"][0]
            assert persisted["body"]["authority"] == "ACOUSTIC_FEATURES_ONLY"
            encoded = json.dumps(persisted, ensure_ascii=False).lower()
            assert "consent_check" not in encoded and "consent_receipt" not in encoded
            assert "pcm16" not in encoded
        offer_rows = runtime.store.rows("SELECT payload FROM packets WHERE kind='OfferPacket'")
        audio_offers = [json.loads(row["payload"]) for row in offer_rows
                        if json.loads(row["payload"]).get("audio_context_refs")]
        assert {offer["role"] for offer in audio_offers} == {"B1_DETAIL", "B2_GIST"}
        for offer in audio_offers:
            query = next(packet for packet in audio_queries
                         if packet["packet_id"] == offer["query_packet_id"])
            assert offer["audio_context_refs"] == query["audio_context_refs"]
        assert window["pcm16"].hex() not in json.dumps(seen, ensure_ascii=False)

        packet_rows = runtime.store.rows(
            "SELECT payload FROM packets WHERE kind='PerceptPacket'"
        )
        packets = [json.loads(row["payload"]) for row in packet_rows]
        audio_packets = [packet for packet in packets if packet.get("modality") == "audio"]
        text_packets = [packet for packet in packets if packet.get("modality") == "text"]
        # The normal text percept must remain; the audio percept is additive.
        assert len(packets) == 2
        assert len(text_packets) == 1
        assert len(audio_packets) == 1
        raw_pcm_hex = window["pcm16"].hex()
        assert all(raw_pcm_hex not in json.dumps(packet, ensure_ascii=False) for packet in packets)
    finally:
        runtime.close()


def test_c3_native_prompt_rechecks_audio_consent_after_context_save(tmp_path, monkeypatch):
    """Revocation after C3 context persistence must withhold the audio layer before inference."""
    runtime = Runtime(tmp_path)
    revoked = False
    original_save_context = runtime_module.save_context

    def save_context_then_revoke(store, session, event_id, role, messages):
        nonlocal revoked
        result = original_save_context(store, session, event_id, role, messages)
        if role == "C3_LANGUAGE":
            # This is after the exact prompt snapshot was stored but before the
            # Runtime calls runner.generate() for C3.
            revoked = True
        return result

    monkeypatch.setattr(runtime_module, "save_context", save_context_then_revoke)
    try:
        runtime.sleep.cycle.set_policy("enabled", "off")
        runtime.cfg.update(
            deadline_seconds=90,
            observer_seconds=5,
            max_reentry=0,
            observer_mode="background",
            b2_quote_select="off",
            offer_quote_context_chars=0,
            b2_state_slots=0,
        )
        operator = Operator(runtime)
        operator.run(":effort max")
        operator.run(":ctxos active")
        runtime._route = Mock(return_value=("both", {"source": "SYNTHETIC_AUDIO_E2E"}))
        runtime.learner.output_delta = Mock(return_value=None)
        seen = {}

        def consent(source_id, receipt):
            return (
                not revoked
                and source_id == "mic-test-1"
                and receipt == "opaque-local-receipt"
            )

        class Runner:
            def __init__(self, role):
                self.role = role
                self.last_metrics = {
                    "role": role, "status": "FINAL", "generated_tokens": 5,
                    "synthetic": True,
                }

            def generate(self, messages, cancel, deadline, *args, **kwargs):
                seen[self.role] = messages
                if self.role == "B1_DETAIL":
                    yield json.dumps({
                        "summary": "The rent is 120 euros.",
                        "quotes": ["The rent is 120 euros."],
                        "uncertainty": "low", "needs_reentry": False,
                    })
                elif self.role == "B2_GIST":
                    yield json.dumps({
                        "summary": "A long-term reserve is needed.",
                        "quotes": ["The plan preserves a long-term reserve."],
                        "uncertainty": "low", "needs_reentry": False,
                    })
                else:
                    yield "One combined response."

        runners = {
            role: Runner(role)
            for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
        }
        runtime.pool.get = Mock(side_effect=lambda role: runners[role])
        question = (
            "Compare details with planning. The rent is 120 euros. "
            "The plan preserves a long-term reserve."
        )
        runtime.submit(question, audio_window=_window(consent))

        deadline = time.monotonic() + 30
        while not runtime.idle() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert runtime.idle(), "synthetic audio Runtime turn did not settle"
        assert revoked is True

        c3_rendered = json.dumps(seen.get("C3_LANGUAGE", []), ensure_ascii=False)
        assert "RAW_EAR_ACOUSTIC" not in c3_rendered
        last_context = runtime.store.state(
            "LAST_NATIVE_CONTEXT:" + runtime.session, None
        )[0]
        if last_context:
            saved = json.dumps(
                last_context.get("messages") or last_context.get("preview", ""),
                ensure_ascii=False,
            )
            assert "RAW_EAR_ACOUSTIC" not in saved
        assert runtime.store.rows(
            "SELECT id FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT' AND deleted=0"
        ) == []
    finally:
        runtime.close()



def test_audio_context_view_does_not_reenter_non_reentrant_provider_lock(tmp_path):
    """A consumer lease must use its yielded authorization, not reacquire its own lock."""
    store, event, home = _store(tmp_path)
    runtime = Runtime.__new__(Runtime)
    runtime.store = store
    runtime.home = home
    window = _window(lambda source_id, receipt: True)
    try:
        result = consume_pcm16_voice_window(
            runtime, window["pcm16"], sample_rate=window["sample_rate"],
            start_ms=window["start_ms"], event_id=event["event_id"],
            generation_id=store.generation_id, source_id=window["source_id"],
            consent_receipt=window["consent_receipt"],
            consent_check=window["consent_check"],
            consent_guard=window["consent_guard"], finality=window["finality"],
            token_budget=512,
        )
        context = runtime._audio_context_record(event["event_id"], result, window)
        assert context is not None

        lock = threading.Lock()
        state = {"active": True}

        def check(source_id, receipt):
            acquired = lock.acquire(timeout=0.05)
            if not acquired:
                raise RuntimeError("non-reentrant provider lock was reacquired")
            try:
                return (
                    state["active"]
                    and source_id == "mic-test-1"
                    and receipt == "opaque-local-receipt"
                )
            finally:
                lock.release()

        @contextmanager
        def guard(source_id, receipt):
            lock.acquire()
            try:
                yield (
                    state["active"]
                    and source_id == "mic-test-1"
                    and receipt == "opaque-local-receipt"
                )
            finally:
                lock.release()

        # The context store keeps the exact provider functions for later reads.
        context["consent_check"] = check
        context["consent_guard"] = guard
        view = runtime._audio_context_view(event["event_id"], consumer="C3")

        assert view is not None, "consumer re-entered a non-reentrant consent provider"
        assert view["authority"] == "ACOUSTIC_FEATURES_ONLY"
        assert store.rows(
            "SELECT id FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT' AND deleted=0"
        )
    finally:
        store.close()


def test_c3_native_generation_holds_provider_lease_until_stream_completes(tmp_path):
    """Revocation must wait for the complete C3 generate iterator, not just prompt assembly."""
    runtime = Runtime(tmp_path)
    lock = threading.Lock()
    state = {"active": True}
    entered_c3 = threading.Event()
    allow_c3 = threading.Event()
    revoke_started = threading.Event()
    revoke_finished = threading.Event()
    revoker = None

    def consent(source_id, receipt):
        return (
            state["active"]
            and source_id == "mic-test-1"
            and receipt == "opaque-local-receipt"
        )

    @contextmanager
    def guard(source_id, receipt):
        lock.acquire()
        try:
            yield (
                state["active"]
                and source_id == "mic-test-1"
                and receipt == "opaque-local-receipt"
            )
        finally:
            lock.release()

    window = _window(consent)
    window["consent_guard"] = guard
    seen = {}

    class Runner:
        def __init__(self, role):
            self.role = role
            self.last_metrics = {
                "role": role, "status": "FINAL", "generated_tokens": 5,
                "synthetic": True,
            }

        def generate(self, messages, cancel, deadline, *args, **kwargs):
            seen[self.role] = messages
            if self.role == "B1_DETAIL":
                yield json.dumps({
                    "summary": "The rent is 120 euros.",
                    "quotes": ["The rent is 120 euros."],
                    "uncertainty": "low", "needs_reentry": False,
                })
            elif self.role == "B2_GIST":
                yield json.dumps({
                    "summary": "A long-term reserve is needed.",
                    "quotes": ["The plan preserves a long-term reserve."],
                    "uncertainty": "low", "needs_reentry": False,
                })
            else:
                assert state["active"] is True
                entered_c3.set()
                if not allow_c3.wait(5):
                    raise TimeoutError("test did not release the blocked C3 iterator")
                yield "One combined response."

    try:
        runtime.sleep.cycle.set_policy("enabled", "off")
        runtime.cfg.update(
            deadline_seconds=90,
            observer_seconds=5,
            max_reentry=0,
            observer_mode="background",
            b2_quote_select="off",
            offer_quote_context_chars=0,
            b2_state_slots=0,
        )
        operator = Operator(runtime)
        operator.run(":effort max")
        operator.run(":ctxos active")
        runtime._route = Mock(return_value=("both", {"source": "SYNTHETIC_AUDIO_E2E"}))
        runtime.learner.output_delta = Mock(return_value=None)
        runners = {
            role: Runner(role)
            for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
        }
        runtime.pool.get = Mock(side_effect=lambda role: runners[role])
        question = (
            "Compare details with planning. The rent is 120 euros. "
            "The plan preserves a long-term reserve."
        )
        runtime.submit(question, audio_window=window)

        assert entered_c3.wait(30), "normal Runtime turn did not reach C3 generation"

        def revoke():
            revoke_started.set()
            with lock:
                state["active"] = False
            revoke_finished.set()

        revoker = threading.Thread(target=revoke, daemon=True)
        revoker.start()
        assert revoke_started.wait(5)
        blocked_until_generation_finishes = not revoke_finished.wait(0.1)

        # Always release the fake native iterator, even when the assertion is red.
        allow_c3.set()
        deadline = time.monotonic() + 30
        while not runtime.idle() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert runtime.idle(), "synthetic audio Runtime turn did not settle"
        assert revoke_finished.wait(5), "consent revocation did not finish after C3 returned"
        revoker.join(timeout=5)

        assert blocked_until_generation_finishes, (
            "provider revocation completed after prompt assembly but before C3 generation finished"
        )
        assert state["active"] is False
        assert runtime.last_answer()["status"] == "FINAL"
        assert "RAW_EAR_ACOUSTIC" in json.dumps(seen["C3_LANGUAGE"], ensure_ascii=False)
    finally:
        allow_c3.set()
        if revoker is not None:
            revoker.join(timeout=5)
        runtime.close()
