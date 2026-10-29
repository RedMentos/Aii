#!/usr/bin/env python3
"""P2X disjoint source-composition train/validation fixture; source-only, no fitting."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re

SCHEMA = "v13.p2x.disjoint_receiver_trainset.v1"
SEED = 2026102921
DOMAINS = (
    ("festival venue", "rental fee", "tokens", "access window", "ticks", "covered"),
    ("workshop equipment", "kit size", "blocks", "assembly window", "beats", "reusable"),
    ("community garden", "water allocation", "drops", "setup window", "cycles", "shaded"),
    ("satellite mockups", "payload mass", "units", "spin-up window", "steps", "shielded"),
    ("exhibition crates", "container volume", "cells", "opening window", "slots", "insured"),
    ("classroom planning", "seat quota", "places", "preparation window", "intervals", "accessible"),
)
SHEETS = (((56, 19, True), (266, 11, False)),
          ((206, 13, True), (131, 11, True)))
RULES = ((101, 23, True), (251, 23, False), (176, 15, True))
ARMS = ("c3_only", "b1_only", "b2_only", "both_exact", "shuffled")
NEGATIVES = ("c3_only", "b1_only", "b2_only", "shuffled")
ACTIONS = ("A", "B", "NONE", "UNKNOWN")


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _tf(v):
    return "true" if v else "false"


def _oracle(rule, options):
    budget, deadline, required = rule
    eligible = [(o[0], o[1], name) for name, o in zip("AB", options)
                if o[0] <= budget and o[1] <= deadline
                and (not required or o[2])]
    return min(eligible)[2] if eligible else "NONE"


def _project(family, sheet, rule):
    return "P2X" + sha(f"{SEED}|{family}|{sheet}|{rule}".encode("ascii"))[:16].upper()


def _partition(family):
    pos = family % 10
    return "calibration" if pos == 0 else "validation" if pos in (1, 2) else "train"


def _row(family, sheet, rule):
    need(0 <= family < 60 and sheet in (0, 1) and rule in (0, 1, 2),
         "P2X_GRID_INDEX_RED")
    domain, a1, u1, a2, u2, flag = DOMAINS[family // 10]
    s = (sheet + ((family // 2) % 2)) % 2
    ri = (rule + family % 3) % 3
    shift = 11 * (family + 1)
    time_shift = family % 4
    options = tuple((o[0] + shift, o[1] + time_shift, o[2])
                    for o in SHEETS[s])
    if family % 2:
        options = options[::-1]
    base = RULES[ri]
    policy = (base[0] + shift, base[1] + time_shift, base[2])
    project = _project(family, sheet, rule)
    current = (f"Project {project}. Choose Option A or Option B using the "
               f"archived {domain} policy and latest option sheet. "
               "If neither qualifies, choose NONE.")
    b2 = (f"Project {project} archived {domain} policy. "
          f"Maximum {a1}: {policy[0]} {u1}. "
          f"Maximum {a2}: {policy[1]} {u2}. "
          f"Required {flag}: {_tf(policy[2])}.")
    def opt(name, x):
        return (f"Option {name}: {a1} {x[0]} {u1}; "
                f"{a2} {x[1]} {u2}; {flag} {_tf(x[2])}.")
    b1 = (f"Project {project} latest {domain} option sheet. "
          + " ".join(opt(name, x) for name, x in zip("AB", options)))
    return {"id": project, "family": family, "domain": domain,
            "sheet_index": sheet, "rule_index": rule,
            "partition": _partition(family), "current": current,
            "b1_source": b1, "b2_source": b2,
            "rule": {"max_first": policy[0], "max_second": policy[1],
                     "require_flag": policy[2]},
            "options": {name: {"first": x[0], "second": x[1], "flag": x[2]}
                        for name, x in zip("AB", options)},
            "oracle_action": _oracle(policy, options)}


def fixtures():
    rows = [_row(f, s, r) for f in range(60)
            for s in range(2) for r in range(3)]
    random.Random(SEED).shuffle(rows)
    return rows


def foreign_sheet(row, rows):
    target = (row["family"] + 10) % 60
    matches = [r for r in rows if r["family"] == target
               and r["sheet_index"] == row["sheet_index"]
               and r["rule_index"] == row["rule_index"]]
    need(len(matches) == 1 and matches[0]["id"] != row["id"],
         "P2X_FOREIGN_IDENTITY_RED")
    return matches[0]["b1_source"]


def _source_project(text):
    m = re.match(r"^Project (P2X[0-9A-F]{16})\b", text)
    return m.group(1) if m else None


def decide_sources(current, sources):
    project = _source_project(current)
    if not project or type(sources) not in (list, tuple):
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
        m = re.search(r"Option " + name + r": ([^.]+)\.", sheets[0])
        if m is None:
            return "UNKNOWN"
        values = re.findall(r"\b\d+\b", m.group(1))
        bools = re.findall(r"\b(true|false)\b", m.group(1))
        if len(values) != 2 or len(bools) != 1:
            return "UNKNOWN"
        options.append((int(values[0]), int(values[1]), bools[0] == "true"))
    return _oracle(policy, options)


def validate(rows):
    need(type(rows) in (tuple, list) and len(rows) == 360, "P2X_COUNT_RED")
    expected = {_row(f, s, r)["id"]: _row(f, s, r)
                for f in range(60) for s in range(2) for r in range(3)}
    ids = [r.get("id") for r in rows]
    need(len(set(ids)) == 360 and set(ids) == set(expected), "P2X_ID_RED")
    partitions = {"calibration": [], "validation": [], "train": []}
    for row in rows:
        need(row == expected[row["id"]], "P2X_SOURCE_OR_ORACLE_TAMPER_RED")
        partitions[row["partition"]].append(row)
        need(not re.search(r"\d+ (?:tokens|ticks|blocks|beats|drops|cycles|units|steps|cells|slots|places|intervals)",
                           row["current"]), "P2X_CURRENT_NUMERIC_LEAK_RED")
        foreign = foreign_sheet(row, rows)
        need(decide_sources(row["current"], []) == "UNKNOWN"
             and decide_sources(row["current"], [row["b1_source"]]) == "UNKNOWN"
             and decide_sources(row["current"], [row["b2_source"]]) == "UNKNOWN"
             and decide_sources(row["current"], [row["b2_source"], foreign]) == "UNKNOWN",
             "P2X_SINGLE_OR_FOREIGN_SOURCE_LEAK_RED")
        need(decide_sources(row["current"], [row["b2_source"], row["b1_source"]])
             == row["oracle_action"], "P2X_BOTH_SOURCE_ORACLE_RED")
    need({p: len(v) for p, v in partitions.items()} ==
         {"calibration": 36, "validation": 72, "train": 252}, "P2X_PARTITION_RED")
    for part, per_action in (("calibration", 12), ("validation", 24), ("train", 84)):
        for action in ("A", "B", "NONE"):
            need(sum(r["oracle_action"] == action for r in partitions[part]) == per_action,
                 "P2X_ACTION_BALANCE_RED")
    for family in range(60):
        group = [r for r in rows if r["family"] == family]
        need(len(group) == 6 and all(sum(r["oracle_action"] == a for r in group) == 2
                                     for a in ("A", "B", "NONE")), "P2X_FAMILY_BALANCE_RED")
    from scripts import p0x_independent_source_holdout as p0x
    old = p0x.fixtures()
    old_ids = {r["id"] for r in old}
    old_sources = {s for r in old for s in (r["current"], r["b1_source"], r["b2_source"])}
    need(not old_ids.intersection(ids) and not any(
         s in old_sources for r in rows for s in (r["current"], r["b1_source"], r["b2_source"])),
         "P2X_P0X_SOURCE_OVERLAP_RED")
    return {"schema": SCHEMA + ".validation.v1", "status": "P2X_SOURCE_ONLY_NO_TRAINING",
            "rows": 360, "train": 252, "validation": 72, "calibration": 36,
            "train_action_balance": {"A": 84, "B": 84, "NONE": 84},
            "no_p0x_source_overlap": True,
            "step2_status": "UTILITY_FAIL", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def views(row, rows):
    foreign = foreign_sheet(row, rows)
    current = "Current request:\n" + row["current"]
    return {
        "c3_only": current,
        "b1_only": current + "\n\nB1 exact source:\n" + row["b1_source"],
        "b2_only": current + "\n\nB2 exact source:\n" + row["b2_source"],
        "both_exact": current + "\n\nB2 exact source:\n" + row["b2_source"]
                      + "\n\nB1 exact source:\n" + row["b1_source"],
        "shuffled": current + "\n\nB2 exact source:\n" + row["b2_source"]
                    + "\n\nFOREIGN B1 source:\n" + foreign,
    }


def training_and_validation(rows):
    validate(rows)
    train_rows = sorted((r for r in rows if r["partition"] == "train"), key=lambda r: r["id"])
    val_rows = sorted((r for r in rows if r["partition"] == "validation"), key=lambda r: r["id"])
    train, val, answers = [], [], []
    for i, row in enumerate(train_rows):
        rendered = views(row, rows)
        for arm in ("both_exact", NEGATIVES[i % 4]):
            target = row["oracle_action"] if arm == "both_exact" else "UNKNOWN"
            train.append({"id": row["id"], "arm": arm, "target_action": target,
                          "messages": [{"role": "user", "content": rendered[arm]}]})
    random.Random(SEED + 1).shuffle(train)
    for row in val_rows:
        rendered = views(row, rows)
        answers.append({"id": row["id"], "oracle_action": row["oracle_action"]})
        for arm in ARMS:
            val.append({"id": row["id"], "arm": arm,
                        "messages": [{"role": "user", "content": rendered[arm]}]})
    need(len(train) == 504 and len(val) == 360 and len(answers) == 72,
         "P2X_EXPORT_COUNT_RED")
    need({arm: sum(p["arm"] == arm for p in train) for arm in NEGATIVES} ==
         {arm: 63 for arm in NEGATIVES}, "P2X_NEGATIVE_BALANCE_RED")
    need(sum(p["target_action"] == "UNKNOWN" for p in train) == 252
         and all(sum(p["target_action"] == a for p in train) == 84
                 for a in ("A", "B", "NONE")), "P2X_TRAIN_TARGET_BALANCE_RED")
    for p in train + val:
        need(len(p["messages"]) == 1 and p["messages"][0]["role"] == "user"
             and not any(k in p["messages"][0]["content"]
                         for k in ("oracle_action", "target_action", "max_first", "max_second")),
             "P2X_MODEL_INPUT_LEAK_RED")
    return train, val, answers


def export(out, fixture_sha256):
    rows = fixtures()
    need(sha(canonical(rows)) == fixture_sha256, "P2X_EXTERNAL_FIXTURE_PIN_RED")
    train, val, answers = training_and_validation(rows)
    out = Path(out)
    need(not out.exists() and not out.is_symlink(), "P2X_FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    data = {"train.jsonl": train, "validation_inputs.jsonl": val,
            "validation_answers.jsonl": answers}
    hashes = {}
    for name, records in data.items():
        raw = b"".join(canonical(record) + b"\n" for record in records)
        with (out / name).open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        hashes[name] = sha(raw)
    manifest = {"schema": SCHEMA + ".export.v1",
                "status": "P2X_SOURCE_ONLY_NO_TRAINING",
                "seed": SEED, "fixture_sha256": fixture_sha256,
                "train_examples": 504, "validation_inputs": 360,
                "validation_answers": 72, "sha256": hashes,
                "step2_status": "UTILITY_FAIL", "jepa_weight": 0,
                "redmi_measured": False, "whole_system_complete": False}
    with (out / "manifest.json").open("xb") as f:
        f.write(canonical(manifest)); f.flush(); os.fsync(f.fileno())
    return manifest


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path)
    p.add_argument("--fixture-sha256")
    args = p.parse_args(argv)
    rows = fixtures()
    report = validate(rows)
    report["fixture_sha256"] = sha(canonical(rows))
    if args.out is not None:
        need(args.fixture_sha256 is not None, "P2X_EXTERNAL_PIN_REQUIRED")
        report["export"] = export(args.out, args.fixture_sha256)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
