"""Contract tests for the RAW EYE provider entrypoint and frame scope."""

import pytest

from v13 import vision_ui_frame_ingress as ingress


def observation():
    return {
        "schema": "v14.a5.ui-observation/1",
        "modality": "ui",
        "source_id": "ui-frame-source-0001",
        "capture_session_id": "ui-frame-session-0001",
        "consent_receipt_ref": "receipt-frame-0001",
        "capture_method": "MEDIA_PROJECTION",
        "capture_scope": "FULL_DISPLAY",
        "api_level": 34,
        "clock": "ELAPSED_REALTIME",
        "event_kind": "SCREEN_FRAME_AVAILABLE",
        "start_ms": 1000,
        "end_ms": 1033,
        "finality": "FINAL",
        "action_authority": False,
        "learning_authority": False,
        "raw_capture_persisted": False,
    }


def test_provider_entrypoint_returns_consumer_dict_and_zeroizes(monkeypatch):
    runtime = object()
    obs = observation()
    frame = bytearray(b"compressed-frame")
    lease = object()
    verifier = object()
    expected = {"status": "WIRED_SYNTHETIC", "truth_authority": 0}
    issued = []
    consumed = []

    def issue(actual_lease, actual_obs, verify_fn):
        issued.append((actual_lease, actual_obs, verify_fn))
        return verifier

    def consume(actual_runtime, actual_obs, actual_frame, **kwargs):
        consumed.append((actual_runtime, actual_obs, actual_frame, kwargs))
        return expected

    monkeypatch.setattr(ingress, "_issue_provider_frame_verifier", issue)
    monkeypatch.setattr(ingress, "consume_projected_frame", consume)

    result = ingress.consume_projected_frame_from_provider(
        runtime, obs, frame, consent_lease=lease,
        verify_fn=lambda *_: True, current_source="current query",
    )

    assert result is expected
    assert issued[0][0] is lease and issued[0][1] is obs
    assert callable(issued[0][2])
    assert consumed[0][0] is runtime and consumed[0][1] is obs
    assert consumed[0][2] is frame
    assert consumed[0][3]["consent_lease"] is lease
    assert consumed[0][3]["frame_verifier"] is verifier
    assert frame == bytearray(len(frame))


def test_provider_entrypoint_zeroizes_when_verifier_issuance_fails(monkeypatch):
    frame = bytearray(b"untrusted-frame")

    def reject(*_args):
        raise PermissionError("receipt rejected")

    monkeypatch.setattr(ingress, "_issue_provider_frame_verifier", reject)
    with pytest.raises(PermissionError, match="receipt rejected"):
        ingress.consume_projected_frame_from_provider(
            object(), observation(), frame, consent_lease=object(),
            verify_fn=lambda *_: True, current_source="query",
        )
    assert frame == bytearray(len(frame))


def test_frame_scope_is_a_context_manager_and_revokes_after_consumer(monkeypatch):
    runtime = object()
    obs = observation()
    frame = bytearray(b"frame")
    expected = {"status": "WIRED_SYNTHETIC"}
    calls = []
    monkeypatch.setattr(ingress, "consume_projected_frame", lambda *args, **kwargs: expected)
    monkeypatch.setattr(ingress, "revoke_ui_observation", lambda actual_runtime, source_id: calls.append((actual_runtime, source_id)))

    scope = ingress.consume_projected_frame_scope(
        runtime, obs, frame, consent_lease=object(), current_source="query",
    )
    assert hasattr(scope, "__enter__") and hasattr(scope, "__exit__")
    with scope as result:
        assert result is expected
        assert calls == []
    assert calls == [(runtime, obs["source_id"])]
