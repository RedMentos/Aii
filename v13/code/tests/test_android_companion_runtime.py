import base64
import hashlib
import json

import pytest

from v13 import android_control, android_outcomes
from v13.contracts import packet
from v13.android_companion_runtime import AndroidCompanionController
from v13.store import Store
from v13.operator import Operator


PUBLIC_KEY = bytes.fromhex(
    "046b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296"
    "4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5"
)
KEY_ID = "698bea63dc44a344663ff1429aea10842df27b6b991ef25866b2c6c02cdcc5be"
PUBLIC_KEY_INFO = {
    "schema": "v14.android-companion-public-key/1",
    "algorithm": "ECDSA_P256_SHA256",
    "key_id": KEY_ID,
    "public_key_sec1_base64": base64.b64encode(PUBLIC_KEY).decode("ascii"),
    "key_storage_status": "ANDROID_KEYSTORE_SOFTWARE_BACKED",
}
BODY = {
    "schema": "v14.android-companion-receipt/1",
    "nonce": "1" * 32,
    "action_id": "2" * 32,
    "capability": "launch_app",
    "digest": "0e1b8771ccce5e24b8dcfd99466b6e553413dc684f3ef3cd4c3da52ad52d6b15",
    "issued_at": 999,
    "expires_at": 1030,
    "status": "DISPATCHED_UNVERIFIED",
    "local_consent": True,
    "observed": False,
    "os_permission_status": "NOT_REQUIRED_FOR_LAUNCH_APP",
    "key_storage_status": "ANDROID_KEYSTORE_SOFTWARE_BACKED",
    "key_id": KEY_ID,
}
SUCCESS_RECEIPT = {
    "body": BODY,
    "key_id": KEY_ID,
    "signature": "MEUCIQCj6DaMCL0/ofDX/AxaFXbnT+ItjasEn7c0HNpRmsW28AIgQ6UwgRkmD46+1dAyhr1NOR6tBMlnER7j/f6Lz9RiKBI=",
}
def _sign_test_body(body):
    """Sign a test-only receipt with private scalar 1 (fixture public key is P-256 G)."""
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
    generator_x = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
    r = generator_x
    s = (int.from_bytes(hashlib.sha256(raw).digest(), "big") + r) % order
    if s == 0:
        raise AssertionError("test fixture produced an invalid ECDSA scalar")

    def der_integer(value):
        encoded = value.to_bytes((value.bit_length() + 7) // 8, "big")
        if encoded[0] & 0x80:
            encoded = bytes([0]) + encoded
        return bytes([2, len(encoded)]) + encoded

    payload = der_integer(r) + der_integer(s)
    signature = bytes([0x30, len(payload)]) + payload
    return base64.b64encode(signature).decode("ascii")
DENIAL_BODY = {**BODY, "nonce": "3" * 32, "status": "USER_DENIED", "local_consent": False}
DENIAL_RECEIPT = {
    "body": DENIAL_BODY,
    "key_id": KEY_ID,
    "signature": "MEYCIQCYn0+HoA+9gtJtrgVHZQKBjFyYZYlx8rZCwrGmXW1l+QIhALh6j5POEMCWZ/+3Kv0o2b6SwLHze1CATCRbGHjZhkgQ",
}


class RuntimeStub:
    def __init__(self, home):
        self.home = home
        self.store = Store(home)
        self.session = self.store.new_session()
        self.idle_checks = 0

    def require_idle(self):
        self.idle_checks += 1


class FakeTransport:
    def __init__(self, receipt=None, *, enabled=True):
        self.receipt = receipt
        self.enabled = enabled
        self.submitted = []
        self.pending_items = []
        self.cancelled = []

    def public_key(self):
        return dict(PUBLIC_KEY_INFO)

    def capabilities(self):
        return {
            "schema": "v14.android-capability-registry/1",
            "enabled": self.enabled,
            "termux_paired": True,
            "capabilities": [{
                "capability": "launch_app",
                "status": "READY_WITH_PER_ACTION_CONSENT" if self.enabled else "OFF_STOP_SWITCH",
            }],
        }

    def submit(self, request):
        self.submitted.append(request)
        self.pending_items.append({
            "action_id": request["action_id"],
            "package": request["args"]["package"],
            "expires_at_ms": int(request["expires_at"] * 1000),
        })
        return {"status": "PENDING_USER_APPROVAL", "action_id": request["action_id"]}

    def outcome(self, action_id):
        if self.receipt is None:
            return {"status": "NOT_READY", "action_id": action_id}
        return {"status": "READY", "action_id": action_id, "receipt": self.receipt}

    def cancel(self, action_id):
        self.pending_items = [item for item in self.pending_items if item["action_id"] != action_id]
        self.cancelled.append(action_id)
        return {"status": "CANCELLED", "action_id": action_id}

    def pending(self):
        return {"status": "OK", "pending": list(self.pending_items)}


def make_runtime(tmp_path):
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    return RuntimeStub(home)


def test_pair_pin_launch_and_signed_receipt_are_tty_driven_and_non_authoritative(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "2" * (size * 2))
    runtime = make_runtime(tmp_path)
    transport = FakeTransport(SUCCESS_RECEIPT)
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)

    assert json.loads(controller.status())["broker_stopped"] is True
    pair = json.loads(controller.pair())
    assert pair["key_id"] == KEY_ID
    assert pair["key_auto_trusted"] is False
    with pytest.raises(android_control.ControlDenied):
        controller.trust(KEY_ID, False)
    assert json.loads(controller.trust(KEY_ID, True))["status"] == "PINNED"

    with pytest.raises(android_control.ControlDenied):
        controller.launch("com.example.app", False)
    pending = json.loads(controller.launch("com.example.app", True))
    assert pending["status"] == "PENDING_USER_APPROVAL"
    assert pending["companion_approval_required"] is True
    assert pending["device_execution_claimed"] is False
    request = transport.submitted[0]
    assert request["capability"] == "launch_app"
    assert request["permission_bypass"] is False
    assert request["model_authority"] is False
    assert request["companion_local_consent_required"] is True
    assert request["android_os_permission_required"] is False
    assert request["local_approval"] == "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION"

    recorded = json.loads(controller.poll(pending["action_id"]))
    assert recorded["status"] == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert recorded["observed"] is False
    assert recorded["t8_authoritative"] is False
    assert recorded["world_learning_eligible"] is False
    assert json.loads(controller.poll(pending["action_id"]))["status"] == "ALREADY_FINAL"

    packet = runtime.store.one("SELECT kind,payload FROM packets WHERE id=?", (recorded["packet_id"],))
    assert packet["kind"] == "ActionOutcome"
    actual = json.loads(packet["payload"])["actual"]
    assert actual["auth_scheme"] == "ECDSA_P256_SHA256_ANDROID_KEYSTORE"
    assert actual["observed"] is False
    assert actual["world_learning_eligible"] is False
    assert runtime.idle_checks == 4
    runtime.store.close()
    controller.broker.close()


