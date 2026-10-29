"""Run101: preregistered two-project real Age0 F1/F5 -> current C3 Linux native.

New review-only generalization cohort, NOT Runtime._turn, not Redmi.
Prereg FIRST: RUN101_TWO_PROJECT_C3_NATIVE_PREREG.md and pre-code amendment.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import traceback
from pathlib import Path

from scripts.run93_source_c3_native_e2e import install as install_pinned
from scripts.run93_source_c3_native_e2e import MODEL_SHA, REVISION

SCHEMA = "v13.run101.two_project_c3_linux_native.v1"
CASES = (
    ("Dovan", "731 Euro", "What is the budget for Project Dovan?"),
    ("Mira", "942 Euro", "What is the budget for Project Mira?"),
)
MISSING = "What is the budget for Project Elyra?"
OUTSIDE = "Who leads Project Dovan?"


def _preflight_ok(value, expected):
    return (isinstance(value, dict) and value.get("status") == expected
            and value.get("native_calls") == 0
            and value.get("model_called") is False
            and (expected == "READY" or not re.search(r"\d", str(value.get("answer") or ""))))


def _native_ok(value, project, amount, ref):
    if not isinstance(value, dict):
        return False
    if (value.get("status") != "FINAL" or value.get("native_calls") != 1
            or value.get("model_called") is not True
            or value.get("process_reaped") is not True
            or value.get("model_revision") != REVISION
            or value.get("source_ref") != ref):
        return False
    answer = value.get("answer")
    if not isinstance(answer, str):
        return False
    expected_number = amount.split(" ", 1)[0]
    numbers = re.findall(r"(?<!\w)\d+(?!\w)", answer)
    return (numbers == [expected_number]
            and bool(re.search(r"\bProject\s+" + re.escape(project) + r"\b", answer, re.I))
            and bool(re.search(r"\b(?:Euro|Euros|EUR)\b|€", answer, re.I)))


def _age0(cfg):
    return (cfg.get("system_stage") == 0
            and cfg.get("learning_mode") == "RECORD_ONLY"
            and cfg.get("latents_enabled") is False
            and cfg.get("jepa_weight", 0) == 0)


def run(home, out):
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise RuntimeError("LINUX_X86_64_ONLY")
    if out.exists():
        raise FileExistsError("FRESH_EVIDENCE_DIRECTORY_REQUIRED")
    out.mkdir(parents=True)
    report = {
        "schema": SCHEMA, "status": "INCOMPLETE",
        "evidence_kind": "LINUX_NATIVE_C3_TWO_PUBLIC_SYNTHETIC_SOURCES",
        "platform": platform.platform(), "model_sha256": MODEL_SHA,
        "model_revision": REVISION, "seed": 13, "max_tokens": 64,
        "deadline_s": 90, "source_cases": [
            {"project": project, "value": value, "query": query}
            for project, value, query in CASES],
        "native": [], "controls": {}, "negative_gates_promoted": False,
        "whole_system_complete": False, "redmi_measured": False,
    }
    try:
        from v13.runtime import Runtime
        from v13.operator import Operator
        from scripts.ask_verified_budget import BudgetContext, query as ask

        runtime = Runtime(home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            if not _age0(runtime.cfg):
                raise AssertionError("AGE0_REQUIRED")
            operator = Operator(runtime)
            ids = {}
            refs = {}
            for project, value, question in CASES:
                key = "Project " + project + " budget"
                event = runtime.store.event(runtime.session, key)
                ids[project] = runtime.memory.feedback(
                    event["event_id"], "fact", value, key=key, permission="record")
                ready = json.loads(operator.run(":verified " + question))
                if not _preflight_ok(ready, "READY"):
                    raise AssertionError("OPERATOR_READY_" + project)
                if ready.get("memory_id") != ids[project]:
                    raise AssertionError("OPERATOR_ID_" + project)
                refs[project] = ready["source_ref"]
            if refs["Dovan"] == refs["Mira"]:
                raise AssertionError("SOURCE_REF_NOT_DISTINCT")
            session = runtime.session
            report["source_refs"] = refs
            report["session_reused"] = bool(session)
        finally:
            runtime.close()

        context = BudgetContext(home)
        try:
            if not _age0(context.cfg) or context.session != session:
                raise AssertionError("RESTART_AGE0_SESSION")
            absent = ask(context, MISSING, native=True)
            outside = ask(context, OUTSIDE, native=True)
            if not _preflight_ok(absent, "CLARIFY"):
                raise AssertionError("MISSING_SOURCE_NOT_REFUSED")
            if not _preflight_ok(outside, "NOT_APPLICABLE"):
                raise AssertionError("OUT_OF_SCOPE_NOT_REFUSED")
            report["controls"]["missing"] = absent["status"]
            report["controls"]["out_of_scope"] = outside["status"]
            report["controls"]["pre_native_calls"] = (
                absent["native_calls"] + outside["native_calls"])
            for project, value, question in CASES:
                ready = ask(context, question, native=False)
                if (not _preflight_ok(ready, "READY")
                        or ready.get("memory_id") != ids[project]
                        or ready.get("source_ref") != refs[project]):
                    raise AssertionError("REOPEN_PREFLIGHT_" + project)
            # Native jobs strictly serialized by the existing query's unload.
            for project, value, question in CASES:
                actual = ask(context, question, native=True,
                             timeout_s=90, max_tokens=64)
                report["native"].append({
                    "project": project, "value": value, "result": actual,
                    "accepted": _native_ok(actual, project, value, refs[project]),
                })
                if actual.get("native_calls") == 1 and actual.get("status") == "NATIVE_RELEASE_NOT_PROVEN":
                    raise AssertionError("NATIVE_RELEASE_NOT_PROVEN")
        finally:
            context.close()

        runtime = Runtime(home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            if runtime.session != session:
                raise AssertionError("SECOND_RESTART_SESSION")
            operator = Operator(runtime)
            conflict_key = "Project Dovan budgets"
            event = runtime.store.event(runtime.session, conflict_key)
            conflict_id = runtime.memory.feedback(
                event["event_id"], "fact", "809 Euro",
                key=conflict_key, permission="record")
            conflict = json.loads(operator.run(":verified " + CASES[0][2]))
            if not _preflight_ok(conflict, "CLARIFY"):
                raise AssertionError("CONFLICT_NOT_REFUSED")
            report["controls"]["conflict"] = conflict["status"]
            for memory_id in (ids["Dovan"], conflict_id):
                operator.run(":forget " + str(memory_id) + " --confirm")
            forgotten = json.loads(operator.run(":verified " + CASES[0][2]))
            retained = json.loads(operator.run(":verified " + CASES[1][2]))
            if not _preflight_ok(forgotten, "CLARIFY"):
                raise AssertionError("FORGOTTEN_SOURCE_RESURRECTED")
            if not _preflight_ok(retained, "READY"):
                raise AssertionError("UNRELATED_SOURCE_LOST")
            if retained.get("source_ref") != refs["Mira"]:
                raise AssertionError("UNRELATED_SOURCE_REF_CHANGED")
            report["controls"]["after_forget"] = forgotten["status"]
            report["controls"]["unrelated_retained"] = retained["status"]
        finally:
            runtime.close()

        context = BudgetContext(home)
        try:
            denied = ask(context, CASES[0][2], native=True)
            if not _preflight_ok(denied, "CLARIFY"):
                raise AssertionError("POST_FORGET_NATIVE_NOT_REFUSED")
            report["controls"]["post_forget_native_calls"] = denied["native_calls"]
        finally:
            context.close()

        report["status"] = (
            "TWO_PROJECT_C3_NATIVE_PASS"
            if len(report["native"]) == len(CASES)
            and all(item["accepted"] for item in report["native"])
            else "TWO_PROJECT_C3_NATIVE_RED"
        )
    except BaseException as exc:
        report["status"] = "RUN101_ERROR"
        report["error_type"] = type(exc).__name__
        report["error_message"] = str(exc)[:320]
        traceback.print_exc(file=sys.stderr)
    finally:
        path = out / "run101-report.json"
        path.write_text(json.dumps(report, indent=2, sort_keys=True,
                                   ensure_ascii=False, allow_nan=False) + "\n",
                        encoding="utf-8")
        print(json.dumps({"status": report["status"], "evidence": str(path)},
                         sort_keys=True))
    return report["status"] == "TWO_PROJECT_C3_NATIVE_PASS"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--install", action="store_true")
    args = p.parse_args(argv)
    home = args.home.expanduser().resolve()
    if args.install:
        print(json.dumps(install_pinned(home), sort_keys=True))
        return 0
    if args.out is None:
        p.error("--out required without --install")
    return 0 if run(home, args.out.expanduser().resolve()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
