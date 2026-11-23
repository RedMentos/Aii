"""HB1a: isolated real Linux-native 24 B1/B2 + 30 C3 diagnostic executor.

Preregged before code in HB1A_TWO_BODY_NATIVE_PREREG.md. No Runtime._turn
activation, no learning, no native latent exchange and no Canon gate promotion.
"""
from __future__ import annotations
import argparse
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
from scripts import hb1a_two_body_native_pilot as hb1

SCHEMA = "v13.hb1a.native_execution.v1"


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
         "HB1A_LINUX_X86_64_ONLY")
    need(shutil.disk_usage(home).free >= 4_000_000_000, "HB1A_DISK_BUDGET_RED")
    meminfo = Path("/proc/meminfo").read_text()
    match = re.search(r"^MemAvailable:\s+(\d+)\s+kB", meminfo, re.M)
    need(match is not None and int(match.group(1)) * 1024 >= 3_500_000_000,
         "HB1A_MEMORY_BUDGET_RED")
    cgroup = Path("/sys/fs/cgroup/memory.max")
    if cgroup.exists():
        cap = cgroup.read_text().strip()
        need(cap == "max" or (cap.isdecimal() and int(cap) >= 3_000_000_000),
             "HB1A_CGROUP_BUDGET_RED")


def install(home):
    """Install only already-catalogued pinned public models in isolated home."""
    from scripts.run93_source_c3_native_e2e import install as install_c3
    from v13.models import ModelManager
    admit(home)
    install_c3(home)
    manager = ModelManager(home)
    manager.install("body")
    manager.install("gist")
    checks = manager.verify(deep=True)
    for role, key in (("B1_DETAIL", "body"), ("B2_GIST", "gist"),
                      ("C3_LANGUAGE", "language")):
        need(checks.get(key, {}).get("ok") is True
             and checks[key].get("hash_checked") is True
             and manager.revision(role) == hb1.MODEL_REVISIONS[role]
             and file_sha(manager.path_for(role)) == hb1.MODEL_SHAS[role],
             "HB1A_INSTALL_MODEL_PIN_RED_" + role)
    return {"status": "HB1A_THREE_MODELS_INSTALLED_AND_HASH_VERIFIED",
            "model_sha256": hb1.MODEL_SHAS, "native_calls": 0}


