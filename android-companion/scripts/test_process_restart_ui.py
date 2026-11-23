#!/usr/bin/env python3
"""Unit tests for safe transient-overlay handling in the emulator harness."""
from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

import test_process_restart as harness

from process_restart_ui import button_center, transient_overlay_action


def make_tree(nodes: list[dict[str, str]]) -> ET.Element:
    root = ET.Element("hierarchy")
    for attrs in nodes:
        ET.SubElement(root, "node", attrs)
    return root


class ProcessRestartUiTests(unittest.TestCase):
    def test_poll_delay_backs_off_and_caps(self) -> None:
        from process_restart_ui import poll_delay
        self.assertEqual(poll_delay(-1), 2.5)
        self.assertEqual(poll_delay(0), 2.5)
        self.assertEqual(poll_delay(1), 3.25)
        self.assertEqual(poll_delay(4), 5.0)
        self.assertEqual(poll_delay(100), 5.0)

    def test_system_ui_anr_prefers_wait_not_close_app(self) -> None:
        root = make_tree([
            {"text": "System UI isn't responding", "class": "android.widget.TextView"},
            {"text": "Close app", "class": "android.widget.Button", "bounds": "[0,0][100,50]"},
            {"text": "Wait", "class": "android.widget.Button", "bounds": "[100,0][200,50]"},
        ])
        self.assertEqual(transient_overlay_action(root), "Wait")
        self.assertEqual(button_center(root, "Wait"), (150, 25))

    def test_anr_without_wait_fails_closed(self) -> None:
        root = make_tree([
            {"text": "System UI isn't responding", "class": "android.widget.TextView"},
            {"text": "Close app", "class": "android.widget.Button", "bounds": "[0,0][100,50]"},
        ])
        self.assertEqual(transient_overlay_action(root), "SYSTEM_UI_UNRESPONSIVE")

    def test_immersive_confirmation_uses_got_it(self) -> None:
        root = make_tree([
            {"text": "Viewing full screen", "class": "android.widget.TextView"},
            {"text": "To exit, swipe down from the top.", "class": "android.widget.TextView"},
            {"text": "GOT IT", "class": "android.widget.Button", "bounds": "[440,0][640,137]"},
        ])
        self.assertEqual(transient_overlay_action(root), "GOT IT")
        self.assertEqual(button_center(root, "got it"), (540, 68))

    def test_normal_companion_screen_has_no_overlay_action(self) -> None:
        root = make_tree([
            {"text": "STOPPED (restart requires explicit re-enable)", "class": "android.widget.TextView"},
            {"text": "Enable / Stop companion", "class": "android.widget.Button", "bounds": "[10,20][210,70]"},
        ])
        self.assertIsNone(transient_overlay_action(root))

    def test_masked_attribute_token_does_not_hide_visible_companion_state(self) -> None:
        from process_restart_ui import parse_hierarchy, visible_labels
        xml = (
            "<hierarchy><node text='V14 Android Companion&#10;"
            "State: STOPPED (restart requires explicit re-enable)' "
            "class='android.widget.TextView' long-clickable='false' "
            "*** selected='false' bounds='[0,0][100,100]' /></hierarchy>"
        )
        root = parse_hierarchy(xml)
        labels = "\\n".join(visible_labels(root))
        self.assertIn("STOPPED (restart requires explicit re-enable)", labels)

    def test_unrelated_malformed_hierarchy_still_fails_closed(self) -> None:
        from process_restart_ui import parse_hierarchy
        with self.assertRaises(ET.ParseError):
            parse_hierarchy("<hierarchy><node text='unterminated></hierarchy>")

    def test_text_view_is_not_treated_as_a_button(self) -> None:
        root = make_tree([
            {"text": "Wait", "class": "android.widget.TextView", "bounds": "[0,0][100,50]"},
        ])
        self.assertIsNone(button_center(root, "Wait"))


