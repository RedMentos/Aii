"""QA regressions for the production WorldJEPA checkpoint publisher.

These tests exercise the real source-bound NPZ save/load path and the dirfd
publication helpers. GitHub/Linux results do not prove Bionic/SELinux behavior
on the Redmi; Android-native publication remains a separate device gate.
"""
import errno
import os
import stat

import numpy as np
import pytest

from v13 import world_jepa as wj
from v13 import world_jepa_shadow_checkpoint as checkpoint


SOURCE_SHA = "a" * 64
DEST_NAME = "jepa-0123456789abcdef0123456789abcdef.npz"


def _fitted_model():
    rng = np.random.default_rng(41)
    x = rng.normal(size=(24, 4))
    actions = np.eye(2, dtype=np.float64)[np.arange(len(x)) % 2]
    x2 = x.copy()
    x2[np.arange(len(x2)), np.arange(len(x2)) % x2.shape[1]] += 0.2
    return wj.WorldJEPA(seed=41, ensemble=1).fit(
        x, actions, x2, steps=2, log_every=1
    )


def _private_directory(path):
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def _create_racing_target(dir_fd, name, payload=b"foreign-racer"):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dir_fd)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def _pending_entries(directory):
    return [item for item in directory.iterdir()
            if item.name.startswith(checkpoint.PENDING_PREFIX)]


@pytest.mark.parametrize("denial_errno", [errno.EPERM, errno.EACCES])
def test_hardlink_denial_falls_back_to_verified_renameat2_publication(
    tmp_path, monkeypatch, denial_errno
):
    directory = _private_directory(tmp_path / "checkpoint")
    destination = directory / DEST_NAME
    model = _fitted_model()
    real_rename = checkpoint._rename_named_no_replace
    rename_calls = []

    def deny_hardlink(_dir_fd, _source, _dest):
        raise OSError(denial_errno, os.strerror(denial_errno))

    def record_rename(dir_fd, source, dest):
        rename_calls.append((source, dest))
        return real_rename(dir_fd, source, dest)

    monkeypatch.setattr(checkpoint, "_hardlink_named_no_replace", deny_hardlink)
    monkeypatch.setattr(checkpoint, "_rename_named_no_replace", record_rename)

    receipt = checkpoint.save(model, destination, SOURCE_SHA)

    assert len(rename_calls) == 1
    assert rename_calls[0][0].startswith(checkpoint.PENDING_PREFIX)
    assert rename_calls[0][1] == DEST_NAME
    assert destination.is_file()
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert _pending_entries(directory) == []
    assert receipt["optimizer_state_persisted"] is True
    restored = checkpoint.load(destination, SOURCE_SHA, receipt["sha256"])
    assert restored._fit_steps == model._fit_steps


@pytest.mark.parametrize("race_stage", ["hardlink", "renameat2"])
def test_racing_destination_is_never_replaced_and_pending_name_is_removed(
    tmp_path, monkeypatch, race_stage
):
    directory = _private_directory(tmp_path / race_stage)
    destination = directory / DEST_NAME
    model = _fitted_model()
    payload = b"pre-existing concurrent publisher"
    real_link = checkpoint._hardlink_named_no_replace
    real_rename = checkpoint._rename_named_no_replace

    def race_link(dir_fd, source, dest):
        _create_racing_target(dir_fd, dest, payload)
        return real_link(dir_fd, source, dest)

    def race_rename(dir_fd, source, dest):
        _create_racing_target(dir_fd, dest, payload)
        return real_rename(dir_fd, source, dest)

    if race_stage == "hardlink":
        monkeypatch.setattr(checkpoint, "_hardlink_named_no_replace", race_link)
    else:
        monkeypatch.setattr(
            checkpoint, "_hardlink_named_no_replace",
            lambda _dir_fd, _source, _dest: (_ for _ in ()).throw(
                OSError(errno.EPERM, os.strerror(errno.EPERM))
            ),
        )
        monkeypatch.setattr(checkpoint, "_rename_named_no_replace", race_rename)

    with pytest.raises(FileExistsError):
        checkpoint.save(model, destination, SOURCE_SHA)

    assert destination.read_bytes() == payload
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert _pending_entries(directory) == []


def test_directory_fsync_failure_rolls_back_published_fallback_inode(
    tmp_path, monkeypatch
):
    directory = _private_directory(tmp_path / "fsync-rollback")
    destination = directory / DEST_NAME
    model = _fitted_model()
    real_fsync = os.fsync
    failed_directory_fsync = False

    def deny_hardlink(_dir_fd, _source, _dest):
        raise OSError(errno.EPERM, os.strerror(errno.EPERM))

    def fail_first_directory_fsync(fd):
        nonlocal failed_directory_fsync
        if stat.S_ISDIR(os.fstat(fd).st_mode) and not failed_directory_fsync:
            failed_directory_fsync = True
            raise OSError(errno.EIO, "injected directory fsync failure")
        return real_fsync(fd)

    monkeypatch.setattr(checkpoint, "_hardlink_named_no_replace", deny_hardlink)
    monkeypatch.setattr(checkpoint.os, "fsync", fail_first_directory_fsync)

    with pytest.raises(OSError, match="directory fsync failure"):
        checkpoint.save(model, destination, SOURCE_SHA)

    assert failed_directory_fsync is True
    assert not destination.exists()
    assert _pending_entries(directory) == []
