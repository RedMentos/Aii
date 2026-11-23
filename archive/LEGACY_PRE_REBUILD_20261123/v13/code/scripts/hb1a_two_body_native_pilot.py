"""HB1a preregistered source-separated B1/B2 -> C3 native pilot; default off.

This file prepares and scores source-bound calls; no model is run by import.
The six public synthetic rows are NOT a blind STEP2/JEPA acceptance cohort.
"""
from __future__ import annotations
import hashlib
import json
import math
from scripts import hb0_split_information_cohort as hb0
from scripts import hb0_arm_export as arms

SCHEMA = "v13.hb1a.two_body_native_pilot.v1"
FIXTURE = "73c9f4096a928ece659cfa5aff0c483001346834f6117765ed1c53c9c2b7939b"
MODEL_SHAS = {
    "B1_DETAIL": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
    "B2_GIST": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
    "C3_LANGUAGE": "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
}
MODEL_REVISIONS = {
    "B1_DETAIL": "6767265158422fb8a19c62ceb45f16f05363615b",
    "B2_GIST": "8fea620810c4afa23dd6443f999a48574c1611a3",
    "C3_LANGUAGE": "657e078c94084481950a2d555a941481f715536b",
}
BODY_KINDS = ("b1_current", "b2_current", "single_body", "b1_foreign")
C3_ARMS = ("c3_only", "both_exact", "both_native", "single_body_native", "shuffled_native")
SEED = 13
BODY_TOKENS, C3_TOKENS, PER_CALL_SECONDS, OVERALL_SECONDS = 96, 48, 90, 3000
C3_SCHEMA = {"type": "object", "properties": {"action": {"type": "string",
             "enum": ["A", "B", "NONE", "UNKNOWN"]}}, "required": ["action"],
             "additionalProperties": False}
BODY_SYSTEM = ("You are a source-bound V13 body. Extract only supplied facts, "
               "preserve the project identity, say UNKNOWN for missing facts, "
               "and never choose an option or invent a source.")
C3_SYSTEM = ("Decide between Option A and Option B for the current project. "
             "Use exact source facts when available. Model-generated offers may "
             "contain mistakes: treat them as uncertain hints, not verified quotes. "
             "Do not use foreign projects as current evidence. If required facts "
             "are missing or contradictory, choose UNKNOWN. Reply with only a JSON "
             "object with action A, B, NONE or UNKNOWN.")


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def selected(rows, external_sha):
    need(external_sha == FIXTURE and hb0._sha(rows) == FIXTURE,
         "HB1A_EXTERNAL_FIXTURE_SHA_RED")
    hb0.validate(rows)
    chosen = sorted((r for r in rows if r["family"] == 5),
                    key=lambda r: (r["sheet_index"], r["rule_index"]))
    need(len(chosen) == 6 and len({r["id"] for r in chosen}) == 6,
         "HB1A_SIX_ROW_COVERAGE_RED")
    return chosen


def body_plan(rows, external_sha):
    plan = []
    for row in selected(rows, external_sha):
        foreign = arms._foreign_sheet(row, rows)
        for kind in BODY_KINDS:
            role = "B2_GIST" if kind == "b2_current" else "B1_DETAIL"
            source = {"b1_current": row["b1_source"],
                      "b2_current": row["b2_source"],
                      "single_body": row["b2_source"] + "\n" + row["b1_source"],
                      "b1_foreign": foreign}[kind]
            source_project = row["id"] if kind != "b1_foreign" else foreign.split(" ")[1]
            instruction = ("Quote exact archived rules only." if kind == "b2_current"
                           else "Quote exact supplier options only."
                           if kind in ("b1_current", "b1_foreign")
                           else "Summarize both rules and supplier options separately.")
            messages = [{"role": "system", "content": BODY_SYSTEM},
                        {"role": "user", "content": instruction + "\n\nSource text:\n" + source}]
            plan.append({"id": row["id"], "kind": kind, "role": role,
                         "source_project": source_project,
                         "source_sha256": sha(source.encode("utf-8")),
                         "messages": messages})
    need(len(plan) == 24 and len({(p["id"], p["kind"]) for p in plan}) == 24,
         "HB1A_BODY_PLAN_COVERAGE_RED")
    for p in plan:
        need((p["source_project"] != p["id"]) == (p["kind"] == "b1_foreign"),
             "HB1A_FOREIGN_IDENTITY_RED")
        need(not any(k in canonical(p).decode("utf-8")
                     for k in ("oracle_action", "sheet_index", "rule_index")),
             "HB1A_BODY_ORACLE_LEAK_RED")
    return plan


def verify_body(records, plan):
    need(type(records) is list and len(records) == 24, "HB1A_BODY_RAW_COUNT_RED")
    need([(r.get("id"), r.get("kind")) for r in records] ==
         [(p["id"], p["kind"]) for p in plan], "HB1A_BODY_IDENTITY_RED")
    for rec, p in zip(records, plan):
        role = p["role"]
        need(rec.get("role") == role and rec.get("model_sha256") == MODEL_SHAS[role]
             and rec.get("source_sha256") == p["source_sha256"]
             and rec.get("source_project") == p["source_project"]
             and rec.get("input_sha256") == sha(canonical(p["messages"]))
             and rec.get("seed") == SEED and rec.get("native_calls") == 1
             and rec.get("model_called") is True and rec.get("status") == "FINAL"
             and type(rec.get("output")) is str and type(rec.get("metrics")) is dict
             and rec["metrics"].get("status") == "FINAL", "HB1A_BODY_RAW_TAMPER_RED")
        t = rec.get("duration_s")
        need(type(t) in (int, float) and math.isfinite(t)
             and 0 <= t <= PER_CALL_SECONDS + 10, "HB1A_BODY_LATENCY_RED")