class ProcessRestartWaitRecoveryTests(unittest.TestCase):
    def test_wait_for_text_uses_one_safe_wait_and_never_close_app(self) -> None:
        from unittest.mock import patch
        import test_process_restart as harness

        overlay = make_tree([
            {"text": "System UI isn't responding", "class": "android.widget.TextView"},
            {"text": "Close app", "class": "android.widget.Button", "bounds": "[0,0][100,50]"},
            {"text": "Wait", "class": "android.widget.Button", "bounds": "[100,0][200,50]"},
        ])
        stopped = make_tree([
            {"text": harness.STOPPED_TEXT, "class": "android.widget.TextView"},
        ])
        with (
            patch.object(harness, "hierarchy", side_effect=[overlay, stopped]),
            patch.object(harness, "adb", return_value="") as adb_call,
            patch.object(harness.time, "sleep"),
        ):
            labels = harness.wait_for_text(harness.STOPPED_TEXT, timeout=2.0)
        self.assertIn(harness.STOPPED_TEXT, labels)
        adb_call.assert_called_once_with("shell", "input", "tap", "150", "25")
        self.assertNotIn("Close app", repr(adb_call.call_args_list))

    def test_wait_for_text_fails_after_two_waits_without_selecting_close_app(self) -> None:
        from unittest.mock import patch
        import test_process_restart as harness

        overlay = make_tree([
            {"text": "System UI isn't responding", "class": "android.widget.TextView"},
            {"text": "Close app", "class": "android.widget.Button", "bounds": "[0,0][100,50]"},
            {"text": "Wait", "class": "android.widget.Button", "bounds": "[100,0][200,50]"},
        ])
        with (
            patch.object(harness, "hierarchy", side_effect=[overlay, overlay, overlay]),
            patch.object(harness, "adb", return_value="") as adb_call,
            patch.object(harness.time, "sleep"),
        ):
            with self.assertRaisesRegex(AssertionError, "after two safe Wait actions"):
                harness.wait_for_text(harness.STOPPED_TEXT, timeout=2.0)
        self.assertEqual(
            adb_call.call_args_list,
            [
                unittest.mock.call("shell", "input", "tap", "150", "25"),
                unittest.mock.call("shell", "input", "tap", "150", "25"),
            ],
        )
        self.assertNotIn("Close app", repr(adb_call.call_args_list))

    def test_wait_budget_rejects_more_than_two_safe_waits(self) -> None:
        import test_process_restart as harness

        with self.assertRaisesRegex(ValueError, "0, 1 or 2"):
            harness.wait_for_text(harness.STOPPED_TEXT, wait_budget=3)


class ProcessRestartFinalSnapshotRecoveryTests(unittest.TestCase):
    def test_final_hierarchy_snapshot_can_recover_one_explicit_wait(self) -> None:
        from unittest.mock import patch
        import test_process_restart as harness

        original_monotonic = harness.time.monotonic
        clock_values = iter([0.0, 1.0])

        def clock():
            try:
                return next(clock_values)
            except StopIteration:
                return original_monotonic()

        stopped = make_tree([
            {"text": harness.STOPPED_TEXT, "class": "android.widget.TextView"},
        ])
        overlay_xml = (
            '<hierarchy>'
            '<node text="System UI isn\'t responding" class="android.widget.TextView"/>'
            '<node text="Close app" class="android.widget.Button" bounds="[0,0][100,50]"/>'
            '<node text="Wait" class="android.widget.Button" bounds="[100,0][200,50]"/>'
            '</hierarchy>'
        )
        with (
            patch.object(harness, "hierarchy", return_value=stopped),
            patch.object(harness, "hierarchy_xml", return_value=overlay_xml),
            patch.object(harness, "adb", return_value="") as adb_call,
            patch.object(harness.time, "monotonic", side_effect=clock),
            patch.object(harness.time, "sleep"),
        ):
            labels = harness.wait_for_text(harness.STOPPED_TEXT, timeout=0.01)
        self.assertIn(harness.STOPPED_TEXT, labels)
        adb_call.assert_called_once_with("shell", "input", "tap", "150", "25")

    def test_final_snapshot_without_wait_button_fails_without_tapping(self) -> None:
        from unittest.mock import patch
        import test_process_restart as harness

        original_monotonic = harness.time.monotonic
        clock_values = iter([0.0, 1.0])

        def clock():
            try:
                return next(clock_values)
            except StopIteration:
                return original_monotonic()

        overlay_xml = (
            '<hierarchy>'
            '<node text="System UI isn\'t responding" class="android.widget.TextView"/>'
            '<node text="Close app" class="android.widget.Button" bounds="[0,0][100,50]"/>'
            '</hierarchy>'
        )
        with (
            patch.object(harness, "hierarchy_xml", return_value=overlay_xml),
            patch.object(harness, "adb", return_value="") as adb_call,
            patch.object(harness, "process_id", return_value=""),
            patch.object(harness.time, "monotonic", side_effect=clock),
        ):
            with self.assertRaisesRegex(AssertionError, "UI did not show expected state"):
                harness.wait_for_text(harness.STOPPED_TEXT, timeout=0.01)
        taps = [
            call for call in adb_call.call_args_list
            if len(call.args) >= 3 and call.args[:3] == ("shell", "input", "tap")
        ]
        self.assertEqual(taps, [])