def test_signed_denial_is_persisted_and_stop_cancels_pending_requests(tmp_path, monkeypatch):
    ids = iter(["2" * 32, "5" * 32])
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: next(ids))
    runtime = make_runtime(tmp_path)
    transport = FakeTransport(DENIAL_RECEIPT)
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)
    denied = json.loads(controller.launch("com.example.app", True))
    result = json.loads(controller.poll(denied["action_id"]))
    assert result["status"] == "COMPANION_USER_DENIED"
    assert result["observed"] is False
    assert result["t8_authoritative"] is False

    second = json.loads(controller.launch("com.example.other", True))
    stopped = json.loads(controller.stop())
    assert stopped["status"] == "LOCAL_BROKER_STOPPED"
    assert second["action_id"] in transport.cancelled
    assert controller.broker.stopped is True
    runtime.store.close()
    controller.broker.close()


def test_key_rotation_and_disabled_companion_fail_closed(tmp_path):
    runtime = make_runtime(tmp_path)
    transport = FakeTransport(enabled=False)
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)
    with pytest.raises(android_control.ControlDenied, match="paired and enabled"):
        controller.launch("com.example.app", True)
    transport.public_key = lambda: {
        **PUBLIC_KEY_INFO,
        "key_id": "0" * 64,
    }
    with pytest.raises(android_control.ControlDenied, match="fingerprint mismatch"):
        controller.launch("com.example.app", True)
    runtime.store.close()
    controller.broker.close()


