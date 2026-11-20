import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_outcomes import (
    accept_companion_receipt, persist_companion_outcome,
    trusted_transition_eligible, InvalidOutcome,
)
from v13.android_companion_protocol import (
    ReceiptVerifier, CompanionDenied, SCHEMA, sign_fixture,
)


SECRET = b"per-install-test-secret-32-bytes!!"
SOURCE_REF = {
    "source_id": "src-android-1",
    "sha256": "a" * 64,
    "char_start": 0,
    "char_end": 18,
    "modality": "text",
}


def make_receipt(proposal, *, nonce, now=1000.0, capability=None, local_consent=True):
    body = {
        "schema": SCHEMA,
        "nonce": nonce,
        "action_id": proposal.action_id,
        "capability": capability or proposal.capability,
        "digest": proposal.digest,
        "issued_at": now - 1,
        "expires_at": now + 30,
        "status": "EXECUTED",
        "local_consent": local_consent,
    }
    return {"body": body, "mac": sign_fixture(SECRET, body)}


class FakeStore:
    def __init__(self, event_id, source_ref):
        self.event_id = event_id
        self.source_ref = source_ref
        self.packets = []
        self.event = {
            "event_id": event_id,
            "brain_generation_id": "gen-android-1",
            "source_ref": source_ref,
        }

    def one(self, sql, params):
        if params == (self.event_id,):
            return {"packet": json.dumps(self.event)}
        return None

    def read_source(self, ref):
        if ref != self.source_ref:
            raise ValueError("unknown source")
        return "open the approved app"

    def add_packet(self, kind, value):
        self.packets.append((kind, value))


def setup(tmp_path, *, clock=lambda: 1000.0):
    broker = AndroidControlBroker(tmp_path / "broker.sqlite", clock=clock)
    verifier = ReceiptVerifier(tmp_path / "receipt.sqlite", SECRET, clock=clock)
    broker.start()
    verifier.start()
    return broker, verifier


def approved_dispatch(broker, *, event_id="evt-android-1", source_ref=SOURCE_REF):
    proposal = broker.propose(
        "back", {}, ttl=30, event_id=event_id, source_ref=source_ref
    )
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    envelope = broker.dispatch_approved(proposal.action_id)
    return proposal, envelope


def test_dispatch_requires_local_approval_and_marks_companion_boundaries(tmp_path):
    broker = AndroidControlBroker(tmp_path / "broker.sqlite", clock=lambda: 1000.0)
    broker.start()
    p = broker.propose("back", {}, ttl=30)
    with pytest.raises(ControlDenied):
        broker.dispatch_approved(p.action_id)
    broker.approve(p.action_id, confirmed_by_local_ui=True)
    envelope = broker.dispatch_approved(p.action_id)
    assert envelope["schema"] == "v14.android-action-request/1"
    assert envelope["companion_local_consent_required"] is True
    assert envelope["android_os_permission_required"] is True
    assert envelope["permission_bypass"] is False
    assert envelope["model_authority"] is False
    with pytest.raises(ControlDenied):
        broker.dispatch_approved(p.action_id)
    broker.close()


def test_valid_receipt_returns_non_authoritative_typed_outcome_and_packet(tmp_path):
    broker, verifier = setup(tmp_path)
    proposal, envelope = approved_dispatch(broker)
    assert envelope["action_id"] == proposal.action_id
    receipt = make_receipt(proposal, nonce="a" * 32)
    outcome = accept_companion_receipt(broker, verifier, proposal.action_id, receipt)
    assert outcome.status == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert outcome.observed is False
    assert outcome.evidence_level == "COMPANION_RECEIPT_ONLY"
    assert outcome.details["auth_scheme"] == "HMAC_SHA256_PER_INSTALL"
    assert outcome.details["t8_authoritative"] is False
    assert outcome.details["world_learning_eligible"] is False
    assert trusted_transition_eligible(outcome) is False
    store = FakeStore("evt-android-1", SOURCE_REF)
    packet = persist_companion_outcome(store, outcome)
    assert packet["kind"] == "AndroidActionOutcome"
    assert packet["source_refs"] == [SOURCE_REF]
    assert packet["observed"] is False
    assert packet["auth_scheme"] == "HMAC_SHA256_PER_INSTALL"
    assert packet["t8_authoritative"] is False
    assert packet["world_learning_eligible"] is False
    assert packet["trusted_transition_eligible"] is False
    assert store.packets == [("AndroidActionOutcome", packet)]
    broker.close()
    verifier.close()


def test_replay_rejects_and_consumes_second_approval(tmp_path):
    broker, verifier = setup(tmp_path)
    first, _ = approved_dispatch(broker)
    receipt = make_receipt(first, nonce="b" * 32)
    accept_companion_receipt(broker, verifier, first.action_id, receipt)
    second, _ = approved_dispatch(broker)
    replay = make_receipt(second, nonce="b" * 32)
    with pytest.raises(CompanionDenied, match="replay"):
        accept_companion_receipt(broker, verifier, second.action_id, replay)
    assert second.action_id not in broker.dispatched
    assert any(row[1] == "companion_receipt_rejected" for row in broker.events())
    broker.close()
    verifier.close()


