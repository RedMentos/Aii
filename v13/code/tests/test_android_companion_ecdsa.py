import copy
import json
import base64

import pytest

from v13 import android_control
from v13.android_companion_ecdsa import ECDSAReceiptVerifier
from v13.android_companion_protocol import CompanionDenied
from v13.android_outcomes import accept_and_persist_companion_receipt, trusted_transition_eligible
from v13.store import Store


PUBLIC_KEY = bytes.fromhex(
    "046b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296"
    "4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5"
)
KEY_ID = "698bea63dc44a344663ff1429aea10842df27b6b991ef25866b2c6c02cdcc5be"
SIGNATURE = "MEUCIQCj6DaMCL0/ofDX/AxaFXbnT+ItjasEn7c0HNpRmsW28AIgQ6UwgRkmD46+1dAyhr1NOR6tBMlnER7j/f6Lz9RiKBI="
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
RECEIPT = {"body": BODY, "key_id": KEY_ID, "signature": SIGNATURE}
DENIAL_BODY = {
    **BODY, "nonce": "3" * 32, "status": "USER_DENIED", "local_consent": False,
}
DENIAL_RECEIPT = {
    "body": DENIAL_BODY, "key_id": KEY_ID,
    "signature": "MEYCIQCYn0+HoA+9gtJtrgVHZQKBjFyYZYlx8rZCwrGmXW1l+QIhALh6j5POEMCWZ/+3Kv0o2b6SwLHze1CATCRbGHjZhkgQ",
}
FAILED_BODY = {
    **BODY, "nonce": "4" * 32, "status": "FAILED_TO_DISPATCH", "local_consent": True,
}
FAILED_RECEIPT = {
    "body": FAILED_BODY, "key_id": KEY_ID,
    "signature": "MEYCIQCP5EHhE3jytExvf7pDOuTWiJ68O/EnaVUYEGfgUxI7wgIhALxgnBWYC60h84Zkk/ez/IGotFur/iLq9egH1zTS17n+",
}
UNKNOWN_BODY = {
    **BODY, "nonce": "5" * 32, "status": "OUTCOME_UNKNOWN", "local_consent": True,
}
UNKNOWN_RECEIPT = {
    "body": UNKNOWN_BODY, "key_id": KEY_ID,
    "signature": "MEQCIBPKs5qyAcPpLiJkD9fTWkWv2BFfkx16ItaMJuz34DpvAiBZuWaR9L8gPtSGPUAR782DiT8IRO5PJPoQxTHGy6ZtrA==",
}

ENVELOPE = {
    "action_id": BODY["action_id"],
    "capability": BODY["capability"],
    "digest": BODY["digest"],
}


def verifier(path, clock=lambda: 1000.0):
    value = ECDSAReceiptVerifier(path, PUBLIC_KEY, KEY_ID, clock=clock)
    value.start()
    return value


def test_pinned_android_keystore_signature_verifies(tmp_path):
    value = verifier(tmp_path / "ecdsa.sqlite")
    attestation = value.verify(ENVELOPE, RECEIPT, consume_nonce=False)
    assert attestation["auth_scheme"] == "ECDSA_P256_SHA256_ANDROID_KEYSTORE"
    assert attestation["status"] == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert attestation["local_approval_evidence"] == "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"
    assert attestation["key_storage_status"] == "ANDROID_KEYSTORE_SOFTWARE_BACKED"
    assert attestation["t8_authoritative"] is False
    value.close()


def test_signed_user_denial_and_dispatch_failure_remain_non_authoritative(tmp_path):
    value = verifier(tmp_path / "outcomes.sqlite")
    denied = value.verify(ENVELOPE, DENIAL_RECEIPT, consume_nonce=False)
    failed = value.verify(ENVELOPE, FAILED_RECEIPT, consume_nonce=False)
    assert denied["status"] == "COMPANION_USER_DENIED"
    assert denied["companion_local_consent_claim"] is False
    assert denied["local_approval_evidence"] == "ANDROID_COMPANION_USER_DENIAL"
    assert failed["status"] == "COMPANION_DISPATCH_FAILED"
    assert failed["companion_local_consent_claim"] is True
    assert failed["local_approval_evidence"] == "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"
    assert denied["t8_authoritative"] is False
    assert failed["t8_authoritative"] is False
    value.close()


