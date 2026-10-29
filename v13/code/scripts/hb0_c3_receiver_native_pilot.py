"""HB0c: serial pinned C3 Linux-native exact-source receiver diagnostic.

No B1/B2 inference, learning, tool authority or Canon gate promotion.
Public synthetic family 5 only. Registered BEFORE implementation/execution.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import platform
import re
import shutil
import threading
import time
from pathlib import Path

from scripts import hb0_split_information_cohort as hb0
from scripts import hb0_arm_export as arms

SCHEMA = "v13.hb0.c3_receiver_native_pilot.v1"
MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
REVISION = "657e078c94084481950a2d555a941481f715536b"
FAMILY = 5
ARM_ORDER = ("c3_only", "both_exact", "single_body_dual", "shuffled_b1")
SEED = 13
TOKENS = 64
PER_CALL_SECONDS = 75
OVERALL_SECONDS = 1800


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def plan(rows, expected_sha256):
    prompts, _ = arms.build(rows, expected_sha256)
    selected = [r for r in rows if r["family"] == FAMILY]
    require(len(selected) == 6, "HB0C_FAMILY_COVERAGE_RED")
    selected.sort(key=lambda r: (r["sheet_index"], r["rule_index"]))
    mapping = {(p["id"], p["arm"]): p for p in prompts}
    chosen = [mapping[(r["id"], arm)] for r in selected for arm in ARM_ORDER]
    require(len(chosen) == 24
            and len({(p["id"], p["arm"]) for p in chosen}) == 24,
            "HB0C_PLAN_COVERAGE_RED")
    for p in chosen:
        require("oracle_action" not in json.dumps(p)
                and "sheet_index" not in json.dumps(p)
                and "rule_index" not in json.dumps(p),
                "HB0C_ORACLE_INPUT_LEAK_RED")
    return chosen


def action(text):
    """Strict initial commitment parser; ambiguous prose is UNPARSEABLE."""
    if type(text) is not str:
        return "UNPARSEABLE"
    if re.match(r"^\s*(?:i\s+)?(?:choose|pick|select|recommend)\s+(?:the\s+)?option\s+([AB])\b", text, re.I):
        return re.match(r"^\s*(?:i\s+)?(?:choose|pick|select|recommend)\s+(?:the\s+)?option\s+([AB])\b", text, re.I).group(1).upper()
    if re.match(r"^\s*(?:neither\s+option|no\s+option)\s+(?:is\s+)?(?:eligible|valid)", text, re.I):
        return "NONE"
    if re.match(r"^\s*(?:unknown\b|i\s+(?:cannot|can't)\s+decide\b|not\s+enough\s+information\b)", text, re.I):
        return "UNKNOWN"
    return "UNPARSEABLE"


def score(records, rows, expected_sha256):
    plan_rows = plan(rows, expected_sha256)
    expected = [(p["id"], p["arm"]) for p in plan_rows]
    input_hashes = {(p["id"], p["arm"]): sha(canonical(p["messages"]))
                    for p in plan_rows}
    require(type(records) is list and len(records) == 24, "HB0C_RAW_COUNT_RED")
    require([(r.get("id"), r.get("arm")) for r in records] == expected,
            "HB0C_RAW_IDENTITY_RED")
    answers = {r["id"]: r["oracle_action"] for r in rows if r["family"] == FAMILY}
    per_arm = {arm: {"exact": 0, "wrong_committed": 0,
                     "unknown": 0, "unparseable": 0, "latency_s": []}
               for arm in ARM_ORDER}
    details = []
    for record in records:
        require(record.get("status") == "FINAL"
                and record.get("model_called") is True
                and record.get("native_calls") == 1
                and record.get("seed") == SEED
                and record.get("model_sha256") == MODEL_SHA
                and record.get("input_sha256")
                    == input_hashes[(record["id"], record["arm"])]
                and type(record.get("metrics")) is dict
                and record["metrics"].get("status") == "FINAL",
                "HB0C_NATIVE_ROW_INVALID")
        duration = record.get("duration_s")
        require(type(duration) in (int, float) and math.isfinite(duration)
                and 0 <= duration <= PER_CALL_SECONDS + 10,
                "HB0C_NONFINITE_LATENCY_RED")
        predicted = action(record.get("output"))
        truth = answers[record["id"]]
        stats = per_arm[record["arm"]]
        stats["exact"] += int(predicted == truth)
        stats["wrong_committed"] += int(predicted in ("A", "B", "NONE") and predicted != truth)
        stats["unknown"] += int(predicted == "UNKNOWN")
        stats["unparseable"] += int(predicted == "UNPARSEABLE")
        stats["latency_s"].append(duration)
        details.append({"id": record["id"], "arm": record["arm"],
                        "predicted": predicted, "oracle": truth,
                        "exact": predicted == truth})
    summary = {
        arm: {"exact": data["exact"],
              "wrong_committed": data["wrong_committed"],
              "unknown": data["unknown"],
              "unparseable": data["unparseable"],
              "mean_latency_s": sum(data["latency_s"]) / 6}
        for arm, data in per_arm.items()
    }
    return {
        "schema": SCHEMA + ".score.v1", "status": "POSTHOC_EXPLORATORY_NO_GATE",
        "evidence_kind": "LINUX_NATIVE_ONLY_IF_RAW_VERIFIED",
        "source_fixture_sha256": expected_sha256,
        "rows": 24, "per_arm": summary, "details": details,
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "b3_status": "FAIL", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "claim_limit": "Six public synthetic rows; C3 only; no B1/B2 generated evidence",
    }


def _admit(home):
    require(platform.system() == "Linux" and platform.machine() in ("x86_64", "amd64"),
            "HB0C_LINUX_X86_64_ONLY")
    require(shutil.disk_usage(home).free >= 1024 * 1024 * 1024,
            "HB0C_DISK_BUDGET_RED")
    meminfo = Path("/proc/meminfo").read_text()
    m = re.search(r"^MemAvailable:\s+(\d+)\s+kB", meminfo, re.M)
    require(m is not None and int(m.group(1)) * 1024 >= 2_000_000_000,
            "HB0C_MEMORY_BUDGET_RED")
    cgroup = Path("/sys/fs/cgroup/memory.max")
    if cgroup.exists():
        raw = cgroup.read_text().strip()
        require(raw == "max" or (raw.isdecimal() and int(raw) >= 2_000_000_000),
                "HB0C_CGROUP_BUDGET_RED")


def run_native(home, out, fixture_sha256):
    from v13.common import atomic_write, file_hash
    from v13.config import initialize
    from v13.models import ModelManager
    from v13.runners import RunnerPool

    home = Path(home).resolve()
    out = Path(out).resolve()
    require(home.is_dir() and (home / "config/models.json").is_file(),
            "HB0C_PINNED_HOME_REQUIRED")
    require(not out.exists() and out.parent.is_dir(), "HB0C_FRESH_OUT_REQUIRED")
    _admit(home)
    rows = hb0.fixtures()
    inputs = plan(rows, fixture_sha256)
    cfg = initialize(home)
    require(cfg.get("system_stage") == 0
            and cfg.get("learning_mode") == "RECORD_ONLY"
            and cfg.get("latents_enabled") is False
            and cfg.get("jepa_weight", 0) == 0,
            "HB0C_AGE0_RECORD_ONLY_REQUIRED")
    cfg = dict(cfg, c3_decode_mode="server", c3_sampling="anti_echo",
               context_tokens=2048, threads=2, answer_tokens=TOKENS,
               temperature=.1)
    manager = ModelManager(home)
    verified = manager.verify(deep=True)
    require(verified.get("language", {}).get("ok") is True
            and verified["language"].get("hash_checked") is True
            and manager.revision("C3_LANGUAGE") == REVISION
            and file_hash(manager.path_for("C3_LANGUAGE")) == MODEL_SHA,
            "HB0C_C3_PIN_RED")
    binary = home / "bin/llama-server"
    require(binary.is_file(), "HB0C_NATIVE_BINARY_MISSING")
    binary_sha = file_hash(binary)
    out.mkdir(mode=0o700)
    atomic_write(out / "INPUTS.json", canonical(inputs).decode("utf-8"))
    receipt = {
        "schema": SCHEMA, "status": "RUNNING",
        "evidence_kind": "LINUX_NATIVE_C3_SYNTHETIC_PUBLIC_PILOT",
        "fixture_sha256": fixture_sha256, "model_sha256": MODEL_SHA,
        "model_revision": REVISION, "runner_sha256_before": binary_sha,
        "seed": SEED, "tokens": TOKENS, "family": FAMILY,
        "arms": list(ARM_ORDER), "expected_native_calls": 24,
        "input_sha256": sha(canonical(inputs)),
        "age_authority": 0, "jepa_weight": 0, "weight_updates": False,
        "redmi_measured": False, "canonical_gate_pass": False,
        "whole_system_complete": False,
    }
    records = []
    def persist():
        atomic_write(out / "RAW.json", canonical({
            "status": receipt["status"], "rows": records,
            "model_sha256": MODEL_SHA, "fixture_sha256": fixture_sha256
        }).decode("utf-8"))
        atomic_write(out / "RECEIPT.json", canonical(receipt).decode("utf-8"))
    persist()
    lock_path = out / "native_owner.lock"
    pool = None
    released = None
    try:
        with lock_path.open("xb") as owner:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            pool = RunnerPool(home, manager, cfg)
            runner = pool.get("C3_LANGUAGE")
            start = time.monotonic()
            for p in inputs:
                remaining = OVERALL_SECONDS - (time.monotonic() - start)
                require(remaining > 10, "HB0C_OVERALL_DEADLINE_RED")
                deadline = time.monotonic() + min(PER_CALL_SECONDS, remaining)
                begun = time.monotonic()
                output = "".join(runner.generate(
                    p["messages"], threading.Event(), deadline,
                    max_tokens=TOKENS, seed=SEED))
                metrics = dict(runner.last_metrics)
                require(metrics.get("status") == "FINAL",
                        "HB0C_NATIVE_GENERATION_NOT_FINAL")
                records.append({
                    "id": p["id"], "arm": p["arm"], "status": "FINAL",
                    "input_sha256": sha(canonical(p["messages"])),
                    "output": output, "duration_s": time.monotonic() - begun,
                    "metrics": metrics, "model_sha256": MODEL_SHA,
                    "model_called": True, "native_calls": 1, "seed": SEED,
                })
                receipt["recorded_calls"] = len(records)
                persist()
            released = pool.unload()
            pool = None
            require(released.get("process_reaped") is True, "HB0C_PROCESS_REAP_RED")
            require(file_hash(manager.path_for("C3_LANGUAGE")) == MODEL_SHA
                    and file_hash(binary) == binary_sha,
                    "HB0C_MODEL_OR_BINARY_CHANGED")
            analysis = score(records, rows, fixture_sha256)
            atomic_write(out / "SCORE.json", canonical(analysis).decode("utf-8"))
            receipt["status"] = "RECORDED_LINUX_NATIVE_C3_DIAGNOSTIC_NO_GATE"
            receipt["process_reaped"] = True
            receipt["model_sha256_after"] = MODEL_SHA
            receipt["runner_sha256_after"] = file_hash(binary)
            receipt["raw_sha256"] = sha(canonical({"status": receipt["status"], "rows": records,
                              "model_sha256": MODEL_SHA, "fixture_sha256": fixture_sha256}))
            receipt["score_sha256"] = file_hash(out / "SCORE.json")
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fixture-sha256", required=True)
    args = parser.parse_args(argv)
    receipt = run_native(args.home, args.out, args.fixture_sha256)
    print(json.dumps({"status": receipt["status"],
                      "recorded_calls": receipt["recorded_calls"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
