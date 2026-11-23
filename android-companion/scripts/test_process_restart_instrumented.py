#!/usr/bin/env python3
"""Drive real Android Espresso UI checks around an externally forced process death.

Espresso clicks the companion's actual visible MainActivity button. The host
then verifies PID disappearance, starts a fresh instrumentation process, and
checks that provider startup returns to STOPPED. This avoids relying on
System-UI/uiautomator hierarchy dumps, which repeatedly ANR on the TCG runner.
"""
from __future__ import annotations

import re
import subprocess
import time

PACKAGE = "com.redmentos.v14.companion"
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
    return adb("shell", "pidof", PACKAGE, timeout=10.0).strip()


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


def run_instrumentation(method: str, timeout: float = 180.0) -> str:
    if method not in ALLOWED_METHODS:
        raise ValueError("instrumentation method is not allowlisted")
    target = TEST_CLASS + "#" + method
    output = adb(
        "shell", "am", "instrument", "-w", "-r",
        "-e", "class", target, TEST_RUNNER,
        timeout=timeout,
    )
    if "FAILURES!!!" in output or "INSTRUMENTATION_FAILED" in output:
        raise AssertionError("Android instrumentation reported failure: " + output[-4000:])
    if not re.search(r"\\bOK\\s*\\(1 test\\)", output):
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
    # Start from a known stopped process. The first instrumentation launch
    # creates a fresh app process, whose ContentProvider must persist OFF.
    adb("shell", "am", "force-stop", PACKAGE)
    wait_for_process(present=False)
    run_instrumentation(INITIAL_METHOD)
    first_pid = wait_for_process(present=True)

    # This is the actual process-death boundary, outside the target app and
    # outside the instrumentation runner.
    adb("shell", "am", "force-stop", PACKAGE)
    wait_for_process(present=False)

    # Starting instrumentation launches a new target process. Provider
    # onCreate() must reset its process grant and persisted flag to OFF.
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
