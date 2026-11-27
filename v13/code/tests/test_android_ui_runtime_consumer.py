from contextlib import contextmanager
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13 import android_ui_runtime
from v13.android_companion_ui_frames import UIFrameGrant


def _refs():
    return [
        {"source_id": "ui-source", "sha256": "a" * 64, "char_start": 0, "char_end": 32, "modality": "ui"},
        {"source_id": "ui-frame", "sha256": "b" * 64, "char_start": 0, "char_end": 0, "modality": "image"},
    ]


def _binding():
    return {
        "schema": "v14.ephemeral-ui-observation-binding/1",
        "event_id": "event-1",
        "brain_generation_id": "generation-1",
        "source_id": "ui-source",
        "frame_source_id": "ui-frame",
        "frame_sha256": "b" * 64,
        "capture_session_id": "mp-123",
        "consent_receipt_ref": "mp-123",
        "capture_method": "MEDIA_PROJECTION",
        "capture_scope": "FULL_DISPLAY",
        "feature_method": "HANDCRAFTED_RAW_EYE_V1",
        "feature_revision": "v14.raw-eye.ui/1",
        "finality": "FINAL",
        "action_authority": False,
        "learning_authority": False,
        "truth_authority": 0,
        "raw_capture_persisted": False,
        "derived_packet_persisted": False,
        "student_projector_used": False,
        "student_estimate_authority": "NONE",
    }


def _context(text="global: luminance=0.42; edges=0.18"):
    return {
        "text": text,
        "binding": _binding(),
        "source_refs": _refs(),
        "event_id": "event-1",
        "brain_generation_id": "generation-1",
        "audit": dict(_binding()) | {"status": "CONSUMED", "context_chars": len(text), "c3_context_attached": False},
    }


def _packet():
    refs = _refs()
    return {
        "packet_id": "percept-1",
        "event_id": "event-1",
        "brain_generation_id": "generation-1",
        "modality": "ui",
        "finality": "FINAL",
        "feature_method": "HANDCRAFTED_RAW_EYE_V1",
        "feature_revision": "v14.raw-eye.ui/1",
        "frame_binding_status": "PROVIDER_CALLBACK_ACCEPTED",
        "capture_method": "MEDIA_PROJECTION",
        "capture_scope": "FULL_DISPLAY",
        "capture_session_id": "mp-123",
        "consent_receipt_ref": "mp-123",
        "frame_sha256": "b" * 64,
        "raw_capture_persisted": False,
        "derived_packet_persisted": False,
        "action_authority": False,
        "learning_authority": False,
        "truth_authority": 0,
        "student_projector_used": False,
        "student_estimate": {"authority": "NONE"},
        "source_ref": refs[0],
        "provenance": refs,
    }


def test_body_ui_query_is_ephemeral_source_bound_and_non_authoritative():
    context = _context()
    query, binding, refs = android_ui_runtime.body_ui_query(context, "event-1", "generation-1")
    visual = query["current_ui_observation"]
    assert visual["summary"] == context["text"]
    assert visual["source_binding"]["frame_sha256"] == "b" * 64
    assert visual["authority"] == "TRANSIENT_LOW_LEVEL_FEATURES_ONLY"
    assert visual["can_quote_as_source_text"] is False
    assert visual["action_authority"] is False
    assert visual["learning_authority"] is False
    assert binding == context["binding"]
    assert refs == context["source_refs"]
    assert "summary" not in binding


@pytest.mark.parametrize("mutate", [
    lambda c: c["binding"].update(action_authority=True),
    lambda c: c["binding"].update(learning_authority=True),
    lambda c: c["binding"].update(truth_authority=1),
    lambda c: c["binding"].update(raw_capture_persisted=True),
    lambda c: c["binding"].update(event_id="other-event"),
    lambda c: c["binding"].update(frame_sha256="not-a-digest"),
    lambda c: c["source_refs"][1].update(sha256="c" * 64),
    lambda c: c["source_refs"][0].update(source_id="other-source"),
    lambda c: c.update(text="x" * 321),
])
def test_body_ui_query_rejects_authority_stale_or_oversized_context(mutate):
    context = _context()
    mutate(context)
    with pytest.raises(ValueError):
        android_ui_runtime.body_ui_query(context, "event-1", "generation-1")


