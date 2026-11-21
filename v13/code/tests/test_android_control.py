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
    tmp_path, monkeypatch, *, data_mode=0o771, data_gid=1000, user_mode=0o711
):
    data_root = tmp_path / "data"
    user_root = data_root / "user"
    user_zero = user_root / "0"
    private = user_zero / "com.termux"
    private.mkdir(parents=True)
    os.chmod(data_root, data_mode)
    os.chmod(user_root, user_mode)
    os.chmod(user_zero, 0o700)
    os.chmod(private, 0o700)
    monkeypatch.setattr(android_control, "_ANDROID_DATA_ROOT", data_root)
    real_lstat = Path.lstat
    owners = {
        data_root: (android_control._ANDROID_SYSTEM_UID, data_gid),
        user_root: (android_control._ANDROID_SYSTEM_UID, android_control._ANDROID_SYSTEM_GID),
        user_zero: (android_control._ANDROID_SYSTEM_UID, android_control._ANDROID_SYSTEM_GID),
    }

    def android_lstat(path):
        info = real_lstat(path)
        owner = owners.get(path)
        if owner is not None:
            return SimpleNamespace(st_mode=info.st_mode, st_uid=owner[0], st_gid=owner[1])
        return info

    monkeypatch.setattr(Path, "lstat", android_lstat)
    return private


def test_android13_data_user_zero_bind_mount_ancestors_allow_exact_system_0771(tmp_path, monkeypatch):
    # AOSP Android 13: /data is system:system 0771; /data/user is 0711;
    # /data/user/0 is a system-owned bind mount; the Termux app dir is private.
    private = _android13_data_user_zero_path(tmp_path, monkeypatch)
    broker = AndroidControlBroker(private / "audit.sqlite")
    assert stat.S_IMODE(broker.db_path.stat().st_mode) == 0o600
    broker.close()


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