def test_operator_refuses_model_origin_for_android_control(tmp_path):
    runtime = make_runtime(tmp_path)
    with pytest.raises(ValueError, match="lokale Operator-Eingaben"):
        Operator(runtime).run(":android status", origin="MODEL")
    runtime.store.close()



def test_submit_timeout_with_unconfirmed_remote_cancel_keeps_receipt_pollable(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "2" * (size * 2))

    class AmbiguousTransport(FakeTransport):
        def submit(self, request):
            super().submit(request)
            raise TimeoutError("ack lost after remote commit")

        def cancel(self, action_id):
            self.cancelled.append(action_id)
            raise TimeoutError("remote cancellation not confirmed")

    runtime = make_runtime(tmp_path)
    transport = AmbiguousTransport()
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)

    submitted = json.loads(controller.launch("com.example.app", True))
    action_id = "2" * 32
    assert submitted["status"] == "SUBMIT_UNCERTAIN"
    assert submitted["action_id"] == action_id
    assert controller.broker.action_state(action_id) == "SUBMIT_UNCERTAIN"

    transport.receipt = SUCCESS_RECEIPT
    polled = json.loads(controller.poll(action_id))
    assert polled["status"] == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert controller.broker.action_state(action_id) == "RECEIPT_VERIFIED"
    runtime.store.close()
    controller.broker.close()


def test_cancel_timeout_and_stop_do_not_finalize_an_ambiguous_remote_action(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "2" * (size * 2))
    runtime = make_runtime(tmp_path)
    transport = FakeTransport()
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)
    pending = json.loads(controller.launch("com.example.app", True))
    action_id = pending["action_id"]

    def timeout_cancel(_action_id):
        raise TimeoutError("remote cancel acknowledgement lost")

    transport.cancel = timeout_cancel
    cancelled = json.loads(controller.cancel(action_id))
    assert cancelled["status"] == "SUBMIT_UNCERTAIN"
    assert controller.broker.action_state(action_id) == "SUBMIT_UNCERTAIN"

    stopped = json.loads(controller.stop())
    assert stopped["status"] == "LOCAL_BROKER_STOPPED"
    assert action_id in stopped["uncertain_action_ids"]
    assert controller.broker.action_state(action_id) == "SUBMIT_UNCERTAIN"
    runtime.store.close()
    controller.broker.close()


def test_mismatched_submit_ack_cancels_local_and_remote_action(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "2" * (size * 2))

    class MismatchedAckTransport(FakeTransport):
        def submit(self, request):
            super().submit(request)
            return {"status": "PENDING_USER_APPROVAL", "action_id": "f" * 32}

    runtime = make_runtime(tmp_path)
    transport = MismatchedAckTransport()
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)

    with pytest.raises(android_control.ControlDenied, match="exact action id"):
        controller.launch("com.example.app", True)

    action_id = "2" * 32
    assert transport.cancelled == [action_id]
    assert controller.broker.action_state(action_id) == "CANCELLED"
    runtime.store.close()
    controller.broker.close()


