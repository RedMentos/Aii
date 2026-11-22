"""P0X preregistered 600-call C3 exact/single/foreign source-arm plan/scorer.

No model inference or training by import. Preregistered before C3-only baseline
result; frozen P0X fixture and source strings are not altered.
"""
from __future__ import annotations
import math

from scripts import p0x_independent_source_holdout as p0x
from scripts import p0x_c3_150_baseline as baseline
from scripts import hb1a_two_body_native_pilot as hb1

SCHEMA = "v13.p0x.c3_source_arms.v1"
ARMS = ("b1_only", "b2_only", "both_exact", "shuffled")
FIXTURE_SHA256 = baseline.FIXTURE_SHA256
C3_MODEL_SHA256 = baseline.C3_MODEL_SHA256
RUNNER_SHA256 = baseline.RUNNER_SHA256
SEED = 13
TOKENS = 48
PER_CALL_SECONDS = 90
OVERALL_SECONDS = 2700


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def plan_and_answers():
    rows = p0x.fixtures()
    need(p0x.sha(p0x.canonical(rows)) == FIXTURE_SHA256,
         "P0X_ARMS_FIXTURE_DRIFT_RED")
    inputs, answers = p0x.model_inputs(rows)
    by_key = {(p["id"], p["arm"]): p for p in inputs}
    result = []
    for answer in answers:
        key = answer["id"]
        for arm in ARMS:
            original = by_key[(key, arm)]
            need(len(original["messages"]) == 1
                 and original["messages"][0]["role"] == "user",
                 "P0X_ARMS_SOURCE_VIEW_RED")
            messages = [{"role": "system", "content": hb1.C3_SYSTEM},
                        dict(original["messages"][0])]
            raw = hb1.canonical(messages).decode("utf-8")
            need(not any(term in raw for term in
                         ("oracle_action", "sheet_index", "rule_index",
                          "max_first", "max_second")),
                 "P0X_ARMS_ORACLE_INPUT_RED")
            result.append({"id": key, "arm": arm, "messages": messages,
                           "schema": hb1.C3_SCHEMA})
    need(len(result) == 600 and len({(p["id"], p["arm"]) for p in result}) == 600,
         "P0X_ARMS_COUNT_RED")
    need([result[i]["id"] for i in range(0, 600, 4)] ==
         [a["id"] for a in answers], "P0X_ARMS_ANSWER_ORDER_RED")
    return result, answers


def score(records, plan, answers):
    need(type(records) is list and len(records) == 600,
         "P0X_ARMS_RAW_COUNT_RED")
    need(type(plan) is list and len(plan) == 600
         and type(answers) is list and len(answers) == 150,
         "P0X_ARMS_PLAN_COUNT_RED")
    need([(r.get("id"), r.get("arm")) for r in records] ==
         [(p["id"], p["arm"]) for p in plan],
         "P0X_ARMS_RAW_IDENTITY_RED")
    oracle = {a["id"]: a["oracle_action"] for a in answers}
    summary = {arm: {k: 0 for k in ("exact", "wrong_committed", "unknown", "unparseable")}
               for arm in ARMS}
    labels = {arm: {k: 0 for k in ("A", "B", "NONE", "UNKNOWN", "UNPARSEABLE")}
              for arm in ARMS}
    details = []
    for rec, p in zip(records, plan):
        need(rec.get("status") == "FINAL" and rec.get("model_called") is True
             and rec.get("native_calls") == 1 and rec.get("seed") == SEED
             and rec.get("model_sha256") == C3_MODEL_SHA256
             and rec.get("input_sha256") == hb1.sha(hb1.canonical(p["messages"]))
             and rec.get("schema_sha256") == hb1.sha(hb1.canonical(p["schema"]))
             and type(rec.get("metrics")) is dict
             and rec["metrics"].get("status") == "FINAL",
             "P0X_ARMS_RAW_BINDING_RED")
        duration = rec.get("duration_s")
        need(type(duration) in (int, float) and math.isfinite(duration)
             and 0 <= duration <= PER_CALL_SECONDS + 10,
             "P0X_ARMS_LATENCY_RED")
        label = hb1.parse_action(rec.get("output"))
        truth = oracle[rec["id"]]
        kind = ("exact" if label == truth else
                "wrong_committed" if label in ("A", "B", "NONE") else
                "unknown" if label == "UNKNOWN" else "unparseable")
        summary[rec["arm"]][kind] += 1
        labels[rec["arm"]][label] += 1
        details.append({"id_sha256": hb1.sha(rec["id"].encode()),
                        "arm": rec["arm"], "parsed": label, "oracle": truth})
    need(all(sum(v.values()) == 150 for v in summary.values()),
         "P0X_ARMS_SCORE_COVERAGE_RED")
    return {"schema": SCHEMA + ".score.v1",
            "status": "P0X_NATIVE_SOURCE_ABLATION_DIAGNOSTIC_NO_GATE",
            "rows": 600, "c3_native_calls": 600,
            "per_arm": summary, "output_labels": labels,
            "details": details,
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
            "lp3_status": "FAIL", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False,
            "claim_limit": "Public synthetic exact-source C3 ablation only, not B1/B2 generated offer utility"}


def compare_to_baseline(score_arms, score_baseline):
    need(score_arms.get("schema") == SCHEMA + ".score.v1"
         and score_baseline.get("schema") == baseline.SCHEMA + ".score.v1"
         and score_baseline.get("rows") == 150
         and score_baseline.get("c3_native_calls") == 150
         and score_baseline.get("headroom_sufficient") is True
         and score_baseline.get("oracle_headroom", -1) >= 15,
         "P0X_ARMS_BASELINE_HEADROOM_RED")
    base_exact = score_baseline["per_arm"]["c3_only"]["exact"]
    exact = score_arms["per_arm"]["both_exact"]["exact"]
    need(type(base_exact) is int and type(exact) is int
         and 0 <= base_exact <= 150 and 0 <= exact <= 150,
         "P0X_ARMS_BASELINE_SCORE_RED")
    improvement = exact - base_exact
    return {"schema": SCHEMA + ".comparison.v1",
            "status": "SOURCE_ABLATION_DESCRIPTIVE_NO_GATE",
            "baseline_exact": base_exact, "both_exact": exact,
            "improvement": improvement,
            "threshold": 15, "threshold_met": improvement >= 15,
            "both_exceeds_singles": all(exact > score_arms["per_arm"][arm]["exact"]
                                        for arm in ("b1_only", "b2_only")),
            "shuffled_wrong_committed": score_arms["per_arm"]["shuffled"]["wrong_committed"],
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "redmi_measured": False, "whole_system_complete": False}
