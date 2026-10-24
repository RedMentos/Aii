#!/usr/bin/env python3
"""Staged, OFF-by-default bridge for a statically linked clone3 helper.

Never invoke the preregistered LP3 runner via this candidate until an
independent delegated writable-cgroup kernel test has passed. A sealed memfd
pins the helper bytes across check/exec. This does not prove global ownership.
"""
from contextlib import contextmanager
import json
import fcntl
import hashlib
import os
from pathlib import Path
import platform
import re
import stat
import struct


class AtomicBootstrapBlocked(RuntimeError):
    pass


_MACHINE = {'x86_64': 62, 'aarch64': 183}
_MAX_BINARY_BYTES = 16 * 1024 * 1024


def _check_static_elf(data):
    """Reject dynamic interpreters, dynamic sections, wrong arch and ELF32.

    This is an ELF *structural* check, not a compiler/source provenance proof.
    """
    if len(data) < 64 or data[:6] != b'\x7fELF\x02\x01':
        raise AtomicBootstrapBlocked('static Linux ELF64 little-endian required')
    machine = _MACHINE.get(platform.machine())
    if machine is None or struct.unpack_from('<H', data, 18)[0] != machine:
        raise AtomicBootstrapBlocked('ELF architecture does not match host')
    e_type = struct.unpack_from('<H', data, 16)[0]
    if e_type != 2:  # ET_EXEC; deliberately reject static PIE / ET_DYN
        raise AtomicBootstrapBlocked('ET_EXEC static binary required')
    phoff = struct.unpack_from('<Q', data, 32)[0]
    phentsize, phnum = struct.unpack_from('<HH', data, 54)
    if not 1 <= phnum <= 64 or phentsize < 56 or phentsize > 256:
        raise AtomicBootstrapBlocked('invalid ELF program header table')
    if phoff > len(data) or phnum * phentsize > len(data) - phoff:
        raise AtomicBootstrapBlocked('ELF program headers outside file')
    types = [struct.unpack_from('<I', data, phoff + i * phentsize)[0]
             for i in range(phnum)]
    if 3 in types or 2 in types:  # PT_INTERP or PT_DYNAMIC
        raise AtomicBootstrapBlocked('dynamic loader segment forbidden before cgroup join')
    if 1 not in types:  # PT_LOAD
        raise AtomicBootstrapBlocked('ELF has no loadable segment')


@contextmanager
def sealed_static_helper(path, expected_sha256):
    """Yield a sealed memfd holding the exact hash-bound static executable.

    Caller must keep this context open until subprocess.Popen has returned.
    Only use `pass_fds=(fd,)` and `executable=/proc/self/fd/FD` together.
    No file path can be swapped between validation and exec.
    """
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256 or ''):
        raise AtomicBootstrapBlocked('explicit 64-digit helper SHA256 required')
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise AtomicBootstrapBlocked('regular nonsymlink helper required')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0)
    sourcefd = os.open(path, flags)
    try:
        info = os.fstat(sourcefd)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
            raise AtomicBootstrapBlocked('helper file must be regular and not group/world writable')
        if not 4096 <= info.st_size <= _MAX_BINARY_BYTES:
            raise AtomicBootstrapBlocked('helper size outside bound')
        data = bytearray()
        while len(data) <= _MAX_BINARY_BYTES:
            chunk = os.read(sourcefd, min(1024 * 1024, _MAX_BINARY_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != info.st_size:
            raise AtomicBootstrapBlocked('helper changed during read')
        data = bytes(data)
        if hashlib.sha256(data).hexdigest() != expected_sha256:
            raise AtomicBootstrapBlocked('helper SHA256 mismatch')
        _check_static_elf(data)
    finally:
        os.close(sourcefd)
    if not hasattr(os, 'memfd_create'):
        raise AtomicBootstrapBlocked('sealed Linux memfd unavailable')
    memfd = os.memfd_create('lp3-atomic-reviewed', flags=os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        for start in range(0, len(data), 1024 * 1024):
            chunk = memoryview(data)[start:start + 1024 * 1024]
            while chunk:
                n = os.write(memfd, chunk)
                if n <= 0:
                    raise AtomicBootstrapBlocked('short memfd write')
                chunk = chunk[n:]
        seals = (fcntl.F_SEAL_WRITE | fcntl.F_SEAL_SHRINK |
                 fcntl.F_SEAL_GROW | fcntl.F_SEAL_SEAL)
        fcntl.fcntl(memfd, fcntl.F_ADD_SEALS, seals)
        if fcntl.fcntl(memfd, fcntl.F_GET_SEALS) & seals != seals:
            raise AtomicBootstrapBlocked('helper memfd seals not verified')
        yield memfd
    finally:
        os.close(memfd)


def launch_spec(memfd, group, marker, command):
    """Return Popen args/kwargs; no child is launched by this function.

    Caller must own `group` as a fresh delegated lp3-active subtree and must
    close/reap on failure. This adapter is not a standalone safety gate.
    """
    group, marker = Path(group), Path(marker)
    if (not group.is_absolute() or group.name != 'lp3-active' or
            len(group.parts) < 6 or group.parts[:4] != ('/', 'sys', 'fs', 'cgroup') or
            not marker.is_absolute() or not command or
            not Path(command[0]).is_absolute()):
        raise AtomicBootstrapBlocked('absolute owned group, marker and command required')
    return ([f'/proc/self/fd/{memfd}', str(group), str(marker), '--', *map(str, command)],
            {'executable': f'/proc/self/fd/{memfd}', 'pass_fds': (memfd,)})


def _unique_json_pairs(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError('duplicate JSON key')
        data[key] = value
    return data


def verify_atomic_marker(marker, group, helper_pid):
    """Check a bounded, nonsymlink, closed-schema helper receipt.

    This is not a kernel membership proof or a global ownership lease.
    The coordinator must independently drain the owned cgroup and fail
    closed on surviving descendants before publishing evidence.
    """
    if type(helper_pid) is not int or helper_pid <= 0:
        raise AtomicBootstrapBlocked('invalid helper PID')
    group = str(group)
    if (not group.startswith('/sys/fs/cgroup/') or
            not group.endswith('/lp3-active') or
            len(Path(group).parts) < 6 or
            os.path.normpath(group) != group or
            len(group) >= 2048):
        raise AtomicBootstrapBlocked('noncanonical cgroup receipt path')
    try:
        fd = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
                raise AtomicBootstrapBlocked('marker size/type invalid')
            raw = os.read(fd, 4097)
            if len(raw) > 4096:
                raise AtomicBootstrapBlocked('marker too large')
        finally:
            os.close(fd)
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_json_pairs)
    except (OSError, UnicodeError, ValueError) as exc:
        raise AtomicBootstrapBlocked('atomic helper marker unreadable') from exc
    keys = {'schema', 'cgroup', 'helper_pid', 'child_pid',
            'atomic_placement', 'pidfd', 'verified_membership'}
    if (type(data) is not dict or set(data) != keys or
            data['schema'] != 'V13_LP3_ATOMIC_CLONE3_V1' or
            data['cgroup'] != group or
            type(data['helper_pid']) is not int or data['helper_pid'] != helper_pid or
            type(data['child_pid']) is not int or data['child_pid'] <= 0 or
            data['child_pid'] == helper_pid or
            data['atomic_placement'] is not True or data['pidfd'] is not True or
            data['verified_membership'] is not True):
        raise AtomicBootstrapBlocked('atomic helper marker does not match registered launch')
    return data['child_pid']