def test_signed_unknown_outcome_is_approved_but_not_claimed_as_dispatched(tmp_path):
    value = verifier(tmp_path / "unknown.sqlite")
    unknown = value.verify(ENVELOPE, UNKNOWN_RECEIPT, consume_nonce=False)
    assert unknown["status"] == "COMPANION_OUTCOME_UNKNOWN"
    assert unknown["receipt_status"] == "OUTCOME_UNKNOWN"
    assert unknown["companion_local_consent_claim"] is True
    assert unknown["local_approval_evidence"] == "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"
    assert unknown["observed"] is False
    assert unknown["t8_authoritative"] is False
    value.close()


def test_signature_scope_status_and_key_pin_fail_closed(tmp_path):
    value = verifier(tmp_path / "ecdsa.sqlite")
    changed = copy.deepcopy(RECEIPT)
    changed["body"]["status"] = "EXECUTED"
    with pytest.raises(CompanionDenied):
        value.verify(ENVELOPE, changed, consume_nonce=False)
    changed = copy.deepcopy(RECEIPT)
    changed["body"]["observed"] = True
    with pytest.raises(CompanionDenied):
        value.verify(ENVELOPE, changed, consume_nonce=False)
    with pytest.raises(CompanionDenied, match="scope mismatch"):
        value.verify({**ENVELOPE, "digest": "b" * 64}, RECEIPT, consume_nonce=False)
    with pytest.raises(ValueError, match="fingerprint"):
        ECDSAReceiptVerifier(tmp_path / "wrong.sqlite", PUBLIC_KEY, "0" * 64)
    value.close()


def test_ecdsa_nonce_is_single_use_when_verifier_owns_commit(tmp_path):
    value = verifier(tmp_path / "ecdsa.sqlite")
    value.verify(ENVELOPE, RECEIPT, consume_nonce=True)
    with pytest.raises(CompanionDenied, match="replay"):
        value.verify(ENVELOPE, RECEIPT, consume_nonce=True)
    value.close()


def test_signed_user_denial_persists_without_learning_authority(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "2" * (size * 2))
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session()
    event = store.event(session, "open the approved app")
    broker = android_control.AndroidControlBroker(tmp_path / "denied-broker.sqlite", clock=lambda: 1000.0)
    receipt_verifier = verifier(tmp_path / "denied-ecdsa.sqlite")
    broker.start()
    proposal = broker.propose(
        "launch_app", {"package": "com.example.app"}, ttl=30,
        event_id=event["event_id"], source_ref=event["source_ref"],
    )
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    broker.dispatch_approved(proposal.action_id)
    outcome, packet = accept_and_persist_companion_receipt(
        store, broker, receipt_verifier, proposal.action_id, DENIAL_RECEIPT
    )
    assert outcome.status == "COMPANION_USER_DENIED"
    assert outcome.details["companion_local_consent_claim"] is False
    assert outcome.details["local_approval_evidence"] == "ANDROID_COMPANION_USER_DENIAL"
    assert outcome.observed is False
    assert trusted_transition_eligible(outcome) is False
    stored = store.one("SELECT payload FROM packets WHERE id=?", (packet["packet_id"],))
    stored_packet = json.loads(stored["payload"])
    actual = stored_packet["actual"]
    assert stored_packet["status"] == "COMPANION_USER_DENIED"
    assert actual["receipt_status"] == "USER_DENIED"
    assert actual["companion_local_consent_claim"] is False
    assert actual["world_learning_eligible"] is False
    store.close()
    broker.close()
    receipt_verifier.close()


def test_keystore_receipt_persists_source_bound_non_authoritative_outcome(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "2" * (size * 2))
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session()
    event = store.event(session, "open the approved app")

    broker = android_control.AndroidControlBroker(tmp_path / "broker.sqlite", clock=lambda: 1000.0)
    receipt_verifier = verifier(tmp_path / "ecdsa.sqlite")
    broker.start()
    proposal = broker.propose(
        "launch_app", {"package": "com.example.app"}, ttl=30,
        event_id=event["event_id"], source_ref=event["source_ref"],
    )
    assert proposal.action_id == BODY["action_id"]
    assert proposal.digest == BODY["digest"]
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    broker.dispatch_approved(proposal.action_id)

    outcome, packet = accept_and_persist_companion_receipt(
        store, broker, receipt_verifier, proposal.action_id, RECEIPT
    )
    assert outcome.status == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert outcome.observed is False
    assert outcome.evidence_level == "COMPANION_RECEIPT_ONLY"
    assert outcome.details["local_approval_evidence"] == "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"
    assert outcome.details["android_os_permission_status"] == "NOT_REQUIRED_FOR_LAUNCH_APP"
    assert outcome.details["key_storage_status"] == "ANDROID_KEYSTORE_SOFTWARE_BACKED"
    assert outcome.details["t8_authoritative"] is False
    assert outcome.details["world_learning_eligible"] is False
    assert trusted_transition_eligible(outcome) is False

    stored = store.one("SELECT kind,payload FROM packets WHERE id=?", (packet["packet_id"],))
    assert stored["kind"] == "ActionOutcome"
    actual = json.loads(stored["payload"])["actual"]
    assert actual["auth_scheme"] == "ECDSA_P256_SHA256_ANDROID_KEYSTORE"
    assert actual["observed"] is False
    assert actual["t8_authoritative"] is False
    assert actual["world_learning_eligible"] is False
    assert actual["local_approval_evidence"] == "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"
    assert actual["receipt_verified_at"] == 1000.0
    assert actual["signed_receipt"]["body"]["issued_at"] == 999

    store.close()
    broker.close()
    receipt_verifier.close()