def test_scope_and_local_consent_mismatch_fail_closed(tmp_path):
    broker, verifier = setup(tmp_path)
    proposal, _ = approved_dispatch(broker)
    wrong_scope = make_receipt(proposal, nonce="c" * 32, capability="tap")
    with pytest.raises(CompanionDenied, match="scope mismatch"):
        accept_companion_receipt(broker, verifier, proposal.action_id, wrong_scope)
    assert proposal.action_id not in broker.dispatched
    proposal2, _ = approved_dispatch(broker)
    no_consent = make_receipt(proposal2, nonce="d" * 32, local_consent=False)
    with pytest.raises(CompanionDenied, match="no confirmed execution"):
        accept_companion_receipt(broker, verifier, proposal2.action_id, no_consent)
    broker.close()
    verifier.close()


def test_stop_expiry_and_restart_revoke_dispatched_actions(tmp_path):
    now = [1000.0]
    broker, verifier = setup(tmp_path, clock=lambda: now[0])
    proposal, _ = approved_dispatch(broker)
    broker.stop()
    with pytest.raises(ControlDenied):
        accept_companion_receipt(broker, verifier, proposal.action_id,
                                 make_receipt(proposal, nonce="e" * 32))
    broker.start()
    proposal2, _ = approved_dispatch(broker)
    now[0] = 1031.0
    with pytest.raises(ControlDenied):
        accept_companion_receipt(broker, verifier, proposal2.action_id,
                                 make_receipt(proposal2, nonce="f" * 32, now=1031.0))
    broker.close()
    verifier.close()


def test_receipt_verifier_is_thread_safe_and_nonce_is_single_use(tmp_path):
    verifier = ReceiptVerifier(tmp_path / "receipt.sqlite", SECRET, clock=lambda: 1000.0)
    verifier.start()
    proposal = type("P", (), {"action_id": "1" * 32, "capability": "back", "digest": "d" * 64})()
    envelope = {"action_id": proposal.action_id, "capability": proposal.capability,
                "digest": proposal.digest}
    body = {"schema": SCHEMA, "nonce": "9" * 32, "action_id": proposal.action_id,
            "capability": proposal.capability, "digest": proposal.digest,
            "issued_at": 999.0, "expires_at": 1020.0, "status": "EXECUTED",
            "local_consent": True}
    receipt = {"body": body, "mac": sign_fixture(SECRET, body)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _verify_once(verifier, envelope, receipt), range(2)))
    assert sum(result == "OK" for result in results) == 1
    assert sum(result == "REPLAY" for result in results) == 1
    verifier.close()


def _verify_once(verifier, envelope, receipt):
    try:
        verifier.verify(envelope, receipt)
        return "OK"
    except CompanionDenied as exc:
        if "replay" in str(exc):
            return "REPLAY"
        raise


def test_invalid_mac_and_expired_receipt_consume_dispatch(tmp_path):
    broker, verifier = setup(tmp_path)
    proposal, _ = approved_dispatch(broker)
    bad_mac = make_receipt(proposal, nonce="h" * 32)
    bad_mac["mac"] = "0" * 64
    with pytest.raises(CompanionDenied, match="invalid authentication"):
        accept_companion_receipt(broker, verifier, proposal.action_id, bad_mac)
    assert proposal.action_id not in broker.dispatched
    proposal2, _ = approved_dispatch(broker)
    too_long = make_receipt(proposal2, nonce="i" * 32)
    too_long["body"]["issued_at"] = 900.0
    too_long["body"]["expires_at"] = 1100.0
    too_long["mac"] = sign_fixture(SECRET, too_long["body"])
    with pytest.raises(CompanionDenied, match="expired receipt"):
        accept_companion_receipt(broker, verifier, proposal2.action_id, too_long)
    assert proposal2.action_id not in broker.dispatched
    broker.close()
    verifier.close()


def test_source_reference_validation_is_fail_closed(tmp_path):
    broker = AndroidControlBroker(tmp_path / "broker.sqlite", clock=lambda: 1000.0)
    broker.start()
    with pytest.raises(ControlDenied):
        broker.propose("back", {}, event_id="evt", source_ref={"source_id": "x", "sha256": "bad"})
    with pytest.raises(ControlDenied):
        broker.propose("back", {}, event_id="evt", source_ref=None)
    broker.close()


def test_persist_requires_source_binding(tmp_path):
    broker, verifier = setup(tmp_path)
    proposal, _ = approved_dispatch(broker, source_ref=None, event_id=None)
    outcome = accept_companion_receipt(
        broker, verifier, proposal.action_id,
        make_receipt(proposal, nonce="g" * 32),
    )
    with pytest.raises(InvalidOutcome, match="source-bound event"):
        persist_companion_outcome(FakeStore("evt-android-1", SOURCE_REF), outcome)
    broker.close()
    verifier.close()
