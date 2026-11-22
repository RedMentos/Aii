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


def hierarchy() -> ET.Element:
    adb("shell", "uiautomator", "dump", "/sdcard/v14-window.xml", timeout=20)
    raw = adb("exec-out", "cat", "/sdcard/v14-window.xml", timeout=10)
    return ET.fromstring(raw)


def visible_text() -> str:
    root = hierarchy()
    return "\n".join(node.attrib.get("text", "") for node in root.iter("node"))


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


def wait_for_text(needle: str, timeout: float = 20.0) -> str:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        swipe_to_top()
        last = visible_text()
        if needle in last:
            return last
        time.sleep(.35)
    raise AssertionError("UI did not show expected state: " + needle
                         + "; visible labels=" + last[:1200])


def tap_button(label: str) -> None:
    deadline = time.monotonic() + 15.0
    width, height = screen_size()
    while time.monotonic() < deadline:
        root = hierarchy()
        for node in root.iter("node"):
            if node.attrib.get("text") != label:
                continue
            bounds = node.attrib.get("bounds", "")
            match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
            if not match:
                continue
            x1, y1, x2, y2 = map(int, match.groups())
            adb("shell", "input", "tap", str((x1 + x2) // 2),
                str((y1 + y2) // 2))
            return
        adb("shell", "input", "swipe", str(width // 2),
            str(int(height * .86)), str(width // 2),
            str(int(height * .24)), "450")
        time.sleep(.25)
    raise AssertionError("could not locate visible companion button: " + label)


def process_id() -> str:
    return adb("shell", "pidof", PACKAGE, check=False).strip()


def wait_for_process(absent: bool, timeout: float = 12.0) -> str:
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
    adb("shell", "am", "start", "-n", COMPONENT)
    wait_for_text(STOPPED_TEXT)

    tap_button(TOGGLE_LABEL)
    enabled = wait_for_text(ENABLED_TEXT)
    assert ENABLED_TEXT in enabled

    tap_button(TOGGLE_LABEL)
    stopped = wait_for_text(STOPPED_TEXT)
    assert ENABLED_TEXT not in stopped

    tap_button(TOGGLE_LABEL)
    enabled = wait_for_text(ENABLED_TEXT)
    assert ENABLED_TEXT in enabled
    old_pid = wait_for_process(absent=False)

    adb("shell", "am", "force-stop", PACKAGE)
    wait_for_process(absent=True)
    adb("shell", "am", "start", "-n", COMPONENT)
    wait_for_process(absent=False)
    restarted = wait_for_text(STOPPED_TEXT)
    assert ENABLED_TEXT not in restarted

    print("PASS: visible stop blocks the enabled state; force-stop killed PID "
          + old_pid + "; provider/activity restart returned STOPPED without "
          "re-pairing, action submission, or capability grant.")


if __name__ == "__main__":
    main()
