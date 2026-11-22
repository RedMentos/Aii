#!/usr/bin/env python3
"""Unit tests for safe transient-overlay handling in the emulator harness."""
from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from process_restart_ui import button_center, transient_overlay_action


def make_tree(nodes: list[dict[str, str]]) -> ET.Element:
    root = ET.Element("hierarchy")
    for attrs in nodes:
        ET.SubElement(root, "node", attrs)
    return root


class ProcessRestartUiTests(unittest.TestCase):
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

    def test_text_view_is_not_treated_as_a_button(self) -> None:
        root = make_tree([
            {"text": "Wait", "class": "android.widget.TextView", "bounds": "[0,0][100,50]"},
        ])
        self.assertIsNone(button_center(root, "Wait"))


if __name__ == "__main__":
    unittest.main()
