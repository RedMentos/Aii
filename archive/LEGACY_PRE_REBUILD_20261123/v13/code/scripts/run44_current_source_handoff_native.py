#!/usr/bin/env python3
"""Run44 disjoint seed307 serialized Linux-native B2→C3 handoff pilot.

This is a review-only utility experiment. It never changes live Runtime, age,
model weights, original SourceHandoff registrations, or any production gate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import time

from v13.common import atomic_write, dumps, file_hash
from v13.config import DEFAULTS, initialize, save_config
from v13.runtime import Runtime
from tests.integration_step2_utility import installed_artifacts, installed_links

FIXTURE_SHA256 = "9dd92347af6275c8cd687a05aa4f1c63bbf5ba9f84a05af0b4c43e211fc6e530"
ARMS = ("A_CURRENT_ONLY", "B_VERIFIED_B2_TO_C3", "C_RAW_PRIOR_TO_C3")
ORDER = (("A_CURRENT_ONLY", "B_VERIFIED_B2_TO_C3", "C_RAW_PRIOR_TO_C3"),
         ("B_VERIFIED_B2_TO_C3", "C_RAW_PRIOR_TO_C3", "A_CURRENT_ONLY"),
         ("C_RAW_PRIOR_TO_C3", "A_CURRENT_ONLY", "B_VERIFIED_B2_TO_C3"),
         ("A_CURRENT_ONLY", "C_RAW_PRIOR_TO_C3", "B_VERIFIED_B2_TO_C3"))
SYS = ("Use only supplied source text. Do not infer a missing budget or deadline. "
       "Apply earlier project rules if available, otherwise say UNKNOWN. "
       "An option is eligible only if cost <= budget, days <= deadline, and "
       "local if local-only is required. Choose the cheapest eligible option. "
       "If no eligible option exists choose NONE. If budget is missing choose UNKNOWN. "
       "Return only a JSON object with choice and remaining; remaining is null "
       "for NONE or UNKNOWN. No explanation.")
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["choice", "remaining"],
          "properties": {"choice": {"type": "string", "enum": ["A", "B", "NONE", "UNKNOWN"]},
                         "remaining": {"type": ["integer", "null"]}}}
CONFIG = DEFAULTS | {"threads": 2, "temperature": 0., "seed": 13,
                     "observer_mode": "off", "observer_tokens": 160,
                     "observer_seconds": 60, "answer_tokens": 96,
                     "deadline_seconds": 180, "b2_state_slots": 4,
                     "body_residency_mb": 0, "history_turns": 0,
                     "memory_top_k": 0, "teacher_enabled": False,
                     "learning_mode": "RECORD_ONLY", "b2_control": "two_body",
                     "b2_quote_select": "pointer", "offer_quote_context_chars": 200,
                     "b2_offer_body_state": False}
NEGATIVE = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "world_jepa_authority": "SHADOW",
            "redmi_measured": False, "whole_system_complete": False}


def load_fixture(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise ValueError("RUN44_FROZEN_FIXTURE_SHA256")
    data = json.loads(raw)
    if (data.get("schema") != "v13.run44.current_source_handoff_native_seed307.v1"
            or data.get("seed") != 307 or data.get("sampling_seed") != 13
            or data.get("arms") != list(ARMS) or len(data.get("fixtures", [])) != 4):
        raise ValueError("RUN44_FROZEN_COHORT")
    if [f["id"] for f in data["fixtures"]] != ["Quartz", "Amber", "Onyx", "Ivory"]:
        raise ValueError("RUN44_FROZEN_FIXTURE_ORDER")
    for f in data["fixtures"]:
        if (set(f) != {"id", "prior", "current", "oracle"}
                or type(f["prior"]) is not str or type(f["current"]) is not str
                or not f["prior"] or not f["current"]
                or not f["current"].startswith("Project " + f["id"])
                or "budget " in f["current"].lower() and re.search(r"budget\s+\d", f["current"].lower())
                or set(f["oracle"]) != {"choice", "remaining"}):
            raise ValueError("RUN44_FIXTURE_STRUCTURE_OR_LEAK")
    return data


def messages(arm, fixture, analysts=None):
    if arm not in ARMS:
        raise ValueError("RUN44_ARM")
    payload = {"current_source": fixture["current"]}
    if arm == "B_VERIFIED_B2_TO_C3":
        if type(analysts) is not list or not analysts:
            raise ValueError("RUN44_B2_VERIFIED_ANALYSTS_REQUIRED")
        payload["analysts"] = analysts
    elif arm == "C_RAW_PRIOR_TO_C3":
        payload["prior_source"] = fixture["prior"]
    out = [{"role": "system", "content": SYS},
           {"role": "user", "content": dumps(payload)}]
    if "oracle" in dumps(out):
        raise ValueError("RUN44_ORACLE_LEAK")
    return out


def score_answer(raw, oracle):
    try:
        result = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
        if (type(result) is not dict or set(result) != {"choice", "remaining"}
                or result["choice"] not in ("A", "B", "NONE", "UNKNOWN")
                or (result["remaining"] is not None and type(result["remaining"]) is not int)):
            return {"correct": 0, "valid_json": False, "parsed": None}
        return {"correct": int(result == oracle), "valid_json": True, "parsed": result}
    except (ValueError, TypeError, OverflowError):
        return {"correct": 0, "valid_json": False, "parsed": None}


def row_key(row):
    return row["fixture"] + "/" + row["arm"]


def score_rows(rows):
    out = {arm: {"rows": 0, "correct": 0, "structural": 0} for arm in ARMS}
    for row in rows:
        item = out[row["arm"]]
        item["rows"] += 1
        item["correct"] += row["score"]["correct"]
        item["structural"] += int(row["status"] == "RECORDED")
    return out


def pilot_signal(summary):
    if any(summary[a]["rows"] != 4 or summary[a]["structural"] != 4 for a in ARMS):
        return False
    a, b, c = (summary[arm]["correct"] for arm in ARMS)
    return b >= a + 2 and b >= c - 1 and b >= 2


def run_row(home, installed, fixture, arm):
    initialize(home)
    save_config(home, CONFIG)
    installed_links(home, installed)
    r = Runtime(home)
    row = {"fixture": fixture["id"], "arm": arm, "status": "ERROR",
           "prior_sha256": hashlib.sha256(fixture["prior"].encode()).hexdigest(),
           "current_sha256": hashlib.sha256(fixture["current"].encode()).hexdigest(),
           "oracle_visible_to_native": False, "native_answer": "",
           "native_c3_final": False, "native_b2_finals": [],
           "verified_quote_refs": [], "process_releases": [],
           "score": {"correct": 0, "valid_json": False, "parsed": None}}
    start = time.monotonic()
    try:
        if arm == "B_VERIFIED_B2_TO_C3":
            prior = r.store.event(r.session, fixture["prior"])
            row["prior_source_ref"] = prior["source_ref"]
            first = r.cognition.offer("B2_GIST", prior, 0, time.monotonic()+60)
            row["native_b2_finals"].append(first["native_metrics"].get("status") == "FINAL")
            r.pool.unload()
            current = r.store.event(r.session, fixture["current"])
            row["current_source_ref"] = current["source_ref"]
            second = r.cognition.offer("B2_GIST", current, 0, time.monotonic()+60)
            row["native_b2_finals"].append(second["native_metrics"].get("status") == "FINAL")
            analysts = r.cognition.analyst_context([second], current, 0)
            row["verified_quote_refs"] = [q["source_ref"] for a in analysts for q in a["verified_quotes"]]
            row["verified_quote_texts"] = [q["text"] for a in analysts for q in a["verified_quotes"]]
            row["prior_quote_verified"] = any(
                ref["source_id"] == prior["source_ref"]["source_id"]
                and bool(r.store.read_source(ref))
                for ref in row["verified_quote_refs"])
            row["offer_packet_ids"] = [first["packet_id"], second["packet_id"]]
            row["current_event_id"] = current["event_id"]
            r.pool.unload()
            msgs = messages(arm, fixture, analysts)
        else:
            if arm == "C_RAW_PRIOR_TO_C3":
                prior = r.store.event(r.session, fixture["prior"])
                row["prior_source_ref"] = prior["source_ref"]
            current = r.store.event(r.session, fixture["current"])
            row["current_source_ref"] = current["source_ref"]
            row["current_event_id"] = current["event_id"]
            msgs = messages(arm, fixture)
        row["native_prompt_sha256"] = hashlib.sha256(dumps(msgs).encode()).hexdigest()
        row["native_prompt"] = msgs
        runner = r.pool.get("C3_LANGUAGE")
        deadline = time.monotonic() + 90
        row["native_answer"] = "".join(runner.generate(msgs, r.cancel_event, deadline, 96, SCHEMA, seed=13))
        row["native_c3_metrics"] = dict(runner.last_metrics)
        row["native_c3_final"] = runner.last_metrics.get("status") == "FINAL"
        r.pool.unload()
        row["score"] = score_answer(row["native_answer"], fixture["oracle"])
        if (row["native_c3_final"] and all(row["native_b2_finals"])
                and (arm != "B_VERIFIED_B2_TO_C3" or row.get("prior_quote_verified") is True)):
            row["status"] = "RECORDED"
        else:
            row["status"] = "STRUCTURAL_FAIL"
    except (Exception, KeyboardInterrupt) as exc:
        row["error_type"] = type(exc).__name__
        row["error"] = str(exc)[:500]
        row["status"] = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "ERROR"
    finally:
        try:
            r.close()
        except Exception as exc:
            row["close_error_type"] = type(exc).__name__
            row["status"] = "STRUCTURAL_FAIL"
        row["process_releases"] = list(r.pool.release_history)
        row["processes_reaped"] = bool(row["process_releases"]) and all(
            x.get("process_reaped") is True for x in row["process_releases"])
        if row["status"] == "RECORDED" and not row["processes_reaped"]:
            row["status"] = "STRUCTURAL_FAIL"
            row["score"]["correct"] = 0
        if row["status"] != "RECORDED":
            row["score"]["correct"] = 0
        row["elapsed_seconds"] = round(time.monotonic()-start, 3)
    return row


def run(installed, out, fixture_path):
    fixture = load_fixture(fixture_path)
    if out.exists():
        raise FileExistsError("RUN44_EXISTING_OUTPUT_REFUSED")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {"schema": "v13.run44.current_source_handoff_native_result.v1",
              "fixture_sha256": FIXTURE_SHA256, "seed": 307,
              "binding": binding, "registered": True, "rows": [],
              "row_sha256": {}, "status": "RUNNING",
              "negative_gates": NEGATIVE}
    atomic_write(out/"report.json", dumps(report))
    for f, order in zip(fixture["fixtures"], ORDER):
        for arm in order:
            home = out / (f["id"] + "-" + arm)
            if home.exists():
                raise FileExistsError("RUN44_UNFINISHED_HOME_REUSE_REFUSED")
            row = run_row(home, installed, f, arm)
            report["rows"].append(row)
            report["row_sha256"][row_key(row)] = hashlib.sha256(dumps(row).encode()).hexdigest()
            report["summary"] = score_rows(report["rows"])
            atomic_write(out/"report.json", dumps(report))
            print(dumps({"fixture": f["id"], "arm": arm,
                         "status": row["status"], "score": row["score"]["correct"]}), flush=True)
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    report["pilot_signal"] = pilot_signal(report["summary"]) and report["installed_binding_unchanged"]
    report["status"] = ("PILOT_SIGNAL_ONLY_NO_PROMOTION" if report["pilot_signal"]
                        else "UTILITY_FAIL" if all(r["status"] == "RECORDED" for r in report["rows"])
                        else "STRUCTURAL_RED")
    atomic_write(out/"report.json", dumps(report))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    result = run(args.home, args.out, args.fixture)
    print(dumps({"status": result["status"], "summary": result["summary"],
                 "pilot_signal": result["pilot_signal"]}))


if __name__ == "__main__":
    main()