def test_action_intent_history_is_session_scoped_restartable_and_non_authoritative(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "2" * (size * 2))
    runtime = make_runtime(tmp_path)
    transport = FakeTransport(SUCCESS_RECEIPT)
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)

    pending = json.loads(controller.launch("com.example.private_app", True))
    action_id = pending["action_id"]
    # Bind the signed fixture to this exact request. Reusing SUCCESS_RECEIPT
    # would correctly fail because its digest belongs to com.example.app.
    request = transport.submitted[-1]
    body = {
        **BODY,
        "action_id": action_id,
        "digest": request["digest"],
        "nonce": "7" * 32,
    }
    transport.receipt = {
        "body": body,
        "key_id": KEY_ID,
        "signature": _sign_test_body(body),
    }
    intent_row = runtime.store.one(
        "SELECT payload FROM packets WHERE kind='ActionIntent' AND event_id=?",
        (pending["source_event_id"],),
    )
    intent = json.loads(intent_row["payload"])
    assert intent["producer_component"] == "C5_ANDROID_COMPANION"
    assert intent["action_id"] == action_id
    assert intent["action_type"] == "launch_app"
    assert intent["permission"] == "OPERATOR_TTY_AND_ANDROID_COMPANION_UI"

    other_session = runtime.store.new_session()
    other_event = runtime.store.event(other_session, "other session action")
    other_intent = packet(
        "ActionIntent", "C5_ANDROID_COMPANION", other_event["event_id"],
        other_event["brain_generation_id"], [other_event["source_ref"]],
        action_id="9" * 32, action_type="launch_app",
        permission="OPERATOR_TTY_AND_ANDROID_COMPANION_UI",
    )
    runtime.store.add_packet("ActionIntent", other_intent)

    before_restart = json.loads(controller.history())
    assert before_restart["session_scoped"] is True
    assert before_restart["count"] == 1
    assert before_restart["actions"][0]["action_id"] == action_id
    assert before_restart["actions"][0]["action_state"] == "DISPATCHED"
    assert "com.example.private_app" not in json.dumps(before_restart)
    assert "9" * 32 not in json.dumps(before_restart)

    controller.broker.close()
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    after_restart = json.loads(controller.history())
    assert after_restart["actions"][0]["action_state"] == "DISPATCHED"

    receipt = json.loads(controller.poll(action_id))
    assert receipt["status"] == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert receipt["observed"] is False
    assert receipt["t8_authoritative"] is False
    assert receipt["world_learning_eligible"] is False

    history = json.loads(controller.history())
    item = history["actions"][0]
    assert item["action_id"] == action_id
    assert item["outcome_status"] == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert item["observed"] is False
    assert item["evidence_level"] == "COMPANION_RECEIPT_ONLY"
    assert item["t8_authoritative"] is False
    assert item["world_learning_eligible"] is False
    assert "com.example.private_app" not in json.dumps(history)
    assert runtime.store.one("SELECT 1 FROM actions WHERE event_id=?", (pending["source_event_id"],)) is None

    # The ordinary local operator route exposes the read-only history; model-origin calls remain blocked.
    # A matching action_id alone must never join another event or elevate receipt authority.
    stored_outcome = runtime.store.one(
        "SELECT payload FROM packets WHERE kind='ActionOutcome' AND event_id=?",
        (pending["source_event_id"],),
    )
    valid_outcome = json.loads(stored_outcome["payload"])
    unrelated = runtime.store.event(runtime.session, "unrelated same-session event")
    forged_actual = {
        **valid_outcome["actual"],
        "observed": True,
        "t8_authoritative": True,
        "world_learning_eligible": True,
        "trusted_transition_eligible": True,
    }
    mismatched = packet(
        "ActionOutcome", "C5_ANDROID_COMPANION", unrelated["event_id"],
        unrelated["brain_generation_id"], [unrelated["source_ref"]],
        action_id=action_id, status="COMPANION_OUTCOME_UNKNOWN", actual=forged_actual,
    )
    runtime.store.add_packet("ActionOutcome", mismatched)
    authority_forgery = packet(
        "ActionOutcome", "C5_ANDROID_COMPANION", valid_outcome["event_id"],
        valid_outcome["brain_generation_id"], valid_outcome["provenance"],
        action_id=action_id, status="COMPANION_OUTCOME_UNKNOWN", actual=forged_actual,
    )
    runtime.store.add_packet("ActionOutcome", authority_forgery)
    after_forgery = json.loads(controller.history())
    assert after_forgery["actions"][0]["outcome_status"] == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert after_forgery["actions"][0]["observed"] is False
    assert after_forgery["actions"][0]["t8_authoritative"] is False
    assert after_forgery["actions"][0]["world_learning_eligible"] is False

    tty_history = json.loads(Operator(runtime).run(":android history"))
    assert tty_history["count"] == 1
    with pytest.raises(ValueError, match="lokale Operator-Eingaben"):
        Operator(runtime).run(":android history", origin="MODEL")

    runtime._android_companion_controller.broker.close()
    controller.broker.close()
    runtime.store.close()


