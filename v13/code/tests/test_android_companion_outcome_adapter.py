import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_outcomes import (
    accept_companion_receipt, accept_and_persist_companion_receipt,
    persist_companion_outcome, trusted_transition_eligible, InvalidOutcome,
    ActionOutcome,
)
from v13.store import Store
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


def make_real_store(tmp_path):
    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session()
    event = store.event(session, "open the approved app")
    return store, event, home


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
    assert envelope["android_os_permission_required"] is False
    assert envelope["permission_bypass"] is False
    assert envelope["model_authority"] is False
    with pytest.raises(ControlDenied):
        broker.dispatch_approved(p.action_id)
    broker.close()


def test_valid_receipt_persists_through_real_store_and_notifies_after_commit(tmp_path):
    broker, verifier = setup(tmp_path)
    store, event, _ = make_real_store(tmp_path)
    proposal, envelope = approved_dispatch(
        broker, event_id=event["event_id"], source_ref=event["source_ref"]
    )
    assert envelope["action_id"] == proposal.action_id
    receipt = make_receipt(proposal, nonce="a" * 32)
    notified = []
    outcome, packet = accept_and_persist_companion_receipt(
        store, broker, verifier, proposal.action_id, receipt,
        on_outcome=notified.append,
    )
    assert outcome.status == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
    assert outcome.observed is False
    assert outcome.evidence_level == "COMPANION_RECEIPT_ONLY"
    assert outcome.details["auth_scheme"] == "HMAC_SHA256_PER_INSTALL"
    assert outcome.details["receipt_nonce"] == "a" * 32
    assert outcome.details["t8_authoritative"] is False
    assert outcome.details["world_learning_eligible"] is False
    assert trusted_transition_eligible(outcome) is False
    assert packet["provenance"] == [event["source_ref"]]
    stored = store.one("SELECT kind,payload FROM packets WHERE id=?", (packet["packet_id"],))
    assert stored["kind"] == "ActionOutcome"
    stored_packet = json.loads(stored["payload"])
    actual = stored_packet["actual"]
    assert actual["outcome_kind"] == "ANDROID_COMPANION_RECEIPT"
    assert actual["observed"] is False
    assert actual["auth_scheme"] == "HMAC_SHA256_PER_INSTALL"
    assert actual["receipt_nonce"] == "a" * 32
    assert actual["companion_local_consent_claim"] is True
    assert actual["local_approval_evidence"] == "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION"
    assert actual["android_os_permission_status"] == "REQUIRED_NOT_VERIFIED"
    assert actual["key_storage_status"] == "UNVERIFIED"
    assert actual["t8_authoritative"] is False
    assert actual["world_learning_eligible"] is False
    assert actual["trusted_transition_eligible"] is False
    assert notified == [outcome]
    assert store.one("SELECT payload FROM packets WHERE id=?", (packet["packet_id"],)) is not None
    assert store.read_source(event["source_ref"]) == "open the approved app"
    forged = ActionOutcome(
        action_id=outcome.action_id, capability=outcome.capability,
        status=outcome.status, timestamp=outcome.timestamp, observed=True, evidence_level=outcome.evidence_level,
        details=outcome.details,
    )
    with pytest.raises(InvalidOutcome, match="non-authoritative"):
        persist_companion_outcome(store, forged)
    store.close()
    broker.close()
    verifier.close()


def test_replay_rejects_second_action_at_atomic_store_commit(tmp_path):
    broker, verifier = setup(tmp_path)
    store, event, _ = make_real_store(tmp_path)
    first, _ = approved_dispatch(
        broker, event_id=event["event_id"], source_ref=event["source_ref"]
    )
    receipt = make_receipt(first, nonce="b" * 32)
    first_outcome = accept_companion_receipt(broker, verifier, first.action_id, receipt)
    first_packet = persist_companion_outcome(store, first_outcome)
    second, _ = approved_dispatch(
        broker, event_id=event["event_id"], source_ref=event["source_ref"]
    )
    replay = make_receipt(second, nonce="b" * 32)
    second_outcome = accept_companion_receipt(broker, verifier, second.action_id, replay)
    with pytest.raises(InvalidOutcome, match="receipt nonce replay"):
        persist_companion_outcome(store, second_outcome)
    assert second.action_id not in broker.dispatched
    assert store.one(
        "SELECT payload FROM packets WHERE id=?", (first_packet["packet_id"],)
    ) is not None
    assert len(store.rows("SELECT id FROM packets WHERE kind='ActionOutcome'")) == 1
    store.close()
    broker.close()
    verifier.close()


def test_nonce_replay_rejected_across_distinct_source_events(tmp_path):
    broker, verifier = setup(tmp_path)
    store, first_event, _ = make_real_store(tmp_path)
    second_session = store.new_session("second source")
    second_event = store.event(second_session, "open settings")

    first, _ = approved_dispatch(
        broker, event_id=first_event["event_id"], source_ref=first_event["source_ref"]
    )
    first_outcome = accept_companion_receipt(
        broker, verifier, first.action_id, make_receipt(first, nonce="c" * 32)
    )
    persist_companion_outcome(store, first_outcome)

    second, _ = approved_dispatch(
        broker, event_id=second_event["event_id"], source_ref=second_event["source_ref"]
    )
    second_outcome = accept_companion_receipt(
        broker, verifier, second.action_id, make_receipt(second, nonce="c" * 32)
    )
    with pytest.raises(InvalidOutcome, match="receipt nonce replay"):
        persist_companion_outcome(store, second_outcome)

    assert len(store.rows("SELECT id FROM packets WHERE kind='ActionOutcome'")) == 1
    store.close()
    broker.close()
    verifier.close()


def test_companion_persistence_is_idempotent_after_store_restart(tmp_path):
    broker, verifier = setup(tmp_path)
    store, event, home = make_real_store(tmp_path)
    proposal, _ = approved_dispatch(
        broker, event_id=event["event_id"], source_ref=event["source_ref"]
    )
    outcome = accept_companion_receipt(
        broker, verifier, proposal.action_id,
        make_receipt(proposal, nonce="6" * 32),
    )
    first = persist_companion_outcome(store, outcome)
    store.close()
    reopened = Store(home)
    second = persist_companion_outcome(reopened, outcome)
    assert second["packet_id"] == first["packet_id"]
    assert len(reopened.rows("SELECT id FROM packets WHERE kind='ActionOutcome'")) == 1
    reopened.close()
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
    bad_mac = make_receipt(proposal, nonce="8" * 32)
    bad_mac["mac"] = "0" * 64
    with pytest.raises(CompanionDenied, match="invalid authentication"):
        accept_companion_receipt(broker, verifier, proposal.action_id, bad_mac)
    assert proposal.action_id not in broker.dispatched
    proposal2, _ = approved_dispatch(broker)
    too_long = make_receipt(proposal2, nonce="9" * 32)
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
        make_receipt(proposal, nonce="7" * 32),
    )
    with pytest.raises(InvalidOutcome, match="source-bound event"):
        persist_companion_outcome(FakeStore("evt-android-1", SOURCE_REF), outcome)
    broker.close()
    verifier.close()
