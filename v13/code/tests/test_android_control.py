import hashlib
import os
import sqlite3
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest
import v13.android_control as android_control
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



def test_audit_database_is_private_under_permissive_umask(tmp_path):
    path = tmp_path / "audit.sqlite"
    old_umask = os.umask(0)
    try:
        broker = AndroidControlBroker(path)
    finally:
        os.umask(old_umask)
    try:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert broker.db_path == path
    finally:
        broker.close()


def test_existing_audit_database_permissions_are_restricted(tmp_path):
    path = tmp_path / "existing.sqlite"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE existing_row (value TEXT)")
    connection.commit()
    connection.close()
    os.chmod(path, 0o644)

    broker = AndroidControlBroker(path)
    try:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    finally:
        broker.close()


def test_audit_database_rejects_symlink_without_touching_target(tmp_path):
    target = tmp_path / "private-target.sqlite"
    target.write_bytes(b"do not modify")
    link = tmp_path / "audit.sqlite"
    link.symlink_to(target)

    with pytest.raises(ControlDenied):
        AndroidControlBroker(link)

    assert target.read_bytes() == b"do not modify"


def test_audit_database_rejects_symlinked_parent(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real_dir, target_is_directory=True)

    with pytest.raises(ControlDenied):
        AndroidControlBroker(alias / "audit.sqlite")

    assert not (real_dir / "audit.sqlite").exists()


def test_audit_database_rejects_hardlink_without_chmodding_target(tmp_path):
    target = tmp_path / "target.sqlite"
    target.write_bytes(b"not an audit database")
    os.chmod(target, 0o644)
    alias = tmp_path / "audit.sqlite"
    os.link(target, alias)

    with pytest.raises(ControlDenied):
        AndroidControlBroker(alias)

    assert stat.S_IMODE(target.stat().st_mode) == 0o644
    assert target.read_bytes() == b"not an audit database"


def test_audit_database_rejects_unapproved_symlinked_ancestor(tmp_path):
    real_dir = tmp_path / "real"
    nested = real_dir / "nested"
    nested.mkdir(parents=True)
    alias = tmp_path / "caller-controlled-alias"
    alias.symlink_to(real_dir, target_is_directory=True)

    with pytest.raises(ControlDenied, match="unapproved symlink"):
        AndroidControlBroker(alias / "nested" / "audit.sqlite")

    assert not (nested / "audit.sqlite").exists()


def test_legacy_android_data_symlink_allowlist_is_exact():
    from pathlib import Path
    import v13.android_control as android_control

    # Compatibility fallback for releases where this path is a symlink.
    # Android 13 uses a bind mount and is tested separately below.
    assert android_control._ANDROID_PLATFORM_SYMLINKS == (
        (Path("/data/user/0"), Path("/data/data")),
    )


def test_audit_database_allows_only_configured_platform_symlink_alias(tmp_path, monkeypatch):
    import v13.android_control as android_control

    real_dir = tmp_path / "real"
    nested = real_dir / "nested"
    nested.mkdir(parents=True)
    alias = tmp_path / "platform-alias"
    alias.symlink_to(real_dir, target_is_directory=True)
    monkeypatch.setattr(android_control, "_ANDROID_PLATFORM_SYMLINKS", ((alias, real_dir),))

    broker = AndroidControlBroker(alias / "nested" / "audit.sqlite")
    try:
        assert stat.S_IMODE((nested / "audit.sqlite").stat().st_mode) == 0o600
    finally:
        broker.close()


