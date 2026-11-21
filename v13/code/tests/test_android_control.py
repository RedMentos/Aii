import os
import sqlite3
import stat

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


def test_android_platform_alias_direction_matches_aosp():
    from pathlib import Path
    import v13.android_control as android_control

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

    with pytest.raises(ControlDenied, match="owner-controlled"):
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