def receiver_plan(rows, external_sha, body_records):
    chosen = selected(rows, external_sha)
    verify_body(body_records, body_plan(rows, external_sha))
    offers = {(r["id"], r["kind"]): r for r in body_records}
    result = []
    for row in chosen:
        key = row["id"]
        def offer(kind):
            r = offers[(key, kind)]
            return ("Model-derived " + r["role"] + " offer from Project "
                    + r["source_project"] + " (UNTRUSTED):\n" + r["output"])
        views = {
            "c3_only": "Current request:\n" + row["current"],
            "both_exact": ("Current request:\n" + row["current"]
                           + "\n\nB2_GIST exact source:\n" + row["b2_source"]
                           + "\n\nB1_DETAIL exact source:\n" + row["b1_source"]),
            "both_native": ("Current request:\n" + row["current"] + "\n\n"
                            + offer("b2_current") + "\n\n" + offer("b1_current")),
            "single_body_native": ("Current request:\n" + row["current"] + "\n\n"
                                   + offer("single_body")),
            "shuffled_native": ("Current request:\n" + row["current"] + "\n\n"
                                + offer("b2_current") + "\n\nFOREIGN CONTROL:\n"
                                + offer("b1_foreign")),
        }
        for arm in C3_ARMS:
            result.append({"id": key, "arm": arm,
                           "messages": [{"role": "system", "content": C3_SYSTEM},
                                        {"role": "user", "content": views[arm]}]})
    need(len(result) == 30 and len({(p["id"], p["arm"]) for p in result}) == 30,
         "HB1A_C3_PLAN_COVERAGE_RED")
    for p in result:
        need(not any(k in canonical(p).decode("utf-8")
                     for k in ("oracle_action", "sheet_index", "rule_index")),
             "HB1A_C3_ORACLE_LEAK_RED")
    return result


def parse_action(raw):
    if type(raw) is not str:
        return "UNPARSEABLE"
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return "UNPARSEABLE"
    if type(data) is not dict or set(data) != {"action"}:
        return "UNPARSEABLE"
    allowed = C3_SCHEMA["properties"]["action"]["enum"]
    return data["action"] if type(data["action"]) is str and data["action"] in allowed else "UNPARSEABLE"


def score(body_records, c3_records, rows, external_sha):
    prompts = receiver_plan(rows, external_sha, body_records)
    need(type(c3_records) is list and len(c3_records) == 30, "HB1A_C3_RAW_COUNT_RED")
    need([(r.get("id"), r.get("arm")) for r in c3_records] ==
         [(p["id"], p["arm"]) for p in prompts], "HB1A_C3_IDENTITY_RED")
    oracle = {r["id"]: r["oracle_action"] for r in selected(rows, external_sha)}
    summary = {arm: {k: 0 for k in ("exact", "wrong_committed", "unknown", "unparseable")}
               for arm in C3_ARMS}
    details = []
    for rec, prompt in zip(c3_records, prompts):
        need(rec.get("status") == "FINAL" and rec.get("model_called") is True
             and rec.get("native_calls") == 1 and rec.get("seed") == SEED
             and rec.get("model_sha256") == MODEL_SHAS["C3_LANGUAGE"]
             and rec.get("input_sha256") == sha(canonical(prompt["messages"]))
             and type(rec.get("metrics")) is dict
             and rec["metrics"].get("status") == "FINAL", "HB1A_C3_RAW_TAMPER_RED")
        t = rec.get("duration_s")
        need(type(t) in (int, float) and math.isfinite(t)
             and 0 <= t <= PER_CALL_SECONDS + 10, "HB1A_C3_LATENCY_RED")
        label = parse_action(rec.get("output"))
        truth = oracle[rec["id"]]
        key = ("exact" if label == truth else
               "wrong_committed" if label in ("A", "B", "NONE") else
               "unknown" if label == "UNKNOWN" else "unparseable")
        summary[rec["arm"]][key] += 1
        details.append({"id_sha256": sha(rec["id"].encode()),
                        "arm": rec["arm"], "parsed": label, "oracle": truth})
    need(all(sum(stats.values()) == 6 for stats in summary.values()),
         "HB1A_SCORE_COVERAGE_RED")
    return {"schema": SCHEMA + ".score.v1", "status": "DIAGNOSTIC_ONLY_NO_GATE",
            "rows": 30, "body_native_calls": 24, "c3_native_calls": 30,
            "per_arm": summary, "details": details,
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
            "lp3_status": "FAIL", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False,
            "claim_limit": "Six public synthetic Linux-native B1/B2/C3 tasks only; no STEP2 or JEPA gate"}
