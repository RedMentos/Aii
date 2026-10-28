"""Stage-19 proof negative controls; no native execution is mocked as a PASS."""
import errno
import unittest
from unittest.mock import patch

from v13.proof_lifecycle import cancelled_native_process_stopped, pid_alive


class CancelledNativePidEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.pid = 4101
        self.runner = {
            "status": "CANCELLED",
            "interruption_unload": {
                "process_reaped": True,
                "before": {"pid": self.pid},
            },
        }

    def test_unrelated_resident_is_not_cancelled_child(self):
        self.assertTrue(cancelled_native_process_stopped(
            self.runner, [5102, 5103], probe=lambda pid: False))
        self.assertTrue(cancelled_native_process_stopped(
            self.runner, [], probe=lambda pid: False))

    def test_cancelled_child_still_in_pool_fails(self):
        self.assertFalse(cancelled_native_process_stopped(
            self.runner, [5102, self.pid], probe=lambda pid: False))

    def test_cancelled_child_still_alive_in_os_fails(self):
        self.assertFalse(cancelled_native_process_stopped(
            self.runner, [5102], probe=lambda pid: True))

    def test_unknown_or_throwing_os_probe_fails(self):
        self.assertFalse(cancelled_native_process_stopped(
            self.runner, [], probe=lambda pid: None))
        def raises(pid):
            raise OSError("probe unavailable")
        self.assertFalse(cancelled_native_process_stopped(
            self.runner, [], probe=raises))

    def test_missing_reaping_proof_fails(self):
        for value in (False, None, "true", 1):
            row = dict(self.runner)
            row["interruption_unload"] = {
                "process_reaped": value, "before": {"pid": self.pid}}
            self.assertFalse(cancelled_native_process_stopped(
                row, [], probe=lambda pid: False))
        self.assertFalse(cancelled_native_process_stopped(
            {"status": "CANCELLED"}, [], probe=lambda pid: False))

    def test_bad_pid_fails(self):
        for pid in (None, 0, -2, True, "4101", 4.5):
            row = {"status": "CANCELLED", "interruption_unload": {
                "process_reaped": True, "before": {"pid": pid}}}
            self.assertFalse(cancelled_native_process_stopped(
                row, [], probe=lambda pid: False))

    def test_bad_status_or_malformed_evidence_fails(self):
        for status in ("FINAL", "DEADLINE", None):
            row = dict(self.runner, status=status)
            self.assertFalse(cancelled_native_process_stopped(
                row, [], probe=lambda pid: False))
        for row in (None, {}, {"status": "CANCELLED",
                               "interruption_unload": {"process_reaped": True,
                                                       "before": []}}):
            self.assertFalse(cancelled_native_process_stopped(
                row, [], probe=lambda pid: False))

    def test_bad_pool_pid_list_fails(self):
        for pool in (None, "4101", [True], [0], [1, "2"]):
            self.assertFalse(cancelled_native_process_stopped(
                self.runner, pool, probe=lambda pid: False))

    def test_os_pid_probe_absent(self):
        with patch("v13.proof_lifecycle.os.kill", side_effect=ProcessLookupError(errno.ESRCH, "gone")):
            self.assertFalse(pid_alive(self.pid))

    def test_os_pid_probe_live_and_unknown_fail_closed(self):
        with patch("v13.proof_lifecycle.os.kill", return_value=None):
            self.assertTrue(pid_alive(self.pid))
        with patch("v13.proof_lifecycle.os.kill", side_effect=PermissionError(errno.EPERM, "unknown")):
            self.assertTrue(pid_alive(self.pid))


if __name__ == "__main__":
    unittest.main()
