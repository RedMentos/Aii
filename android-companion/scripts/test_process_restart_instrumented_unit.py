#!/usr/bin/env python3
"""Unit tests for the Espresso/host process-death integration driver."""
from __future__ import annotations

import unittest
from unittest.mock import call, patch

import test_process_restart_instrumented as harness


class InstrumentationDriverTests(unittest.TestCase):
    def test_instrumentation_unlocks_emulator_without_prelaunching_target(self):
        output = "INSTRUMENTATION_RESULT: stream=\n\nOK (1 test)\nINSTRUMENTATION_CODE: -1"
        with (
            patch.object(harness, "prepare_emulator_for_instrumentation") as prepare,
            patch.object(harness, "adb", return_value=output) as adb_call,
        ):
            self.assertEqual(harness.run_instrumentation(harness.INITIAL_METHOD), output)
        prepare.assert_called_once_with()
        adb_call.assert_called_once_with(
            "shell", "am", "instrument", "-w", "-r", "-e", "class",
            harness.TEST_CLASS + "#" + harness.INITIAL_METHOD,
            harness.TEST_RUNNER, timeout=180.0,
        )

    def test_instrumentation_rejects_failure_even_if_runner_returns_text(self):
        output = "FAILURES!!!\nTests run: 1, Failures: 1\nINSTRUMENTATION_CODE: -1"
        with (
            patch.object(harness, "prepare_emulator_for_instrumentation"),
            patch.object(harness, "adb", return_value=output),
        ):
            with self.assertRaisesRegex(AssertionError, "reported failure"):
                harness.run_instrumentation(harness.RESTART_METHOD)

    def test_instrumentation_rejects_missing_success_marker(self):
        with (
            patch.object(harness, "prepare_emulator_for_instrumentation"),
            patch.object(harness, "adb", return_value="INSTRUMENTATION_CODE: -1"),
        ):
            with self.assertRaisesRegex(AssertionError, "exactly one passing test"):
                harness.run_instrumentation(harness.RESTART_METHOD)

    def test_unlisted_instrumentation_method_never_reaches_adb(self):
        with (
            patch.object(harness, "prepare_emulator_for_instrumentation") as prepare,
            patch.object(harness, "adb") as adb_call,
        ):
            with self.assertRaisesRegex(ValueError, "not allowlisted"):
                harness.run_instrumentation("arbitraryMethod")
        prepare.assert_not_called()
        adb_call.assert_not_called()

    def test_prepare_emulator_wakes_unlocks_and_requires_stopped_target(self):
        with (
            patch.object(harness, "adb", return_value="") as adb_call,
            patch.object(harness, "process_id", return_value="") as pid,
        ):
            harness.prepare_emulator_for_instrumentation()

        self.assertEqual(
            adb_call.call_args_list,
            [
                call("shell", "input", "keyevent", "KEYCODE_WAKEUP"),
                call("shell", "wm", "dismiss-keyguard"),
            ],
        )
        pid.assert_called_once_with()

    def test_prepare_emulator_rejects_host_prelaunched_target(self):
        with (
            patch.object(harness, "adb", return_value="") as adb_call,
            patch.object(harness, "process_id", return_value="1234"),
        ):
            with self.assertRaisesRegex(AssertionError, "must be stopped"):
                harness.prepare_emulator_for_instrumentation()
        self.assertEqual(adb_call.call_count, 2)

    def test_process_id_accepts_pidof_exit_one_as_no_process(self):
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=1,
            stdout="",
            stderr="",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            self.assertEqual(harness.process_id(), "")

    def test_process_id_accepts_numeric_pid_output(self):
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=0,
            stdout="1234 5678\n",
            stderr="",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            self.assertEqual(harness.process_id(), "1234 5678")

    def test_process_id_does_not_hide_adb_transport_errors(self):
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=127,
            stdout="",
            stderr="adb: device offline",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "pidof failed"):
                harness.process_id()

    def test_process_id_rejects_exit_one_with_transport_error(self):
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=1,
            stdout="",
            stderr="error: device offline",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "ambiguous result"):
                harness.process_id()

    def test_process_id_rejects_exit_one_with_unexpected_stdout(self):
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=1,
            stdout="not-a-pid",
            stderr="",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "ambiguous result"):
                harness.process_id()

    def test_process_id_rejects_success_without_a_pid(self):
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=0,
            stdout="",
            stderr="",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "ambiguous result"):
                harness.process_id()

    def test_wait_for_process_polls_until_requested_state(self):
        with (
            patch.object(harness, "process_id", side_effect=["", "4321"]),
            patch.object(harness.time, "monotonic", side_effect=[0.0, 0.1, 0.2]),
            patch.object(harness.time, "sleep") as sleep,
        ):
            self.assertEqual(harness.wait_for_process(present=True, timeout=1.0), "4321")
        sleep.assert_called_once_with(0.25)

    def test_read_target_process_accepts_only_allowlisted_marker(self):
        with patch.object(harness, "adb", return_value="1234|987654321"):
            self.assertEqual(
                harness.read_target_process("qa-process-first.pid"),
                ("1234", 987654321),
            )

    def test_read_target_process_rejects_untrusted_marker(self):
        with patch.object(harness, "adb") as adb_call:
            with self.assertRaisesRegex(ValueError, "not allowlisted"):
                harness.read_target_process("../outside.pid")
        adb_call.assert_not_called()

    def test_read_target_process_rejects_malformed_identity(self):
        with patch.object(harness, "adb", return_value="not-a-pid"):
            with self.assertRaisesRegex(AssertionError, "malformed"):
                harness.read_target_process("qa-process-restart.pid")

    def test_main_accepts_natural_activity_teardown_and_proves_new_pid(self):
        with (
            patch.object(harness, "adb", return_value="") as adb_call,
            patch.object(harness, "wait_for_process", side_effect=["", "", ""]) as wait_call,
            patch.object(harness, "process_id", side_effect=["", ""]) as process_call,
            patch.object(harness, "read_target_process",
                         side_effect=[("111", 1000), ("222", 2000)]) as identity_call,
            patch.object(harness, "run_instrumentation") as instrument_call,
        ):
            harness.main()

        self.assertEqual(adb_call.call_args_list, [
            call("shell", "am", "force-stop", harness.PACKAGE),
            call("shell", "run-as", harness.PACKAGE, "rm", "-f",
                 "files/qa-process-first.pid", "files/qa-process-restart.pid"),
        ])
        self.assertEqual(wait_call.call_args_list, [
            call(present=False), call(present=False), call(present=False)
        ])
        self.assertEqual(process_call.call_count, 2)
        self.assertEqual(identity_call.call_args_list, [
            call("qa-process-first.pid"), call("qa-process-restart.pid")
        ])
        self.assertEqual(instrument_call.call_args_list, [
            call(harness.INITIAL_METHOD), call(harness.RESTART_METHOD)
        ])

    def test_main_forces_stop_when_activity_process_remains_resident(self):
        with (
            patch.object(harness, "adb", return_value="") as adb_call,
            patch.object(harness, "wait_for_process", side_effect=["", "", ""]) as wait_call,
            patch.object(harness, "process_id", side_effect=["111", "222"]),
            patch.object(harness, "read_target_process",
                         side_effect=[("111", 1000), ("222", 2000)]),
            patch.object(harness, "run_instrumentation") as instrument_call,
        ):
            harness.main()

        self.assertEqual(adb_call.call_args_list, [
            call("shell", "am", "force-stop", harness.PACKAGE),
            call("shell", "run-as", harness.PACKAGE, "rm", "-f",
                 "files/qa-process-first.pid", "files/qa-process-restart.pid"),
            call("shell", "am", "force-stop", harness.PACKAGE),
            call("shell", "am", "force-stop", harness.PACKAGE),
        ])
        self.assertEqual(wait_call.call_count, 3)
        self.assertEqual(instrument_call.call_args_list, [
            call(harness.INITIAL_METHOD), call(harness.RESTART_METHOD)
        ])

    def test_restart_instrumentation_is_not_run_if_process_survives_force_stop(self):
        with (
            patch.object(harness, "adb", return_value=""),
            patch.object(harness, "wait_for_process",
                         side_effect=["", AssertionError("PID remained")]),
            patch.object(harness, "process_id", return_value="111"),
            patch.object(harness, "read_target_process", return_value=("111", 1000)),
            patch.object(harness, "run_instrumentation") as instrument_call,
        ):
            with self.assertRaisesRegex(AssertionError, "PID remained"):
                harness.main()
        instrument_call.assert_called_once_with(harness.INITIAL_METHOD)

    def test_main_rejects_nonadvancing_process_start_time(self):
        with (
            patch.object(harness, "adb", return_value=""),
            patch.object(harness, "wait_for_process", side_effect=["", "", ""]),
            patch.object(harness, "process_id", side_effect=["", ""]),
            patch.object(harness, "read_target_process",
                         side_effect=[("111", 2000), ("222", 1000)]),
            patch.object(harness, "run_instrumentation"),
        ):
            with self.assertRaisesRegex(AssertionError, "later target process"):
                harness.main()


if __name__ == "__main__":
    unittest.main()
