"""Run18 adversarial checks for child-process group lifetime (software/synthetic)."""
import json
import os
import signal
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

from test_lp3_serial_cohort import SerialCohortTests, mod


def process_running(pid):
    """Linux /proc distinguishes a zombie (already dead) from a live process."""
    stat_path = Path(f'/proc/{pid}/stat')
    try:
        return stat_path.read_text().split(') ', 1)[1][0] != 'Z'
    except FileNotFoundError:
        return False


class OrphanGroupReview(SerialCohortTests):
    def test_reaped_leader_with_live_descendant_fails_and_poisons_without_unsafe_killpg(self):
        child_pid_path = self.root / 'spawned.pid'
        self.candidate.write_text(
            'import subprocess,sys\n'
            f'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"])\n'
            f'open({str(child_pid_path)!r},"w").write(str(p.pid))\n'
        )
        child_pid = None
        child_pidfd = None
        try:
            with patch.object(mod, 'check', return_value=self.ready), \
                 patch.object(mod, 'audit', return_value=self.good_audit), \
                 patch.object(mod, 'receipt_for', return_value={'schema':'synthetic'}), \
                 patch.object(mod.os, 'killpg', wraps=os.killpg) as killpg:
                with self.assertRaisesRegex(mod.LaunchBlocked, 'surviving process-group'):
                    self.call()
                # The leader was already reaped. Numeric PGID signalling could
                # kill an unrelated process after PID reuse (Run21 contract).
                self.assertTrue(all(call.args[1] == 0 for call in killpg.call_args_list),
                                'post-reap process group must only receive signal-0 probes')
            child_pid = int(child_pid_path.read_text())
            if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
                self.fail('Linux pidfd required for safe fixture cleanup')
            child_pidfd = os.pidfd_open(child_pid, 0)
            status = json.loads((self.evidence / 'launch_status.json').read_text())
            self.assertEqual(status['status'], 'WRAPPER_OR_AUDIT_FAILED_PRESERVED')
            self.assertTrue(status['owned_group_residue_detected'])
            self.assertFalse(status['owned_group_absent'])
            self.assertTrue(status['local_lock_poisoned'])
            self.assertTrue(self.lock.read_bytes().startswith(b'LP3_UNRESOLVED_OWNED_GROUP'))
            self.assertFalse((self.evidence / 'receipt.json').exists())
            # Synthetic cgroup cannot safely contain/kill a descendant. This
            # deliberately stays a failure, not a native isolation proof.
            self.assertTrue(process_running(child_pid))
        finally:
            # Only the test fixture's stable pidfd may be signalled. Never
            # send SIGKILL to an unverified/reused numeric PID or PGID.
            if child_pidfd is not None:
                try:
                    signal.pidfd_send_signal(child_pidfd, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                finally:
                    os.close(child_pidfd)

class LockPoisonReview(SerialCohortTests):
    def test_unverified_descendant_cleanup_poison_persists_across_attempts(self):
        with patch.object(mod, 'check', return_value=self.ready), \
             patch.object(mod, '_cleanup_owned_group', return_value={
                 'owned_group_residue_detected': True, 'owned_group_absent': False}):
            with self.assertRaises(mod.LaunchBlocked):
                self.call()
        self.assertTrue(self.lock.read_bytes().startswith(b'LP3_UNRESOLVED_OWNED_GROUP'))
        self.assertEqual(json.loads((self.evidence / 'launch_status.json').read_text())['local_lock_poisoned'], True)
        with patch.object(mod, 'check', return_value=self.ready):
            with self.assertRaisesRegex(mod.LaunchBlocked, 'poisoned'):
                self.call(out=self.root/'next-attempt', evidence_dir=self.root/'next-evidence')
        self.assertFalse((self.root/'next-evidence').exists())
