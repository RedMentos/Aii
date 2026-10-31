#!/usr/bin/env python3
"""Run115J disjoint seed997: exact-source typed JEF -> C3 user-role formatter.

No native B1/B2/JEF/C2, output delivery, tool dispatch or learning authority.
Original Run115I NO_GAIN, Run115C RED and all frozen earlier cohorts remain.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

from v13.common import atomic_write, dumps, file_hash
from v13.config import DEFAULTS
from v13.models import ModelManager
from v13.runtime import Runtime
from v13.store import audit_closed
from v13.two_source_c3_role_boundary_candidate import (
    SYSTEM, build_role_separated_c3_shadow,
)
from v13.jef_two_source_role_formatter_candidate import build_typed_jef_role_formatter
from scripts.run111_c3_b2_context_native import _prepare_home
from scripts.run113b_b1b2_c3_native import _reaped
from scripts.run47_jef_c3_typed_receiver_native import score

SEED = 997
FIXTURE_SHA = "3cfe98d4903aaef56dd412ad426d743941fa0115b346cdf77d9abeaf2fbeb2a0"
IDS = ("Kairo", "Lythos", "Oxara", "Perrin", "Sereon", "Valtor")
EXPECTED = (("A", 10), ("B", 60), ("NONE", None),
            ("A", 40), ("B", 30), ("NONE", None))
ARMS = ("RAW_SOURCE_ROLE", "TYPED_JEF_ROLE")
C3_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
C3_REV = "657e078c94084481950a2d555a941481f715536b"
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
C3_FILE = "LFM2.5-350M-QAD-Q4_0.gguf"
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["choice", "remaining"],
          "properties": {
              "choice": {"type": "string", "enum": ["A", "B", "NONE"]},
              "remaining": {"type": ["integer", "null"]}}}
TASK = (
    "Evaluate the exact earlier project constraints against the current "
    "options. Select the cheapest eligible option meeting maximum budget, "
    "deadline and local-only requirement. Return only a JSON object with "
    "choice A, B or NONE and remaining budget as an integer, or null for NONE. "
    "If the earlier policy is missing, do not assume constraints or invent "
    "missing facts. No tools, actions or live output are authorized."
)
CONFIG = DEFAULTS | {
    "threads": 2, "temperature": 0.0, "seed": SEED,
    "observer_mode": "off", "answer_tokens": 96,
    "deadline_seconds": 120, "observer_seconds": 30,
    "body_residency_mb": 0, "history_turns": 0,
    "memory_top_k": 0, "teacher_enabled": False,
    "learning_mode": "RECORD_ONLY",
}


def fixture(path):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError("RUN115J_FROZEN_FIXTURE_SHA_RED")
    data = json.loads(raw)
    if (set(data) != {"schema", "seed", "arms", "rows"}
            or data["schema"] != "v13.run115j.typed_jef_role_seed997.v1"
            or type(data["seed"]) is not int or data["seed"] != SEED
            or data["arms"] != list(ARMS)
            or type(data["rows"]) is not list or len(data["rows"]) != 6
            or [r.get("id") for r in data["rows"]] != list(IDS)
            or [(r.get("oracle", {}).get("choice"),
                 r.get("oracle", {}).get("remaining"))
                for r in data["rows"]] != list(EXPECTED)):
        raise ValueError("RUN115J_FROZEN_COHORT_RED")
    for row in data["rows"]:
        if (set(row) != {"id", "prior", "current", "oracle"}
                or not row["prior"].startswith("Project " + row["id"] + ".")
                or not row["current"].startswith("Project " + row["id"] + ".")
                or "oracle" in row["prior"].lower()
                or "oracle" in row["current"].lower()):
            raise ValueError("RUN115J_SOURCE_SHAPE_RED")
    return data["rows"]


def _pin_c3(installed):
    m = ModelManager(installed)
    if (file_hash(m.path_for("C3_LANGUAGE")) != C3_SHA
            or m.revision("C3_LANGUAGE") != C3_REV
            or file_hash(installed / "bin/llama-server") != RUNNER_SHA):
        raise ValueError("RUN115J_C3_MODEL_OR_RUNNER_PIN_RED")


def _prompts(runtime, prior, current, row):
    raw = build_role_separated_c3_shadow(
        runtime, prior, current, operator_opt_in=True)
    typed = build_typed_jef_role_formatter(
        runtime, prior, current, operator_opt_in=True)
    refs = [prior["source_ref"], current["source_ref"]]
    if (raw.get("status") != "SHADOW_C3_DATA_ROLE_BOUNDARY_VERIFIED"
            or typed.get("status") != "SHADOW_TYPED_JEF_ROLE_FORMATTER_VERIFIED"
            or raw.get("source_refs") != refs or typed.get("source_refs") != refs
            or raw.get("applied") is not False or typed.get("applied") is not False
            or raw.get("delivery_authority") != 0
            or typed.get("delivery_authority") != 0
            or typed.get("learning_authority") != 0
            or typed.get("native_jef_calls") != 0
            or typed.get("typed_jef_candidate") != row["oracle"]):
        raise ValueError("RUN115J_BOUNDARY_OR_JEF_ORACLE_RED")
    raw_messages = [
        {"role": "system", "content": SYSTEM + "\n" + TASK},
        {"role": "user", "content": raw["messages"][1]["content"]},
    ]
    typed_messages = typed["messages"]
    prompts = {ARMS[0]: raw_messages, ARMS[1]: typed_messages}
    for arm, messages in prompts.items():
        if ([m["role"] for m in messages] != ["system", "user"]
                or row["prior"] in messages[0]["content"]
                or row["current"] in messages[0]["content"]
                or '"oracle"' in dumps(messages)
                or '"expected"' in dumps(messages)
                or row["prior"] not in messages[1]["content"]
                or row["current"] not in messages[1]["content"]):
            raise ValueError("RUN115J_ROLE_OR_ORACLE_LEAK_RED_" + arm)
        payload = json.loads(messages[1]["content"])
        if arm == ARMS[1]:
            if (payload.get("typed_jef_candidate") != row["oracle"]
                    or payload.get("typed_candidate_authority") != 0):
                raise ValueError("RUN115J_TYPED_CANDIDATE_RED")
        elif "typed_jef_candidate" in payload:
            raise ValueError("RUN115J_TYPED_LEAK_TO_RAW_RED")
    return prompts, [raw["context_plan_packet_id"],
                     typed["context_plan_packet_id"]], typed["typed_jef_candidate"]

def _run_row(row, index, work, report, save, installed):
    native = installed is not None
    home = work / row["id"]
    _prepare_home(home, installed, CONFIG)
    runtime = Runtime(home)
    entry = {"id": row["id"], "status": "INCOMPLETE", "arms": [],
             "closed_store_ok": False, "no_live_output": False}
    report["rows"].append(entry)
    save()
    try:
        prior = runtime.store.event(runtime.session, row["prior"])
        current = runtime.store.event(runtime.session, row["current"])
        entry["source_refs"] = [prior["source_ref"], current["source_ref"]]
        prompts, entry["context_plan_packet_ids"], entry["typed_jef_candidate"] = _prompts(
            runtime, prior, current, row)
        order = ARMS if index % 2 == 0 else ARMS[::-1]
        for arm in order:
            messages = prompts[arm]
            item = {"arm": arm, "status": "INCOMPLETE",
                    "messages": messages,
                    "messages_sha256": sha256(dumps(messages).encode()).hexdigest(),
                    "native_final": False, "process_reaped": False,
                    "score": None}
            entry["arms"].append(item)
            save()
            if native:
                before = len(runtime.pool.release_history)
                try:
                    runner = runtime.pool.get("C3_LANGUAGE")
                    report["native_c3_calls"] += 1
                    save()
                    output = "".join(runner.generate(
                        messages, runtime.cancel_event, time.monotonic() + 90,
                        96, SCHEMA, seed=SEED))
                    item["output"] = output
                    item["native_metrics"] = dict(runner.last_metrics)
                    item["score"] = score(output, row["oracle"])
                    item["native_final"] = (
                        item["native_metrics"].get("status") == "FINAL")
                finally:
                    runtime.pool.unload()
                    item["process_reaped"] = _reaped(
                        runtime.pool.release_history[before:])
                    save()
                item["status"] = (
                    "RECORDED" if item["native_final"] and
                    item["process_reaped"] and
                    item["native_metrics"].get("actual_model") == C3_FILE
                    else "STRUCTURAL_RED")
                if item["status"] != "RECORDED":
                    raise ValueError("RUN115J_NATIVE_FINAL_OR_REAP_RED")
            else:
                item["status"] = "MODEL_FREE_PROMPT_VERIFIED"
            save()
        entry["status"] = "RECORDED" if native else "MODEL_FREE_PREFLIGHT_PASS"
    except Exception as exc:
        entry["status"] = "STRUCTURAL_RED"
        entry["error_type"] = type(exc).__name__
        entry["error"] = str(exc)[:320]
    finally:
        try:
            entry["no_live_output"] = (
                runtime.store.one(
                    "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                    "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0
                and runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0)
        except Exception:
            entry["no_live_output"] = False
        runtime.close()
        try:
            entry["closed_store_ok"] = bool(audit_closed(home)["ok"])
        except Exception:
            entry["closed_store_ok"] = False
        if not entry["closed_store_ok"] or not entry["no_live_output"]:
            entry["status"] = "STRUCTURAL_RED"
        save()


def run(fixture_path, work, out, *, installed=None):
    rows = fixture(fixture_path)
    work, out = Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError("RUN115J_FRESH_WORK_AND_REPORT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    native = installed is not None
    installed = Path(installed).resolve() if native else None
    report = {
        "schema": "v13.run115j.typed_jef_role_native.v1",
        "seed": SEED, "fixture_sha256": FIXTURE_SHA,
        "status": "INCOMPLETE", "native": native,
        "native_c3_calls": 0, "native_b1_calls": 0, "native_b2_calls": 0,
        "native_jef_calls": 0,
        "native_c2": False, "native_jef": False,
        "rows": [], "scores": {arm: 0 for arm in ARMS},
        "exploratory_role_signal": False,
        "age0": "RECORD_ONLY", "step2_exit": "EVIDENCE_NOT_PASSING",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "output_committed": False, "tool_dispatches": 0,
        "learning_authority": 0, "delivery_authority": 0,
    }
    path = out / "report.json"
    def save():
        atomic_write(path, dumps(report))
    save()
    try:
        if native:
            _pin_c3(installed)
        for i, row in enumerate(rows):
            _run_row(row, i, work, report, save, installed)
        structural = len(report["rows"]) == 6 and all(
            r["status"] == ("RECORDED" if native else "MODEL_FREE_PREFLIGHT_PASS")
            and r["closed_store_ok"] and r["no_live_output"]
            and len(r["arms"]) == 2
            and set(x["arm"] for x in r["arms"]) == set(ARMS)
            and all(x["status"] ==
                    ("RECORDED" if native else "MODEL_FREE_PROMPT_VERIFIED")
                    for x in r["arms"])
            for r in report["rows"])
        if not structural:
            report["status"] = "STRUCTURAL_RED"
        elif not native:
            report["status"] = "MODEL_FREE_SIX_CASE_PREFLIGHT_PASS"
        else:
            for row in report["rows"]:
                for arm in row["arms"]:
                    report["scores"][arm["arm"]] += arm["score"]["correct"]
            full = report["scores"][ARMS[1]]
            control = report["scores"][ARMS[0]]
            none_rows = [r for r in report["rows"]
                         if r["id"] in ("Oxara", "Valtor")]
            no_false_none = all(
                next(a for a in r["arms"] if a["arm"] == ARMS[1])
                ["score"]["parsed"] in (
                    {"choice": "NONE", "remaining": None}, None)
                for r in none_rows)
            report["exploratory_role_signal"] = (
                full >= 5 and full - control >= 2 and no_false_none)
            report["status"] = (
                "NATIVE_COMPLETE_TYPED_SIGNAL" if report["exploratory_role_signal"]
                else "NATIVE_COMPLETE_NO_GAIN")
    except Exception as exc:
        report["status"] = "STRUCTURAL_RED"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:320]
    save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--installed", type=Path)
    a = p.parse_args()
    result = run(a.fixture, a.work, a.out, installed=a.installed)
    print(dumps({"status": result["status"], "rows": len(result["rows"]),
                 "native_c3_calls": result["native_c3_calls"],
                 "scores": result["scores"],
                 "exploratory_role_signal": result["exploratory_role_signal"]}))
    return 0 if result["status"] in (
        "MODEL_FREE_SIX_CASE_PREFLIGHT_PASS",
        "NATIVE_COMPLETE_TYPED_SIGNAL",
        "NATIVE_COMPLETE_NO_GAIN") else 2


if __name__ == "__main__":
    raise SystemExit(main())
