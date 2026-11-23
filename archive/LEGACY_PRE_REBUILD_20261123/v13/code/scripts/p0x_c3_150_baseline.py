"""P0X preregistered 150 held-out C3-only baseline plan and strict scorer.

No native execution or training by import. Source fixture and model pins frozen
before implementation. Never promote STEP2 from a C3-only baseline.
"""
from __future__ import annotations
import math

from scripts import p0x_independent_source_holdout as p0x
from scripts import hb1a_two_body_native_pilot as hb1

SCHEMA = "v13.p0x.c3_150_baseline.v1"
FIXTURE_SHA256 = "ab03aba600e8085b02247657cc5fb718195e89a83641ef69ad006a27c776647e"
C3_MODEL_SHA256 = hb1.MODEL_SHAS["C3_LANGUAGE"]
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
SEED = 13
TOKENS = 48
PER_CALL_SECONDS = 90
OVERALL_SECONDS = 1680


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def plan_and_answers():
    rows = p0x.fixtures()
    need(p0x.sha(p0x.canonical(rows)) == FIXTURE_SHA256,
         "P0X_BASELINE_FIXTURE_DRIFT_RED")
    prompts, answers = p0x.model_inputs(rows)
    selected = [p for p in prompts if p["arm"] == "c3_only"]
    need(len(selected) == 150 and len(answers) == 150, "P0X_BASELINE_COUNT_RED")
    answer_ids = [a["id"] for a in answers]
    need([p["id"] for p in selected] == answer_ids,
         "P0X_BASELINE_ANSWER_ORDER_RED")
    plan = []
    for p in selected:
        need(len(p["messages"]) == 1 and p["messages"][0]["role"] == "user",
             "P0X_BASELINE_INPUT_VIEW_RED")
        messages = [{"role": "system", "content": hb1.C3_SYSTEM},
                    dict(p["messages"][0])]
        serialized = hb1.canonical(messages).decode("utf-8")
        need(not any(term in serialized for term in
                     ("oracle_action", "sheet_index", "rule_index", "B1 exact source",
                      "B2 exact source", "FOREIGN B1 source", "max_first", "max_second")),
             "P0X_BASELINE_SOURCE_LEAK_RED")
        plan.append({"id": p["id"], "messages": messages,
                     "schema": hb1.C3_SCHEMA})
    need(len({p["id"] for p in plan}) == 150, "P0X_BASELINE_DUPLICATE_RED")
    return plan, answers


def score(records, plan, answers):
    need(type(records) is list and len(records) == 150,
         "P0X_BASELINE_RAW_COUNT_RED")
    need(type(plan) is list and len(plan) == 150
         and type(answers) is list and len(answers) == 150,
         "P0X_BASELINE_PLAN_COUNT_RED")
    need([r.get("id") for r in records] == [p["id"] for p in plan]
         == [a["id"] for a in answers], "P0X_BASELINE_IDENTITY_RED")
    summary = {key: 0 for key in ("exact", "wrong_committed", "unknown", "unparseable")}
    labels = {key: 0 for key in ("A", "B", "NONE", "UNKNOWN", "UNPARSEABLE")}
    details = []
    for rec, p, answer in zip(records, plan, answers):
        need(rec.get("status") == "FINAL" and rec.get("model_called") is True
             and rec.get("native_calls") == 1 and rec.get("seed") == SEED
             and rec.get("model_sha256") == C3_MODEL_SHA256
             and rec.get("input_sha256") == hb1.sha(hb1.canonical(p["messages"]))
             and rec.get("schema_sha256") == hb1.sha(hb1.canonical(p["schema"]))
             and type(rec.get("metrics")) is dict
             and rec["metrics"].get("status") == "FINAL",
             "P0X_BASELINE_RAW_BINDING_RED")
        duration = rec.get("duration_s")
        need(type(duration) in (int, float) and math.isfinite(duration)
             and 0 <= duration <= PER_CALL_SECONDS + 10,
             "P0X_BASELINE_LATENCY_RED")
        label = hb1.parse_action(rec.get("output"))
        truth = answer["oracle_action"]
        need(truth in ("A", "B", "NONE"), "P0X_BASELINE_ORACLE_RED")
        kind = ("exact" if label == truth else
                "wrong_committed" if label in ("A", "B", "NONE") else
                "unknown" if label == "UNKNOWN" else "unparseable")
        summary[kind] += 1
        labels[label] += 1
        details.append({"id_sha256": hb1.sha(rec["id"].encode()),
                        "parsed": label, "oracle": truth})
    need(sum(summary.values()) == 150, "P0X_BASELINE_SCORE_COUNT_RED")
    headroom = 150 - summary["exact"]
    return {"schema": SCHEMA + ".score.v1",
            "status": "P0X_NATIVE_C3_ONLY_HEADROOM_DIAGNOSTIC_NO_GATE",
            "rows": 150, "c3_native_calls": 150,
            "per_arm": {"c3_only": summary}, "output_labels": labels,
            "oracle_software_exact": 150, "oracle_headroom": headroom,
            "headroom_minimum": 15, "headroom_sufficient": headroom >= 15,
            "details": details,
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
            "lp3_status": "FAIL", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False,
            "claim_limit": "Public synthetic C3-only baseline, no B1/B2 complementarity or independent model-native proof"}
