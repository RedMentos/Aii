"""Run18 adversarial checks for child-process group lifetime (software/synthetic)."""
import json
import os
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
    def test_successful_leader_with_live_descendant_is_not_success(self):
        child_pid_path = self.root / 'spawned.pid'
        self.candidate.write_text(
            'import subprocess,sys\n'
            f'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"])\n'
            f'open({str(child_pid_path)!r},"w").write(str(p.pid))\n'
        )
        child_pid = None
        try:
            with patch.object(mod, 'check', return_value=self.ready), \
                 patch.object(mod, 'audit', return_value=self.good_audit), \
                 patch.object(mod, 'receipt_for', return_value={'schema':'synthetic'}):
                try:
                    self.call()
                except mod.LaunchBlocked:
                    pass
            child_pid = int(child_pid_path.read_text())
            status = json.loads((self.evidence / 'launch_status.json').read_text())
            self.assertNotEqual(status['status'], 'LOCAL_CLOSED_EVIDENCE_UNPUBLISHED_ANCHOR')
            self.assertFalse((self.evidence / 'receipt.json').exists())
            for _ in range(20):
                if not process_running(child_pid):
                    break
                time.sleep(.05)
            self.assertFalse(process_running(child_pid), 'descendant still running after wrapper unlocked')
        finally:
            if child_pid is None and child_pid_path.exists():
                child_pid = int(child_pid_path.read_text())
            if child_pid is not None and process_running(child_pid):
                try:
                    os.kill(child_pid, 9)
                except ProcessLookupError:
                    pass

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
