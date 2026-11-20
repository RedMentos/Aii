import pytest
from v13.android_control import AndroidControlBroker, ControlDenied


def test_denied_until_explicit_local_confirmation_and_one_shot(tmp_path):
    b = AndroidControlBroker(tmp_path / "audit.sqlite")
    p = b.propose("tap", {"x": 10, "y": 20})
    with pytest.raises(ControlDenied):
        b.approve(p.action_id, confirmed_by_local_ui=True)
    b.start()
    p = b.propose("tap", {"x": 10, "y": 20})
    with pytest.raises(ControlDenied):
        b.approve(p.action_id)
    p = b.propose("tap", {"x": 10, "y": 20})
    b.approve(p.action_id, confirmed_by_local_ui=True)
    assert b.execute(p.action_id)["status"] == "DRY_RUN_ONLY"
    with pytest.raises(ControlDenied):
        b.execute(p.action_id)
    assert any(row[1] == "dry_run" for row in b.events())
    b.close()


def test_stop_expiry_and_live_refusal(tmp_path):
    now = [100.0]
    b = AndroidControlBroker(tmp_path / "audit.sqlite", clock=lambda: now[0])
    b.start()
    p = b.propose("back", {}, ttl=1)
    now[0] += 2
    with pytest.raises(ControlDenied):
        b.approve(p.action_id, confirmed_by_local_ui=True)
    p = b.propose("observe_ui", {})
    b.approve(p.action_id, confirmed_by_local_ui=True)
    with pytest.raises(ControlDenied, match="companion"):
        b.execute(p.action_id, dry_run=False)
    p = b.propose("back", {})
    b.approve(p.action_id, confirmed_by_local_ui=True)
    b.stop()
    with pytest.raises(ControlDenied):
        b.execute(p.action_id)


@pytest.mark.parametrize("cap,args", [
    ("shell", {"command": "rm -rf /"}), ("tap", {"x": True, "y": 2}),
    ("type_text", {"text": "a\nsecret"}), ("launch_app", {"package": "../bad"}),
    ("swipe", {"x1": 0, "y1": 0, "x2": 1, "y2": 1, "duration_ms": 99999}),
    ("back", {"extra": 1}),
])
def test_invalid_actions_fail_closed(tmp_path, cap, args):
    b = AndroidControlBroker(tmp_path / "audit.sqlite")
    with pytest.raises(ControlDenied):
        b.propose(cap, args)



def test_companion_receipt_is_persisted_in_real_store(tmp_path):
    from v13.android_companion_protocol import ReceiptVerifier, SCHEMA, sign_fixture
    from v13.android_outcomes import (
        ActionOutcome, InvalidOutcome, accept_and_persist_companion_receipt,
        persist_companion_outcome,
    )
    from v13.store import Store
    from v13.world_model import transitions
    import json

    home = tmp_path / "runtime"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    broker = AndroidControlBroker(tmp_path / "broker.sqlite", clock=lambda: 1000.0)
    secret = b"per-install-test-secret-32-bytes!!"
    verifier = ReceiptVerifier(tmp_path / "receipt.sqlite", secret, clock=lambda: 1000.0)
    try:
        broker.start()
        verifier.start()
        event = store.event(store.new_session(), "open the approved app")
        proposal = broker.propose(
            "back", {}, ttl=30, event_id=event["event_id"],
            source_ref=event["source_ref"],
        )
        broker.approve(proposal.action_id, confirmed_by_local_ui=True)
        broker.dispatch_approved(proposal.action_id)
        body = {
            "schema": SCHEMA, "nonce": "a" * 32,
            "action_id": proposal.action_id, "capability": proposal.capability,
            "digest": proposal.digest, "issued_at": 999.0, "expires_at": 1030.0,
            "status": "EXECUTED", "local_consent": True,
        }
        receipt = {"body": body, "mac": sign_fixture(secret, body)}
        outcome, packet = accept_and_persist_companion_receipt(
            store, broker, verifier, proposal.action_id, receipt,
        )
        row = store.one(
            "SELECT kind,payload FROM packets WHERE id=?", (packet["packet_id"],)
        )
        assert row["kind"] == "ActionOutcome"
        persisted = json.loads(row["payload"])
        assert persisted["provenance"] == [event["source_ref"]]
        actual = persisted["actual"]
        assert actual["outcome_kind"] == "ANDROID_COMPANION_RECEIPT"
        assert actual["observed"] is False
        assert actual["t8_authoritative"] is False
        assert actual["world_learning_eligible"] is False
        assert actual["receipt_nonce"] == "a" * 32
        # Companion receipts are audit packets only: World-JEPA's T8 source
        # consumer reads committed Store.actions + ActionSelection, not this packet.
        assert store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0
        assert all(item["action_id"] != proposal.action_id for item in transitions(store))
        forged = ActionOutcome(
            action_id=outcome.action_id, capability=outcome.capability,
            status=outcome.status, timestamp=outcome.timestamp, observed=True, evidence_level=outcome.evidence_level,
            details=outcome.details,
        )
        with pytest.raises(InvalidOutcome, match="non-authoritative"):
            persist_companion_outcome(store, forged)
        assert outcome.observed is False
    finally:
        store.close()
        broker.close()
        verifier.close()