def test_audit_database_rejects_fifo_without_opening_it_for_blocking_io(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation unavailable")
    fifo = tmp_path / "audit.sqlite"
    os.mkfifo(fifo)

    with pytest.raises(ControlDenied):
        AndroidControlBroker(fifo)

    assert stat.S_ISFIFO(fifo.lstat().st_mode)


def test_audit_database_rejects_group_or_world_writable_parent(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    os.chmod(shared, 0o777)

    with pytest.raises(ControlDenied, match="owner-controlled"):
        AndroidControlBroker(shared / "audit.sqlite")

    assert not (shared / "audit.sqlite").exists()


def test_audit_database_rejects_parent_owned_by_another_uid(tmp_path, monkeypatch):
    if not hasattr(os, "getuid"):
        pytest.skip("Android/Linux UID ownership check unavailable")
    real_uid = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: real_uid + 1)

    with pytest.raises(ControlDenied, match="owner"):
        AndroidControlBroker(tmp_path / "audit.sqlite")

    assert not (tmp_path / "audit.sqlite").exists()


def test_audit_database_allows_nonwritable_shared_parent(tmp_path):
    parent = tmp_path / "traversable"
    parent.mkdir()
    os.chmod(parent, 0o755)

    broker = AndroidControlBroker(parent / "audit.sqlite")
    try:
        assert stat.S_IMODE((parent / "audit.sqlite").stat().st_mode) == 0o600
    finally:
        broker.close()


def test_audit_database_rejects_writable_ancestor_even_when_parent_is_private(tmp_path):
    shared = tmp_path / "shared"
    private = shared / "private"
    private.mkdir(parents=True)
    os.chmod(shared, 0o777)
    os.chmod(private, 0o700)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_audit_database_allows_sticky_shared_ancestor(tmp_path):
    shared = tmp_path / "sticky"
    private = shared / "private"
    private.mkdir(parents=True)
    os.chmod(shared, 0o1777)
    os.chmod(private, 0o700)
    broker = AndroidControlBroker(private / "audit.sqlite")
    assert stat.S_IMODE(broker.db_path.stat().st_mode) == 0o600
    broker.close()


def _android13_data_user_zero_path(
    tmp_path, monkeypatch, *, data_mode=0o771, data_uid=1000, data_gid=1000,
    user_mode=0o711, bind_mode=0o771, bind_uid=1000, bind_gid=1000,
    target_mode=0o771, target_uid=1000, target_gid=1000, bind_inode_matches=True,
):
    data_root = tmp_path / "data"
    data_root.mkdir()
    data_data = data_root / "data"
    data_data.mkdir()
    user_root = data_root / "user"
    user_root.mkdir()
    user_zero = user_root / "0"
    user_zero.mkdir()
    private = user_zero / "com.termux"
    private.mkdir()
    os.chmod(data_root, data_mode)
    os.chmod(data_data, target_mode)
    os.chmod(user_root, user_mode)
    os.chmod(user_zero, bind_mode)
    os.chmod(private, 0o700)
    monkeypatch.setattr(android_control, "_ANDROID_DATA_ROOT", data_root)
    real_lstat = Path.lstat
    target_info = real_lstat(data_data)
    synthetic = {
        data_root: (data_uid, data_gid, real_lstat(data_root).st_dev, real_lstat(data_root).st_ino, real_lstat(data_root).st_mode),
        user_root: (android_control._ANDROID_SYSTEM_UID, android_control._ANDROID_SYSTEM_GID, real_lstat(user_root).st_dev, real_lstat(user_root).st_ino, real_lstat(user_root).st_mode),
        data_data: (target_uid, target_gid, target_info.st_dev, target_info.st_ino, stat.S_IFDIR | target_mode),
        user_zero: (
            bind_uid, bind_gid, target_info.st_dev,
            target_info.st_ino if bind_inode_matches else target_info.st_ino + 1,
            stat.S_IFDIR | bind_mode,
        ),
    }

    def android_lstat(path):
        info = real_lstat(path)
        item = synthetic.get(path)
        if item is not None:
            uid, gid, dev, ino, mode = item
            return SimpleNamespace(st_mode=mode, st_uid=uid, st_gid=gid, st_dev=dev, st_ino=ino)
        return info

    monkeypatch.setattr(Path, "lstat", android_lstat)
    return private


def test_android13_data_user_zero_bind_mount_ancestors_allow_exact_system_0771(tmp_path, monkeypatch):
    # AOSP Android 13: /data is 0771 system:system; /data/user is 0711;
    # /data/user/0 and /data/data share the same device/inode via bind mount.
    private = _android13_data_user_zero_path(tmp_path, monkeypatch)
    broker = AndroidControlBroker(private / "audit.sqlite")
    assert stat.S_IMODE(broker.db_path.stat().st_mode) == 0o600
    broker.close()


def test_android13_data_user_zero_rejects_unverified_bind_mount_inode(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, bind_inode_matches=False)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_android13_data_user_zero_rejects_wrong_bind_mount_uid(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, bind_uid=999)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_android13_data_user_zero_rejects_wrong_bind_mount_gid(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, bind_gid=1001)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_android13_data_user_zero_rejects_wrong_bind_mount_mode(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, bind_mode=0o773)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_android13_data_user_zero_rejects_wrong_bind_mount_target_mode(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, target_mode=0o773)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_android13_data_0771_rejects_wrong_system_group(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, data_gid=1001)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_android13_data_world_writable_mode_is_rejected(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, data_mode=0o773)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_android13_data_user_group_writable_ancestor_is_rejected(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, user_mode=0o771)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_audit_database_rejects_writable_parent_of_allowlisted_symlink(tmp_path, monkeypatch):
    shared = tmp_path / "shared"
    target = tmp_path / "safe-target"
    private = target / "private"
    shared.mkdir()
    private.mkdir(parents=True)
    os.chmod(shared, 0o777)
    os.chmod(private, 0o700)
    alias = shared / "alias"
    alias.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(
        android_control,
        "_ANDROID_PLATFORM_SYMLINKS",
        ((alias, target),),
    )
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(alias / "private" / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()



def test_android13_data_0771_rejects_wrong_system_owner(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, data_uid=999)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_legacy_android_data_target_group_write_exception_is_exact(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    legacy_data = data_root / "data"
    legacy_data.mkdir(parents=True)
    monkeypatch.setattr(android_control, "_ANDROID_DATA_ROOT", data_root)
    exact = SimpleNamespace(
        st_uid=android_control._ANDROID_SYSTEM_UID,
        st_gid=android_control._ANDROID_SYSTEM_GID,
        st_mode=stat.S_IFDIR | 0o771,
    )
    assert android_control._trusted_android_data_group_write(legacy_data, exact)
    assert not android_control._trusted_android_data_group_write(
        legacy_data, SimpleNamespace(
            st_uid=999, st_gid=android_control._ANDROID_SYSTEM_GID,
            st_mode=stat.S_IFDIR | 0o771,
        )
    )
    assert not android_control._trusted_android_data_group_write(
        legacy_data, SimpleNamespace(
            st_uid=android_control._ANDROID_SYSTEM_UID, st_gid=1001,
            st_mode=stat.S_IFDIR | 0o771,
        )
    )
    assert not android_control._trusted_android_data_group_write(
        legacy_data, SimpleNamespace(
            st_uid=android_control._ANDROID_SYSTEM_UID,
            st_gid=android_control._ANDROID_SYSTEM_GID,
            st_mode=stat.S_IFDIR | 0o773,
        )
    )
    assert not android_control._trusted_android_data_group_write(
        data_root / "other", exact
    )


def test_android13_data_user_zero_rejects_wrong_bind_mount_target_uid(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, target_uid=999)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_android13_data_user_zero_rejects_wrong_bind_mount_target_gid(tmp_path, monkeypatch):
    private = _android13_data_user_zero_path(tmp_path, monkeypatch, target_gid=1001)
    with pytest.raises(ControlDenied, match="ancestor"):
        AndroidControlBroker(private / "audit.sqlite")
    assert not (private / "audit.sqlite").exists()


def test_approved_proposal_arguments_cannot_be_mutated_after_confirmation(tmp_path):
    broker = AndroidControlBroker(tmp_path / "audit.sqlite")
    try:
        broker.start()
        proposal = broker.propose("tap", {"x": 10, "y": 20})
        original_digest = hashlib.sha256(
            android_control._canonical("tap", {"x": 10, "y": 20}).encode()
        ).hexdigest()
        assert proposal.digest == original_digest

        broker.approve(proposal.action_id, confirmed_by_local_ui=True)
        with pytest.raises(TypeError):
            proposal.args["x"] = 999

        envelope = broker.execute(proposal.action_id)
        assert envelope["args"] == {"x": 10, "y": 20}
        assert envelope["digest"] == original_digest
        # The returned transport envelope is a detached copy too.
        envelope["args"]["x"] = 999
        assert proposal.args["x"] == 10
    finally:
        broker.close()



def test_companion_receipt_is_persisted_in_real_store(tmp_path):
    from v13.android_companion_protocol import ReceiptVerifier, SCHEMA, sign_fixture
    from v13.android_outcomes import (
        ActionOutcome, InvalidOutcome, accept_and_persist_companion_receipt,
        persist_companion_outcome,
    )
    from v13.store import Store
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
        assert actual["companion_local_consent_claim"] is True
        assert actual["local_approval_evidence"] == "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION"
        assert actual["android_os_permission_status"] == "REQUIRED_NOT_VERIFIED"
        assert actual["key_storage_status"] == "UNVERIFIED"
        # World-JEPA's T8 consumer reads committed Store.actions and requires a
        # committed ActionSelection; this receipt creates neither.
        assert store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0
        assert store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ActionSelection' AND event_id=?",
            (event["event_id"],),
        )["n"] == 0
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



def test_dispatched_action_survives_broker_restart_and_preserves_source_binding(tmp_path):
    db_path = tmp_path / "durable-broker.sqlite"
    clock = lambda: 1000.0
    source_ref = {
        "source_id": "event-source-1", "sha256": "a" * 64,
        "char_start": 0, "char_end": 12, "modality": "text",
    }
    first = AndroidControlBroker(db_path, clock=clock)
    first.start()
    proposal = first.propose(
        "launch_app", {"package": "com.example.app"}, ttl=30,
        event_id="event-1", source_ref=source_ref,
    )
    first.approve(proposal.action_id, confirmed_by_local_ui=True)
    envelope = first.dispatch_approved(proposal.action_id)
    assert envelope["permission_bypass"] is False
    first.close()  # process shutdown must not cancel a still-pending companion receipt

    resumed = AndroidControlBroker(db_path, clock=clock)
    resumed.start()
    restored = resumed.consume_dispatched(proposal.action_id)
    assert restored.digest == proposal.digest
    assert restored.event_id == "event-1"
    assert restored.source_ref == source_ref
    resumed.record_companion_receipt(proposal.action_id, proposal.digest, verified=True)
    state = resumed.db.execute(
        "SELECT state FROM control_actions WHERE action_id=?", (proposal.action_id,)
    ).fetchone()[0]
    assert state == "RECEIPT_VERIFIED"
    resumed.close()


def test_stop_preserves_uncertain_dispatch_and_consumed_receipt_across_restart(tmp_path):
    db_path = tmp_path / "uncertain-broker.sqlite"
    source_ref = {
        "source_id": "event-source-1", "sha256": "a" * 64,
        "char_start": 0, "char_end": 12, "modality": "text",
    }
    first = AndroidControlBroker(db_path, clock=lambda: 1000.0)
    first.start()
    proposal = first.propose(
        "launch_app", {"package": "com.example.app"}, ttl=30,
        event_id="event-1", source_ref=source_ref,
    )
    first.approve(proposal.action_id, confirmed_by_local_ui=True)
    first.dispatch_approved(proposal.action_id)
    assert first.mark_submit_uncertain(proposal.action_id) is True
    first.stop()
    assert first.action_state(proposal.action_id) == "SUBMIT_UNCERTAIN"
    first.close()

    resumed = AndroidControlBroker(db_path, clock=lambda: 1000.0)
    resumed.start()
    restored = resumed.consume_dispatched(proposal.action_id)
    assert restored.digest == proposal.digest
    assert restored.source_ref == source_ref
    assert resumed.action_state(proposal.action_id) == "RECEIPT_CONSUMED"
    resumed.stop()
    assert resumed.action_state(proposal.action_id) == "RECEIPT_CONSUMED"
    resumed.close()

    retry = AndroidControlBroker(db_path, clock=lambda: 1000.0)
    retry.start()
    assert retry.consume_dispatched(proposal.action_id).digest == proposal.digest
    retry.close()


def test_cancel_revokes_local_dispatch_and_type_text_is_not_persisted(tmp_path):
    db_path = tmp_path / "cancel-broker.sqlite"
    broker = AndroidControlBroker(db_path, clock=lambda: 1000.0)
    broker.start()
    proposal = broker.propose("launch_app", {"package": "com.example.app"}, ttl=30)
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    broker.dispatch_approved(proposal.action_id)
    assert broker.cancel(proposal.action_id) is True
    with pytest.raises(ControlDenied):
        broker.consume_dispatched(proposal.action_id)

    typed = broker.propose("type_text", {"text": "private text"}, ttl=30)
    args_json = broker.db.execute(
        "SELECT args_json FROM control_actions WHERE action_id=?", (typed.action_id,)
    ).fetchone()[0]
    assert args_json is None
    broker.close()
    resumed = AndroidControlBroker(db_path, clock=lambda: 1000.0)
    assert typed.action_id not in resumed.pending
    state = resumed.db.execute(
        "SELECT state FROM control_actions WHERE action_id=?", (typed.action_id,)
    ).fetchone()[0]
    assert state == "DROPPED_ON_RESTART"
    resumed.close()
