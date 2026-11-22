"""Fail-closed, reversible activation of a verified local llama-server candidate.

The caller stages the candidate away from the active runner and holds the
coordinator lock. Atomic rename protects each individual file; a power loss
between binary and manifest renames is detected by bootstrap's runner.json SHA
check, not claimed to be a two-file crash-atomic transaction.
"""
import contextlib
import os
from pathlib import Path
import subprocess
import uuid

from .common import Unavailable, atomic_write, dumps, file_hash


def activate_runner_candidate(candidate, binary, manifest, *, tag, platform):
    candidate, binary, manifest = map(Path, (candidate, binary, manifest))
    if candidate.is_symlink() or not candidate.is_file():
        raise Unavailable('Native runner candidate missing or symlinked')
    before = candidate.stat()
    try:
        result = subprocess.run([str(candidate), '--version'], capture_output=True,
                                text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Unavailable('Native runner candidate --version unavailable') from exc
    if result.returncode:
        raise Unavailable('llama-server startet nicht: ' + result.stderr[-600:])
    after = candidate.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise Unavailable('Native runner candidate changed during validation')
    digest = file_hash(candidate)
    if manifest.is_symlink():
        raise Unavailable('Runner manifest symlink refused')
    binary.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    nonce = uuid.uuid4().hex
    stage_link = binary.with_name('.' + binary.name + '.stage-' + nonce)
    backup_link = binary.with_name('.' + binary.name + '.backup-' + nonce)
    stage_manifest = manifest.with_name('.' + manifest.name + '.stage-' + nonce)
    record = {'tag': tag, 'platform': platform, 'binary_sha256': digest,
              'version': (result.stdout + result.stderr).strip(), 'phone_runner_proof': None}
    had_previous = binary.is_symlink() or binary.exists()
    try:
        atomic_write(stage_manifest, dumps(record))
        stage_link.symlink_to(candidate.resolve(strict=True))
        if had_previous:
            if binary.is_symlink():
                backup_link.symlink_to(os.readlink(binary))
            elif binary.is_file():
                os.link(binary, backup_link)
            else:
                raise Unavailable('Unsupported existing native runner type')
        os.replace(stage_link, binary)
        try:
            os.replace(stage_manifest, manifest)
        except BaseException:
            if had_previous:
                os.replace(backup_link, binary)
            else:
                binary.unlink(missing_ok=True)
            raise
        for directory in {binary.parent, manifest.parent}:
            with contextlib.suppress(OSError):
                fd = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        return record
    finally:
        stage_link.unlink(missing_ok=True)
        stage_manifest.unlink(missing_ok=True)
        backup_link.unlink(missing_ok=True)
