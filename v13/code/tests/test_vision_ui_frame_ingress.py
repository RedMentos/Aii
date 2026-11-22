"""Synthetic MediaProjection frame tests for the RAW EYE UI adapter."""
from contextlib import contextmanager
from io import BytesIO
import hashlib
import threading
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from v13.a5_ui_admission_bridge import A5UIRuntimeAdapter, ui_observation_lease
from v13.vision_ui_frame_ingress import consume_projected_frame


class _Attention:
    def perceive(self, event_id, segments, *, goal="", file_requests=True):
        assert file_requests is False
        return {
            "segments": [{"index": i, "score": 0.25, "source_ref": x["source_ref"]}
                         for i, x in enumerate(segments)],
            "highres": [], "requests": [], "truth_authority": 0,
        }


class _Cursor:
    def fetchone(self):
        return None


class _Connection:
    def execute(self, *args, **kwargs):
        return _Cursor()


class _Store:
    def __init__(self, lock):
        self.mutex = lock

    @contextmanager
    def tx(self):
        yield _Connection()


def make_runtime(monkeypatch, with_store=False):
    runtime = SimpleNamespace(
        turn_event={"event_id": "evt_ui_frame_1", "brain_generation_id": "gen_ui_frame_1"},
        current="turn",
        cancel_event=threading.Event(),
    )
    if with_store:
        runtime.store = _Store(threading.RLock())
    monkeypatch.setattr(
        "v13.vision_ui_frame_ingress.attention_module.controller",
        lambda _runtime: _Attention(),
    )
    return runtime


def observation(finality="FINAL", method="MEDIA_PROJECTION", event_kind="SCREEN_FRAME_AVAILABLE"):
    value = {
        "schema": "v14.a5.ui-observation/1",
        "modality": "ui",
        "source_id": "ui-frame-source-0001",
        "capture_session_id": "ui-frame-session-0001",
        "consent_receipt_ref": "receipt-frame-0001",
        "capture_method": method,
        "capture_scope": "FULL_DISPLAY" if method == "MEDIA_PROJECTION" else "ACCESSIBILITY_TREE",
        "api_level": 34,
        "clock": "ELAPSED_REALTIME",
        "event_kind": event_kind,
        "start_ms": 1000,
        "end_ms": 1033,
        "finality": finality,
        "action_authority": False,
        "learning_authority": False,
        "raw_capture_persisted": False,
    }
    if method == "ACCESSIBILITY_ASSISTIVE":
        value["accessibility_purpose"] = "DISABILITY_ASSISTANCE"
    return value


