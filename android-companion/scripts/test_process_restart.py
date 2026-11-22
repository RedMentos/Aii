#!/usr/bin/env python3
"""Exercise the real Android companion stop/restart boundary on an emulator.

This runs from the GitHub host, outside the companion process. It force-stops
the installed app process, verifies that the PID disappears, relaunches the
visible MainActivity, and checks that provider startup persisted OFF. It never
pairs Termux, submits an action, or grants a capability.
"""
from __future__ import annotations

import re
import subprocess
import time
import xml.etree.ElementTree as ET

from process_restart_ui import button_center, poll_delay, transient_overlay_action, visible_labels

PACKAGE = "com.redmentos.v14.companion"
COMPONENT = PACKAGE + "/.MainActivity"
TOGGLE_LABEL = "Enable / Stop companion"
STOPPED_TEXT = "STOPPED (restart requires explicit re-enable)"
ENABLED_TEXT = "ENABLED FOR THIS PROCESS"


def adb(*args: str, check: bool = True, timeout: float = 25.0) -> str:
    result = subprocess.run(
        ["adb", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode:
        raise RuntimeError(
            "adb " + " ".join(args) + " failed: "
            + result.stderr[-1000:]
        )
    return result.stdout.strip()


def screen_size() -> tuple[int, int]:
    output = adb("shell", "wm", "size", check=False)
    match = re.search(r"(\d+)x(\d+)", output)
    if not match:
        return 1080, 1920
    return int(match.group(1)), int(match.group(2))


def hierarchy_xml() -> str:
    # /sdcard is app-scoped on Android 13 and is not reliably readable by the
    # shell after uiautomator writes it. Keep this host-only probe artifact in
    # the shell-owned temporary directory instead of touching app storage.
    path = "/data/local/tmp/v14-window.xml"
    adb("shell", "uiautomator", "dump", path, timeout=20)
    return adb("exec-out", "cat", path, timeout=10)


def hierarchy() -> ET.Element:
    return ET.fromstring(hierarchy_xml())


def foreground_diagnostic() -> str:
    activity = adb("shell", "dumpsys", "activity", "activities", check=False)
    window = adb("shell", "dumpsys", "window", "windows", check=False)
    activity_lines = [line.strip() for line in activity.splitlines()
                      if "mResumedActivity" in line or "topResumedActivity" in line]
    window_lines = [line.strip() for line in window.splitlines()
                    if "mCurrentFocus" in line or "mFocusedApp" in line]
    return "pidof=" + process_id() + "; activity=" + repr(activity_lines[:3]) \
        + "; window=" + repr(window_lines[:3])


def swipe_to_bottom() -> None:
    width, height = screen_size()
    x = width // 2
    adb("shell", "input", "swipe", str(x), str(int(height * .86)),
        str(x), str(int(height * .24)), "450")


def swipe_to_top() -> None:
    width, height = screen_size()
    x = width // 2
    adb("shell", "input", "swipe", str(x), str(int(height * .24)),
        str(x), str(int(height * .86)), "450")


def handle_transient_overlay(root: ET.Element) -> bool:
    """Dismiss only known benign overlays; never close an unresponsive app."""
    action = transient_overlay_action(root)
    if action is None:
        return False
    if action == "SYSTEM_UI_UNRESPONSIVE":
        raise AssertionError(
            "Android emulator System UI is unresponsive and exposes no Wait "
            "button; refusing to select Close app"
        )
    center = button_center(root, action)
    if center is None:
        raise AssertionError("transient Android overlay has no safe button: " + action)
    adb("shell", "input", "tap", str(center[0]), str(center[1]))
    time.sleep(1.2 if action == "Wait" else 0.4)
    return True


def wait_for_text(needle: str, timeout: float = 45.0) -> str:
    deadline = time.monotonic() + timeout
    last = ""
    attempts = 0
    while time.monotonic() < deadline:
        try:
            root = hierarchy()
        except (RuntimeError, ET.ParseError, subprocess.TimeoutExpired):
            time.sleep(poll_delay(attempts))
            continue
        if handle_transient_overlay(root):
            attempts = 0
            continue
        last = "\n".join(visible_labels(root))
        if needle in last:
            return last
        attempts += 1
        # Avoid flooding a slow TCG emulator with continuous UIAutomator dumps
        # and swipes. Scroll only after several unsuccessful observations.
        if attempts % 4 == 0:
            try:
                swipe_to_top()
            except RuntimeError:
                pass
        time.sleep(poll_delay(attempts))
    try:
        xml = hierarchy_xml()[:3000]
    except Exception as exc:
        xml = "hierarchy unavailable: " + type(exc).__name__
    raise AssertionError("UI did not show expected state: " + needle
                         + "; visible labels=" + last[:1200]
                         + "; " + foreground_diagnostic()
                         + "; hierarchy=" + xml)


def tap_button(label: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    width, height = screen_size()
    attempts = 0
    while time.monotonic() < deadline:
        try:
            root = hierarchy()
        except (RuntimeError, ET.ParseError, subprocess.TimeoutExpired):
            time.sleep(poll_delay(attempts))
            continue
        if handle_transient_overlay(root):
            attempts = 0
            continue
        center = button_center(root, label)
        if center is not None:
            adb("shell", "input", "tap", str(center[0]), str(center[1]))
            return
        attempts += 1
        if attempts % 3 == 0:
            adb("shell", "input", "swipe", str(width // 2),
                str(int(height * .86)), str(width // 2),
                str(int(height * .24)), "450")
        time.sleep(poll_delay(attempts))
    raise AssertionError("could not locate visible companion button: " + label)


def persisted_enabled() -> str:
    raw = adb("shell", "run-as", PACKAGE, "cat",
              "shared_prefs/v14-companion.xml")
    root = ET.fromstring(raw)
    for node in root:
        if node.tag == "boolean" and node.attrib.get("name") == "enabled":
            return node.attrib.get("value", "")
    raise AssertionError("persisted companion enabled flag is missing")


def process_id() -> str:
    return adb("shell", "pidof", PACKAGE, check=False).strip()


def wait_for_process(absent: bool, timeout: float = 45.0) -> str:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        last = process_id()
        if bool(last) != absent:
            return last
        time.sleep(.2)
    raise AssertionError(
        "companion process did not become " + ("absent" if absent else "present")
        + "; pidof=" + last
    )


def main() -> None:
    adb("shell", "am", "force-stop", PACKAGE, check=False)
    adb("shell", "wm", "dismiss-keyguard", check=False)
    adb("shell", "input", "keyevent", "82", check=False)
    adb("shell", "am", "start", "-n", COMPONENT, timeout=60)
    wait_for_process(absent=False)
    wait_for_text(STOPPED_TEXT, timeout=60.0)

    assert persisted_enabled() == "false"

    tap_button(TOGGLE_LABEL)
    enabled = wait_for_text(ENABLED_TEXT)
    assert ENABLED_TEXT in enabled
    assert persisted_enabled() == "true"

    tap_button(TOGGLE_LABEL)
    stopped = wait_for_text(STOPPED_TEXT)
    assert ENABLED_TEXT not in stopped
    assert persisted_enabled() == "false"

    tap_button(TOGGLE_LABEL)
    enabled = wait_for_text(ENABLED_TEXT)
    assert ENABLED_TEXT in enabled
    assert persisted_enabled() == "true"
    old_pid = wait_for_process(absent=False)

    adb("shell", "am", "force-stop", PACKAGE)
    wait_for_process(absent=True)
    adb("shell", "am", "start", "-n", COMPONENT)
    wait_for_process(absent=False)
    restarted = wait_for_text(STOPPED_TEXT, timeout=60.0)
    assert ENABLED_TEXT not in restarted
    assert persisted_enabled() == "false"

    print("PASS: visible stop persisted OFF; force-stop killed PID "
          + old_pid + "; provider/activity restart returned STOPPED without "
          "re-pairing, action submission, or capability grant.")


if __name__ == "__main__":
    main()