def test_empty_a5_context_keeps_only_content_free_binding():
    query, binding, refs = android_ui_runtime.body_ui_query(_context(""), "event-1", "generation-1")
    assert query == {}
    assert binding["source_id"] == "ui-source"
    assert len(refs) == 2


def test_c3_ui_context_is_added_to_a_copy_not_the_saved_context():
    base = [{"role": "system", "content": "stable context"}, {"role": "user", "content": "what is on screen?"}]
    injected = android_ui_runtime.append_c3_ui_context(base, _context(), "event-1", "generation-1")
    assert "CURRENT TURN — USER-APPROVED TRANSIENT SCREEN OBSERVATION" in injected[0]["content"]
    assert "luminance=0.42" in injected[0]["content"]
    assert base[0]["content"] == "stable context"
    assert len(injected) == len(base)


def test_current_turn_context_holds_grant_and_perception_scope_until_exit(monkeypatch):
    packet = _packet()
    envelope = SimpleNamespace(optional_context="global: luminance=0.42", included_ids=["ui-source"], omitted_ids=[])
    result = {
        "packet": packet, "context_envelope": envelope, "context_packet_count": 1,
        "raw_capture_persisted": False, "derived_packet_persisted": False,
        "caller_buffer_overwritten": True, "action_authority": False,
        "learning_authority": False, "truth_authority": 0,
        "frame_binding_status": "PROVIDER_CALLBACK_ACCEPTED",
    }
    events = []

    class FakeGrant:
        lease = object()
        @contextmanager
        def consume_scope(self, *args, **kwargs):
            events.append("scope_open")
            try:
                yield result
            finally:
                events.append("scope_close")

    class FakeController:
        trust_path = SimpleNamespace(exists=lambda: True)
        @contextmanager
        def open_current_turn(self, runtime):
            events.append("grant_open")
            try:
                yield FakeGrant()
            finally:
                events.append("grant_close")

    class FakeAdapter:
        def __init__(self, runtime):
            pass
        def context(self, event_id, lease):
            assert event_id == "event-1"
            assert lease is not None
            return [packet]

    runtime = SimpleNamespace(
        turn_event={"event_id": "event-1", "brain_generation_id": "generation-1"},
        current="turn",
        _android_companion_controller=FakeController(),
    )
    monkeypatch.setattr(android_ui_runtime, "A5UIRuntimeAdapter", FakeAdapter)
    with android_ui_runtime.current_turn_context(runtime, "screen?") as context:
        assert context["text"] == "global: luminance=0.42"
        assert context["audit"]["raw_capture_persisted"] is False
        assert context["audit"]["derived_packet_persisted"] is False
        assert context["audit"]["action_authority"] is False
        assert events == ["grant_open", "scope_open"]
    assert events == ["grant_open", "scope_open", "scope_close", "grant_close"]


def test_current_turn_context_no_frame_is_a_non_error(monkeypatch):
    class FakeController:
        trust_path = SimpleNamespace(exists=lambda: True)
        @contextmanager
        def open_current_turn(self, runtime):
            yield None
    runtime = SimpleNamespace(
        turn_event={"event_id": "e", "brain_generation_id": "g"},
        current="turn",
        _android_companion_controller=FakeController(),
    )
    with android_ui_runtime.current_turn_context(runtime, "question") as context:
        assert context is None


def test_current_turn_context_does_not_instantiate_companion_for_ordinary_chat():
    runtime = SimpleNamespace(turn_event={"event_id": "e", "brain_generation_id": "g"}, current="turn")
    with android_ui_runtime.current_turn_context(runtime, "question") as context:
        assert context is None


def test_current_turn_context_requires_active_runtime_turn():
    runtime = SimpleNamespace(turn_event=None, current="idle")
    with android_ui_runtime.current_turn_context(runtime, "question") as context:
        assert context is None


