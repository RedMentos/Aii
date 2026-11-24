"""Model-free regression tests for the bounded installer smoke, not a native gate."""
import subprocess
import unittest
from unittest.mock import Mock, patch

from scripts import install_selftest as smoke


class InstallSelftestContract(unittest.TestCase):
    def test_exact_allowlist_has_core_runtime_and_no_dynamic_discovery(self):
        names = smoke.SMOKE_CASES
        self.assertEqual(len(names), 18)
        self.assertEqual(len(set(names)), len(names))
        self.assertTrue(any("test_age.AgeChecks." in name for name in names))
        self.assertTrue(any("test_runtime_queue.DurableRuntimeQueue." in name for name in names))
        self.assertTrue(any("test_standstill." in name for name in names))
        self.assertTrue(any("test_source_handoff_candidate." in name for name in names))
        self.assertTrue(any("test_admission." in name for name in names))
        self.assertNotIn("discover(", smoke.load_exact_suite.__code__.co_names)
        self.assertEqual(smoke.load_exact_suite().countTestCases(), len(names))

    def test_missing_or_empty_test_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            smoke.load_exact_suite(())
        with self.assertRaisesRegex(ValueError, "duplicate"):
            smoke.load_exact_suite((smoke.SMOKE_CASES[0],) * 2)
        with self.assertRaisesRegex(ValueError, "missing or substituted"):
            smoke.load_exact_suite(("test_age.AgeChecks.test_nonexistent_run97",))

    def test_timeout_is_bounded_and_kills_worker_group(self):
        process = Mock(pid=123456)
        process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="install-smoke", timeout=1), 0
        ]
        with patch.object(smoke.subprocess, "Popen", return_value=process) as launch:
            with patch.object(smoke.os, "killpg") as kill:
                self.assertEqual(smoke.run_bounded(1), 124)
        self.assertTrue(launch.call_args.kwargs["start_new_session"])
        self.assertEqual(launch.call_args.kwargs["env"]["NO_MODEL_DOWNLOADS"], "1")
        kill.assert_called_once_with(123456, smoke.signal.SIGKILL)
        self.assertEqual(process.wait.call_count, 2)

    def test_nonzero_worker_failure_is_not_promoted(self):
        process = Mock()
        process.wait.return_value = 2
        with patch.object(smoke.subprocess, "Popen", return_value=process):
            self.assertEqual(smoke.run_bounded(10), 2)

    def test_invalid_timeout_refused(self):
        for seconds in (0, -1, 121, 0.5, "120"):
            with self.subTest(seconds=seconds):
                with self.assertRaises(ValueError):
                    smoke.run_bounded(seconds)


if __name__ == "__main__":
    unittest.main()
