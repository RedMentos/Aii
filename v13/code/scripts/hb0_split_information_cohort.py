"""HB0/P0: deterministic split-information structural cohort (NOT native utility).

Registered before implementation in HB0_SPLIT_INFORMATION_COHORT_PREREG.md.
The generator is deliberately public/synthetic and may not be treated as a
blind model holdout. No model inference, training, runtime activation or gate
promotion. An independent fresh model cohort is required for P0 acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path

from scripts import context_option_safe_scope_candidate as safe
from v13.agi.eligibility import recipe

SCHEMA = "v13.hb0.split_information_structural.v1"
SEED = 20261029
FAMILIES = 25
# Fixed 2x3 counterfactual grid; outcomes by row:
# sheet 0: NONE, NONE, B; sheet 1: B, A, A.
# Thus every rule column requires the sheet, and each sheet requires rules.
SHEETS = (
    ((45, 6, False), (35, 6, True)),
    ((35, 4, True), (55, 2, False)),
)
RULES = (
    (60, 3, False),
    (60, 5, False),
    (70, 7, True),
)
ACTIONS = ("A", "B", "NONE")


def _tf(value):
    return str(value).lower()


def _sha(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _rule_text(rule):
    return (f"Budget {rule[0]} euros. Deadline {rule[1]} days. "
            f"Local-only requirement: {_tf(rule[2])}.")


def _option_text(options):
    return " ".join(
        f"Option {entity}: cost {o[0]} euros, duration {o[1]} days, "
        f"local {_tf(o[2])}."
        for entity, o in zip("AB", options)
    )


def _row(family, sheet_index, rule_index):
    # Add the same offset to all budgets and costs. The entire 2x3
    # counterfactual decision matrix remains unchanged across families.
    shift = 3 * family
    # Opaque per-world identity: never encode sheet/rule axes in the prompt.
    # Public synthetic IDs are NOT a blind held-out evaluation key.
    digest = hashlib.sha256(f"{SEED}|{family}|{sheet_index}|{rule_index}".encode("ascii")).hexdigest()[:14]
    project = "HB0" + digest.upper()
    rule = RULES[rule_index]
    rule = (rule[0] + shift, rule[1], rule[2])
    options = tuple((o[0] + shift, o[1], o[2])
                    for o in SHEETS[sheet_index])
    b2 = f"Project {project} kickoff notes. " + _rule_text(rule)
    b1 = f"Project {project} supplier sheet. " + _option_text(options)
    # Conflicting, separately identified material is present in full history
    # to exercise the identity firewall; never visible to the split bodies.
    foreign = (
        f"Project Archive{family:02d} supplier notes. "
        + _rule_text((rule[0] + 99, rule[1] + 3, not rule[2]))
        + " " + _option_text(((1, 1, True), (2, 1, True)))
    )
    current = (f"Project {project}. Decide between Option A and Option B "
               "using the archived project rules and latest supplier sheet.")
    option_dicts = [
        {"entity": entity, "cost": o[0], "days": o[1], "local": o[2]}
        for entity, o in zip("AB", options)
    ]
    action, _ = recipe(*rule, option_dicts)
    return {
        "id": project, "family": family, "sheet_index": sheet_index,
        "rule_index": rule_index,
        "partition": "calibration" if family < 5 else "structural_holdout",
        "current": current,
        "b1_source": b1, "b2_source": b2,
        "foreign_distractor": foreign,
        "history": [b2, foreign, b1],
        "rules": {"budget": rule[0], "deadline": rule[1],
                  "local_only": rule[2]},
        "options": option_dicts,
        "oracle_action": action,
    }


def fixtures():
    rows = [_row(f, s, r) for f in range(FAMILIES)
            for s in range(2) for r in range(3)]
    random.Random(SEED).shuffle(rows)
    return rows


def validate(rows):
    """Fail closed on broken source separation, counterfactuals or oracle.

    Checks the default-off source parser only as a software control; never
    interprets it as model performance or native STEP2 evidence.
    """
    if type(rows) not in (list, tuple) or len(rows) != 150:
        raise ValueError("HB0_COUNT_RED")
    ids = [r.get("id") for r in rows]
    if any(type(i) is not str for i in ids) or len(set(ids)) != 150:
        raise ValueError("HB0_ID_RED")
    expected = {_row(f, s, ri)["id"]: _row(f, s, ri)
                for f in range(FAMILIES) for s in range(2) for ri in range(3)}
    if set(ids) != set(expected):
        raise ValueError("HB0_COVERAGE_RED")
    count = {a: 0 for a in ACTIONS}
    grid = {}
    for row in rows:
        if row != expected[row["id"]]:
            raise ValueError("HB0_SOURCE_OR_ORACLE_TAMPER_RED")
        current = row["current"]
        if re.search(r"\b(?:budget|deadline|cost|duration|local-only|local\s+(?:true|false))\b",
                     current, re.I):
            raise ValueError("HB0_CURRENT_LEAK_RED")
        if row["b1_source"] not in row["history"] or row["b2_source"] not in row["history"]:
            raise ValueError("HB0_SOURCE_MISSING_RED")
        if safe.decide_safe(current, [])["action"] != "UNKNOWN":
            raise ValueError("HB0_CURRENT_ONLY_COMMIT_RED")
        if safe.decide_safe(current, [row["b1_source"]])["action"] != "UNKNOWN":
            raise ValueError("HB0_B1_ONLY_COMMIT_RED")
        if safe.decide_safe(current, [row["b2_source"]])["action"] != "UNKNOWN":
            raise ValueError("HB0_B2_ONLY_COMMIT_RED")
        if safe.decide_safe(current, [row["foreign_distractor"]])["action"] != "UNKNOWN":
            raise ValueError("HB0_FOREIGN_LEAK_RED")
        if safe.decide_safe(current, [row["foreign_distractor"], row["b1_source"]])["action"] != "UNKNOWN":
            raise ValueError("HB0_MISSING_B2_LEAK_RED")
        if safe.decide_safe(current, [row["b2_source"], row["foreign_distractor"]])["action"] != "UNKNOWN":
            raise ValueError("HB0_MISSING_B1_LEAK_RED")
        got = safe.decide_safe(current, row["history"])
        if got["action"] != row["oracle_action"]:
            raise ValueError("HB0_FULL_SOURCE_CONTROL_RED")
        rule = row["rules"]
        oracle, _ = recipe(rule["budget"], rule["deadline"],
                           rule["local_only"], row["options"])
        if oracle != row["oracle_action"]:
            raise ValueError("HB0_ORACLE_RED")
        count[oracle] += 1
        grid[(row["family"], row["sheet_index"], row["rule_index"])] = oracle
    if count != {"A": 50, "B": 50, "NONE": 50}:
        raise ValueError("HB0_BALANCE_RED")
    for f in range(FAMILIES):
        matrix = [[grid[(f, s, r)] for r in range(3)] for s in range(2)]
        if (sorted(matrix[0] + matrix[1]) != sorted(["A", "A", "B", "B", "NONE", "NONE"])
                or any(matrix[0][r] == matrix[1][r] for r in range(3))
                or any(len(set(row)) < 2 for row in matrix)):
            raise ValueError("HB0_COUNTERFACTUAL_RED")
    return {"rows": 150, "families": FAMILIES, "action_counts": count,
            "calibration_rows": 30, "structural_holdout_rows": 120,
            "complete_source_parser_matches": 150,
            "single_view_committed": 0, "foreign_only_committed": 0}


def inspect():
    rows = fixtures()
    checks = validate(rows)
    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_STRUCTURAL_READY_NO_GATE",
        "evidence_kind": "SOFTWARE_SYNTHETIC_NO_MODEL",
        "seed": SEED, "fixture_sha256": _sha(rows),
        "checks": checks, "fixtures": rows,
        "native_calls": 0, "model_called": False,
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "b3_status": "FAIL", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "claim_limit": "No measured C3 baseline, B1/B2 complementarity, or blind native holdout",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    if args.out.exists():
        raise FileExistsError("FRESH_HB0_EVIDENCE_REQUIRED")
    report = inspect()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["checks"],
                      "fixture_sha256": report["fixture_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