def test_ui_frame_grant_scope_keeps_perception_scope_open_and_zeroizes(monkeypatch):
    from v13 import vision_ui_frame_ingress

    events = []
    result = {"status": "WIRED_SYNTHETIC"}
    lease = SimpleNamespace(active_for=lambda runtime, generation: True)

    @contextmanager
    def fake_scope(runtime, observation, frame_buffer, **kwargs):
        assert kwargs["consent_lease"] is lease
        events.append("perception_open")
        try:
            yield result
        finally:
            events.append("perception_close")

    monkeypatch.setattr(vision_ui_frame_ingress, "consume_projected_frame_from_provider_scope", fake_scope)
    frame = bytearray(b"jpeg")
    runtime = SimpleNamespace(turn_event={"brain_generation_id": "generation-1"})
    grant = UIFrameGrant(
        {"frame_buffer": frame, "observation": {"source_id": "ui-source"}, "verify_frame": lambda *args: True},
        lease,
        SimpleNamespace(),
    )
    with grant.consume_scope(runtime, current_source="screen?") as consumed:
        assert consumed is result
        assert events == ["perception_open"]
    assert events == ["perception_open", "perception_close"]
    assert frame == bytearray(b"\x00" * 4)


def test_normal_runtime_turn_uses_the_same_ui_context_for_bodies_and_c3_without_persisting_it():
    code_dir = Path(__file__).resolve().parents[1]
    overlay_path = code_dir / "scripts" / "integrated_android_ui_runtime_candidate_20261127.py"
    spec = importlib.util.spec_from_file_location("v14_android_ui_runtime_overlay_test", overlay_path)
    assert spec is not None and spec.loader is not None
    overlay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    sources = {
        relative: (code_dir / relative).read_bytes()
        for relative in ("v13/runtime.py", "v13/cognition.py", "v13/operator.py")
    }
    composed = overlay.apply_sources(code_dir, sources)
    runtime_source = composed["v13/runtime.py"].decode("utf-8")
    cognition_source = composed["v13/cognition.py"].decode("utf-8")
    operator_source = composed["v13/operator.py"].decode("utf-8")
    assert runtime_source.index("current_turn_context(self,text") < runtime_source.index("self.cognition.offer")
    assert "valid_until=deadline,ui_context=ui_context" in runtime_source
    assert runtime_source.index("save_context(") < runtime_source.index("append_c3_ui_context")
    assert runtime_source.index("append_c3_ui_context") < runtime_source.index("runner.generate(messages")
    assert "ui_frame_stack.close()" in runtime_source
    assert "body_ui_query(ui_context,e['event_id'],e['brain_generation_id'])" in cognition_source
    assert "ephemeral_ui_binding" in cognition_source
    assert "ui_observation_binding" in cognition_source
    assert "if cmd=='android':" in operator_source
    assert "from .android_companion_runtime import operator_command" in operator_source
    from v13.runtime_deploy import REQUIRED
    assert {
        "v13/android_ui_runtime.py",
        "v13/android_companion_runtime.py",
        "v13/android_companion_ui_frames.py",
        "v13/android_companion_transport.py",
        "v13/android_companion_ecdsa.py",
        "v13/android_capabilities.py",
        "v13/android_control.py",
        "v13/android_outcomes.py",
        "v13/a5_ui_admission_bridge.py",
        "v13/vision_ui_frame_ingress.py",
    } <= set(REQUIRED)


def test_controller_open_current_turn_checks_readiness_and_closes_provider(monkeypatch, tmp_path):
    from v13.android_companion_runtime import AndroidCompanionController
    from v13 import android_companion_ui_frames

    events = []

    class FakeVerifier:
        def __init__(self, *args, **kwargs):
            events.append("verifier")

    class FakeProvider:
        ready = True
        def __init__(self, transport, verifier):
            events.append("provider")
        def status(self):
            return {"status": "FRAME_READY" if self.ready else "NO_FRAME"}
        @contextmanager
        def open_current_turn(self, runtime):
            events.append("grant_open")
            try:
                yield "grant"
            finally:
                events.append("grant_close")
        def close(self):
            events.append("provider_close")

    monkeypatch.setattr(android_companion_ui_frames, "ECDSAUIFrameReceiptVerifier", FakeVerifier)
    monkeypatch.setattr(android_companion_ui_frames, "AndroidCompanionFrameProvider", FakeProvider)
    controller = object.__new__(AndroidCompanionController)
    controller._pinned_key = lambda: ({"key_id": "pinned"}, b"public-key", {})
    controller.ui_frame_verifier_path = tmp_path / "ui-frame-verifier.sqlite"
    controller.clock = lambda: 123
    controller.transport = object()

    FakeProvider.ready = True
    with controller.open_current_turn(object()) as grant:
        assert grant == "grant"
        assert events == ["verifier", "provider", "grant_open"]
    assert events == ["verifier", "provider", "grant_open", "grant_close", "provider_close"]

    events.clear()
    FakeProvider.ready = False
    with controller.open_current_turn(object()) as grant:
        assert grant is None
        assert events == ["verifier", "provider", "provider_close"]