def image_buffer():
    image = Image.new("RGB", (64, 64), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.rectangle((38, 14, 59, 52), fill=(230, 20, 18))
    draw.rectangle((8, 8, 19, 24), fill=(12, 180, 220))
    output = BytesIO()
    image.save(output, format="PNG")
    image.close()
    return bytearray(output.getvalue())


def lease_for(runtime, obs, callbacks=None, lock=None):
    lock = lock or threading.RLock()

    def check(*_args):
        return True

    @contextmanager
    def guard(*_args):
        with lock:
            yield True

    def subscribe(source_id, receipt, session, request_cancel, on_revoked):
        if callbacks is not None:
            callbacks[source_id] = (request_cancel, on_revoked)
        def unsubscribe():
            if callbacks is not None:
                callbacks.pop(source_id, None)
        return unsubscribe

    return ui_observation_lease(
        runtime, obs, runtime.turn_event["brain_generation_id"],
        check, guard, subscribe,
    )


def test_media_projection_frame_reaches_a5_a4_and_existing_ui_context(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    expected_hash = hashlib.sha256(frame).hexdigest()
    prompt = "Describe only the visible UI state; preserve this exact request."

    with lease_for(runtime, obs) as lease:
        result = consume_projected_frame(
            runtime, obs, frame, consent_lease=lease,
            frame_binding_check=lambda _obs, _sha, _size: True,
            current_source=prompt, goal="red panel", token_budget=512,
        )
        packets = A5UIRuntimeAdapter(runtime).context(runtime.turn_event["event_id"], lease)
        assert packets == (result["packet"],)
        assert result["status"] == "WIRED_SYNTHETIC"
        assert result["packet"]["modality"] == "ui"
        assert result["packet"]["frame_sha256"] == expected_hash
        assert len(result["packet"]["segments"]) == 18  # UI event + global + 16 tiles
        assert result["packet"]["raw_capture_persisted"] is False
        assert result["packet"]["derived_packet_persisted"] is False
        assert result["packet"]["teacher_used"] is False
        assert result["packet"]["student_projector_used"] is False
        assert result["packet"]["learning_authority"] is False
        assert result["packet"]["action_authority"] is False
        assert result["a4"]["truth_authority"] == 0
        assert result["context_envelope"].current_source == prompt
        assert result["context_packet_count"] == 1
        assert result["caller_buffer_overwritten"] is True
        assert not any(frame)


def test_provisional_frame_is_never_admitted_to_c3_context(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation(finality="PROVISIONAL")
    frame = image_buffer()
    prompt = "Keep the exact source."

    with lease_for(runtime, obs) as lease:
        result = consume_projected_frame(
            runtime, obs, frame, consent_lease=lease,
            frame_binding_check=lambda _obs, _sha, _size: True,
            current_source=prompt, token_budget=512,
        )
        assert result["admission"].status == "EMPTY_OR_UNAUTHORIZED"
        assert result["context_envelope"].current_source == prompt
        assert result["context_envelope"].optional_context == ""
        assert result["context_packet_count"] == 0
        assert A5UIRuntimeAdapter(runtime).context(runtime.turn_event["event_id"], lease) == ()
        assert result["caller_buffer_overwritten"] is True


def test_wrong_receipt_and_non_projection_events_fail_closed(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        wrong = dict(obs, consent_receipt_ref="receipt-other")
        with pytest.raises(PermissionError, match="lease"):
            consume_projected_frame(
                runtime, wrong, frame, consent_lease=lease,
                frame_binding_check=lambda _obs, _sha, _size: True,
                current_source="Describe this.",
            )
        assert not any(frame)

    runtime = make_runtime(monkeypatch)
    obs = observation(method="ACCESSIBILITY_ASSISTIVE", event_kind="WINDOW_CONTENT_CHANGED")
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        with pytest.raises(PermissionError, match="MediaProjection"):
            consume_projected_frame(
                runtime, obs, frame, consent_lease=lease,
                frame_binding_check=lambda _obs, _sha, _size: True,
                current_source="Describe this.",
            )
        assert not any(frame)


def test_cancelled_lease_cannot_cache_frame_and_overwrites_buffer(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        runtime.cancel_event.set()
        with pytest.raises(PermissionError, match="lease"):
            consume_projected_frame(
                runtime, obs, frame, consent_lease=lease,
                frame_binding_check=lambda _obs, _sha, _size: True,
                current_source="Describe this.",
            )
        assert obs["source_id"] not in getattr(runtime, "_a5_ui_context_cache", {})
        assert not any(frame)


def test_revocation_clears_ephemeral_visual_packet_cache(monkeypatch):
    runtime = make_runtime(monkeypatch, with_store=True)
    obs = observation()
    frame = image_buffer()
    callbacks = {}
    with lease_for(runtime, obs, callbacks=callbacks, lock=runtime.store.mutex) as lease:
        result = consume_projected_frame(
            runtime, obs, frame, consent_lease=lease,
            frame_binding_check=lambda _obs, _sha, _size: True,
            current_source="Describe this.",
        )
        assert A5UIRuntimeAdapter(runtime).context(runtime.turn_event["event_id"], lease)
        request_cancel, on_revoked = callbacks[obs["source_id"]]
        assert request_cancel() is True
    cleanup = on_revoked()
    assert cleanup["cache_cleared"] is True
    assert obs["source_id"] not in runtime._a5_ui_context_cache
    assert result["caller_buffer_overwritten"] is True


def test_zero_budget_preserves_current_source_and_bad_frames_are_overwritten(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    prompt = "Never truncate this exact current user source."
    with lease_for(runtime, obs) as lease:
        result = consume_projected_frame(
            runtime, obs, frame, consent_lease=lease,
            frame_binding_check=lambda _obs, _sha, _size: True,
            current_source=prompt, token_budget=0, context_budget_chars=0,
        )
        assert result["admission"].status == "EMPTY_OR_UNAUTHORIZED"
        assert result["context_envelope"].current_source == prompt
        assert result["context_envelope"].optional_context == ""

    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = bytearray(b"not an image")
    with lease_for(runtime, obs) as lease:
        with pytest.raises(ValueError):
            consume_projected_frame(
                runtime, obs, frame, consent_lease=lease,
                frame_binding_check=lambda _obs, _sha, _size: True,
                current_source="Describe this.",
            )
        assert not any(frame)


def test_provider_frame_receipt_must_match_exact_frame_digest(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        with pytest.raises(PermissionError, match="digest"):
            consume_projected_frame(
                runtime, obs, frame, consent_lease=lease,
                frame_binding_check=lambda _obs, _sha, _size: False,
                current_source="Describe this.",
            )
        assert not any(frame)


def test_frame_receipt_verifier_is_mandatory_and_oversized_buffer_is_rejected(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        with pytest.raises(PermissionError, match="verifier"):
            consume_projected_frame(
                runtime, obs, frame, consent_lease=lease,
                frame_binding_check=None,
                current_source="Describe this.",
            )
        assert not any(frame)

    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = bytearray(b"x" * (8 * 1024 * 1024 + 1))
    with lease_for(runtime, obs) as lease:
        with pytest.raises(ValueError, match="8 MiB"):
            consume_projected_frame(
                runtime, obs, frame, consent_lease=lease,
                frame_binding_check=lambda _obs, _sha, _size: True,
                current_source="Describe this.",
            )
        assert not any(frame)
