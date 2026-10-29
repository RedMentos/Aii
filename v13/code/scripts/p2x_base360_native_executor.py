#!/usr/bin/env python3
"""P2X frozen 360-call C3 QAD base-only Linux-native validation, no adapter."""
from __future__ import annotations
import argparse
import json
import math
import os
import threading
import time
from pathlib import Path

from scripts import hb1a_two_body_native_pilot as hb1
from scripts import hb1b_c3_format_native_executor as native
from scripts import hb1b_c3_format_followup as hb1b
from scripts import p2x_native_receiver_eval_scorer as scorer

SCHEMA = "v13.p2x.base360_native.v1"
CALL_SECONDS = 90
OVERALL_SECONDS = 2400
MAX_TOKENS = 48
RUNNER_BINARY_SHA = hb1b.RUNNER_SHA256


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def check_age0(cfg, home):
    need(cfg.get("system_stage") == 0
         and cfg.get("learning_mode") == "RECORD_ONLY"
         and cfg.get("latents_enabled") is False
         and cfg.get("jepa_weight", 0) == 0,
         "P2X_BASE360_AGE0_RECORD_ONLY_RED")
    need(not os.environ.get("V13_LLAMA_SERVER"),
         "P2X_BASE360_BINARY_OVERRIDE_RED")
    for rel in ("config/lora-active.json", "config/memory-server.json"):
        path = Path(home) / rel
        if path.exists():
            need(json.loads(path.read_text()) in ({}, {"active": {}}),
                 "P2X_BASE360_ADAPTER_OR_MEMORY_ACTIVE_RED")


def record_call(prompt, output, duration, metrics):
    need(type(prompt) is dict and set(prompt) == {"id", "arm", "messages"}
         and type(prompt["messages"]) is list and len(prompt["messages"]) == 1
         and prompt["messages"][0].get("role") == "user"
         and type(prompt["messages"][0].get("content")) is str,
         "P2X_BASE360_EXACT_ONE_USER_INPUT_REQUIRED")
    need(type(output) is str
         and type(duration) in (int, float) and math.isfinite(duration)
         and 0 <= duration <= CALL_SECONDS
         and type(metrics) is dict and metrics.get("status") == "FINAL",
         "P2X_BASE360_NONFINAL_OR_DURATION_RED")
    return {
        "id": prompt["id"], "arm": prompt["arm"],
        "input_sha256": scorer.sha(scorer.canonical(prompt["messages"])),
        "model_sha256": scorer.MODEL_SHA,
        "runtime_sha256": scorer.RUNTIME_SHA,
        "adapter_sha256": None,
        "seed": scorer.SEED, "status": "FINAL",
        "model_called": True, "native_calls": 1,
        "duration_s": duration, "output": output, "metrics": metrics,
    }



def check_runtime_identity(home):
    """Separate release archive pin from extracted executable SHA256."""
    spec = json.loads((Path(__file__).resolve().parents[1] /
                       "specs/models.json").read_text())
    archive_sha = spec["runner"]["linux_binaries"]["linux-x86_64"]["sha256"]
    need(archive_sha == scorer.RUNTIME_SHA,
         "P2X_BASE360_RUNTIME_ARCHIVE_PIN_RED")
    binary = Path(home) / "bin/llama-server"
    need(binary.is_file() and native.file_sha(binary) == RUNNER_BINARY_SHA,
         "P2X_BASE360_RUNNER_BINARY_PIN_RED")
    return binary


def install(home):
    return native.install(home)


