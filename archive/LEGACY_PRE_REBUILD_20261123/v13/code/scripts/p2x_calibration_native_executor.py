#!/usr/bin/env python3
"""Run preregistered P2X calibration 360-call source-instruction native diagnostic."""
from __future__ import annotations
import argparse
import json
import math
import threading
import time
from pathlib import Path

from scripts import hb1a_two_body_native_pilot as hb1
from scripts import hb1b_c3_format_native_executor as native
from scripts import p2x_base360_native_executor as base
from scripts import p2x_calibration_instruction as cal

SCHEMA = "v13.p2x.calibration_instruction_native.v1"
MAX_TOKENS = 48
CALL_SECONDS = 90
OVERALL_SECONDS = 2400


def need(ok, reason):
    if not ok:
        raise ValueError("P2X_CAL_NATIVE_" + reason)


def record_call(prompt, output, duration, metrics):
    need(type(prompt) is dict and set(prompt) ==
         {"id", "arm", "format", "messages"}, "PROMPT_SHAPE_RED")
    need(type(output) is str and type(metrics) is dict
         and metrics.get("status") == "FINAL"
         and type(duration) in (int, float) and math.isfinite(duration)
         and 0 <= duration <= CALL_SECONDS, "NONFINAL_RED")
    return {
        "id": prompt["id"], "arm": prompt["arm"],
        "format": prompt["format"],
        "input_sha256": cal.sha(cal.canonical(prompt["messages"])),
        "model_sha256": cal.MODEL_SHA,
        "runtime_sha256": cal.RUNTIME_SHA,
        "runner_binary_sha256": cal.BINARY_SHA,
        "adapter_sha256": None, "seed": cal.SEED,
        "status": "FINAL", "model_called": True, "native_calls": 1,
        "duration_s": duration, "metrics": metrics, "output": output,
    }


def run_native(home, out):
    from v13.common import atomic_write
    from v13.config import initialize
    from v13.models import ModelManager
    from v13.runners import RunnerPool

    home, out = Path(home).resolve(), Path(out).resolve()
    need(home.is_dir() and (home / "config/models.json").is_file(),
         "PINNED_HOME_RED")
    need(not out.exists() and not out.is_symlink() and out.parent.is_dir(),
         "FRESH_OUTPUT_RED")
    native.admit(home)
    plan = cal.plan()
    need(len(plan) == 360, "CALIBRATION_PLAN_RED")
    cfg = initialize(home)
    base.check_age0(cfg, home)
    cfg = dict(cfg, c3_decode_mode="server", c3_sampling="off",
               context_tokens=2048, threads=2, answer_tokens=MAX_TOKENS,
               temperature=.1)
    manager = ModelManager(home)
    checks = manager.verify(deep=True)
    need(checks.get("language", {}).get("ok") is True
         and checks["language"].get("hash_checked") is True
         and manager.revision("C3_LANGUAGE") ==
         hb1.MODEL_REVISIONS["C3_LANGUAGE"]
         and native.file_sha(manager.path_for("C3_LANGUAGE")) == cal.MODEL_SHA,
         "MODEL_PIN_RED")
    base.check_runtime_identity(home)
    out.mkdir(mode=0o700)
    atomic_write(out / "INPUTS.json", cal.canonical(plan).decode("utf-8"))
    receipt = {
        "schema": SCHEMA, "status": "RUNNING",
        "evidence_kind": "LINUX_NATIVE_CALIBRATION_ONLY",
        "prereg_commit": "9352843a7ef6fb0eb7cc3307b98f12501e9685c2",
        "fixture_sha256": cal.FIXTURE_SHA,
        "model_sha256_before": cal.MODEL_SHA,
        "runtime_sha256_before": cal.RUNTIME_SHA,
        "runner_binary_sha256_before": cal.BINARY_SHA,
        "adapter_sha256": None, "seed": cal.SEED,
        "max_tokens": MAX_TOKENS, "c3_sampling": "off",
        "expected_calls": 360, "recorded_calls": 0,
        "age_authority": 0, "weight_updates": False,
        "jepa_weight": 0, "ag6_approved": False,
        "redmi_measured": False, "whole_system_complete": False,
    }
    records = []
    def persist():
        atomic_write(out / "RAW.json", cal.canonical(records).decode("utf-8"))
        atomic_write(out / "RECEIPT.json", cal.canonical(receipt).decode("utf-8"))
    persist()
    pool = None
    started = time.monotonic()
    try:
        pool = RunnerPool(home, manager, cfg)
        for prompt in plan:
            remaining = OVERALL_SECONDS - (time.monotonic() - started)
            need(remaining > 10, "OVERALL_DEADLINE_RED")
            begun = time.monotonic()
            runner = pool.get("C3_LANGUAGE")
            output = "".join(runner.generate(
                prompt["messages"], threading.Event(),
                time.monotonic() + min(CALL_SECONDS - 2, remaining),
                max_tokens=MAX_TOKENS, schema=hb1.C3_SCHEMA,
                seed=cal.SEED))
            records.append(record_call(prompt, output,
                                       time.monotonic() - begun,
                                       dict(runner.last_metrics)))
            receipt["recorded_calls"] = len(records)
            persist()
        released = pool.unload()
        pool = None
        need(released.get("process_reaped") is True,
             "PROCESS_REAP_RED")
        need(native.file_sha(manager.path_for("C3_LANGUAGE")) == cal.MODEL_SHA,
             "MODEL_CHANGED_RED")
        base.check_runtime_identity(home)
        score = cal.score(records, plan)
        cal.verify_score(records, score)
        atomic_write(out / "SCORE.json", cal.canonical(score).decode("utf-8"))
        receipt["status"] = "P2X_CALIBRATION_NATIVE_DIAGNOSTIC_NO_GATE"
        receipt["recorded_calls"] = 360
        receipt["process_reaped"] = True
        receipt["model_sha256_after"] = cal.MODEL_SHA
        receipt["runtime_sha256_after"] = cal.RUNTIME_SHA
        receipt["runner_binary_sha256_after"] = cal.BINARY_SHA
        for name, key in (("RAW.json", "raw_sha256"),
                          ("SCORE.json", "score_sha256"),
                          ("INPUTS.json", "inputs_sha256")):
            receipt[key] = native.file_sha(out / name)
        persist()
    except BaseException as exc:
        receipt["status"] = "FAIL_RETAIN_RAW"
        receipt["error_type"] = type(exc).__name__
        receipt["error_message"] = str(exc)[:320]
        persist()
        raise
    finally:
        if pool is not None:
            released = pool.unload()
            receipt["process_reaped_on_exit"] = bool(released.get("process_reaped"))
            persist()
    return receipt


