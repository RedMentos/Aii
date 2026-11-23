#!/usr/bin/env python3
"""Unit tests for the Espresso/host process-death integration driver."""
from __future__ import annotations

import unittest
from unittest.mock import call, patch

import test_process_restart_instrumented as harness


class InstrumentationDriverTests(unittest.TestCase):
    def test_instrumentation_unlocks_emulator_without_prelaunching_target(self):
        output = "INSTRUMENTATION_RESULT: stream=\\n\\nOK (1 test)\\nINSTRUMENTATION_CODE: -1"
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

    def test_wait_for_process_polls_until_requested_state(self):
        with (
            patch.object(harness, "process_id", side_effect=["", "4321"]),
            patch.object(harness.time, "monotonic", side_effect=[0.0, 0.1, 0.2]),
            patch.object(harness.time, "sleep") as sleep,
        ):
            self.assertEqual(harness.wait_for_process(present=True, timeout=1.0), "4321")
        sleep.assert_called_once_with(0.25)

    def test_main_forces_stop_between_two_real_instrumentation_phases(self):
        with (
            patch.object(harness, "adb", return_value="") as adb_call,
            patch.object(harness, "wait_for_process",
                         side_effect=["", "111", "", "222"]) as wait_call,
            patch.object(harness, "run_instrumentation") as instrument_call,
        ):
            harness.main()

        self.assertEqual(
            adb_call.call_args_list,
            [
                call("shell", "am", "force-stop", harness.PACKAGE),
                call("shell", "am", "force-stop", harness.PACKAGE),
            ],
        )
        self.assertEqual(
            wait_call.call_args_list,
            [
                call(present=False),
                call(present=True),
                call(present=False),
                call(present=True),
            ],
        )
        self.assertEqual(
            instrument_call.call_args_list,
            [
                call(harness.INITIAL_METHOD),
                call(harness.RESTART_METHOD),
            ],
        )

    def test_restart_instrumentation_is_not_run_if_process_does_not_die(self):
        with (
            patch.object(harness, "adb", return_value=""),
            patch.object(harness, "wait_for_process",
                         side_effect=["", "111", AssertionError("PID remained")]),
            patch.object(harness, "run_instrumentation") as instrument_call,
        ):
            with self.assertRaisesRegex(AssertionError, "PID remained"):
                harness.main()
        instrument_call.assert_called_once_with(harness.INITIAL_METHOD)


if __name__ == "__main__":
    unittest.main()