def run_native(home, out, fixture_sha):
    from v13.common import atomic_write
    from v13.config import initialize
    from v13.models import ModelManager
    from v13.runners import RunnerPool

    home, out = Path(home).resolve(), Path(out).resolve()
    need(home.is_dir() and (home / "config/models.json").is_file(),
         "HB1A_PINNED_HOME_REQUIRED")
    need(not out.exists() and not out.is_symlink() and out.parent.is_dir(),
         "HB1A_FRESH_OUTPUT_REQUIRED")
    admit(home)
    rows = hb0.fixtures()
    body_plan = hb1.body_plan(rows, fixture_sha)
    cfg = initialize(home)
    need(cfg.get("system_stage") == 0 and cfg.get("learning_mode") == "RECORD_ONLY"
         and cfg.get("latents_enabled") is False and cfg.get("jepa_weight", 0) == 0,
         "HB1A_AGE0_RECORD_ONLY_REQUIRED")
    need(not os.environ.get("V13_LLAMA_SERVER"),
         "HB1A_NATIVE_BINARY_OVERRIDE_REFUSED")
    for rel in ("config/lora-active.json", "config/memory-server.json"):
        path = home / rel
        if path.exists():
            need(json.loads(path.read_text()) in ({}, {"active": {}}),
                 "HB1A_ADAPTER_OR_MEMORY_ACTIVE_RED")
    cfg = dict(cfg, c3_decode_mode="server", c3_sampling="anti_echo",
               context_tokens=2048, threads=2, answer_tokens=hb1.BODY_TOKENS,
               temperature=.1)
    manager = ModelManager(home)
    verified = manager.verify(deep=True)
    for role, key in (("B1_DETAIL", "body"), ("B2_GIST", "gist"),
                      ("C3_LANGUAGE", "language")):
        need(verified.get(key, {}).get("ok") is True
             and verified[key].get("hash_checked") is True
             and manager.revision(role) == hb1.MODEL_REVISIONS[role]
             and file_sha(manager.path_for(role)) == hb1.MODEL_SHAS[role],
             "HB1A_MODEL_PIN_RED_" + role)
    binary = home / "bin/llama-server"
    need(binary.is_file(), "HB1A_NATIVE_BINARY_MISSING")
    runner_sha = file_sha(binary)
    out.mkdir(mode=0o700)
    atomic_write(out / "BODY_INPUTS.json", hb1.canonical(body_plan).decode("utf-8"))
    receipt = {"schema": SCHEMA, "status": "RUNNING",
               "evidence_kind": "LINUX_NATIVE_THREE_ORGAN_PUBLIC_SYNTHETIC",
               "fixture_sha256": fixture_sha, "model_sha256_before": hb1.MODEL_SHAS,
               "runner_sha256_before": runner_sha, "seed": hb1.SEED,
               "body_tokens": hb1.BODY_TOKENS, "c3_tokens": hb1.C3_TOKENS,
               "body_expected": 24, "c3_expected": 30,
               "age_authority": 0, "jepa_weight": 0, "weight_updates": False,
               "redmi_measured": False, "canonical_gate_pass": False,
               "whole_system_complete": False}
    body_records, c3_records = [], []
    def persist():
        atomic_write(out / "RAW.json", hb1.canonical({
            "status": receipt["status"], "fixture_sha256": fixture_sha,
            "body_rows": body_records, "c3_rows": c3_records}).decode("utf-8"))
        atomic_write(out / "RECEIPT.json", hb1.canonical(receipt).decode("utf-8"))
    persist()
    pool = None
    start = time.monotonic()
    try:
        pool = RunnerPool(home, manager, cfg)
        for p in body_plan:
            remaining = hb1.OVERALL_SECONDS - (time.monotonic() - start)
            need(remaining > 10, "HB1A_OVERALL_DEADLINE_RED")
            begun = time.monotonic()
            runner = pool.get(p["role"])
            output = "".join(runner.generate(
                p["messages"], threading.Event(),
                time.monotonic() + min(hb1.PER_CALL_SECONDS, remaining),
                max_tokens=hb1.BODY_TOKENS, seed=hb1.SEED))
            metrics = dict(runner.last_metrics)
            need(metrics.get("status") == "FINAL", "HB1A_BODY_NATIVE_NOT_FINAL")
            body_records.append({
                "id": p["id"], "kind": p["kind"], "role": p["role"],
                "source_project": p["source_project"],
                "source_sha256": p["source_sha256"],
                "input_sha256": hb1.sha(hb1.canonical(p["messages"])),
                "model_sha256": hb1.MODEL_SHAS[p["role"]],
                "output": output, "duration_s": time.monotonic() - begun,
                "metrics": metrics, "model_called": True,
                "native_calls": 1, "seed": hb1.SEED, "status": "FINAL"})
            receipt["body_recorded"] = len(body_records)
            persist()
        c3_plan = hb1.receiver_plan(rows, fixture_sha, body_records)
        atomic_write(out / "C3_INPUTS.json", hb1.canonical(c3_plan).decode("utf-8"))
        for p in c3_plan:
            remaining = hb1.OVERALL_SECONDS - (time.monotonic() - start)
            need(remaining > 10, "HB1A_OVERALL_DEADLINE_RED")
            begun = time.monotonic()
            runner = pool.get("C3_LANGUAGE")
            output = "".join(runner.generate(
                p["messages"], threading.Event(),
                time.monotonic() + min(hb1.PER_CALL_SECONDS, remaining),
                max_tokens=hb1.C3_TOKENS, schema=hb1.C3_SCHEMA, seed=hb1.SEED))
            metrics = dict(runner.last_metrics)
            need(metrics.get("status") == "FINAL", "HB1A_C3_NATIVE_NOT_FINAL")
            c3_records.append({
                "id": p["id"], "arm": p["arm"],
                "input_sha256": hb1.sha(hb1.canonical(p["messages"])),
                "model_sha256": hb1.MODEL_SHAS["C3_LANGUAGE"],
                "output": output, "duration_s": time.monotonic() - begun,
                "metrics": metrics, "model_called": True,
                "native_calls": 1, "seed": hb1.SEED, "status": "FINAL"})
            receipt["c3_recorded"] = len(c3_records)
            persist()
        released = pool.unload()
        pool = None
        need(released.get("process_reaped") is True, "HB1A_PROCESS_REAP_RED")
        for role in hb1.MODEL_SHAS:
            need(file_sha(manager.path_for(role)) == hb1.MODEL_SHAS[role],
                 "HB1A_MODEL_CHANGED_" + role)
        need(file_sha(binary) == runner_sha, "HB1A_BINARY_CHANGED")
        report = hb1.score(body_records, c3_records, rows, fixture_sha)
        atomic_write(out / "SCORE.json", hb1.canonical(report).decode("utf-8"))
        receipt["status"] = "RECORDED_LINUX_NATIVE_THREE_ORGAN_DIAGNOSTIC_NO_GATE"
        receipt["process_reaped"] = True
        receipt["model_sha256_after"] = hb1.MODEL_SHAS
        receipt["runner_sha256_after"] = file_sha(binary)
        receipt["body_recorded"] = 24
        receipt["c3_recorded"] = 30
        persist()
        receipt["raw_sha256"] = file_sha(out / "RAW.json")
        receipt["score_sha256"] = file_sha(out / "SCORE.json")
        receipt["body_inputs_sha256"] = file_sha(out / "BODY_INPUTS.json")
        receipt["c3_inputs_sha256"] = file_sha(out / "C3_INPUTS.json")
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path)
    p.add_argument("--fixture-sha256", default=hb1.FIXTURE)
    p.add_argument("--install", action="store_true")
    args = p.parse_args(argv)
    if args.install:
        print(json.dumps(install(args.home), sort_keys=True))
        return 0
    if args.out is None:
        p.error("--out required without --install")
    result = run_native(args.home, args.out, args.fixture_sha256)
    print(json.dumps({"status": result["status"],
                      "body_recorded": result["body_recorded"],
                      "c3_recorded": result["c3_recorded"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