def verify(evidence):
    evidence = Path(evidence)
    need(evidence.is_dir() and not evidence.is_symlink(),
         "EVIDENCE_DIR_RED")
    inputs = json.loads((evidence / "INPUTS.json").read_text())
    records = json.loads((evidence / "RAW.json").read_text())
    snapshot = json.loads((evidence / "SCORE.json").read_text())
    receipt = json.loads((evidence / "RECEIPT.json").read_text())
    need(inputs == cal.plan(), "FROZEN_PLAN_RED")
    replay = cal.verify_score(records, snapshot)
    need(receipt.get("schema") == SCHEMA
         and receipt.get("status") == "P2X_CALIBRATION_NATIVE_DIAGNOSTIC_NO_GATE"
         and receipt.get("recorded_calls") == 360
         and receipt.get("expected_calls") == 360
         and receipt.get("process_reaped") is True
         and receipt.get("adapter_sha256", "MISSING") is None
         and receipt.get("ag6_approved") is False
         and receipt.get("weight_updates") is False
         and receipt.get("redmi_measured") is False
         and receipt.get("whole_system_complete") is False
         and receipt.get("prereg_commit") ==
         "9352843a7ef6fb0eb7cc3307b98f12501e9685c2",
         "RECEIPT_GATE_RED")
    for name, key in (("RAW.json", "raw_sha256"),
                      ("SCORE.json", "score_sha256"),
                      ("INPUTS.json", "inputs_sha256")):
        need(receipt.get(key) == native.file_sha(evidence / name),
             "RECEIPT_SHA_RED")
    return replay


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--verify", type=Path)
    args = ap.parse_args(argv)
    if args.verify is not None:
        print(json.dumps(verify(args.verify), sort_keys=True))
        return 0
    if args.home is None:
        ap.error("--home required")
    if args.install:
        print(json.dumps(base.install(args.home), sort_keys=True))
        return 0
    if args.out is None:
        ap.error("--out required")
    result = run_native(args.home, args.out)
    print(json.dumps({"status": result["status"],
                      "recorded_calls": result["recorded_calls"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
