#!/usr/bin/env python3
"""Drive Espresso UI checks around an externally forced Android process death.

The host wakes/unlocks the disposable emulator but leaves ActivityScenario as
the sole MainActivity launcher. Espresso then verifies the visible Stop action;
the host kills the app from outside the process and checks that fresh provider
startup is OFF.
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
    result = subprocess.run(
        ["adb", "shell", "pidof", PACKAGE],
        capture_output=True,
        text=True,
        timeout=10.0,
    )
    # Android toybox pidof commonly returns 1 when the package has no PID.
    # That is the expected state after force-stop; command/transport errors
    # remain fatal and must not be interpreted as process death.
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    # Only the exact toybox "not found" shape (exit 1, empty stdout/stderr)
    # means the target is absent. adb transport errors can also return 1;
    # treating those as absence would invalidate the process-death proof.
    if result.returncode == 0 and re.fullmatch(r"\\d+(?:\\s+\\d+)*", stdout):
        return stdout
    if result.returncode == 1 and not stdout and not stderr:
        return ""
    raise RuntimeError(
        "adb pidof failed or returned an ambiguous result (exit="
        + str(result.returncode) + "): stdout=" + stdout[-500:]
        + "; stderr=" + stderr[-500:]
    )


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


def prepare_emulator_for_instrumentation() -> None:
    """Wake/unlock the disposable emulator without pre-launching MainActivity.

    ActivityScenario is the single owner of the test Activity launch. Starting
    MainActivity from the host first created a second launch path and left the
    Espresso root without window focus on the API-33 emulator.
    """
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb("shell", "wm", "dismiss-keyguard")
    pid = process_id()
    if pid:
        raise AssertionError(
            "companion process must be stopped before ActivityScenario launch; pidof="
            + pid
        )


def run_instrumentation(method: str, timeout: float = 180.0) -> str:
    if method not in ALLOWED_METHODS:
        raise ValueError("instrumentation method is not allowlisted")
    prepare_emulator_for_instrumentation()
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
    # Start from a known stopped process. ActivityScenario owns the only
    # MainActivity launch inside each instrumentation invocation.
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
