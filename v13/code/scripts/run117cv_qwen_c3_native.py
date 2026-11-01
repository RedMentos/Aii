#!/usr/bin/env python3
"""Run117CV pinned Linux-native source-only C3 model-capacity comparison.

Review-only: 9 frozen real-Store envelopes x 2 exact model files. No output,
tools, training or age authority. Every failed native attempt retains raw.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import threading
import time

from scripts import run117cu_qwen_c3_source_only_preflight as cu
from scripts import run117cn_c3_source_independence_fixture as frozen
from scripts import jef_c3_schema_fixture_727 as run68
from scripts.run115j_typed_jef_role_native import RUNNER_SHA
from v13.common import atomic_write, dumps, file_hash
from v13.config import DEFAULTS
from v13.models import ModelManager
from v13.runners import LlamaRunner

SCHEMA = "v13.run117cv.qwen_c3_source_only_native.v1"
SEED = 117041
MODELS = ("lfm25_350m", "qwen35_0p8b")
NEGATIVE = {
    "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
    "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
    "world_jepa": "SHADOW", "jepa_weight": 0,
    "redmi_measured": False, "whole_system_complete": False,
    "learning_authority": 0, "delivery_authority": 0,
    "tool_dispatches": 0, "output_committed": False,
    "native_body_calls": 0, "native_c2_calls": 0,
    "native_jef_calls": 0, "independent_generalization": False,
}
CONFIG = DEFAULTS | {
    "threads": 2, "temperature": 0.0, "seed": SEED,
    "observer_mode": "off", "answer_tokens": 96,
    "deadline_seconds": 120, "observer_seconds": 30,
    "body_residency_mb": 0, "history_turns": 0,
    "memory_top_k": 0, "teacher_enabled": False,
    "learning_mode": "RECORD_ONLY",
    "context_tokens": 2048, "native_cache_ram_mb": 0,
    "native_ctx_checkpoints": 0,
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _blob(path):
    raw = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()


def source_pins():
    expected = {
        cu.ROOT / "scripts/run117cu_qwen_c3_source_only_preflight.py":
            "b7e72d029406fa42440566dd2f490c396e3f075f",
        cu.ROOT / "scripts/run117cn_c3_source_independence_fixture.py":
            "a482bc6b289a080b56c4fe721de1337d680119d9",
        cu.ROOT / "v13/jef_c3_source_only_shadow_candidate.py":
            "6886799315457fe51698e43fd483707da7b9b5e2",
        cu.ROOT / "specs/cloud-candidates.json":
            "e84dfe066b15a310700329636734fc85084d4766",
    }
    if any(_blob(p) != h for p, h in expected.items()):
        raise ValueError("RUN117CV_SOURCE_PIN_RED")
    return {str(p.relative_to(cu.ROOT)): h for p, h in expected.items()}


def pinned_paths(installed, qwen_path):
    """No implicit download, substitution, symlink, or model catalog edit."""
    models = {m["id"]: m for m in cu.pinned_models()}
    installed, qwen_path = Path(installed), Path(qwen_path)
    manager = ModelManager(installed)
    lfm = manager.path_for("C3_LANGUAGE")
    runner = installed / "bin/llama-server"
    if (not installed.is_dir() or not lfm.is_file()
            or not qwen_path.is_file() or not runner.is_file()
            or lfm.is_symlink() or qwen_path.is_symlink() or runner.is_symlink()
            or manager.revision("C3_LANGUAGE") != models[MODELS[0]]["revision"]
            or lfm.name != models[MODELS[0]]["local_name"]
            or qwen_path.name != models[MODELS[1]]["local_name"]
            or lfm.stat().st_size != models[MODELS[0]]["size"]
            or qwen_path.stat().st_size != models[MODELS[1]]["size"]
            or file_hash(lfm) != models[MODELS[0]]["sha256"]
            or file_hash(qwen_path) != models[MODELS[1]]["sha256"]
            or file_hash(runner) != RUNNER_SHA):
        raise ValueError("RUN117CV_MODEL_OR_RUNNER_PIN_RED")
    return {MODELS[0]: lfm, MODELS[1]: qwen_path}


def validate_envelopes(rows):
    fixture = frozen.fixtures()
    if (len(rows) != 9 or len(fixture) != 9
            or [r.get("project") for r in rows] != [f["project"] for f in fixture]):
        raise ValueError("RUN117CV_COHORT_RED")
    for row, f in zip(rows, fixture):
        messages = row.get("messages")
        if (row.get("index") != f["index"]
                or row.get("source_sha256") != f["source_sha256"]
                or row.get("source_only") is not True
                or row.get("oracle_visible_to_native") is not False
                or row.get("typed_jef_action_visible") is not False
                or row.get("native_calls") != 0
                or row.get("model_calls") != 0
                or type(messages) is not list or len(messages) != 2
                or [m.get("role") for m in messages] != ["system", "user"]
                or row.get("messages_sha256") != sha(dumps(messages).encode())):
            raise ValueError("RUN117CV_SOURCE_ENVELOPE_RED")
        payload = json.loads(messages[1]["content"])
        if (payload.get("task") != "SOURCE_ONLY_INDEPENDENT_RULE_PROBE"
                or payload.get("typed_jef_action_visible") is not False
                or any(key in payload for key in (
                    "oracle", "expected_action", "suggested_action",
                    "typed_jef_action", "wrong_typed_action_synthetic_only"))
                or any(payload[k]["text"] != f[v] for k, v in (
                    ("current", "current"), ("policy", "policy_source"),
                    ("sheet", "sheet_source")))):
            raise ValueError("RUN117CV_ORACLE_OR_SOURCE_RED")
    return True


def model_order(index):
    return MODELS if index % 2 == 0 else MODELS[::-1]


def summarize(report):
    totals = {name: 0 for name in MODELS}
    gain = loss = 0
    final = reaped = 0
    complete = len(report["rows"]) == 9 and report["native_c3_calls"] == 18
    for row in report["rows"]:
        arms = row.get("arms", [])
        by = {a["model"]: a for a in arms}
        if (len(arms) != 2 or len(by) != 2
                or tuple(a["model"] for a in arms) != model_order(row["index"])
                or row.get("messages_sha256") != arms[0].get("messages_sha256")
                or row.get("messages_sha256") != arms[1].get("messages_sha256")):
            complete = False
        for name in MODELS:
            a = by.get(name, {})
            totals[name] += int(a.get("exact") is True)
            final += int(a.get("native_final") is True)
            reaped += int(a.get("process_reaped") is True)
            if a.get("status") != "RECORDED":
                complete = False
        gain += int(by.get(MODELS[1], {}).get("exact") is True
                    and by.get(MODELS[0], {}).get("exact") is not True)
        loss += int(by.get(MODELS[0], {}).get("exact") is True
                    and by.get(MODELS[1], {}).get("exact") is not True)
    complete = complete and final == reaped == 18 and report.get("pins_unchanged") is True
    report["summary"] = {
        "exact_by_model": totals, "qwen_only_correct": gain,
        "lfm_only_correct": loss, "paired_net": gain - loss,
        "native_final": final, "process_reaped": reaped,
        "complete_native_receipts": bool(complete),
    }
    if not complete:
        return "STRUCTURAL_RED"
    if totals[MODELS[1]] >= 6 and gain - loss >= 3:
        return "EXPLORATORY_CAPACITY_SIGNAL_NON_PROMOTING"
    return "NO_EXPLORATORY_CAPACITY_SIGNAL"


def run(installed, qwen_path, out, runner_factory=LlamaRunner,
        preflight_factory=cu.preflight):
    installed, qwen_path, out = Path(installed), Path(qwen_path), Path(out)
    if out.exists() or not out.parent.is_dir() or out.parent.is_symlink():
        raise FileExistsError("RUN117CV_FRESH_OUTPUT_REQUIRED")
    pins = source_pins()
    paths = pinned_paths(installed, qwen_path)
    preflight = preflight_factory()
    if (preflight.get("status") != "SOURCE_ONLY_MODEL_SWAP_PREFLIGHT_NO_NATIVE"
            or preflight.get("seed") != SEED
            or preflight.get("table_sha256") != frozen.TABLE_SHA256
            or preflight.get("planned_serial_native_calls") != 18
            or preflight.get("native_calls") != 0
            or preflight.get("jepa_weight") != 0):
        raise ValueError("RUN117CV_PREFLIGHT_RED")
    rows = preflight["rows"]
    validate_envelopes(rows)
    out.mkdir(mode=0o700)
    report = {
        "schema": SCHEMA, "status": "RUNNING", "seed": SEED,
        "table_sha256": frozen.TABLE_SHA256, "source_pins": pins,
        "model_pins": preflight["models"],
        "runner_sha256": RUNNER_SHA,
        "native_c3_calls": 0, "rows": [], "pins_unchanged": False,
        "original_failed_attempts_retained": True, **NEGATIVE,
    }
    def save():
        atomic_write(out / "report.json", dumps(report))
    save()
    for row in rows:
        record = {"index": row["index"], "project": row["project"],
                  "source_sha256": row["source_sha256"],
                  "messages_sha256": row["messages_sha256"], "arms": []}
        report["rows"].append(record)
        save()
        for name in model_order(row["index"]):
            arm = {"model": name, "status": "INCOMPLETE",
                   "messages_sha256": row["messages_sha256"],
                   "native_output": "", "native_final": False,
                   "process_reaped": False, "exact": False,
                   "native_metrics": {}, "error_type": None}
            record["arms"].append(arm)
            save()
            runner = None
            proc = None
            try:
                if sha(dumps(row["messages"]).encode()) != row["messages_sha256"]:
                    raise ValueError("RUN117CV_MESSAGES_MUTATED_RED")
                runner = runner_factory(installed, "C3_LANGUAGE", paths[name], CONFIG)
                report["native_c3_calls"] += 1
                save()
                for chunk in runner.generate(
                    row["messages"], threading.Event(),
                    time.monotonic() + 120, 96, run68.SCHEMA, seed=SEED
                ):
                    if type(chunk) is not str:
                        raise TypeError("RUN117CV_NONSTRING_CHUNK_RED")
                    arm["native_output"] += chunk
                    save()  # preserve partial output even if later generation fails
                arm["native_metrics"] = dict(runner.last_metrics)
                arm["native_final"] = arm["native_metrics"].get("status") == "FINAL"
            except BaseException as exc:
                arm["error_type"] = type(exc).__name__
                arm["error"] = str(exc)[:250]
            finally:
                if runner is not None:
                    try:
                        proc = runner.proc
                        arm["release"] = runner.unload()
                        arm["process_reaped"] = (
                            proc is not None and proc.poll() is not None
                            and arm["release"].get("process_reaped") is True)
                    except BaseException as exc:
                        arm["release_error_type"] = type(exc).__name__
                arm["raw_sha256"] = sha(arm["native_output"].encode())
                arm["exact"] = bool(frozen.strict(
                    arm["native_output"],
                    frozen.fixtures()[row["index"]]["expected_for_offline_scorer_only"]))
                arm["status"] = (
                    "RECORDED" if arm["native_final"] and arm["process_reaped"]
                    and arm["native_metrics"].get("actual_model") == paths[name].name
                    and arm["error_type"] is None else "STRUCTURAL_RED")
                save()
    try:
        report["pins_unchanged"] = (
            source_pins() == pins
            and pinned_paths(installed, qwen_path) == paths)
    except (OSError, ValueError):
        report["pins_unchanged"] = False
    report["status"] = summarize(report)
    save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--installed", type=Path, required=True)
    p.add_argument("--qwen", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = run(a.installed, a.qwen, a.out)
    print(dumps({"status": result["status"], "summary": result["summary"],
                 "native_c3_calls": result["native_c3_calls"]}))
    return 0 if result["status"] != "STRUCTURAL_RED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
