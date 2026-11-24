"""P0X preregistered 150-call Linux-native C3-only headroom baseline.

Default off. No B1/B2 source, learning, tools, latents or gate promotion.
"""
from __future__ import annotations
import argparse
import json
import os
import threading
import time
from pathlib import Path

from scripts import hb1a_two_body_native_pilot as hb1
from scripts import hb1b_c3_format_native_executor as hb1b_native
from scripts import p0x_c3_150_baseline as p0x

SCHEMA = "v13.p0x.c3_150_native_baseline.v1"


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def install(home):
    return hb1b_native.install(home)


def run_native(home, out):
    from v13.common import atomic_write
    from v13.config import initialize
    from v13.models import ModelManager
    from v13.runners import RunnerPool

    home, out = Path(home).resolve(), Path(out).resolve()
    need(home.is_dir() and (home / "config/models.json").is_file(),
         "P0X_BASELINE_PINNED_HOME_REQUIRED")
    need(not out.exists() and not out.is_symlink() and out.parent.is_dir(),
         "P0X_BASELINE_FRESH_OUTPUT_REQUIRED")
    hb1b_native.admit(home)
    plan, answers = p0x.plan_and_answers()
    cfg = initialize(home)
    need(cfg.get("system_stage") == 0 and cfg.get("learning_mode") == "RECORD_ONLY"
         and cfg.get("latents_enabled") is False and cfg.get("jepa_weight", 0) == 0,
         "P0X_BASELINE_AGE0_REQUIRED")
    need(not os.environ.get("V13_LLAMA_SERVER"), "P0X_BASELINE_BINARY_OVERRIDE_RED")
    for rel in ("config/lora-active.json", "config/memory-server.json"):
        path = home / rel
        if path.exists():
            need(json.loads(path.read_text()) in ({}, {"active": {}}),
                 "P0X_BASELINE_ADAPTER_OR_MEMORY_ACTIVE_RED")
    cfg = dict(cfg, c3_decode_mode="server", c3_sampling="off",
               context_tokens=2048, threads=2, answer_tokens=p0x.TOKENS,
               temperature=.1)
    manager = ModelManager(home)
    checks = manager.verify(deep=True)
    need(checks.get("language", {}).get("ok") is True
         and checks["language"].get("hash_checked") is True
         and manager.revision("C3_LANGUAGE") == hb1.MODEL_REVISIONS["C3_LANGUAGE"]
         and hb1b_native.file_sha(manager.path_for("C3_LANGUAGE")) == p0x.C3_MODEL_SHA256,
         "P0X_BASELINE_MODEL_PIN_RED")
    binary = home / "bin/llama-server"
    need(binary.is_file() and hb1b_native.file_sha(binary) == p0x.RUNNER_SHA256,
         "P0X_BASELINE_RUNNER_PIN_RED")
    out.mkdir(mode=0o700)
    atomic_write(out / "INPUTS.json", hb1.canonical(plan).decode("utf-8"))
    atomic_write(out / "ANSWERS.json", hb1.canonical(answers).decode("utf-8"))
    receipt = {"schema": SCHEMA, "status": "RUNNING",
               "evidence_kind": "LINUX_NATIVE_C3_ONLY_P0X_PUBLIC_SYNTHETIC",
               "fixture_sha256": p0x.FIXTURE_SHA256,
               "model_sha256_before": p0x.C3_MODEL_SHA256,
               "runner_sha256_before": p0x.RUNNER_SHA256,
               "seed": p0x.SEED, "c3_tokens": p0x.TOKENS,
               "c3_sampling": "off", "expected_calls": 150,
               "age_authority": 0, "jepa_weight": 0,
               "weight_updates": False, "redmi_measured": False,
               "canonical_gate_pass": False, "whole_system_complete": False}
    records = []
    def persist():
        atomic_write(out / "RAW.json", hb1.canonical({
            "status": receipt["status"], "fixture_sha256": p0x.FIXTURE_SHA256,
            "rows": records}).decode("utf-8"))
        atomic_write(out / "RECEIPT.json", hb1.canonical(receipt).decode("utf-8"))
    persist()
    pool = None
    started = time.monotonic()
    try:
        pool = RunnerPool(home, manager, cfg)
        for p in plan:
            remaining = p0x.OVERALL_SECONDS - (time.monotonic() - started)
            need(remaining > 10, "P0X_BASELINE_OVERALL_DEADLINE_RED")
            begun = time.monotonic()
            runner = pool.get("C3_LANGUAGE")
            output = "".join(runner.generate(
                p["messages"], threading.Event(),
                time.monotonic() + min(p0x.PER_CALL_SECONDS, remaining),
                max_tokens=p0x.TOKENS, schema=p["schema"], seed=p0x.SEED))
            metrics = dict(runner.last_metrics)
            need(metrics.get("status") == "FINAL", "P0X_BASELINE_NOT_FINAL")
            records.append({
                "id": p["id"], "input_sha256": hb1.sha(hb1.canonical(p["messages"])),
                "schema_sha256": hb1.sha(hb1.canonical(p["schema"])),
                "model_sha256": p0x.C3_MODEL_SHA256,
                "output": output, "duration_s": time.monotonic() - begun,
                "metrics": metrics, "model_called": True, "native_calls": 1,
                "seed": p0x.SEED, "status": "FINAL"})
            receipt["recorded_calls"] = len(records)
            persist()
        released = pool.unload()
        pool = None
        need(released.get("process_reaped") is True, "P0X_BASELINE_PROCESS_REAP_RED")
        need(hb1b_native.file_sha(manager.path_for("C3_LANGUAGE")) == p0x.C3_MODEL_SHA256
             and hb1b_native.file_sha(binary) == p0x.RUNNER_SHA256,
             "P0X_BASELINE_MODEL_OR_RUNNER_CHANGED_RED")
        score = p0x.score(records, plan, answers)
        atomic_write(out / "SCORE.json", hb1.canonical(score).decode("utf-8"))
        receipt["status"] = "RECORDED_LINUX_NATIVE_P0X_C3_ONLY_BASELINE_NO_GATE"
        receipt["process_reaped"] = True
        receipt["model_sha256_after"] = p0x.C3_MODEL_SHA256
        receipt["runner_sha256_after"] = p0x.RUNNER_SHA256
        receipt["recorded_calls"] = 150
        persist()
        for name, key in (("RAW.json", "raw_sha256"), ("SCORE.json", "score_sha256"),
                          ("INPUTS.json", "inputs_sha256"), ("ANSWERS.json", "answers_sha256")):
            receipt[key] = hb1b_native.file_sha(out / name)
        atomic_write(out / "RECEIPT.json", hb1.canonical(receipt).decode("utf-8"))
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
    ap.add_argument("--home", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--install", action="store_true")
    args = ap.parse_args(argv)
    if args.install:
        print(json.dumps(install(args.home), sort_keys=True))
        return 0
    if args.out is None:
        ap.error("--out required without --install")
    result = run_native(args.home, args.out)
    print(json.dumps({"status": result["status"],
                      "recorded_calls": result["recorded_calls"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
