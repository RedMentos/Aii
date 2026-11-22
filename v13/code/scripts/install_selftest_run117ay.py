#!/usr/bin/env python3
"""Run117AY optional bounded model-free JEF/C2→C3→C5/C6 phone smoke.

Independent opt-in command. Does not modify installed setup.sh default or any
registered legacy/run102/run104 cohort, native model, output or learning gate.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest

from scripts import install_selftest as smoke

APP = Path(__file__).resolve().parents[1]
MAX_SECONDS = 120
EXTRA = (
    "test_run117ax_jef_route_operator_cli.JefRouteOperatorCli.test_six_optin_route_bound_drafts_and_restart",
    "test_run117ax_jef_route_operator_cli.JefRouteOperatorCli.test_forged_route_prompt_refused_before_c5_draft",
    "test_run117ax_jef_route_operator_cli.JefRouteOperatorCli.test_command_line_route_flag_is_explicit",
    "test_run117aw_jef_c2_c3_formatter_route_shadow.JefC2C3RouteShadow.test_valid_c2_is_advisory_not_a_route_override",
)
CASES = smoke.SMOKE_CASES_RUN104_C3_C5_EXIT + EXTRA
ORIGINAL = {
    "legacy_run97": "31b7d96ed740139b07b3b9dcf820aa04fafa13f5dfdcc4645e1df8e8df933f55",
    "run102_c3": "218303e408fab72d705dc3daa2f63dab63e0e34a7ab7ecc31f4954c585a563f5",
    "run104_c3_c5_exit": "d745f4a1df7d54f7b1c1024e7d3aa24603d007070a694a6611d50ba958b96d70",
}


def _cohorts_unchanged():
    if (set(smoke.COHORTS) != set(ORIGINAL)
            or smoke.COHORTS["legacy_run97"] is not smoke.SMOKE_CASES
            or smoke.COHORTS["run102_c3"] is not smoke.SMOKE_CASES_RUN102_C3
            or smoke.run_bounded.__defaults__ != (120, "legacy_run97")
            or len(CASES) != 25 or len(set(CASES)) != 25
            or CASES[:21] != smoke.SMOKE_CASES_RUN104_C3_C5_EXIT
            or CASES[21:] != EXTRA):
        raise ValueError("RUN117AY_REGISTERED_COHORT_OR_EXTENSION_RED")
    for name,expected in ORIGINAL.items():
        got=sha256(json.dumps(smoke.COHORTS[name],
                              separators=(",",":")).encode()).hexdigest()
        if got != expected:
            raise ValueError("RUN117AY_ORIGINAL_COHORT_HASH_RED")
    if 'scripts/install_selftest.py" --cohort run102_c3' not in (
            APP/"setup.sh").read_text():
        raise ValueError("RUN117AY_DEFAULT_INSTALL_CHANGED_RED")


def worker():
    os.environ.update(NO_MODEL_DOWNLOADS="1", DO_NOT_TRACK="1",
                      V13_INSTALL_SMOKE="1",
                      V13_INSTALL_SMOKE_COHORT="run117ay_optional")
    try:
        _cohorts_unchanged()
        suite=smoke.load_exact_suite(CASES)
    except (ValueError, ImportError, AttributeError, OSError) as exc:
        print("RUN117AY_INSTALL_SELFTEST_REFUSED:"+str(exc),file=sys.stderr,
              flush=True)
        return 2
    print("RUN117AY_SCOPE=MODEL_FREE_SOFTWARE_ONLY; NOT_NATIVE_OR_REDMI",
          flush=True)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print("RUN117AY_RESULT tests={} expected=25 failures={} errors={} skipped={}".format(
        result.testsRun,len(result.failures),len(result.errors),
        len(result.skipped)),flush=True)
    return 0 if result.wasSuccessful() and result.testsRun==25 else 1


def run_bounded(seconds=MAX_SECONDS):
    if type(seconds) is not int or not 1 <= seconds <= MAX_SECONDS:
        raise ValueError("RUN117AY_TIMEOUT_NOT_INTEGER_1_TO_120")
    _cohorts_unchanged()
    env=os.environ.copy()
    env.update(NO_MODEL_DOWNLOADS="1",DO_NOT_TRACK="1",
               V13_INSTALL_SMOKE="1",
               V13_INSTALL_SMOKE_COHORT="run117ay_optional")
    dirs=(str(APP),str(APP/"tests"),str(APP/"scripts"))
    env["PYTHONPATH"]=os.pathsep.join(
        (*dirs,*( [env["PYTHONPATH"]] if env.get("PYTHONPATH") else [] )))
    proc=subprocess.Popen(
        [sys.executable,"-m","scripts.install_selftest_run117ay","--worker"],
        cwd=str(APP),env=env,start_new_session=True)
    try:
        code=proc.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            proc.kill()
        proc.wait()
        print("RUN117AY_TIMEOUT_REAPED",file=sys.stderr,flush=True)
        return 124
    if code==0:
        print("RUN117AY_PASS_25_SOFTWARE_ONLY_NOT_NATIVE",flush=True)
    else:
        print("RUN117AY_RED_WORKER_EXIT_"+str(code),file=sys.stderr,flush=True)
    return code


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--timeout-seconds",type=int,default=MAX_SECONDS)
    p.add_argument("--worker",action="store_true",help=argparse.SUPPRESS)
    a=p.parse_args(argv)
    if a.worker:
        return worker()
    try:
        return run_bounded(a.timeout_seconds)
    except ValueError as exc:
        p.error(str(exc))


if __name__=="__main__":
    raise SystemExit(main())