class ProcessRestartLogcatTests(unittest.TestCase):
    def test_failure_logcat_filters_string_output_from_adb(self) -> None:
        from unittest.mock import patch
        import test_process_restart as harness

        raw = (
            "I/ActivityTaskManager: Start proc com.example\n"
            "D/Other: unrelated private line\n"
            "E/AndroidRuntime: FATAL EXCEPTION: main\n"
        )
        with patch.object(harness, "adb", return_value=raw):
            selected = harness.failure_logcat()
        self.assertIn("ActivityTaskManager", selected)
        self.assertIn("FATAL EXCEPTION", selected)
        self.assertNotIn("unrelated private line", selected)

    def test_failure_logcat_handles_empty_string_output(self) -> None:
        from unittest.mock import patch
        import test_process_restart as harness

        with patch.object(harness, "adb", return_value=""):
            self.assertEqual(
                harness.failure_logcat(), "(no matching logcat lines)"
            )



class ProcessRestartLaunchTests(unittest.TestCase):
    def test_launch_dismisses_keyguard_and_waits_without_menu_key(self) -> None:
        from unittest.mock import call, patch
        import test_process_restart as harness

        with (
            patch.object(harness, "adb", return_value="") as adb_call,
            patch.object(harness.time, "sleep") as sleep,
        ):
            harness.launch_companion()

        self.assertEqual(
            adb_call.call_args_list,
            [
                call("shell", "wm", "dismiss-keyguard", check=False),
                call("shell", "am", "start", "-n", harness.COMPONENT, timeout=60),
            ],
        )
        sleep.assert_called_once_with(2.0)

    def test_hierarchy_dump_uses_compressed_snapshot(self) -> None:
        from unittest.mock import call, patch
        import test_process_restart as harness

        with patch.object(harness, "adb", side_effect=["OK", "<hierarchy/>"]) as adb_call:
            self.assertEqual(harness.hierarchy_xml(), "<hierarchy/>")

        self.assertEqual(
            adb_call.call_args_list[0],
            call("shell", "uiautomator", "dump", "--compressed",
                 "/data/local/tmp/v14-window.xml", timeout=20),
        )