def test_unknown_companion_recovery_receipt_is_persisted_without_device_or_learning_authority(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "6" * (size * 2))
    runtime = make_runtime(tmp_path)
    transport = FakeTransport()
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)

    pending = json.loads(controller.launch("com.example.app", True))
    action_id = pending["action_id"]
    request = transport.submitted[-1]
    body = {
        **BODY,
        "action_id": action_id,
        "digest": request["digest"],
        "nonce": "8" * 32,
        "status": "OUTCOME_UNKNOWN",
        "local_consent": True,
    }
    transport.receipt = {
        "body": body,
        "key_id": KEY_ID,
        "signature": _sign_test_body(body),
    }

    recovered = json.loads(controller.poll(action_id))
    assert recovered["status"] == "COMPANION_OUTCOME_UNKNOWN"
    assert recovered["observed"] is False
    assert recovered["t8_authoritative"] is False
    assert recovered["world_learning_eligible"] is False
    assert recovered["receipt_status"] == "OUTCOME_UNKNOWN"

    row = runtime.store.one(
        "SELECT payload FROM packets WHERE kind='ActionOutcome' AND event_id=?",
        (pending["source_event_id"],),
    )
    outcome = json.loads(row["payload"])
    actual = outcome["actual"]
    assert outcome["status"] == "COMPANION_OUTCOME_UNKNOWN"
    assert actual["local_approval_evidence"] == "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"
    assert actual["observed"] is False
    assert actual["t8_authoritative"] is False
    assert actual["world_learning_eligible"] is False
    assert json.loads(controller.poll(action_id))["status"] == "ALREADY_FINAL"

    controller.broker.close()
    runtime.store.close()


def test_android_action_history_rejects_unbounded_or_non_integer_limits(tmp_path):
    runtime = make_runtime(tmp_path)
    controller = AndroidCompanionController(runtime, transport=FakeTransport())
    for invalid in (0, 51, True, 1.5, "5"):
        with pytest.raises(ValueError, match="history limit"):
            controller.history(invalid)
    controller.broker.close()
    runtime.store.close()



def _signed_receipt_for_request(transport, action_id, nonce):
    request = transport.submitted[-1]
    body = {
        **BODY,
        "action_id": action_id,
        "digest": request["digest"],
        "nonce": nonce,
    }
    return {
        "body": body,
        "key_id": KEY_ID,
        "signature": _sign_test_body(body),
    }


def test_claimed_receipt_retries_after_restart_without_redispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "2" * (size * 2))
    runtime = make_runtime(tmp_path)
    transport = FakeTransport()
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)
    pending = json.loads(controller.launch("com.example.app", True))
    action_id = pending["action_id"]
    transport.receipt = _signed_receipt_for_request(transport, action_id, "7" * 32)
    outcome_calls = []
    original_outcome = transport.outcome

    def counted_outcome(selected_action_id):
        outcome_calls.append(selected_action_id)
        return original_outcome(selected_action_id)

    transport.outcome = counted_outcome
    original_persist = android_outcomes.persist_companion_outcome

    def crash_before_store_commit(*args, **kwargs):
        raise OSError("simulated process death after receipt claim")

    monkeypatch.setattr(android_outcomes, "persist_companion_outcome", crash_before_store_commit)
    with pytest.raises(OSError, match="simulated process death"):
        controller.poll(action_id)
    assert controller.broker.action_state(action_id) == "RECEIPT_CONSUMED"
    assert runtime.store.one(
        "SELECT 1 FROM packets WHERE kind='ActionOutcome' AND json_extract(payload,'$.action_id')=?",
        (action_id,),
    ) is None
    assert len(outcome_calls) == 1
    controller.broker.close()

    monkeypatch.setattr(android_outcomes, "persist_companion_outcome", original_persist)
    restarted = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    recovered = json.loads(restarted.poll(action_id))
    assert recovered["status"] == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert recovered["observed"] is False
    assert recovered["t8_authoritative"] is False
    assert recovered["world_learning_eligible"] is False
    assert len(outcome_calls) == 2
    assert len(transport.submitted) == 1
    assert restarted.broker.action_state(action_id) == "RECEIPT_VERIFIED"
    restarted.broker.close()
    runtime.store.close()


