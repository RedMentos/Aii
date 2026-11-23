#!/usr/bin/env python3
"""Drive Espresso UI checks around an externally forced Android process death.

The host wakes/unlocks the disposable emulator, launches the visible activity,
and waits for both WindowManager focus and ActivityTaskManager resume before
starting Espresso. It then verifies a real visible Stop action, kills the app
from outside the process, and checks that a fresh provider startup is OFF.
"""
from __future__ import annotations

import re
import subprocess
import time

PACKAGE = "com.redmentos.v14.companion"
COMPONENT = PACKAGE + "/.MainActivity"
TEST_RUNNER = (
    "com.redmentos.v14.companion.test/"
    "androidx.test.runner.AndroidJUnitRunner"
)
TEST_CLASS = "com.redmentos.v14.companion.CompanionLifecycleInstrumentedTest"
INITIAL_METHOD = "testVisibleStopButtonPersistsOff"
RESTART_METHOD = "testProviderStartupAfterProcessDeathRemainsStopped"
ALLOWED_METHODS = {INITIAL_METHOD, RESTART_METHOD}


def adb(*args: str, timeout: float = 30.0) -> str:
    result = subprocess.run(
        ["adb", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(
            "adb command failed (exit=" + str(result.returncode) + "): "
            + " ".join(args) + "; " + result.stderr[-1000:]
        )
    return result.stdout.strip()


def process_id() -> str:
    result = subprocess.run(
        ["adb", "shell", "pidof", PACKAGE],
        capture_output=True,
        text=True,
        timeout=10.0,
    )
    # Android toybox pidof commonly returns 1 when the package has no PID.
    # That is the expected state after force-stop; command/transport errors
    # remain fatal and must not be interpreted as process death.
    if result.returncode not in (0, 1):
        raise RuntimeError(
            "adb pidof failed (exit=" + str(result.returncode) + "): "
            + result.stderr[-1000:]
        )
    return result.stdout.strip()


def wait_for_process(*, present: bool, timeout: float = 45.0) -> str:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        last = process_id()
        if bool(last) == present:
            return last
        time.sleep(0.25)
    expected = "present" if present else "absent"
    raise AssertionError(
        "companion process did not become " + expected + "; pidof=" + last
    )


def wait_for_activity_focus(timeout: float = 30.0) -> None:
    """Require the companion to be both resumed and the focused window."""
    deadline = time.monotonic() + timeout
    last_focus: list[str] = []
    last_resumed: list[str] = []
    while time.monotonic() < deadline:
        windows = adb("shell", "dumpsys", "window", "windows", timeout=20.0)
        activities = adb("shell", "dumpsys", "activity", "activities", timeout=20.0)
        last_focus = [
            line.strip() for line in windows.splitlines()
            if "mCurrentFocus" in line or "mFocusedApp" in line
        ]
        last_resumed = [
            line.strip() for line in activities.splitlines()
            if "mResumedActivity" in line or "topResumedActivity" in line
        ]
        focus_ok = any(PACKAGE in line for line in last_focus)
        resumed_ok = any(PACKAGE in line for line in last_resumed)
        if focus_ok and resumed_ok:
            return
        time.sleep(0.5)
    raise AssertionError(
        "companion MainActivity did not obtain window focus; focus="
        + repr(last_focus[:3]) + "; resumed=" + repr(last_resumed[:3])
    )


def prepare_foreground_activity() -> None:
    """Wake and foreground the app on the disposable CI emulator only."""
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb("shell", "wm", "dismiss-keyguard")
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    adb("shell", "am", "start", "-W", "-n", COMPONENT, timeout=45.0)
    wait_for_activity_focus()


def run_instrumentation(method: str, timeout: float = 180.0) -> str:
    if method not in ALLOWED_METHODS:
        raise ValueError("instrumentation method is not allowlisted")
    prepare_foreground_activity()
    target = TEST_CLASS + "#" + method
    output = adb(
        "shell", "am", "instrument", "-w", "-r",
        "-e", "class", target, TEST_RUNNER,
        timeout=timeout,
    )
    if "FAILURES!!!" in output or "INSTRUMENTATION_FAILED" in output:
        raise AssertionError("Android instrumentation reported failure: " + output[-4000:])
    if not re.search(r"\bOK\s*\(1 test\)", output):
        raise AssertionError(
            "Android instrumentation did not report exactly one passing test: "
            + output[-4000:]
        )
    if "INSTRUMENTATION_CODE: -1" not in output:
        raise AssertionError(
            "Android instrumentation did not report normal completion: "
            + output[-2000:]
        )
    return output


def main() -> None:
    # Start from a known stopped process. The first instrumentation invocation
    # explicitly foregrounds MainActivity after provider startup.
    adb("shell", "am", "force-stop", PACKAGE)
    wait_for_process(present=False)
    run_instrumentation(INITIAL_METHOD)
    first_pid = wait_for_process(present=True)

    # This is the actual process-death boundary, outside the target app and
    # outside the instrumentation runner.
    adb("shell", "am", "force-stop", PACKAGE)
    wait_for_process(present=False)

    # Starting MainActivity starts a new process. Provider onCreate() must
    # reset the process grant and persisted flag to OFF before the second test.
    run_instrumentation(RESTART_METHOD)
    restarted_pid = wait_for_process(present=True)

    print(
        "PASS: Espresso visibly enabled/stopped the companion; host observed "
        "PID disappearance after force-stop; fresh provider/activity startup "
        "returned STOPPED with enabled=false. PID "
        + first_pid + " -> " + restarted_pid
    )


if __name__ == "__main__":
    main()