class ProcessRestartDurabilityTests(unittest.TestCase):
    def test_stop_marker_requires_persisted_off(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import test_process_restart as harness

        with TemporaryDirectory() as directory:
            marker = Path(directory) / "stop-proof"
            with (
                patch.object(harness, "STOP_PROOF_MARKER", marker),
                patch.object(harness, "persisted_enabled", return_value="true"),
            ):
                with self.assertRaisesRegex(AssertionError, "did not persist OFF"):
                    harness.record_stop_persisted_off()
            self.assertFalse(marker.exists())

            with (
                patch.object(harness, "STOP_PROOF_MARKER", marker),
                patch.object(harness, "persisted_enabled", return_value="false"),
            ):
                harness.record_stop_persisted_off()
            self.assertEqual(marker.read_text(encoding="utf-8").strip(),
                             "STOP_ACTION_PERSISTED_OFF")

    def test_durable_restart_requires_verified_visible_stop_marker(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import test_process_restart as harness

        with TemporaryDirectory() as directory:
            marker = Path(directory) / "stop-proof"
            with (
                patch.object(harness, "STOP_PROOF_MARKER", marker),
                patch.object(harness, "persisted_enabled", return_value="false"),
            ):
                with self.assertRaisesRegex(AssertionError, "no verified visible Stop action marker"):
                    harness.verify_durable_off_after_process_death()

    def test_durable_restart_force_stops_relaunches_and_checks_off(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import call, patch
        import test_process_restart as harness

        with TemporaryDirectory() as directory:
            marker = Path(directory) / "stop-proof"
            marker.write_text("STOP_ACTION_PERSISTED_OFF\n", encoding="utf-8")
            with (
                patch.object(harness, "STOP_PROOF_MARKER", marker),
                patch.object(harness, "persisted_enabled", side_effect=["false", "false"]),
                patch.object(harness, "process_id", return_value="1234"),
                patch.object(harness, "adb") as adb_call,
                patch.object(harness, "wait_for_process", side_effect=["", "5678"]) as wait_call,
                patch.object(harness, "launch_companion") as launch_call,
            ):
                harness.verify_durable_off_after_process_death()

            adb_call.assert_called_once_with("shell", "am", "force-stop", harness.PACKAGE)
            self.assertEqual(wait_call.call_args_list,
                             [call(absent=True), call(absent=False)])
            launch_call.assert_called_once_with()
            self.assertFalse(marker.exists())

    def test_ui_failure_runs_durable_probe_but_remains_a_failure(self) -> None:
        import subprocess
        from unittest.mock import patch
        import test_process_restart as harness

        failures = (
            AssertionError("System UI blocked"),
            subprocess.TimeoutExpired(["adb", "shell", "uiautomator", "dump"], 20),
            subprocess.CalledProcessError(1, ["adb", "shell", "uiautomator", "dump"]),
            FileNotFoundError("adb"),
            RuntimeError("adb transport failed"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with (
                    patch.object(harness, "wait_for_text", side_effect=failure),
                    patch.object(harness, "verify_durable_off_after_process_death") as durable,
                ):
                    with self.assertRaises(type(failure)):
                        harness.wait_for_stopped_ui_or_prove_durable()
                durable.assert_called_once_with()


class ProcessRestartPostRestartDurabilityTests(unittest.TestCase):
    def test_post_restart_ui_failures_report_partial_only_after_marker_and_off(self) -> None:
        import contextlib
        import io
        import subprocess
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import test_process_restart as harness

        failures = (
            AssertionError("System UI blocked"),
            subprocess.TimeoutExpired(["adb", "shell", "uiautomator", "dump"], 20),
            subprocess.CalledProcessError(1, ["adb", "shell", "uiautomator", "dump"]),
            FileNotFoundError("adb"),
            RuntimeError("adb transport failed"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__), TemporaryDirectory() as directory:
                marker = Path(directory) / "stop-proof"
                marker.write_text("STOP_ACTION_PERSISTED_OFF\n", encoding="utf-8")
                output = io.StringIO()
                with (
                    patch.object(harness, "STOP_PROOF_MARKER", marker),
                    patch.object(harness, "persisted_enabled", return_value="false"),
                    patch.object(harness, "wait_for_text", side_effect=failure),
                    contextlib.redirect_stdout(output),
                ):
                    with self.assertRaises(type(failure)):
                        harness.wait_for_restarted_stopped_ui_or_report_durable()
                self.assertIn("PARTIAL_PASS: force-stop/PID disappearance", output.getvalue())

    def test_post_restart_ui_failure_never_claims_partial_without_marker_or_off(self) -> None:
        import contextlib
        import io
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import test_process_restart as harness

        cases = ((False, "false"), (True, "true"))
        for marker_exists, enabled in cases:
            with self.subTest(marker_exists=marker_exists, enabled=enabled), TemporaryDirectory() as directory:
                marker = Path(directory) / "stop-proof"
                if marker_exists:
                    marker.write_text("STOP_ACTION_PERSISTED_OFF\n", encoding="utf-8")
                output = io.StringIO()
                with (
                    patch.object(harness, "STOP_PROOF_MARKER", marker),
                    patch.object(harness, "persisted_enabled", return_value=enabled),
                    patch.object(harness, "wait_for_text", side_effect=AssertionError("UI blocked")),
                    contextlib.redirect_stdout(output),
                ):
                    with self.assertRaisesRegex(AssertionError, "UI blocked"):
                        harness.wait_for_restarted_stopped_ui_or_report_durable()
                self.assertIn("DURABLE_STOP_PROOF_FAILED", output.getvalue())
                self.assertNotIn("PARTIAL_PASS", output.getvalue())


class ProcessRestartPidofTests(unittest.TestCase):
    def test_pidof_exit_one_without_output_means_absent(self):
        from unittest.mock import patch
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=1, stdout="", stderr="",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            self.assertEqual(harness.process_id(), "")

    def test_pidof_numeric_output_means_present(self):
        from unittest.mock import patch
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=0, stdout="1234 5678\n", stderr="",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            self.assertEqual(harness.process_id(), "1234 5678")

    def test_pidof_exit_one_with_transport_error_fails_closed(self):
        from unittest.mock import patch
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=1, stdout="", stderr="error: device offline",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "ambiguous result"):
                harness.process_id()

    def test_pidof_exit_one_with_unexpected_stdout_fails_closed(self):
        from unittest.mock import patch
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=1, stdout="not-a-pid", stderr="",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "ambiguous result"):
                harness.process_id()

    def test_pidof_exit_zero_without_pid_fails_closed(self):
        from unittest.mock import patch
        completed = harness.subprocess.CompletedProcess(
            args=["adb", "shell", "pidof", harness.PACKAGE],
            returncode=0, stdout="", stderr="",
        )
        with patch.object(harness.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "ambiguous result"):
                harness.process_id()


if __name__ == "__main__":
    unittest.main()
