"""Run21: independently guard process-group ID reuse after leader was reaped.

Software/mock evidence ONLY, no real native model, cgroup writes or signals.
"""
import unittest
from unittest.mock import patch
import test_lp3_serial_cohort as base
mod = base.mod


class PostReapOwnershipReview(unittest.TestCase):
    def test_reaped_leader_group_must_never_receive_signals_by_numeric_pgid(self):
        # The launcher calls this only after proc.wait() reaped the direct
        # child. Its numeric PGID no longer proves exclusive ownership; PID
        # reuse can make a later killpg target a different group.
        with patch.object(mod, '_owned_group_exists', return_value=True), \
             patch.object(mod.os, 'killpg') as killpg, \
             patch.object(mod.time, 'sleep') as sleep:
            outcome = mod._cleanup_owned_group(424242, grace=0)
        killpg.assert_not_called()
        sleep.assert_not_called()
        self.assertTrue(outcome['owned_group_residue_detected'])
        self.assertFalse(outcome['owned_group_absent'])

    def test_reaped_leader_absent_group_is_clean_without_signals(self):
        with patch.object(mod, '_owned_group_exists', return_value=False), \
             patch.object(mod.os, 'killpg') as killpg:
            outcome = mod._cleanup_owned_group(424242, grace=0)
        killpg.assert_not_called()
        self.assertFalse(outcome['owned_group_residue_detected'])
        self.assertTrue(outcome['owned_group_absent'])

class PostReapEndToEndReview(unittest.TestCase):
    def setUp(self):
        # Reuse the inherited synthetic fixture without collecting its test
        # methods a second time. No native HF model or cgroup is launched.
        base.SerialCohortTests.setUp(self)

    def test_group_residue_rejects_receipt_without_signaling_numeric_pgid(self):
        with patch.object(mod, 'check', return_value=self.ready), \
             patch.object(mod, '_owned_group_exists', return_value=True), \
             patch.object(mod.os, 'killpg') as killpg:
            with self.assertRaisesRegex(mod.LaunchBlocked, 'surviving process-group'):
                base.SerialCohortTests.call(self)
        killpg.assert_not_called()
        import json
        record = json.loads((self.evidence / 'launch_status.json').read_text())
        self.assertTrue(record['owned_group_residue_detected'])
        self.assertEqual(record['status'], 'WRAPPER_OR_AUDIT_FAILED_PRESERVED')
        self.assertFalse((self.evidence / 'receipt.json').exists())
        self.assertTrue(record.get('local_lock_poisoned', False))


if __name__ == '__main__':
    unittest.main()