def test_keystore_unknown_outcome_persists_without_learning_authority(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "2" * (size * 2))
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session()
    event = store.event(session, "open the approved app")
    broker = android_control.AndroidControlBroker(tmp_path / "unknown-broker.sqlite", clock=lambda: 1000.0)
    receipt_verifier = verifier(tmp_path / "unknown-receipts.sqlite")
    broker.start()
    proposal = broker.propose("launch_app", {"package": "com.example.app"}, ttl=30,
        event_id=event["event_id"], source_ref=event["source_ref"])
    assert proposal.action_id == BODY["action_id"] and proposal.digest == BODY["digest"]
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    broker.dispatch_approved(proposal.action_id)
    outcome, packet = accept_and_persist_companion_receipt(
        store, broker, receipt_verifier, proposal.action_id, UNKNOWN_RECEIPT)
    assert outcome.status == "COMPANION_OUTCOME_UNKNOWN"
    assert outcome.details["receipt_status"] == "OUTCOME_UNKNOWN"
    assert outcome.details["companion_local_consent_claim"] is True
    assert outcome.details["local_approval_evidence"] == "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"
    assert outcome.observed is False and outcome.details["t8_authoritative"] is False
    assert outcome.details["world_learning_eligible"] is False
    stored = store.one("SELECT payload FROM packets WHERE id=?", (packet["packet_id"],))
    assert json.loads(stored["payload"])["actual"]["receipt_status"] == "OUTCOME_UNKNOWN"
    store.close(); broker.close(); receipt_verifier.close()


def test_store_failure_keeps_signed_receipt_retryable_until_durable_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(android_control.secrets, "token_hex", lambda size: "2" * (size * 2))
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session()
    event = store.event(session, "open the approved app")
    broker = android_control.AndroidControlBroker(tmp_path / "retry-broker.sqlite", clock=lambda: 1000.0)
    receipt_verifier = verifier(tmp_path / "retry-ecdsa.sqlite")
    broker.start()
    proposal = broker.propose(
        "launch_app", {"package": "com.example.app"}, ttl=30,
        event_id=event["event_id"], source_ref=event["source_ref"],
    )
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    broker.dispatch_approved(proposal.action_id)

    original_tx = store.tx
    calls = {"count": 0}

    def fail_once():
        if calls["count"] == 0:
            calls["count"] += 1
            raise OSError("simulated Store write failure")
        return original_tx()

    monkeypatch.setattr(store, "tx", fail_once)
    with pytest.raises(OSError, match="simulated Store write failure"):
        accept_and_persist_companion_receipt(
            store, broker, receipt_verifier, proposal.action_id, RECEIPT
        )

    assert broker.action_state(proposal.action_id) == "RECEIPT_CONSUMED"

    outcome, packet = accept_and_persist_companion_receipt(
        store, broker, receipt_verifier, proposal.action_id, RECEIPT
    )
    assert outcome.status == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert broker.action_state(proposal.action_id) == "RECEIPT_VERIFIED"
    stored_count = store.one(
        "SELECT COUNT(*) AS count FROM packets WHERE kind=? AND event_id=?",
        ("ActionOutcome", event["event_id"]),
    )
    assert stored_count["count"] == 1
    stored = store.one("SELECT payload FROM packets WHERE id=?", (packet["packet_id"],))
    actual = json.loads(stored["payload"])["actual"]
    assert actual["receipt_nonce"] == BODY["nonce"]
    assert actual["t8_authoritative"] is False
    assert actual["world_learning_eligible"] is False

    store.close()
    broker.close()
    receipt_verifier.close()
