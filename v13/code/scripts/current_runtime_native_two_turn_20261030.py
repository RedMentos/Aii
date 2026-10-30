"""Current V13 real Runtime/JEF two-turn Linux native integration, review-only.

A connected Runtime run is required: individual C2/B1/B2/C3 CLI smokes are not
an end-to-end proof. Never promotes STEP2, JEPA, Age or Redmi gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import time

from scripts.step2_current_catalog_artifact_probe import git_blob_sha
from v13.common import APP, dumps, file_hash
from v13.config import initialize, save_config
from v13.models import ModelManager
from v13.bootstrap import install_native
from v13.runtime import Runtime

CATALOG_BLOB = "7af05962af41d0bc3f7dd18ef01d4eba55eabf99"
MANAGER_BLOB = "bd035cf8029850cce00b179edf533e53bf24358a"
TOOLS_BLOB = "954a3f468f10195fbce12d27f68585ee7edee2c9"
PINS = {
    "needle": "c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38",
    "language": "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
    "body": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
    "gist": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
}
RUNNER_TAR_SHA = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
PROMPTS = (
    "Budget 120 Euro. Berechne die Hälfte.",
    "Hello.",
)
FINAL = {"FINAL", "ERROR", "DEADLINE", "CANCELLED", "INTERRUPTED"}


def preflight(scratch, evidence):
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise ValueError("Linux x86_64 only")
    if Path(scratch).exists() or Path(evidence).exists():
        raise FileExistsError("Fresh scratch and evidence directories required")
    if shutil.disk_usage(Path(scratch).parent).free < 3 * 1024**3:
        raise OSError("At least 3GiB scratch disk required")
    try:
        raw = Path("/sys/fs/cgroup/memory.max").read_text().strip()
        if raw != "max" and int(raw) < 4 * 1024**3:
            raise OSError("Linux cgroup memory budget below 4GiB")
    except (FileNotFoundError, ValueError):
        pass
    for path, expected in (
        ("specs/models.json", CATALOG_BLOB),
        ("v13/models.py", MANAGER_BLOB),
        ("specs/control_tools.json", TOOLS_BLOB),
    ):
        if git_blob_sha((APP / path).read_bytes()) != expected:
            raise ValueError("Pinned current source drift: " + path)


def _wait(r, event_id, seconds=210):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        row = r.store.one(
            "SELECT * FROM messages WHERE event_id=? AND role='assistant' "
            "ORDER BY id DESC LIMIT 1", (event_id,))
        if row and row["status"] in FINAL:
            return row
        if not r.worker.is_alive():
            raise RuntimeError("Runtime worker died before final message")
        time.sleep(.25)
    r.cancel()
    raise TimeoutError("Native Runtime turn exceeded bounded wait")


def _summary(r, event_id, row):
    meta = json.loads(row["metadata"])
    route = meta.get("route") or {}
    packets = r.store.rows(
        "SELECT kind,payload FROM packets WHERE event_id=?", (event_id,))
    offers = [json.loads(p["payload"]) for p in packets if p["kind"] == "OfferPacket"]
    return {
        "event_id": event_id,
        "status": row["status"],
        "answer_sha256": hashlib.sha256(row["text"].encode()).hexdigest(),
        "answer_chars": len(row["text"]),
        "answer_excerpt": row["text"][:350],
        "model_generated": meta.get("model_generated") is True,
        "route_source": route.get("source") if isinstance(route, dict) else None,
        "native_c2_seen": isinstance(route, dict) and bool(route.get("native_control")),
        "native_c2_metrics": route.get("native_control_metrics") if isinstance(route, dict) else None,
        "offer_roles": [p["role"] for p in offers],
        "offer_native_status": {
            p["role"]: (p.get("native_metrics") or {}).get("status")
            for p in offers
        },
        "output_runner_role": (meta.get("runner") or {}).get("role"),
        "output_runner_status": (meta.get("runner") or {}).get("status"),
        "tool_executed": bool(meta.get("tool_call")),
        "packet_kinds": sorted({p["kind"] for p in packets}),
        "age_authority": 0,
    }


def run(scratch, evidence, progress=print):
    scratch, evidence = Path(scratch), Path(evidence)
    preflight(scratch, evidence)
    scratch.mkdir(parents=True)
    evidence.mkdir(parents=True)
    home = scratch / "home"
    cfg = initialize(home)
    cfg.update(
        learning_mode="RECORD_ONLY",
        route_override="auto",
        context_tokens=512,
        answer_tokens=64,
        observer_tokens=160,
        deadline_seconds=180,
        control_seconds=20.,
        observer_seconds=60.,
        body_residency_mb=0,
        minimum_free_mb=100,
        history_turns=0,
        threads=2,
    )
    save_config(home, cfg)
    manager = ModelManager(home)
    manager.install("all", progress=progress)
    installed = manager.verify(deep=True)
    if set(installed) != set(PINS) or not all(v["ok"] for v in installed.values()):
        raise ValueError("Installed model identity/integrity mismatch")
    for key, expected in PINS.items():
        path = home / manager.installed[key]["files"][manager.installed[key]["main_file"]]["path"]
        if file_hash(path) != expected:
            raise ValueError("Pinned model hash drift: " + key)
    install_native(home, progress=progress)
    runner_tar = home / "tmp/llama-bin.tar.gz"
    if file_hash(runner_tar) != RUNNER_TAR_SHA:
        raise ValueError("Pinned llama.cpp runner archive drift")
    runner_sha = file_hash(home / "bin/llama-server")
    (evidence / "ASSETS.json").write_text(
        dumps({"model_sha256": PINS, "runner_tar_sha256": RUNNER_TAR_SHA,
               "llama_server_sha256": runner_sha,
               "catalog_blob": CATALOG_BLOB, "manager_blob": MANAGER_BLOB,
               "tools_blob": TOOLS_BLOB}) + "\n", encoding="utf-8")

    r = Runtime(home)
    summaries = []
    reaped = False
    try:
        r.sleep.cycle.set_policy("enabled", "off")
        for index, text in enumerate(PROMPTS):
            r.cfg["route_override"] = "auto" if index == 0 else "simple"
            event_id = r.submit(text)
            row = _wait(r, event_id)
            summaries.append(_summary(r, event_id, row))
            if row["status"] != "FINAL":
                break
    finally:
        r.close()
        reaped = not r.pool.pids() and not r.needle.pids()
        logs = evidence / "native_logs"
        logs.mkdir(exist_ok=True)
        for p in sorted((home / "logs").glob("*.log")):
            if p.stat().st_size > 3 * 1024**2:
                raise RuntimeError("Native log exceeds uncapped evidence budget: " + p.name)
            shutil.copyfile(p, logs / p.name)

    first = summaries[0] if summaries else {}
    second = summaries[1] if len(summaries) > 1 else {}
    first_ok = (first.get("status") == "FINAL" and first.get("model_generated")
                and first.get("native_c2_seen")
                and {"B1_DETAIL", "B2_GIST"}.issubset(set(first.get("offer_roles", []))))
    second_ok = (second.get("status") == "FINAL" and second.get("model_generated")
                 and second.get("output_runner_role") == "C3_LANGUAGE")
    report = {
        "schema": "v13.current_runtime.native_two_turn_linux.v1",
        "evidence_kind": "LINUX_NATIVE_CONNECTED_TWO_TURN_REVIEW_ONLY",
        "turns": summaries,
        "first_c2_b1b2_pass": bool(first_ok),
        "second_c3_pass": bool(second_ok),
        "native_two_turn_pass": bool(first_ok and second_ok and reaped),
        "all_native_processes_reaped": reaped,
        "learning_mode": "RECORD_ONLY",
        "external_tools_executed": any(x.get("tool_executed") for x in summaries),
        "redmi_measured": False,
        "step2_semantic_utility_proven": False,
        "step2_gate_promoted": False,
        "b3_promoted": False,
        "body_jepa_promoted": False,
        "jepa_weight": 0,
        "age_authority": 0,
        "whole_system_complete": False,
    }
    (evidence / "REPORT.json").write_text(dumps(report) + "\n", encoding="utf-8")
    if not report["native_two_turn_pass"] or report["external_tools_executed"]:
        raise RuntimeError("Connected native two-turn acceptance RED; original raw retained")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scratch-home", type=Path, required=True)
    p.add_argument("--evidence-dir", type=Path, required=True)
    a = p.parse_args()
    result = run(a.scratch_home, a.evidence_dir)
    print(dumps({"native_two_turn_pass": result["native_two_turn_pass"]}))


if __name__ == "__main__":
    main()
