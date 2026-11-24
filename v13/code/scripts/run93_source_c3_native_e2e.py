"""Run93 preregistered, real Age0 F1/F5 -> current pinned C3 native Linux E2E.

Isolated existing-home operator candidate, NOT production Runtime._turn.
Fixed public synthetic budget fixture; no model weights in evidence.
Prereg: docs/proofs/continuation-20261028/RUN93_SOURCE_C3_NATIVE_E2E_PREREG.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import traceback

from v13.common import file_hash
from v13.config import initialize
from v13.models import ModelManager, catalog
from v13.bootstrap import install_native

QUERY = "What is the budget for Project Elyra?"
WRONG = "What is the budget for Project Dovan?"
OUTSIDE = "Who leads Project Elyra?"
KEY = "Project Elyra budget"
VALUE = "615 Euro"
MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
REVISION = "657e078c94084481950a2d555a941481f715536b"
SCHEMA = "v13.run93.age0_source_c3_linux_native.v1"


def _require_linux():
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise RuntimeError("LINUX_X86_64_ONLY")


def _require_age0(cfg):
    if (cfg.get("system_stage") != 0 or cfg.get("learning_mode") != "RECORD_ONLY"
            or cfg.get("latents_enabled") is not False or cfg.get("jepa_weight", 0) != 0):
        raise RuntimeError("AGE0_RECORD_ONLY_REQUIRED")


def install(home):
    """Use the exact public pinned catalog, no bodies or unrelated models."""
    _require_linux()
    initialize(home)
    manager = ModelManager(home)
    manager.install("language")
    manager.install("needle")  # install_native needs this; NOT a C2 proof
    install_native(home)
    report = manager.verify(deep=True)
    c3 = catalog()["models"]["language"]
    assert c3["revision"] == REVISION
    assert c3["files"][0]["sha256"] == MODEL_SHA
    assert report["language"]["ok"] and report["language"]["hash_checked"]
    assert report["needle"]["ok"] and report["needle"]["hash_checked"]
    assert manager.revision("C3_LANGUAGE") == REVISION
    assert file_hash(manager.path_for("C3_LANGUAGE")) == MODEL_SHA
    return {"status": "RUN93_INSTALL_VERIFIED", "model_sha256": MODEL_SHA,
            "model_revision": REVISION, "needle_installed_for_runner_only": True,
            "model_bytes_exported": False}


def _require_preflight(result, expected):
    if (result.get("status") != expected or result.get("native_calls") != 0
            or result.get("model_called") is not False):
        raise AssertionError("PREFLIGHT_EXPECTED_" + expected)
    if expected != "READY" and any(ch.isdigit() for ch in str(result.get("answer") or "")):
        raise AssertionError("UNVERIFIED_FACT_LEAK")


def run(home, out):
    """One fixed native positive and model-free negatives, then restart/forget."""
    _require_linux()
    if out.exists():
        raise FileExistsError("FRESH_EVIDENCE_DIRECTORY_REQUIRED")
    out.mkdir(parents=True)
    result = {"schema": SCHEMA, "evidence_kind": "LINUX_NATIVE_C3_ONE_SYNTHETIC_SOURCE",
              "platform": platform.platform(), "status": "INCOMPLETE",
              "source_key": KEY, "source_value": VALUE, "query": QUERY,
              "wrong_project_query": WRONG, "model_sha256": MODEL_SHA,
              "model_revision": REVISION, "seed": 13, "max_tokens": 64,
              "deadline_s": 90, "negative_gates_promoted": False,
              "whole_system_complete": False}
    try:
        from v13.runtime import Runtime
        from v13.operator import Operator
        from scripts.ask_verified_budget import BudgetContext, query

        # Real source creation through the actual Age0 Runtime/Store/Memory.
        runtime = Runtime(home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            _require_age0(runtime.cfg)
            operator = Operator(runtime)
            event = runtime.store.event(runtime.session, KEY)
            memory_id = runtime.memory.feedback(event["event_id"], "fact", VALUE,
                                                key=KEY, permission="record")
            op_ready = json.loads(operator.run(":verified " + QUERY))
            _require_preflight(op_ready, "READY")
            if op_ready["memory_id"] != memory_id:
                raise AssertionError("OPERATOR_SOURCE_ID_MISMATCH")
            session = runtime.session
            result["session_reused"] = bool(session)
            result["source_ref"] = op_ready["source_ref"]
            result["operator_preflight"] = {
                "status": op_ready["status"], "native_calls": op_ready["native_calls"]}
        finally:
            runtime.close()

        # Reopen from disk, not an in-memory mock. Controls must not load C3.
        context = BudgetContext(home)
        try:
            _require_age0(context.cfg)
            if context.session != session:
                raise AssertionError("SESSION_NOT_PERSISTED")
            wrong = query(context, WRONG, native=True)
            outside = query(context, OUTSIDE, native=True)
            ready = query(context, QUERY, native=False)
            _require_preflight(wrong, "CLARIFY")
            _require_preflight(outside, "NOT_APPLICABLE")
            _require_preflight(ready, "READY")
            if ready["memory_id"] != memory_id or ready["source_ref"] != op_ready["source_ref"]:
                raise AssertionError("F1_F5_SOURCE_CHANGED_AFTER_REOPEN")
            result["negative_controls"] = {
                "wrong_project": wrong["status"], "out_of_scope": outside["status"],
                "total_native_calls": wrong["native_calls"] + outside["native_calls"]}
            result["ready_messages_sha256"] = ready["messages_sha256"]
            result["native"] = query(context, QUERY, native=True,
                                     timeout_s=90, max_tokens=64)
            result["native_status"] = result["native"]["status"]
        finally:
            context.close()

        # Restart, then a real human forget must revoke all source authority.
        runtime = Runtime(home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            operator = Operator(runtime)
            after_restart = json.loads(operator.run(":verified " + QUERY))
            _require_preflight(after_restart, "READY")
            if after_restart["memory_id"] != memory_id:
                raise AssertionError("SOURCE_NOT_PERSISTED_AFTER_NATIVE")
            operator.run(":forget " + str(memory_id) + " --confirm")
            revoked = json.loads(operator.run(":verified " + QUERY))
            _require_preflight(revoked, "CLARIFY")
            result["restart_and_forget"] = {
                "before": after_restart["status"], "after": revoked["status"],
                "native_calls": after_restart["native_calls"] + revoked["native_calls"]}
        finally:
            runtime.close()

        context = BudgetContext(home)
        try:
            denied = query(context, QUERY, native=True)
            _require_preflight(denied, "CLARIFY")
            result["post_forget_native_calls"] = denied["native_calls"]
        finally:
            context.close()

        native = result["native"]
        if (native.get("status") != "FINAL" or native.get("native_calls") != 1
                or native.get("model_called") is not True
                or native.get("process_reaped") is not True
                or native.get("model_revision") != REVISION):
            result["status"] = "SOURCE_C3_ANSWER_RED"
        else:
            result["status"] = "SOURCE_C3_ANSWER_PASS"
    except BaseException as exc:
        result["status"] = "RUN93_ERROR"
        result["error_type"] = type(exc).__name__
        result["error_message"] = str(exc)[:320]
        traceback.print_exc(file=sys.stderr)
    finally:
        payload = json.dumps(result, ensure_ascii=False, sort_keys=True,
                             indent=2, allow_nan=False) + "\n"
        (out / "run93-report.json").write_text(payload, encoding="utf-8")
        print(json.dumps({"status": result["status"], "evidence": str(out / "run93-report.json"),
                          "native_status": result.get("native_status", "NOT_RUN")},
                         ensure_ascii=False, sort_keys=True))
    return result["status"] == "SOURCE_C3_ANSWER_PASS"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args(argv)
    home = args.home.expanduser().resolve()
    if args.install:
        print(json.dumps(install(home), sort_keys=True))
        return 0
    if args.out is None:
        parser.error("--out required without --install")
    return 0 if run(home, args.out.expanduser().resolve()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