def test_committed_receipt_recovers_locally_after_broker_finalize_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "3" * (size * 2))
    runtime = make_runtime(tmp_path)
    transport = FakeTransport()
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)
    pending = json.loads(controller.launch("com.example.app", True))
    action_id = pending["action_id"]
    transport.receipt = _signed_receipt_for_request(transport, action_id, "8" * 32)
    outcome_calls = []
    original_outcome = transport.outcome

    def counted_outcome(selected_action_id):
        outcome_calls.append(selected_action_id)
        return original_outcome(selected_action_id)

    transport.outcome = counted_outcome
    original_record = controller.broker.record_companion_receipt

    def crash_after_store_commit(selected_action_id, digest, *, verified):
        if verified:
            raise OSError("simulated process death after Store commit")
        return original_record(selected_action_id, digest, verified=verified)

    monkeypatch.setattr(controller.broker, "record_companion_receipt", crash_after_store_commit)
    with pytest.raises(OSError, match="after Store commit"):
        controller.poll(action_id)
    assert controller.broker.action_state(action_id) == "RECEIPT_CONSUMED"
    assert runtime.store.one(
        "SELECT 1 FROM packets WHERE kind='ActionOutcome' AND json_extract(payload,'$.action_id')=?",
        (action_id,),
    ) is not None
    assert len(outcome_calls) == 1
    controller.broker.close()

    restarted = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    recovered = json.loads(restarted.poll(action_id))
    assert recovered["status"] == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert recovered["recovered_from_store"] is True
    assert recovered["observed"] is False
    assert recovered["t8_authoritative"] is False
    assert recovered["world_learning_eligible"] is False
    assert len(outcome_calls) == 1
    assert len(transport.submitted) == 1
    assert restarted.broker.action_state(action_id) == "RECEIPT_VERIFIED"
    restarted.broker.close()
    runtime.store.close()


def test_committed_receipt_recovery_rejects_tampered_store_digest_without_remote_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "4" * (size * 2))
    runtime = make_runtime(tmp_path)
    transport = FakeTransport()
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)
    pending = json.loads(controller.launch("com.example.app", True))
    action_id = pending["action_id"]
    transport.receipt = _signed_receipt_for_request(transport, action_id, "9" * 32)
    outcome_calls = []
    original_outcome = transport.outcome

    def counted_outcome(selected_action_id):
        outcome_calls.append(selected_action_id)
        return original_outcome(selected_action_id)

    transport.outcome = counted_outcome
    original_record = controller.broker.record_companion_receipt

    def crash_after_store_commit(selected_action_id, digest, *, verified):
        if verified:
            raise OSError("simulated process death after Store commit")
        return original_record(selected_action_id, digest, verified=verified)

    monkeypatch.setattr(controller.broker, "record_companion_receipt", crash_after_store_commit)
    with pytest.raises(OSError, match="after Store commit"):
        controller.poll(action_id)
    controller.broker.close()

    with runtime.store.mutex:
        row = runtime.store.db.execute(
            "SELECT id,payload FROM packets WHERE kind='ActionOutcome' AND json_extract(payload,'$.action_id')=?",
            (action_id,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row["payload"])
        payload["actual"]["digest"] = "f" * 64
        runtime.store.db.execute(
            "UPDATE packets SET payload=? WHERE id=?",
            (json.dumps(payload, sort_keys=True), row["id"]),
        )

    restarted = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    with pytest.raises(android_control.ControlDenied, match="receipt-only authority checks"):
        restarted.poll(action_id)
    assert restarted.broker.action_state(action_id) == "RECEIPT_CONSUMED"
    assert len(outcome_calls) == 1
    assert len(transport.submitted) == 1
    restarted.broker.close()
    runtime.store.close()

def test_action_intent_persistence_failure_cancels_before_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "5" * (size * 2))
    runtime = make_runtime(tmp_path)
    transport = FakeTransport()
    controller = AndroidCompanionController(runtime, transport=transport, clock=lambda: 1000.0)
    controller.trust(KEY_ID, True)

    original_add_packet = runtime.store.add_packet

    def fail_intent_persistence(kind, value):
        if kind == "ActionIntent":
            raise OSError("intent persistence unavailable")
        return original_add_packet(kind, value)

    monkeypatch.setattr(runtime.store, "add_packet", fail_intent_persistence)
    try:
        with pytest.raises(OSError, match="intent persistence unavailable"):
            controller.launch("com.example.app", True)

        action_id = "5" * 32
        assert controller.broker.action_state(action_id) == "CANCELLED"
        assert transport.submitted == []
        assert runtime.store.one(
            "SELECT 1 FROM packets WHERE kind='ActionIntent' AND json_extract(payload,'$.action_id')=?",
            (action_id,),
        ) is None
    finally:
        controller.broker.close()
        runtime.store.close()
