#!/usr/bin/env python3
"""Independent P2X calibration native raw/oracle audit; no inference or training."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from scripts import p2x_disjoint_receiver_trainset as cohort

SCHEMA = "v13.p2x.calibration_independent_audit.v1"
FIXTURE_SHA = "cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a"
MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNTIME_SHA = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
BINARY_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
FORMATS = ("original", "instructed")
ARMS = ("c3_only", "b1_only", "b2_only", "both_exact", "shuffled")
LABELS = ("A", "B", "NONE", "UNKNOWN", "UNPARSEABLE")
KINDS = ("exact", "wrong_committed", "unknown", "unparseable")
SEED = 13
SYSTEM = (
    "Return only a JSON object with action A, B, NONE, or UNKNOWN. "
    "Use source facts only for the exact project ID in the current request. "
    "If the B1 option sheet or B2 archived policy is missing, foreign, or inconsistent, return UNKNOWN. "
    "When both matching sources exist, an option qualifies if its first value is at most the policy maximum first, "
    "its second value is at most the policy maximum second, and its flag is true when the policy requires it. "
    "Choose the qualifying option with the smallest first value, then smallest second value, then A before B. "
    "If neither qualifies, return NONE. Never invent source facts."
)


def need(ok, reason):
    if not ok:
        raise ValueError("P2X_CAL_INDEPENDENT_" + reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse(output):
    if type(output) is not str:
        return "UNPARSEABLE"
    try:
        value = json.loads(output)
    except (ValueError, TypeError):
        return "UNPARSEABLE"
    if type(value) is not dict or set(value) != {"action"}:
        return "UNPARSEABLE"
    action = value["action"]
    return action if type(action) is str and action in LABELS[:4] else "UNPARSEABLE"


def reconstruct():
    all_rows = cohort.fixtures()
    need(sha(canonical(all_rows)) == FIXTURE_SHA, "FIXTURE_RED")
    cohort.validate(all_rows)
    selected = sorted((r for r in all_rows if r["partition"] == "calibration"),
                      key=lambda r: r["id"])
    need(len(selected) == 36 and len({r["id"] for r in selected}) == 36,
         "CALIBRATION_RED")
    oracle = {r["id"]: r["oracle_action"] for r in selected}
    need({a: list(oracle.values()).count(a) for a in ("A", "B", "NONE")} ==
         {"A": 12, "B": 12, "NONE": 12}, "ORACLE_BALANCE_RED")
    expected = []
    for row in selected:
        views = cohort.views(row, all_rows)
        for arm in ARMS:
            for fmt in FORMATS:
                messages = ([{"role": "system", "content": SYSTEM}]
                            if fmt == "instructed" else [])
                messages.append({"role": "user", "content": views[arm]})
                expected.append((row["id"], arm, fmt, messages))
    need(len(expected) == 360, "PLAN_COUNT_RED")
    return expected, oracle


def audit_data(inputs, records, score, receipt):
    expected, oracle = reconstruct()
    need(type(inputs) is list and len(inputs) == 360, "INPUT_COUNT_RED")
    need(type(records) is list and len(records) == 360, "RAW_COUNT_RED")
    need(type(score) is dict and type(receipt) is dict, "REPORT_SHAPE_RED")
    counts = {fmt: {arm: {kind: 0 for kind in KINDS} for arm in ARMS}
              for fmt in FORMATS}
    labels = {fmt: {arm: {label: 0 for label in LABELS} for arm in ARMS}
              for fmt in FORMATS}
    details = []
    pairs = {}
    for index, (row, rec, (id_, arm, fmt, messages)) in enumerate(
            zip(inputs, records, expected)):
        need(type(row) is dict and set(row) ==
             {"id", "arm", "format", "messages"}
             and (row["id"], row["arm"], row["format"]) == (id_, arm, fmt)
             and row["messages"] == messages, "INPUT_BINDING_RED")
        need(type(rec) is dict and
             (rec.get("id"), rec.get("arm"), rec.get("format")) ==
             (id_, arm, fmt), "RAW_ORDER_RED")
        duration = rec.get("duration_s")
        need(rec.get("input_sha256") == sha(canonical(messages))
             and rec.get("model_sha256") == MODEL_SHA
             and rec.get("runtime_sha256") == RUNTIME_SHA
             and rec.get("runner_binary_sha256") == BINARY_SHA
             and rec.get("adapter_sha256", "MISSING") is None
             and type(rec.get("seed")) is int and rec["seed"] == SEED
             and rec.get("status") == "FINAL"
             and rec.get("model_called") is True
             and type(rec.get("native_calls")) is int and rec["native_calls"] == 1
             and type(duration) in (int, float) and math.isfinite(duration)
             and 0 <= duration <= 90
             and type(rec.get("metrics")) is dict
             and rec["metrics"].get("status") == "FINAL",
             "RAW_IDENTITY_RED")
        action = parse(rec.get("output"))
        truth = oracle[id_] if arm == "both_exact" else "UNKNOWN"
        kind = ("exact" if action == truth else
                "wrong_committed" if action in ("A", "B", "NONE") else
                "unknown" if action == "UNKNOWN" else "unparseable")
        counts[fmt][arm][kind] += 1
        labels[fmt][arm][action] += 1
        details.append({"id_sha256": sha(id_.encode()), "arm": arm,
                        "format": fmt, "expected": truth,
                        "parsed": action, "kind": kind})
        key = (id_, arm)
        pairs.setdefault(key, {})[fmt] = (action == truth)
    need(len(pairs) == 180 and all(set(x) == set(FORMATS) for x in pairs.values()),
         "PAIRED_COVERAGE_RED")
    paired = {arm: {"improved": 0, "regressed": 0,
                    "both_correct": 0, "both_wrong": 0} for arm in ARMS}
    for (id_, arm), pair in pairs.items():
        old, new = pair["original"], pair["instructed"]
        key = ("both_correct" if old and new else "both_wrong" if not old and not new
               else "improved" if new else "regressed")
        paired[arm][key] += 1
    need(score.get("schema") == "v13.p2x.calibration_instruction.v1.score.v1"
         and score.get("status") == "CALIBRATION_LINUX_NATIVE_DIAGNOSTIC_NO_GATE"
         and score.get("fixture_sha256") == FIXTURE_SHA
         and score.get("model_sha256") == MODEL_SHA
         and score.get("runtime_sha256") == RUNTIME_SHA
         and score.get("runner_binary_sha256") == BINARY_SHA
         and score.get("adapter_sha256", "MISSING") is None
         and type(score.get("rows")) is int and score["rows"] == 360
         and type(score.get("native_calls")) is int and score["native_calls"] == 360
         and score.get("per_arm") == counts
         and score.get("output_labels") == labels
         and score.get("details") == details
         and score.get("step2_status") == "UTILITY_FAIL"
         and score.get("b3_status") == "FAIL"
         and score.get("body_jepa_status") == "UNAVAILABLE"
         and score.get("lp3_status") == "FAIL"
         and type(score.get("jepa_weight")) is int and score["jepa_weight"] == 0
         and score.get("ag6_approved") is False
         and score.get("redmi_measured") is False
         and score.get("whole_system_complete") is False,
         "SCORE_REPLAY_RED")
    need(receipt.get("schema") == "v13.p2x.calibration_instruction_native.v1"
         and receipt.get("status") == "P2X_CALIBRATION_NATIVE_DIAGNOSTIC_NO_GATE"
         and receipt.get("prereg_commit") ==
         "9352843a7ef6fb0eb7cc3307b98f12501e9685c2"
         and receipt.get("expected_calls") == 360
         and receipt.get("recorded_calls") == 360
         and receipt.get("process_reaped") is True
         and receipt.get("model_sha256_before") == MODEL_SHA
         and receipt.get("model_sha256_after") == MODEL_SHA
         and receipt.get("runtime_sha256_before") == RUNTIME_SHA
         and receipt.get("runtime_sha256_after") == RUNTIME_SHA
         and receipt.get("runner_binary_sha256_before") == BINARY_SHA
         and receipt.get("runner_binary_sha256_after") == BINARY_SHA
         and receipt.get("adapter_sha256", "MISSING") is None
         and receipt.get("age_authority") == 0
         and receipt.get("weight_updates") is False
         and receipt.get("ag6_approved") is False
         and type(receipt.get("jepa_weight")) is int and receipt["jepa_weight"] == 0
         and receipt.get("redmi_measured") is False
         and receipt.get("whole_system_complete") is False,
         "RECEIPT_GATE_RED")
    return {"schema": SCHEMA, "status": "INDEPENDENT_RAW_REPLAY_NO_GATE",
            "rows": 360, "native_calls": 360,
            "per_arm": counts, "output_labels": labels, "paired": paired,
            "step2_status": "UTILITY_FAIL", "b3_status": "FAIL",
            "body_jepa_status": "UNAVAILABLE", "lp3_status": "FAIL",
            "jepa_weight": 0, "redmi_measured": False,
            "whole_system_complete": False}


def audit_directory(path):
    root = Path(path)
    need(root.is_dir() and not root.is_symlink(), "DIRECTORY_RED")
    files = {}
    for name in ("INPUTS.json", "RAW.json", "SCORE.json", "RECEIPT.json"):
        file = root / name
        need(file.is_file() and not file.is_symlink(), "FILE_RED")
        files[name] = json.loads(file.read_bytes())
    receipt = files["RECEIPT.json"]
    for name, key in (("INPUTS.json", "inputs_sha256"),
                      ("RAW.json", "raw_sha256"),
                      ("SCORE.json", "score_sha256")):
        need(receipt.get(key) == file_sha(root / name), "FILE_SHA_RED")
    report = audit_data(files["INPUTS.json"], files["RAW.json"],
                        files["SCORE.json"], receipt)
    report["raw_sha256"] = file_sha(root / "RAW.json")
    report["score_sha256"] = file_sha(root / "SCORE.json")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence", type=Path, required=True)
    args = ap.parse_args(argv)
    report = audit_directory(args.evidence)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