def run_native(home, validation_dir, out):
    from v13.common import atomic_write
    from v13.config import initialize
    from v13.models import ModelManager
    from v13.runners import RunnerPool

    home, validation_dir, out = (Path(x).resolve() for x in
                                 (home, validation_dir, out))
    need(home.is_dir() and (home / "config/models.json").is_file(),
         "P2X_BASE360_PINNED_HOME_REQUIRED")
    need(not out.exists() and not out.is_symlink() and out.parent.is_dir(),
         "P2X_BASE360_FRESH_OUTPUT_REQUIRED")
    native.admit(home)
    plan, answers = scorer.load_validation(validation_dir)
    need(len(plan) == 360 and len(answers) == 72,
         "P2X_BASE360_FROZEN_COHORT_RED")
    cfg = initialize(home)
    check_age0(cfg, home)
    cfg = dict(cfg, c3_decode_mode="server", c3_sampling="off",
               context_tokens=2048, threads=2, answer_tokens=MAX_TOKENS,
               temperature=.1)
    manager = ModelManager(home)
    checks = manager.verify(deep=True)
    need(checks.get("language", {}).get("ok") is True
         and checks["language"].get("hash_checked") is True
         and manager.revision("C3_LANGUAGE") ==
         hb1.MODEL_REVISIONS["C3_LANGUAGE"]
         and native.file_sha(manager.path_for("C3_LANGUAGE")) == scorer.MODEL_SHA,
         "P2X_BASE360_MODEL_PIN_RED")
    binary = check_runtime_identity(home)
    out.mkdir(mode=0o700)
    atomic_write(out / "INPUTS.json", scorer.canonical(plan).decode("utf-8"))
    atomic_write(out / "ANSWERS.json", scorer.canonical(answers).decode("utf-8"))
    receipt = {
        "schema": SCHEMA, "status": "RUNNING",
        "evidence_kind": "LINUX_NATIVE_QAD_C3_P2X_BASE_ONLY",
        "fixture_sha256": scorer.FIXTURE_SHA,
        "validation_inputs_sha256": scorer.INPUT_SHA,
        "validation_answers_sha256": scorer.ANSWER_SHA,
        "model_sha256_before": scorer.MODEL_SHA,
        "runtime_sha256_before": scorer.RUNTIME_SHA,
        "runner_binary_sha256_before": RUNNER_BINARY_SHA,
        "adapter_sha256": None,
        "seed": scorer.SEED, "max_tokens": MAX_TOKENS,
        "c3_sampling": "off", "expected_calls": 360,
        "recorded_calls": 0, "age_authority": 0,
        "weight_updates": False, "jepa_weight": 0,
        "redmi_measured": False, "canonical_gate_pass": False,
        "whole_system_complete": False,
    }
    records = []
    def persist():
        atomic_write(out / "RAW.json", scorer.canonical(records).decode("utf-8"))
        atomic_write(out / "RECEIPT.json", scorer.canonical(receipt).decode("utf-8"))
    persist()
    pool = None
    started = time.monotonic()
    try:
        pool = RunnerPool(home, manager, cfg)
        for prompt in plan:
            remaining = OVERALL_SECONDS - (time.monotonic() - started)
            need(remaining > 10, "P2X_BASE360_OVERALL_DEADLINE_RED")
            begun = time.monotonic()
            runner = pool.get("C3_LANGUAGE")
            output = "".join(runner.generate(
                prompt["messages"], threading.Event(),
                time.monotonic() + min(CALL_SECONDS - 2, remaining),
                max_tokens=MAX_TOKENS, schema=hb1.C3_SCHEMA,
                seed=scorer.SEED))
            duration = time.monotonic() - begun
            records.append(record_call(prompt, output, duration,
                                       dict(runner.last_metrics)))
            receipt["recorded_calls"] = len(records)
            persist()
        released = pool.unload()
        pool = None
        need(released.get("process_reaped") is True,
             "P2X_BASE360_PROCESS_REAP_RED")
        need(native.file_sha(manager.path_for("C3_LANGUAGE")) == scorer.MODEL_SHA,
             "P2X_BASE360_MODEL_CHANGED_RED")
        check_runtime_identity(home)
        score = scorer.score(records, plan, answers, adapter_sha256=None)
        scorer._validate_score_snapshot(score)
        atomic_write(out / "SCORE.json", scorer.canonical(score).decode("utf-8"))
        receipt["status"] = "P2X_C3_BASE360_NATIVE_DIAGNOSTIC_NO_GATE"
        receipt["recorded_calls"] = 360
        receipt["process_reaped"] = True
        receipt["model_sha256_after"] = scorer.MODEL_SHA
        receipt["runtime_sha256_after"] = scorer.RUNTIME_SHA
        receipt["runner_binary_sha256_after"] = RUNNER_BINARY_SHA
        for name, key in (("RAW.json", "raw_sha256"),
                          ("SCORE.json", "score_sha256"),
                          ("INPUTS.json", "inputs_sha256"),
                          ("ANSWERS.json", "answers_sha256")):
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home", type=Path, required=True)
    ap.add_argument("--validation-dir", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--install", action="store_true")
    args = ap.parse_args(argv)
    if args.install:
        print(json.dumps(install(args.home), sort_keys=True))
        return 0
    if args.validation_dir is None or args.out is None:
        ap.error("--validation-dir and --out required without --install")
    result = run_native(args.home, args.validation_dir, args.out)
    print(json.dumps({"status": result["status"],
                      "recorded_calls": result["recorded_calls"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
