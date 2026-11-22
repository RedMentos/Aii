"""P0X preregistered 150 held-out split-source structural cohort, software only.

Five domain renderers, 30 families (five calibration + 25 holdout), six
counterfactual tasks per family. No model inference or training by import.
Prereg committed BEFORE implementation: P0X_150_SOURCE_HOLDOUT_PREREG.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re

SCHEMA = "v13.p0x.150_source_holdout.v1"
SEED = 2026102907
BASE_SHEETS = (
    ((15, 8, True), (85, 4, False)),
    ((65, 5, True), (40, 4, True)),
)
BASE_RULES = ((30, 10, True), (80, 10, False), (55, 6, True))
DOMAINS = (
    ("procurement", "cost", "euros", "lead time", "days", "local"),
    ("compute deployment", "RAM", "MB", "startup latency", "ms", "on-device"),
    ("shipping", "shipment weight", "kg", "transit", "hours", "refrigerated"),
    ("laboratory", "power draw", "watts", "setup time", "minutes", "certified"),
    ("archive", "storage", "GB", "retrieval time", "seconds", "offline"),
)
ARMS = ("c3_only", "b1_only", "b2_only", "both_exact", "shuffled")
ACTIONS = ("A", "B", "NONE", "UNKNOWN")


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _tf(value):
    return "true" if value else "false"


def _oracle(rule, options):
    budget, deadline, required = rule
    eligible = [(o[0], o[1], name) for name, o in zip("AB", options)
                if o[0] <= budget and o[1] <= deadline
                and (not required or o[2])]
    return min(eligible)[2] if eligible else "NONE"


def _project(family, sheet, rule):
    digest = sha(f"{SEED}|{family}|{sheet}|{rule}".encode("ascii"))[:16].upper()
    return "P0X" + digest


def _row(family, sheet, rule):
    need(0 <= family < 30 and sheet in (0, 1) and rule in (0, 1, 2),
         "P0X_GRID_INDEX_RED")
    domain = DOMAINS[family // 6]
    domain_name, a1, u1, a2, u2, flag = domain
    # Independent permutations and label swap hide grid position from model.
    s = (sheet + ((family // 2) % 2)) % 2
    ri = (rule + family % 3) % 3
    shift = 7 * (family + 1)
    time_shift = family % 3
    options = tuple((o[0] + shift, o[1] + time_shift, o[2])
                    for o in BASE_SHEETS[s])
    if family % 2:
        options = options[::-1]
    base = BASE_RULES[ri]
    policy = (base[0] + shift, base[1] + time_shift, base[2])
    project = _project(family, sheet, rule)
    current = (f"Project {project}. Choose Option A or Option B using the "
               f"archived {domain_name} policy and latest option sheet. "
               "If neither qualifies, choose NONE.")
    b2 = (f"Project {project} archived {domain_name} policy. "
          f"Maximum {a1}: {policy[0]} {u1}. "
          f"Maximum {a2}: {policy[1]} {u2}. "
          f"Required {flag}: {_tf(policy[2])}.")
    def option_text(name, option):
        return (f"Option {name}: {a1} {option[0]} {u1}; "
                f"{a2} {option[1]} {u2}; {flag} {_tf(option[2])}.")
    b1 = (f"Project {project} latest {domain_name} option sheet. "
          + " ".join(option_text(name, opt) for name, opt in zip("AB", options)))
    return {"id": project, "family": family, "domain": domain_name,
            "sheet_index": sheet, "rule_index": rule,
            "partition": "calibration" if family % 6 == 0 else "holdout",
            "current": current, "b1_source": b1, "b2_source": b2,
            "rule": {"max_first": policy[0], "max_second": policy[1],
                     "require_flag": policy[2]},
            "options": {name: {"first": opt[0], "second": opt[1], "flag": opt[2]}
                        for name, opt in zip("AB", options)},
            "oracle_action": _oracle(policy, options)}


def fixtures():
    rows = [_row(f, s, r) for f in range(30)
            for s in range(2) for r in range(3)]
    random.Random(SEED).shuffle(rows)
    return rows


def foreign_sheet(row, rows):
    target_family = (row["family"] + 6) % 30
    matched = [r for r in rows if r["family"] == target_family
               and r["sheet_index"] == row["sheet_index"]
               and r["rule_index"] == row["rule_index"]]
    need(len(matched) == 1 and matched[0]["id"] != row["id"],
         "P0X_FOREIGN_IDENTITY_RED")
    return matched[0]["b1_source"]


def _source_project(text):
    m = re.match(r"^Project (P0X[0-9A-F]{16})\b", text)
    return m.group(1) if m else None


def decide_sources(current, sources):
    """Independent text parser, deterministic oracle CONTROL, not model evidence."""
    project = _source_project(current)
    if not project or type(sources) not in (tuple, list):
        return "UNKNOWN"
    valid = [s for s in sources if type(s) is str and _source_project(s) == project]
    rules = [s for s in valid if " archived " in s and " policy." in s]
    sheets = [s for s in valid if " latest " in s and " option sheet." in s]
    if len(rules) != 1 or len(sheets) != 1:
        return "UNKNOWN"
    nums = re.findall(r"Maximum [^:]+: (\d+) [^.]+\.", rules[0])
    flag = re.search(r"Required [^:]+: (true|false)\.", rules[0])
    if len(nums) != 2 or flag is None:
        return "UNKNOWN"
    policy = (int(nums[0]), int(nums[1]), flag.group(1) == "true")
    options = []
    for name in "AB":
        match = re.search(r"Option " + name + r": ([^.]+)\.", sheets[0])
        if match is None:
            return "UNKNOWN"
        numbers = re.findall(r"\b\d+\b", match.group(1))
        boolean = re.findall(r"\b(true|false)\b", match.group(1))
        if len(numbers) != 2 or len(boolean) != 1:
            return "UNKNOWN"
        options.append((int(numbers[0]), int(numbers[1]), boolean[0] == "true"))
    return _oracle(policy, options)


def validate(rows):
    need(type(rows) in (tuple, list) and len(rows) == 180, "P0X_COUNT_RED")
    expected = {_row(f, s, r)["id"]: _row(f, s, r)
                for f in range(30) for s in range(2) for r in range(3)}
    ids = [row.get("id") for row in rows]
    need(len(set(ids)) == 180 and set(ids) == set(expected), "P0X_ID_COVERAGE_RED")
    partitions = {"calibration": [], "holdout": []}
    for row in rows:
        need(row == expected[row["id"]], "P0X_SOURCE_OR_ORACLE_TAMPER_RED")
        partitions[row["partition"]].append(row)
        need("P0X" in row["current"] and not re.search(r"\d+ (?:euros|days|MB|ms|kg|hours|watts|minutes|GB|seconds)", row["current"]),
             "P0X_CURRENT_NUMERIC_LEAK_RED")
        foreign = foreign_sheet(row, rows)
        need(_source_project(foreign) != row["id"], "P0X_FOREIGN_HEADER_RED")
        need(decide_sources(row["current"], []) == "UNKNOWN"
             and decide_sources(row["current"], [row["b1_source"]]) == "UNKNOWN"
             and decide_sources(row["current"], [row["b2_source"]]) == "UNKNOWN"
             and decide_sources(row["current"], [foreign]) == "UNKNOWN"
             and decide_sources(row["current"], [row["b2_source"], foreign]) == "UNKNOWN",
             "P0X_SINGLE_SOURCE_OR_FOREIGN_LEAK_RED")
        need(decide_sources(row["current"], [row["b2_source"], foreign, row["b1_source"]])
             == row["oracle_action"], "P0X_BOTH_SOURCE_ORACLE_RED")
    need(len(partitions["calibration"]) == 30
         and len(partitions["holdout"]) == 150, "P0X_PARTITION_RED")
    for part, count in (("calibration", 10), ("holdout", 50)):
        for action in ("A", "B", "NONE"):
            need(sum(row["oracle_action"] == action for row in partitions[part]) == count,
                 "P0X_OUTCOME_BALANCE_RED")
    for family in range(30):
        group = [r for r in rows if r["family"] == family]
        need(len(group) == 6, "P0X_FAMILY_GRID_RED")
        for action in ("A", "B", "NONE"):
            need(sum(r["oracle_action"] == action for r in group) == 2,
                 "P0X_FAMILY_BALANCE_RED")
        for rule in range(3):
            outcomes = [r["oracle_action"] for r in group if r["rule_index"] == rule]
            need(len(outcomes) == 2 and outcomes[0] != outcomes[1],
                 "P0X_SHEET_COUNTERFACTUAL_RED")
    return {"schema": SCHEMA + ".validation.v1", "status": "P0X_SOFTWARE_STRUCTURAL_ONLY",
            "rows": 180, "calibration": 30, "holdout": 150,
            "heldout_action_balance": {"A": 50, "B": 50, "NONE": 50},
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "jepa_weight": 0, "redmi_measured": False,
            "whole_system_complete": False}


def model_inputs(rows):
    validate(rows)
    result = []
    answers = []
    for row in rows:
        if row["partition"] != "holdout":
            continue
        foreign = foreign_sheet(row, rows)
        views = {
            "c3_only": "Current request:\n" + row["current"],
            "b1_only": "Current request:\n" + row["current"] + "\n\nB1 exact source:\n" + row["b1_source"],
            "b2_only": "Current request:\n" + row["current"] + "\n\nB2 exact source:\n" + row["b2_source"],
            "both_exact": "Current request:\n" + row["current"] + "\n\nB2 exact source:\n" + row["b2_source"] + "\n\nB1 exact source:\n" + row["b1_source"],
            "shuffled": "Current request:\n" + row["current"] + "\n\nB2 exact source:\n" + row["b2_source"] + "\n\nFOREIGN B1 source:\n" + foreign,
        }
        for arm in ARMS:
            result.append({"id": row["id"], "arm": arm,
                           "messages": [{"role": "user", "content": views[arm]}]})
        answers.append({"id": row["id"], "oracle_action": row["oracle_action"]})
    need(len(result) == 750 and len(answers) == 150, "P0X_MODEL_ARM_COVERAGE_RED")
    for p in result:
        s = canonical(p).decode("utf-8")
        need(not any(k in s for k in ("oracle_action", "sheet_index", "rule_index", "max_first", "max_second")),
             "P0X_MODEL_ORACLE_LEAK_RED")
    return result, answers


def export(out, expected_fixture_sha256):
    rows = fixtures()
    need(expected_fixture_sha256 == sha(canonical(rows)),
         "P0X_EXTERNAL_FIXTURE_PIN_RED")
    prompts, answers = model_inputs(rows)
    out = Path(out)
    need(not out.exists() and not out.is_symlink(), "P0X_FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    data = {
        "inputs.jsonl": b"".join(canonical(p) + b"\n" for p in prompts),
        "answers.jsonl": b"".join(canonical(a) + b"\n" for a in answers),
    }
    for name, raw in data.items():
        with (out / name).open("xb") as f:
            f.write(raw);f.flush();os.fsync(f.fileno())
    manifest = {"schema": SCHEMA + ".export.v1",
                "status": "P0X_SOURCE_ONLY_NO_NATIVE_NO_GATE",
                "seed": SEED, "fixture_sha256": expected_fixture_sha256,
                "calibration_rows": 30, "holdout_rows": 150,
                "model_inputs": 750, "answers": 150,
                "sha256": {k: sha(v) for k, v in data.items()},
                "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
                "jepa_weight": 0, "redmi_measured": False,
                "whole_system_complete": False}
    with (out / "manifest.json").open("xb") as f:
        f.write(canonical(manifest));f.flush();os.fsync(f.fileno())
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--fixture-sha256")
    args = parser.parse_args(argv)
    rows = fixtures()
    report = validate(rows)
    report["fixture_sha256"] = sha(canonical(rows))
    if args.out is not None:
        need(args.fixture_sha256 is not None, "P0X_EXTERNAL_PIN_REQUIRED")
        report["export"] = export(args.out, args.fixture_sha256)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