def test_normal_runtime_composer_preserves_audio_and_ui_source_bindings():
    code_dir = Path(__file__).resolve().parents[1]
    builder_path = code_dir / "scripts" / "termux_runtime_recovery_candidate_20261121.py"
    spec = importlib.util.spec_from_file_location("v14_ui_audio_composer_test", builder_path)
    assert spec is not None and spec.loader is not None
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    composed = builder.build_sources(code_dir)
    cognition = composed["v13/cognition.py"].decode("utf-8")
    assert "audio_context_refs" in cognition
    assert "ephemeral_ui_binding" in cognition
    assert "ephemeral_ui_source_refs" in cognition
    scope = cognition.split("def analyst_context", 1)[1].split("def communicate", 1)[0]
    assert "query.get('audio_context_refs',[])!=offer.get('audio_context_refs',[])" in scope
    assert "query.get('ephemeral_ui_binding')!=offer.get('ephemeral_ui_binding')" in scope
    assert "query.get('ephemeral_ui_source_refs',[])!=offer.get('ephemeral_ui_source_refs',[])" in scope


def test_ood_student_estimate_is_never_promoted_into_c3_ui_prompt():
    frame_sha = "a" * 64
    refs = [
        {
            "source_id": "ui_summary_source",
            "sha256": "b" * 64,
            "char_start": 0,
            "char_end": 0,
            "modality": "ui",
        },
        {
            "source_id": "ui_frame_source",
            "sha256": frame_sha,
            "char_start": 0,
            "char_end": 0,
            "modality": "ui",
        },
    ]
    binding = {
        "schema": "v14.ephemeral-ui-observation-binding/1",
        "event_id": "event-ood",
        "brain_generation_id": "generation-ood",
        "source_id": refs[0]["source_id"],
        "frame_source_id": refs[1]["source_id"],
        "frame_sha256": frame_sha,
        "capture_session_id": "session-ood",
        "consent_receipt_ref": "receipt-ood",
        "capture_method": "MEDIA_PROJECTION",
        "capture_scope": "FULL_DISPLAY",
        "feature_method": "HANDCRAFTED_RAW_EYE_V1",
        "feature_revision": "raw-eye-v1",
        "finality": "FINAL",
        "action_authority": False,
        "learning_authority": False,
        "truth_authority": 0,
        "raw_capture_persisted": False,
        "derived_packet_persisted": False,
        "student_projector_used": False,
        "student_estimate_authority": "NONE",
        "student_ood_status": "OUT_OF_DISTRIBUTION",
        "ood_regions": ["r00", "r01"],
    }
    ui_context = {
        "binding": binding,
        "source_refs": refs,
        "text": "RAW_EYE: low-level structure only; no OCR or object identity",
    }

    query, returned_binding, returned_refs = android_ui_runtime.body_ui_query(
        ui_context, "event-ood", "generation-ood"
    )

    prompt = query["current_ui_observation"]
    assert prompt["authority"] == "TRANSIENT_LOW_LEVEL_FEATURES_ONLY"
    assert prompt["source_binding"]["frame_sha256"] == frame_sha
    assert "student_estimate" not in prompt
    assert "student_estimate_authority" not in prompt
    assert "student_ood_status" not in prompt
    assert "ood_regions" not in prompt
    assert returned_binding["student_estimate_authority"] == "NONE"
    assert returned_binding["student_ood_status"] == "OUT_OF_DISTRIBUTION"
    assert returned_refs == refs

