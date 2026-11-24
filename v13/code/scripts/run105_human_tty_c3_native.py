"""Run105: operator-command Age0 F1/F5 source -> separate CLI -> real pinned C3.

Linux-native, synthetic public budget only. Not Runtime._turn, not Redmi.
Prereg: docs/proofs/continuation-20261028/RUN105_HUMAN_SOURCE_C3_NATIVE_PREREG.md
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import traceback
from pathlib import Path

from scripts.run93_source_c3_native_e2e import install as install_pinned, MODEL_SHA, REVISION
from v13.common import APP

QUESTION = "What is the budget for Project Elyra?"
WRONG = "What is the budget for Project Dovan?"
OUTSIDE = "Who leads Project Elyra?"
SCHEMA = "v13.run105.human_source_cli_c3_linux_native.v1"


def _age0(cfg):
    return (cfg.get("system_stage") == 0
            and cfg.get("learning_mode") == "RECORD_ONLY"
            and cfg.get("latents_enabled") is False
            and cfg.get("jepa_weight", 0) == 0)


def _preflight_ok(value, expected):
    return (isinstance(value, dict)
            and value.get("status") == expected
            and value.get("native_calls") == 0
            and value.get("model_called") is False
            and (expected == "READY" or not re.search(
                r"\d", str(value.get("answer") or ""))))


def _native_ok(value, source_ref):
    if not isinstance(value, dict):
        return False
    if (value.get("status") != "FINAL" or value.get("native_calls") != 1
            or value.get("model_called") is not True
            or value.get("process_reaped") is not True
            or value.get("model_revision") != REVISION
            or value.get("source_ref") != source_ref):
        return False
    answer = value.get("answer")
    if not isinstance(answer, str):
        return False
    named = re.findall(r"\bProject\s+([A-Za-z][A-Za-z0-9_-]*)\b", answer, re.I)
    return (re.findall(r"(?<!\w)\d+(?!\w)", answer) == ["615"]
            and not re.search(r"(?<!\w)-\s*615\b", answer)
            and bool(named) and all(name.casefold() == "elyra" for name in named)
            and bool(re.search(r"\b(?:Euro|Euros|EUR)\b|€", answer, re.I)))


def _cli(home, question, *, native=True):
    argv = [sys.executable, "-m", "v13", "--home", str(home),
            "source-answer", question]
    if native:
        argv += ["--native", "--timeout", "90", "--max-tokens", "64"]
    process = subprocess.run(argv, cwd=APP, capture_output=True, text=True,
                             timeout=130, check=False)
    # The source-answer lane is machine-readable: exactly one JSON line.
    lines = process.stdout.strip().splitlines()
    if len(lines) != 1:
        raise AssertionError("CLI_NOT_SINGLE_JSON_LINE")
    return process.returncode, json.loads(lines[0])


def run(home, out):
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise RuntimeError("LINUX_X86_64_ONLY")
    if out.exists():
        raise FileExistsError("FRESH_EVIDENCE_DIRECTORY_REQUIRED")
    out.mkdir(parents=True)
    report = {
        "schema": SCHEMA, "status": "INCOMPLETE",
        "evidence_kind": "LINUX_NATIVE_OPERATOR_COMMAND_SOURCE_C3_ONE_PUBLIC_SYNTHETIC_FACT",
        "platform": platform.platform(), "model_revision": REVISION,
        "model_sha256": MODEL_SHA, "seed": 13, "max_tokens": 64,
        "deadline_s": 90, "native_calls_expected": 1,
        "negative_gates_promoted": False, "redmi_measured": False,
        "whole_system_complete": False,
    }
    try:
        from v13.runtime import Runtime
        from v13.operator import Operator

        runtime = Runtime(home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            if not _age0(runtime.cfg):
                raise AssertionError("AGE0_RECORD_ONLY_REQUIRED")
            operator = Operator(runtime)
            preview = json.loads(operator.run(":source budget Elyra 615"))
            if preview.get("status") != "CONFIRM_REQUIRED" or preview.get("writes") is not False:
                raise AssertionError("HUMAN_PREVIEW_FAILED")
            count = runtime.store.one(
                "SELECT count(*) AS n FROM memories WHERE active=1")["n"]
            if count != 0:
                raise AssertionError("PREVIEW_WROTE_MEMORY")
            recorded = json.loads(operator.run(":source budget Elyra 615 --confirm"))
            if (recorded.get("status") != "RECORDED_VERIFIED"
                    or recorded.get("model_called") is not False
                    or recorded.get("native_calls") != 0):
                raise AssertionError("HUMAN_SOURCE_RECORD_FAILED")
            memory_id = recorded["memory_id"]
            source_ref = recorded["source_ref"]
            session = runtime.session
            ready = json.loads(operator.run(":verified " + QUESTION))
            if (not _preflight_ok(ready, "READY")
                    or ready.get("memory_id") != memory_id
                    or ready.get("source_ref") != source_ref):
                raise AssertionError("HUMAN_SOURCE_OPERATOR_NOT_READY")
            report["source_ref"] = source_ref
            report["session_reused"] = bool(session)
            report["preview"] = preview["status"]
            report["recorded"] = recorded["status"]
        finally:
            runtime.close()

        wrong_code, wrong = _cli(home, WRONG)
        outside_code, outside = _cli(home, OUTSIDE)
        if (wrong_code != 0 or not _preflight_ok(wrong, "CLARIFY")
                or outside_code != 0 or not _preflight_ok(outside, "NOT_APPLICABLE")):
            raise AssertionError("NATIVE_NEGATIVE_PREFLIGHT")
        report["controls"] = {
            "wrong_project": wrong["status"], "out_of_scope": outside["status"],
            "pre_native_calls": wrong["native_calls"] + outside["native_calls"],
        }

        native_code, native = _cli(home, QUESTION)
        report["native"] = native
        if native_code != 0 or not _native_ok(native, source_ref):
            raise AssertionError("HUMAN_SOURCE_NATIVE_FINAL_FAILED")

        runtime = Runtime(home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            if not _age0(runtime.cfg) or runtime.session != session:
                raise AssertionError("RESTART_SESSION_AGE0")
            operator = Operator(runtime)
            after = json.loads(operator.run(":verified " + QUESTION))
            if not _preflight_ok(after, "READY") or after.get("source_ref") != source_ref:
                raise AssertionError("SOURCE_NOT_PERSISTED_AFTER_NATIVE")
            lock_code, locked = _cli(home, QUESTION)
            if lock_code != 2 or locked.get("status") != "ERROR":
                raise AssertionError("CONCURRENT_RUNTIME_NOT_REFUSED")
            operator.run(":forget " + str(memory_id) + " --confirm")
            revoked = json.loads(operator.run(":verified " + QUESTION))
            if not _preflight_ok(revoked, "CLARIFY"):
                raise AssertionError("SOURCE_NOT_REVOKED")
            report["controls"]["coordinator_lock"] = locked["status"]
            report["controls"]["human_forget"] = revoked["status"]
        finally:
            runtime.close()

        denied_code, denied = _cli(home, QUESTION)
        if denied_code != 0 or not _preflight_ok(denied, "CLARIFY"):
            raise AssertionError("POST_FORGET_NATIVE_NOT_REFUSED")
        report["controls"]["post_forget_native_calls"] = denied["native_calls"]
        report["status"] = "HUMAN_SOURCE_C3_NATIVE_PASS"
    except BaseException as exc:
        report["status"] = "RUN105_ERROR"
        report["error_type"] = type(exc).__name__
        report["error_message"] = str(exc)[:320]
        traceback.print_exc(file=sys.stderr)
    finally:
        path = out / "run105-report.json"
        path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True,
                                   indent=2, allow_nan=False) + "\n",
                        encoding="utf-8")
        print(json.dumps({"status": report["status"], "evidence": str(path)},
                         sort_keys=True))
    return report["status"] == "HUMAN_SOURCE_C3_NATIVE_PASS"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args(argv)
    home = args.home.expanduser().resolve()
    if args.install:
        print(json.dumps(install_pinned(home), sort_keys=True))
        return 0
    if args.out is None:
        parser.error("--out required without --install")
    return 0 if run(home, args.out.expanduser().resolve()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
