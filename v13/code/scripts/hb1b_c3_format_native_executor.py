"""HB1b preregistered 24-call C3 format/source Linux-native diagnostic.

Default off; only explicit isolated CLI. No learning, tools, Redmi or gate promotion.
Original prereg and anti-echo confound addendum committed before this source.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import threading
import time
from pathlib import Path

from scripts import hb1a_two_body_native_pilot as hb1
from scripts import hb1b_c3_format_followup as hb1b

SCHEMA = "v13.hb1b.c3_format_native_execution.v1"


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def admit(home):
    need(platform.system() == "Linux" and platform.machine() in ("x86_64", "amd64"),
         "HB1B_LINUX_X86_64_ONLY")
    need(shutil.disk_usage(home).free >= 3_000_000_000, "HB1B_DISK_BUDGET_RED")
    match = re.search(r"^MemAvailable:\s+(\d+)\s+kB",
                      Path("/proc/meminfo").read_text(), re.M)
    need(match is not None and int(match.group(1)) * 1024 >= 2_500_000_000,
         "HB1B_MEMORY_BUDGET_RED")
    cap_path = Path("/sys/fs/cgroup/memory.max")
    if cap_path.exists():
        cap = cap_path.read_text().strip()
        need(cap == "max" or (cap.isdecimal() and int(cap) >= 2_000_000_000),
             "HB1B_CGROUP_BUDGET_RED")


def install(home):
    """Install only the existing pinned public C3/Needle/runner in fresh home."""
    from scripts.run93_source_c3_native_e2e import install as install_c3
    from v13.models import ModelManager
    home = Path(home).resolve()
    need(not home.is_symlink(), "HB1B_HOME_SYMLINK_RED")
    home.mkdir(parents=True, exist_ok=True)
    admit(home)
    install_c3(home)
    manager = ModelManager(home)
    checks = manager.verify(deep=True)
    need(checks.get("language", {}).get("ok") is True
         and checks["language"].get("hash_checked") is True
         and manager.revision("C3_LANGUAGE") == hb1.MODEL_REVISIONS["C3_LANGUAGE"]
         and file_sha(manager.path_for("C3_LANGUAGE")) == hb1b.C3_MODEL_SHA256,
         "HB1B_INSTALL_MODEL_PIN_RED")
    need(file_sha(home / "bin/llama-server") == hb1b.RUNNER_SHA256,
         "HB1B_INSTALL_RUNNER_PIN_RED")
    return {"status": "HB1B_C3_AND_RUNNER_PINNED", "native_calls": 0,
            "model_sha256": hb1b.C3_MODEL_SHA256}


def run_native(home, out, parent_root):
    from v13.common import atomic_write
    from v13.config import initialize
    from v13.models import ModelManager
    from v13.runners import RunnerPool

    home, out, parent_root = (Path(p).resolve() for p in (home, out, parent_root))
    need(home.is_dir() and (home / "config/models.json").is_file(),
         "HB1B_PINNED_HOME_REQUIRED")
    need(not out.exists() and not out.is_symlink() and out.parent.is_dir(),
         "HB1B_FRESH_OUTPUT_REQUIRED")
    admit(home)
    plan = hb1b.build(parent_root)  # full parent verifier + exact raw/score pins
    cfg = initialize(home)
    need(cfg.get("system_stage") == 0 and cfg.get("learning_mode") == "RECORD_ONLY"
         and cfg.get("latents_enabled") is False and cfg.get("jepa_weight", 0) == 0,
         "HB1B_AGE0_RECORD_ONLY_REQUIRED")
    need(not os.environ.get("V13_LLAMA_SERVER"), "HB1B_BINARY_OVERRIDE_RED")
    for rel in ("config/lora-active.json", "config/memory-server.json"):
        path = home / rel
        if path.exists():
            need(json.loads(path.read_text()) in ({}, {"active": {}}),
                 "HB1B_ADAPTER_OR_MEMORY_ACTIVE_RED")
    cfg = dict(cfg, c3_decode_mode="server", c3_sampling="off",
               context_tokens=2048, threads=2, answer_tokens=hb1b.TOKENS,
               temperature=.1)
    need(cfg["c3_sampling"] != "anti_echo", "HB1B_SCHEMA_SAMPLER_CONFOUND_RED")
    manager = ModelManager(home)
    checks = manager.verify(deep=True)
    need(checks.get("language", {}).get("ok") is True
         and checks["language"].get("hash_checked") is True
         and manager.revision("C3_LANGUAGE") == hb1.MODEL_REVISIONS["C3_LANGUAGE"]
         and file_sha(manager.path_for("C3_LANGUAGE")) == hb1b.C3_MODEL_SHA256,
         "HB1B_MODEL_PIN_RED")
    binary = home / "bin/llama-server"
    need(binary.is_file() and file_sha(binary) == hb1b.RUNNER_SHA256,
         "HB1B_RUNNER_PIN_RED")
    out.mkdir(mode=0o700)
    atomic_write(out / "INPUTS.json", hb1.canonical(plan).decode("utf-8"))
    receipt = {"schema": SCHEMA, "status": "RUNNING",
               "evidence_kind": "LINUX_NATIVE_C3_FORMAT_PUBLIC_SYNTHETIC",
               "parent_raw_sha256": hb1b.PARENT_RAW_SHA256,
               "parent_score_sha256": hb1b.PARENT_SCORE_SHA256,
               "fixture_sha256": hb1.FIXTURE,
               "model_sha256_before": hb1b.C3_MODEL_SHA256,
               "runner_sha256_before": hb1b.RUNNER_SHA256,
               "seed": hb1b.SEED, "c3_tokens": hb1b.TOKENS,
               "expected_calls": 24, "c3_sampling": "off",
               "age_authority": 0, "jepa_weight": 0,
               "weight_updates": False, "redmi_measured": False,
               "canonical_gate_pass": False, "whole_system_complete": False}
    records = []
    def persist():
        atomic_write(out / "RAW.json", hb1.canonical({
            "status": receipt["status"],
            "parent_raw_sha256": hb1b.PARENT_RAW_SHA256,
            "rows": records}).decode("utf-8"))
        atomic_write(out / "RECEIPT.json", hb1.canonical(receipt).decode("utf-8"))
    persist()
    pool = None
    started = time.monotonic()
    try:
        pool = RunnerPool(home, manager, cfg)
        for p in plan:
            remaining = hb1b.OVERALL_SECONDS - (time.monotonic() - started)
            need(remaining > 10, "HB1B_OVERALL_DEADLINE_RED")
            begun = time.monotonic()
            runner = pool.get("C3_LANGUAGE")
            output = "".join(runner.generate(
                p["messages"], threading.Event(),
                time.monotonic() + min(hb1b.PER_CALL_SECONDS, remaining),
                max_tokens=hb1b.TOKENS, schema=p["schema"], seed=hb1b.SEED))
            metrics = dict(runner.last_metrics)
            need(metrics.get("status") == "FINAL", "HB1B_C3_NATIVE_NOT_FINAL")
            records.append({
                "id": p["id"], "arm": p["arm"],
                "input_sha256": hb1.sha(hb1.canonical(p["messages"])),
                "schema_sha256": (hb1.sha(hb1.canonical(p["schema"]))
                                  if p["schema"] else None),
                "model_sha256": hb1b.C3_MODEL_SHA256,
                "output": output, "duration_s": time.monotonic() - begun,
                "metrics": metrics, "model_called": True, "native_calls": 1,
                "seed": hb1b.SEED, "status": "FINAL"})
            receipt["recorded_calls"] = len(records)
            persist()
        released = pool.unload()
        pool = None
        need(released.get("process_reaped") is True, "HB1B_PROCESS_REAP_RED")
        need(file_sha(manager.path_for("C3_LANGUAGE")) == hb1b.C3_MODEL_SHA256,
             "HB1B_MODEL_CHANGED_RED")
        need(file_sha(binary) == hb1b.RUNNER_SHA256, "HB1B_RUNNER_CHANGED_RED")
        report = hb1b.score(records, plan)
        atomic_write(out / "SCORE.json", hb1.canonical(report).decode("utf-8"))
        receipt["status"] = "RECORDED_LINUX_NATIVE_C3_FORMAT_DIAGNOSTIC_NO_GATE"
        receipt["process_reaped"] = True
        receipt["model_sha256_after"] = hb1b.C3_MODEL_SHA256
        receipt["runner_sha256_after"] = hb1b.RUNNER_SHA256
        receipt["recorded_calls"] = 24
        persist()
        receipt["raw_sha256"] = file_sha(out / "RAW.json")
        receipt["score_sha256"] = file_sha(out / "SCORE.json")
        receipt["inputs_sha256"] = file_sha(out / "INPUTS.json")
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--parent-evidence-dir", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args(argv)
    if args.install:
        print(json.dumps(install(args.home), sort_keys=True))
        return 0
    if args.out is None or args.parent_evidence_dir is None:
        parser.error("--out and --parent-evidence-dir required without --install")
    result = run_native(args.home, args.out, args.parent_evidence_dir)
    print(json.dumps({"status": result["status"],
                      "recorded_calls": result["recorded_calls"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
