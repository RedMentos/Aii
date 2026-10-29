"""Native cancellation gate must measure the canceled worker, not all pool roles.

Synthetic PID and reaping evidence only. No actual native launch or gate promotion.
"""
import unittest

from tests import integration_real as acceptance


class CancelProcessIdentity(unittest.TestCase):
    def _check(self, runner, pids, alive):
        fn = getattr(acceptance, "cancelled_worker_stopped", None)
        self.assertTrue(callable(fn), "acceptance must expose worker-specific check")
        return fn(runner, pids, is_alive=alive)

    def test_unrelated_resident_pid_does_not_fail_reaped_worker(self):
        runner = {"status": "CANCELLED",
                  "interruption_unload": {"before": {"pid": 8454, "resolved_proc_pid": 8454},
                                          "process_reaped": True}}
        self.assertTrue(self._check(runner, [9001], lambda pid: False))
        self.assertFalse(not [9001], "old global-pool-empty gate was a false negative")

    def test_canceled_worker_still_resident_fails(self):
        runner = {"status": "CANCELLED",
                  "interruption_unload": {"before": {"pid": 8454}, "process_reaped": True}}
        self.assertFalse(self._check(runner, [8454, 9001], lambda pid: False))

    def test_process_alive_even_if_unlisted_fails(self):
        runner = {"status": "CANCELLED",
                  "interruption_unload": {"before": {"pid": 8454}, "process_reaped": True}}
        self.assertFalse(self._check(runner, [9001], lambda pid: pid == 8454))

    def test_missing_or_unreaped_evidence_fails_closed(self):
        for unload in ({}, {"process_reaped": False, "before": {"pid": 8454}},
                       {"process_reaped": True, "before": {}},
                       {"process_reaped": True, "before": {"pid": True}}):
            with self.subTest(unload=unload):
                self.assertFalse(self._check(
                    {"status": "CANCELLED", "interruption_unload": unload},
                    [], lambda pid: False))

    def test_non_cancelled_runner_cannot_pass(self):
        runner = {"status": "FINAL",
                  "interruption_unload": {"before": {"pid": 8454}, "process_reaped": True}}
        self.assertFalse(self._check(runner, [], lambda pid: False))


if __name__ == "__main__":
    unittest.main()
