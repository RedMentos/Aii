import base64
import json

import pytest

from v13 import android_control
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
