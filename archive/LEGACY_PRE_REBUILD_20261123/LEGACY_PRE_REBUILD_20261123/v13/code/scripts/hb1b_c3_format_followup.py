"""HB1b preregistered C3 output-format follow-up; SOURCE-ONLY plan/scorer.

Posthoc-motivated prospective diagnostic. No model is run by importing this
module. The six public HB1a rows are NOT an independent STEP2 holdout.
Prereg: HB1B_C3_FORMAT_SOURCE_PREREG.md, committed before implementation.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from scripts import hb0_split_information_cohort as hb0
from scripts import hb1a_two_body_native_pilot as hb1
from scripts import hb1a_independent_native_verifier as parent_verify

SCHEMA = "v13.hb1b.c3_format_source_followup.v1"
ARMS = ("exact_schema", "exact_plain", "native_schema", "native_plain")
PARENT_RAW_SHA256 = "abbcacec1217e51dfc592d2e981db9597162b475ca01886151fa99c39a1df7e1"
PARENT_SCORE_SHA256 = "b7ba7c038d420cba7bb78dc62cba0b66ed7d41b50c8f5e7b4f9f85e3697c3c44"
C3_MODEL_SHA256 = hb1.MODEL_SHAS["C3_LANGUAGE"]
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
SEED = 13
TOKENS = 48
PER_CALL_SECONDS = 90
OVERALL_SECONDS = 1800
_FORMAT_OLD = "Reply with only a JSON object with action A, B, NONE or UNKNOWN."
_FORMAT_NEW = "Reply with only A, B, NONE or UNKNOWN."


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def _load_parent(root):
    root = Path(root)
    verified = parent_verify.verify(root)
    need(verified["raw_sha256"] == PARENT_RAW_SHA256
         and verified["score_sha256"] == PARENT_SCORE_SHA256,
         "HB1B_PARENT_RAW_SHA_RED")
    raw = json.loads((root / "RAW.json").read_bytes())
    return raw["body_rows"]


def build(parent_root):
    """Build four source-matched arms per task from verified HB1a native raw."""
    bodies = _load_parent(parent_root)
    rows = hb0.fixtures()
    original = hb1.receiver_plan(rows, hb1.FIXTURE, bodies)
    by_key = {(p["id"], p["arm"]): p for p in original}
    need(hb1.C3_SYSTEM.count(_FORMAT_OLD) == 1, "HB1B_SYSTEM_FORMAT_DRIFT_RED")
    plain_system = hb1.C3_SYSTEM.replace(_FORMAT_OLD, _FORMAT_NEW)
    result = []
    for row in hb1.selected(rows, hb1.FIXTURE):
        key = row["id"]
        for arm in ARMS:
            source = "both_exact" if arm.startswith("exact") else "both_native"
            base = by_key[(key, source)]
            messages = [dict(m) for m in base["messages"]]
            need(messages[0] == {"role": "system", "content": hb1.C3_SYSTEM}
                 and messages[1]["role"] == "user",
                 "HB1B_SOURCE_VIEW_RED")
            if arm.endswith("plain"):
                messages[0]["content"] = plain_system
            result.append({"id": key, "arm": arm, "messages": messages,
                           "schema": hb1.C3_SCHEMA if arm.endswith("schema") else None})
    need(len(result) == 24 and len({(x["id"], x["arm"]) for x in result}) == 24,
         "HB1B_COVERAGE_RED")
    for row in hb1.selected(rows, hb1.FIXTURE):
        key = row["id"]
        matched = {x["arm"]: x for x in result if x["id"] == key}
        need(matched["exact_schema"]["messages"][1] == matched["exact_plain"]["messages"][1]
             and matched["native_schema"]["messages"][1] == matched["native_plain"]["messages"][1],
             "HB1B_SOURCE_FORMAT_PAIR_DRIFT_RED")
    for p in result:
        payload = hb1.canonical(p).decode("utf-8")
        need(not any(term in payload for term in ("oracle_action", "sheet_index", "rule_index")),
             "HB1B_ORACLE_INPUT_RED")
    return result


def parse(raw, arm):
    need(arm in ARMS, "HB1B_ARM_RED")
    if arm.endswith("schema"):
        return hb1.parse_action(raw)
    if type(raw) is not str:
        return "UNPARSEABLE"
    value = raw.strip()
    return value if value in hb1.C3_SCHEMA["properties"]["action"]["enum"] else "UNPARSEABLE"


def score(records, plan):
    need(type(records) is list and len(records) == 24, "HB1B_RAW_COUNT_RED")
    need(type(plan) is list and len(plan) == 24, "HB1B_PLAN_COUNT_RED")
    need([(r.get("id"), r.get("arm")) for r in records] ==
         [(p["id"], p["arm"]) for p in plan], "HB1B_RAW_IDENTITY_RED")
    oracle = {r["id"]: r["oracle_action"] for r in hb1.selected(hb0.fixtures(), hb1.FIXTURE)}
    summary = {arm: {k: 0 for k in ("exact", "wrong_committed", "unknown", "unparseable")}
               for arm in ARMS}
    labels = {arm: {k: 0 for k in ("A", "B", "NONE", "UNKNOWN", "UNPARSEABLE")}
              for arm in ARMS}
    details = []
    for rec, prompt in zip(records, plan):
        need(rec.get("status") == "FINAL" and rec.get("model_called") is True
             and rec.get("native_calls") == 1 and rec.get("seed") == SEED
             and rec.get("model_sha256") == C3_MODEL_SHA256
             and rec.get("input_sha256") == hb1.sha(hb1.canonical(prompt["messages"]))
             and rec.get("schema_sha256") ==
                 (hb1.sha(hb1.canonical(prompt["schema"])) if prompt["schema"] else None)
             and type(rec.get("metrics")) is dict
             and rec["metrics"].get("status") == "FINAL",
             "HB1B_RAW_BINDING_RED")
        duration = rec.get("duration_s")
        need(type(duration) in (int, float) and math.isfinite(duration)
             and 0 <= duration <= PER_CALL_SECONDS + 10, "HB1B_LATENCY_RED")
        label = parse(rec.get("output"), rec["arm"])
        truth = oracle[rec["id"]]
        kind = ("exact" if label == truth else
                "wrong_committed" if label in ("A", "B", "NONE") else
                "unknown" if label == "UNKNOWN" else "unparseable")
        summary[rec["arm"]][kind] += 1
        labels[rec["arm"]][label] += 1
        details.append({"id_sha256": hb1.sha(rec["id"].encode()),
                        "arm": rec["arm"], "parsed": label, "oracle": truth})
    need(all(sum(v.values()) == 6 for v in summary.values()), "HB1B_SCORE_COVERAGE_RED")
    return {"schema": SCHEMA + ".score.v1", "status": "POSTHOC_MOTIVATED_NEW_NATIVE_DIAGNOSTIC_NO_GATE",
            "rows": 24, "c3_native_calls": 24, "per_arm": summary,
            "output_labels": labels, "details": details,
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
            "lp3_status": "FAIL", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False,
            "claim_limit": "Six reused public synthetic tasks; format/source diagnostic only, not independent holdout"}
