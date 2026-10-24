#!/usr/bin/env python3
"""Linux cgroup-v2 containment for the isolated LP3 launcher candidate.

Only a fresh cgroup created under an operator-delegated parent may be killed.
This is process-lifecycle containment, NOT a sandbox against privileged or
hostile tasks which can migrate themselves out of a writable hierarchy.
Never infer global job ownership or memory fit from a cgroup alone.
"""
import json
import os
from pathlib import Path
import sys
import time


class ContainmentBlocked(RuntimeError):
    pass


def _mountpoint():
    """Require the known cgroup2 mount, not a lookalike directory."""
    mount = Path('/sys/fs/cgroup')
    try:
        lines = Path('/proc/self/mountinfo').read_text().splitlines()
    except OSError as exc:
        raise ContainmentBlocked('cannot inspect cgroup2 mount') from exc
    for line in lines:
        left, sep, right = line.partition(' - ')
        if sep and len(right.split()) >= 1 and right.split()[0] == 'cgroup2':
            # mountinfo escapes spaces as octal; fixed mount path has none.
            if left.split()[4] == str(mount):
                if not (mount / 'cgroup.controllers').is_file():
                    break
                return mount
    raise ContainmentBlocked('verified /sys/fs/cgroup cgroup2 mount unavailable')


def _strict_delegated_parent(parent):
    mount = _mountpoint()
    parent = Path(parent)
    if not parent.is_absolute() or parent == mount or mount not in parent.parents:
        raise ContainmentBlocked('explicit delegated cgroup parent required below cgroup2 mount')
    current = mount
    for part in parent.relative_to(mount).parts:
        if part in ('.', '..'):
            raise ContainmentBlocked('invalid cgroup parent component')
        current = current / part
        if current.is_symlink() or not current.is_dir():
            raise ContainmentBlocked('cgroup parent symlink or missing directory')
    if parent.resolve(strict=True) != parent:
        raise ContainmentBlocked('noncanonical cgroup parent')
    if not (parent / 'cgroup.procs').is_file():
        raise ContainmentBlocked('cgroup parent not delegated')
    return parent


def _populated(group):
    try:
        values = dict(line.split(None, 1) for line in (group / 'cgroup.events').read_text().splitlines())
    except (OSError, ValueError) as exc:
        raise ContainmentBlocked('cgroup.events unreadable') from exc
    if values.get('populated') not in ('0', '1'):
        raise ContainmentBlocked('cgroup.events missing valid populated state')
    return values['populated'] == '1'


class CgroupV2Job:
    """Fresh exclusively-owned subtree; kill ONLY that subtree on failure."""
    def __init__(self, parent, marker):
        parent = _strict_delegated_parent(parent)
        self.marker = Path(marker)
        # Fixed exclusive slot survives SIGKILL/crash; never silently reuse.
        # mkdir is the atomic same-parent ownership claim.
        self.group = parent / 'lp3-active'
        try:
            self.group.mkdir(mode=0o700, exist_ok=False)
        except FileExistsError as exc:
            raise ContainmentBlocked('active/stale LP3 cgroup exists; independent recovery required') from exc
        self.closed = False
        try:
            for name in ('cgroup.procs', 'cgroup.events', 'cgroup.kill', 'cgroup.type'):
                if not (self.group / name).is_file():
                    raise ContainmentBlocked('kernel cgroup v2 control missing: ' + name)
            if (self.group / 'cgroup.type').read_text().strip() != 'domain':
                raise ContainmentBlocked('cgroup is not a domain')
            if not os.access(self.group / 'cgroup.procs', os.W_OK):
                raise ContainmentBlocked('cannot move helper into owned cgroup')
            if not os.access(self.group / 'cgroup.kill', os.W_OK):
                raise ContainmentBlocked('cannot terminate owned cgroup')
            if _populated(self.group):
                raise ContainmentBlocked('new cgroup unexpectedly populated')
        except BaseException:
            try:
                self.group.rmdir()
            except OSError:
                # Do not delete or signal any unknown process; report failure.
                pass
            raise

    def wrap(self, command):
        helper = Path(__file__).with_name('lp3_cgroup_join.py').resolve(strict=True)
        # Python normally executes site/.pth startup hooks before the script.
        # Such hooks could fork before the helper joins the owned cgroup.
        # Isolate ONLY this stdlib-only pre-join helper; the actual registered
        # native command is exec'd unchanged after verified membership.
        return [sys.executable, '-I', '-S', str(helper), str(self.group), str(self.marker), '--', *command]

    def _joined(self, pid):
        try:
            data = json.loads(self.marker.read_text())
        except (OSError, ValueError):
            return False
        return (type(data) is dict and type(data.get('pid')) is int
                and data['pid'] == pid and data.get('cgroup') == str(self.group)
                and data.get('verified_membership') is True)

    def _drain(self, grace=3.0):
        """SIGKILL the *fresh owned subtree* if populated; never host/root."""
        residue = _populated(self.group)
        if residue:
            with (self.group / 'cgroup.kill').open('w') as stream:
                stream.write('1\n')
            deadline = time.monotonic() + grace
            while time.monotonic() < deadline and _populated(self.group):
                time.sleep(min(.05, max(0.0, deadline - time.monotonic())))
        empty = not _populated(self.group)
        if empty:
            try:
                self.group.rmdir()
                self.closed = True
            except OSError:
                empty = False
        return {'cgroup_residue_detected': residue,
                'contained_job_empty': empty and self.closed}

    def finish(self, leader_pid):
        joined = self._joined(leader_pid)
        outcome = self._drain()
        outcome['cgroup_join_verified'] = joined
        # Residue after the direct child exited is ALWAYS a failed cohort,
        # even if cgroup.kill successfully cleared the detached descendants.
        return outcome

    def abort(self):
        if self.closed:
            return {'contained_job_empty': True}
        return self._drain()


def host_readiness(parent):
    """Read-only preflight; never mkdir, move a PID, or signal a process."""
    try:
        path = _strict_delegated_parent(parent)
        if (path / 'lp3-active').exists():
            raise ContainmentBlocked('active/stale LP3 cgroup exists; do not overlap or auto-clear')
        if not os.access(path, os.W_OK):
            raise ContainmentBlocked('delegated cgroup parent is not writable')
        return {'status': 'CGROUP_V2_PARENT_CANDIDATE', 'parent': str(path),
                'claim_limit': 'not a fork/setsid kernel proof; no global owner proof'}
    except (ContainmentBlocked, OSError) as exc:
        return {'status': 'BLOCKED', 'reason': str(exc)}
