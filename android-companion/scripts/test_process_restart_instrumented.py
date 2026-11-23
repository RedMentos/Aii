#!/usr/bin/env python3
"""Drive Espresso UI checks around an externally forced Android process death.

The host wakes/unlocks the disposable emulator, launches the visible activity,
and verifies WindowManager focus plus ActivityTaskManager resume before
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


def diagnostic_logcat() -> str:
    try:
        output = adb("logcat", "-d", "-t", "300", "-v", "brief", timeout=15.0)
    except Exception as exc:
        return "logcat unavailable: " + type(exc).__name__
    needles = (
        "AndroidRuntime", "FATAL EXCEPTION", "ANR in ",
        "Application Not Responding", "ActivityTaskManager",
        "WindowManager", "InputDispatcher", PACKAGE,
    )
    selected = [
        line for line in output.splitlines()
        if any(token in line for token in needles)
    ]
    return "\n".join(selected[-40:]) or "(no matching logcat lines)"


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


def wait_for_activity_focus(
    timeout: float = 30.0, *, start_output: str = "", pid: str = "",
) -> None:
    """Require the companion to be both resumed and the focused window."""
    deadline = time.monotonic() + timeout
    last_focus: list[str] = []
    last_resumed: list[str] = []
    last_package_lines: list[str] = []
    while time.monotonic() < deadline:
        # The summary dumpsys window output includes mCurrentFocus; the
        # windows subcommand can omit that summary on some API-33 images.
        windows = adb("shell", "dumpsys", "window", timeout=20.0)
        activities = adb("shell", "dumpsys", "activity", "activities", timeout=20.0)
        last_focus = [
            line.strip() for line in windows.splitlines()
            if "mCurrentFocus" in line or "mFocusedApp" in line
        ]
        last_resumed = [
            line.strip() for line in activities.splitlines()
            if "mResumedActivity" in line or "topResumedActivity" in line
        ]
        last_package_lines = [
            line.strip() for line in (windows + "\n" + activities).splitlines()
            if PACKAGE in line
        ][:8]
        focus_ok = any(PACKAGE in line for line in last_focus)
        resumed_ok = any(PACKAGE in line for line in last_resumed)
        if focus_ok and resumed_ok:
            return
        time.sleep(0.5)

    raise AssertionError(
        "companion MainActivity did not obtain window focus; pidof=" + pid
        + "; am_start=" + repr(start_output[-1200:])
        + "; focus=" + repr(last_focus[:3])
        + "; resumed=" + repr(last_resumed[:3])
        + "; package_lines=" + repr(last_package_lines)
        + "; logcat=" + diagnostic_logcat()
    )


def prepare_foreground_activity() -> None:
    """Wake and foreground the app on the disposable CI emulator only."""
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb("shell", "wm", "dismiss-keyguard")
    # Match the established companion launcher path: no HOME key (which
    # exercises System UI unnecessarily) and no -W wait-for-draw ambiguity.
    start_output = adb("shell", "am", "start", "-n", COMPONENT, timeout=45.0)
    time.sleep(2.0)
    pid = process_id()
    if not pid:
        raise AssertionError(
            "am start did not create companion process; am_start="
            + repr(start_output[-1200:]) + "; logcat=" + diagnostic_logcat()
        )
    wait_for_activity_focus(start_output=start_output, pid=pid)


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
