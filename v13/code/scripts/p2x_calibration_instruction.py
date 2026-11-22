#!/usr/bin/env python3
"""P2X 36-ID calibration-only source instruction ablation; no model calls on import."""
from __future__ import annotations

import hashlib
import json
import math
import re

from scripts import hb1a_two_body_native_pilot as hb1
from scripts import p2x_disjoint_receiver_trainset as cohort
from scripts import p2x_native_receiver_eval_scorer as parent

SCHEMA = "v13.p2x.calibration_instruction.v1"
FIXTURE_SHA = "cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a"
MODEL_SHA = parent.MODEL_SHA
RUNTIME_SHA = parent.RUNTIME_SHA
BINARY_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
SEED = 13
FORMATS = ("original", "instructed")
ARMS = cohort.ARMS
SYSTEM = (
    "Return only a JSON object with action A, B, NONE, or UNKNOWN. "
    "Use source facts only for the exact project ID in the current request. "
    "If the B1 option sheet or B2 archived policy is missing, foreign, or inconsistent, return UNKNOWN. "
    "When both matching sources exist, an option qualifies if its first value is at most the policy maximum first, "
    "its second value is at most the policy maximum second, and its flag is true when the policy requires it. "
    "Choose the qualifying option with the smallest first value, then smallest second value, then A before B. "
    "If neither qualifies, return NONE. Never invent source facts."
)
KINDS = ("exact", "wrong_committed", "unknown", "unparseable")
LABELS = ("A", "B", "NONE", "UNKNOWN", "UNPARSEABLE")


def need(ok, reason):
    if not ok:
        raise ValueError("P2X_CAL_" + reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def calibration():
    rows = cohort.fixtures()
    need(sha(canonical(rows)) == FIXTURE_SHA, "FIXTURE_SHA_RED")
    cohort.validate(rows)
    selected = sorted((r for r in rows if r["partition"] == "calibration"),
                      key=lambda r: r["id"])
    need(len(selected) == 36 and len({r["id"] for r in selected}) == 36,
         "CALIBRATION_COVERAGE_RED")
    need(all(sum(r["oracle_action"] == a for r in selected) == 12
             for a in ("A", "B", "NONE")), "CALIBRATION_BALANCE_RED")
    return rows, selected


def plan():
    rows, selected = calibration()
    result = []
    for row in selected:
        view = cohort.views(row, rows)
        for arm in ARMS:
            for fmt in FORMATS:
                messages = ([{"role": "system", "content": SYSTEM}] if fmt == "instructed"
                            else []) + [{"role": "user", "content": view[arm]}]
                need(not any(term in canonical(messages).decode("utf-8")
                             for term in ("oracle_action", "target_action",
                                          "max_first", "max_second")),
                     "PROMPT_ORACLE_LEAK_RED")
                result.append({"id": row["id"], "arm": arm,
                               "format": fmt, "messages": messages})
    need(len(result) == 360
         and len({(p["id"], p["arm"], p["format"]) for p in result}) == 360,
         "PLAN_COUNT_RED")
    for index in range(0, 360, 2):
        original, instructed = result[index:index + 2]
        need(original["format"] == "original" and instructed["format"] == "instructed"
             and original["messages"] == [instructed["messages"][1]]
             and instructed["messages"][0] == {"role": "system", "content": SYSTEM},
             "ONE_FACTOR_RED")
    return result


def score(records, expected_plan=None):
    frozen = plan()
    if expected_plan is not None:
        need(type(expected_plan) is list and expected_plan == frozen,
             "PLAN_TAMPER_RED")
    need(type(records) is list and len(records) == 360, "RAW_COUNT_RED")
    oracle = {r["id"]: r["oracle_action"] for r in calibration()[1]}
    per_arm = {fmt: {arm: {kind: 0 for kind in KINDS} for arm in ARMS}
               for fmt in FORMATS}
    labels = {fmt: {arm: {label: 0 for label in LABELS} for arm in ARMS}
              for fmt in FORMATS}
    details = []
    for rec, prompt in zip(records, frozen):
        need(type(rec) is dict and
             (rec.get("id"), rec.get("arm"), rec.get("format")) ==
             (prompt["id"], prompt["arm"], prompt["format"]), "RAW_ORDER_RED")
        duration = rec.get("duration_s")
        need(rec.get("input_sha256") == sha(canonical(prompt["messages"]))
             and rec.get("model_sha256") == MODEL_SHA
             and rec.get("runtime_sha256") == RUNTIME_SHA
             and rec.get("runner_binary_sha256") == BINARY_SHA
             and rec.get("adapter_sha256", "MISSING") is None
             and type(rec.get("seed")) is int and rec["seed"] == SEED
             and rec.get("status") == "FINAL" and rec.get("model_called") is True
             and type(rec.get("native_calls")) is int and rec["native_calls"] == 1
             and type(duration) in (int, float) and math.isfinite(duration)
             and 0 <= duration <= 90
             and type(rec.get("metrics")) is dict
             and rec["metrics"].get("status") == "FINAL",
             "RAW_BINDING_RED")
        parsed = parent.strict_action(rec.get("output"))
        expected = oracle[rec["id"]] if rec["arm"] == "both_exact" else "UNKNOWN"
        kind = ("exact" if parsed == expected else
                "wrong_committed" if parsed in ("A", "B", "NONE") else
                "unknown" if parsed == "UNKNOWN" else "unparseable")
        per_arm[rec["format"]][rec["arm"]][kind] += 1
        labels[rec["format"]][rec["arm"]][parsed] += 1
        details.append({"id_sha256": sha(rec["id"].encode("utf-8")),
                        "arm": rec["arm"], "format": rec["format"],
                        "expected": expected, "parsed": parsed, "kind": kind})
    need(all(sum(k.values()) == 36 for f in per_arm.values()
             for k in f.values()), "ARM_COVERAGE_RED")
    return {"schema": SCHEMA + ".score.v1",
            "status": "CALIBRATION_LINUX_NATIVE_DIAGNOSTIC_NO_GATE",
            "evidence_kind": "CALIBRATION_ONLY_NOT_BLIND_VALIDATION",
            "fixture_sha256": FIXTURE_SHA, "model_sha256": MODEL_SHA,
            "runtime_sha256": RUNTIME_SHA, "runner_binary_sha256": BINARY_SHA,
            "adapter_sha256": None, "rows": 360, "native_calls": 360,
            "per_arm": per_arm, "output_labels": labels, "details": details,
            "step2_status": "UTILITY_FAIL", "b3_status": "FAIL",
            "body_jepa_status": "UNAVAILABLE", "lp3_status": "FAIL",
            "jepa_weight": 0, "ag6_approved": False,
            "redmi_measured": False, "whole_system_complete": False}


def verify_score(records, snapshot):
    """Independent replay against all raw records and the immutable generator."""
    expected = score(records)
    need(type(snapshot) is dict and canonical(snapshot) == canonical(expected),
         "SCORE_REPLAY_RED")
    return {"status": "CALIBRATION_RAW_SCORE_REPLAY_VERIFIED_NO_GATE",
            "rows": 360, "native_calls": 360,
            "raw_sha256": sha(canonical(records)),
            "score_sha256": sha(canonical(snapshot)),
            "step2_status": "UTILITY_FAIL", "jepa_weight": 0,
            "whole_system_complete": False}
