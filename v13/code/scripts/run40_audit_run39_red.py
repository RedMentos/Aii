#!/usr/bin/env python3
"""Independent, read-only Run39 original RED ZIP audit (stdlib; never promotes)."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import zipfile

ORIGINAL_SHA256 = "b329db427059274a34d51fd5c4d06e90173c9cae06c478a8648aec7249a8410a"
SOURCE_SHA = "ad8e3d43995b970342757b720d2c66dbb5697aa1"
SEEDS = (501, 502, 503)
ARMS = ("two_slot", "six_slot", "balanced_slot")
CLASSES = ("own_only_self", "world_only_world", "both_world", "none_self")
NEGATIVES = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
             "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
             "jepa_weight": 0, "world_jepa_authority": "SHADOW",
             "redmi_measured": False, "whole_system_complete": False}


def require(ok, reason):
    if not ok:
        raise ValueError("RUN40_" + reason)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def parse_json(data):
    return json.loads(data, parse_constant=lambda value: require(False, "NONFINITE_JSON"))


def rank(values):
    require(all(finite(v) for v in values), "RANK_NONFINITE")
    ranks = [0] * len(values)
    for position, index in enumerate(sorted(range(len(values)), key=lambda i: (values[i], i))):
        ranks[index] = position
    return ranks


def spearman(x, y):
    require(len(x) == len(y) and len(x) >= 3, "SPEARMAN_SUPPORT")
    a, b = rank(x), rank(y)
    ma, mb = statistics.mean(a), statistics.mean(b)
    aa, bb = [v - ma for v in a], [v - mb for v in b]
    denom = math.sqrt(sum(v*v for v in aa) * sum(v*v for v in bb))
    require(denom > 0, "SPEARMAN_UNDEFINED")
    return sum(u*v for u, v in zip(aa, bb)) / denom


def binding_w7_support(rows):
    for row in rows:
        a, b = row["attribution"]["jepa"], row["attribution"]["no_action"]
        require(a["n"] == b["n"], "W7_MISMATCHED_CLASS_COUNTS")
        if any(type(a["n"][k]) is not int or a["n"][k] < 15
               for k in ("own_only", "world_only", "both", "none")):
            return False
    return True


def original_w1_w6(rows):
    pool = lambda key: statistics.mean(r["cf_retrieval"][key] for r in rows)
    conf_err = [pair for row in rows for pair in row["_conf_err"]]
    require(all(len(pair) == 2 and all(finite(v) for v in pair)
                for pair in conf_err), "CONF_ERR_ROWS")
    rho = spearman([x[0] for x in conf_err], [x[1] for x in conf_err])
    j = {k: statistics.mean(r["attribution"]["jepa"][k] for r in rows)
         for k in ("own_only_self", "world_only_world", "none_self", "balanced")}
    c = statistics.mean(r["attribution"]["no_action"]["balanced"] for r in rows)
    gates = {
        "W1_cf_retrieval_covered": pool("jepa_covered") >= .80 and all(
            r["cf_retrieval"]["jepa_covered"] >= .70 for r in rows),
        "W2_controls_fail": pool("no_action_covered") <= .40 and
            pool("shuffled_action_covered") <= .40 and
            pool("jepa_covered") - max(pool("no_action_covered"),
                                        pool("shuffled_action_covered")) >= .30,
        "W3_no_collapse": all(r["collapse"]["effective_rank"] >= 4 and
                              r["collapse"]["min_std"] >= .05 for r in rows),
        "W4_confidence_tracks_error": rho <= -.30 and all(
            r["confidence"]["held_out_all_uncertain"] is True for r in rows),
        "W5_attribution_jepa": j["own_only_self"] >= .90 and
            j["world_only_world"] >= .90 and j["none_self"] >= .80,
        "W6_no_action_attribution_worse": c <= j["balanced"] - .20,
    }
    return gates, {"rho": round(rho, 6), "balanced_jepa": round(j["balanced"], 6),
                   "balanced_no_action": round(c, 6),
                   "covered_cf": round(pool("jepa_covered"), 6)}


def gap(row, metric):
    a, b = row["attribution"]["jepa"], row["attribution"]["no_action"]
    return (a[metric] - b[metric]) if metric != "macro" else sum(
        a[k] - b[k] for k in CLASSES) / 4


def audit_bytes(raw, expected_sha=ORIGINAL_SHA256):
    require(hashlib.sha256(raw).hexdigest() == expected_sha, "ORIGINAL_SHA256")
    import io
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        require(len(names) == len(set(names)) and z.testzip() is None,
                "ZIP_DUPLICATE_OR_CRC")
        require(all(n and not n.startswith("/") and ".." not in n.split("/")
                    for n in names), "ZIP_PATH")
        require("SHA256SUMS" in names, "MANIFEST_MISSING")
        lines = z.read("SHA256SUMS").decode("ascii").splitlines()
        entries = {}
        for line in lines:
            require(len(line) >= 68 and line[64:68] == "  ./", "MANIFEST_FORMAT")
            digest, name = line[:64], line[68:]
            require(len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
                    and name not in entries, "MANIFEST_DUPLICATE")
            entries[name] = digest
        require(set(entries) == set(names) - {"SHA256SUMS"}, "MANIFEST_COVERAGE")
        require(all(hashlib.sha256(z.read(n)).hexdigest() == h
                    for n, h in entries.items()), "MANIFEST_HASH")
        require(z.read("HEAD.txt").decode().strip() == SOURCE_SHA, "SOURCE_SHA")
        for key, expected in {"PINS": 0, "VENV": 0, "DEPS": 0, "TEST": 0,
                              "REALFILE": 1, "REPORT_CHECK": 1, "COMPILE": 0,
                              "PRIVACY": 0, "DIFF": 0}.items():
            require(z.read(key + "_EXIT.txt").decode().strip() == str(expected),
                    "STAGE_" + key)
        result = parse_json(z.read("RESULT.json"))
        require(result["schema"] == "v13.run39.world_jepa_action_balanced_exact_row.v1"
                and result["registered"] is True and result["seeds"] == list(SEEDS)
                and result["args"] == {"train": 4000, "cf": 150,
                                       "attr": 300, "steps": 3000}, "COHORT")
        require(result["status"] == "RED" and result.get("error") ==
                "ValueError: RUN39_W7_SUPPORT", "ORIGINAL_RED")
        require(result["affected_slot_copies"] == 5 and
                result["same_collected_rows"] is True and
                result["same_core_parameter_count"] is True and
                result["same_optimizer_steps"] is True and
                result["same_training_example_count"] is False and
                result["global_96d_capacity_control_complete"] is False,
                "ARM_DESIGN")
        require(all(type(result.get(k)) is type(v) and result[k] == v
                    for k, v in NEGATIVES.items()), "NEGATIVE_GATES")
        all_rows = {}
        for arm in ARMS:
            rows = []
            require(len(result[arm]) == len(SEEDS), "ARM_COMPLETENESS")
            for i, seed in enumerate(SEEDS):
                name = f"work/{arm}-{seed}-RESULT.json"
                require(name in entries, "RAW_SEED_MISSING")
                row = parse_json(z.read(name))
                require(row["seed"] == seed and row["n_train"] == 3600,
                        "ROW_IDENTITY")
                stripped = {k: v for k, v in row.items() if k != "_conf_err"}
                require(stripped == result[arm][i], "AGGREGATE_ROW_MISMATCH")
                require(row["capacity"]["world_concat_dim"] == 96,
                        "CAPACITY")
                rows.append(row)
            all_rows[arm] = rows
        for i, seed in enumerate(SEEDS):
            counts = [all_rows[arm][i]["attribution"]["jepa"]["n"]
                      for arm in ARMS]
            require(counts[0] == counts[1] == counts[2], "CLASS_COUNT_ARM_MISMATCH")
            require(f"work/seed-{seed}/world-{seed}.json" in entries and
                    f"work/seed-{seed}/world-{seed}.log" in entries,
                    "FILEWORLD_MISSING")
        require(not binding_w7_support(all_rows["two_slot"]) and
                not binding_w7_support(all_rows["six_slot"]) and
                not binding_w7_support(all_rows["balanced_slot"]),
                "ORIGINAL_SUPPORT_RED_NOT_REPRODUCED")
        gates = {}
        summaries = {}
        for arm in ARMS:
            gates[arm], summaries[arm] = original_w1_w6(all_rows[arm])
        require(gates["two_slot"] == result["two_slot_gates"],
                "ORIGINAL_TWO_SLOT_GATES_MISMATCH")
        require(gates["balanced_slot"]["W4_confidence_tracks_error"] is False
                and all(not g["W6_no_action_attribution_worse"]
                        for g in gates.values()), "BINDING_NEGATIVES")
        delta = {}
        for metric in ("balanced", "macro"):
            values = [round(gap(a, metric) - gap(b, metric), 6)
                      for a, b in zip(all_rows["balanced_slot"],
                                      all_rows["six_slot"])]
            delta[metric] = {"per_seed": values,
                             "mean": round(statistics.mean(values), 6)}
        require(all(all(finite(v) for v in item["per_seed"]) for item in delta.values()),
                "EXPLORATORY_NONFINITE")
        h1 = delta["balanced"]["mean"] >= .05 and all(
            v >= -.01 for v in delta["balanced"]["per_seed"])
        h3 = delta["macro"]["mean"] >= .03 and all(
            v >= -.01 for v in delta["macro"]["per_seed"])
        require(not h1 and not h3, "DESCRIPTIVE_OUTCOME_CHANGED")
        return {"schema": "v13.run40.original_run39_red_audit.v1",
                "original_artifact_id": 13022689982,
                "original_zip_sha256": ORIGINAL_SHA256,
                "original_source_sha": SOURCE_SHA,
                "zip_crc": "PASS", "manifest_entries": len(entries),
                "raw_per_seed_results": 9, "original_status": "RED",
                "red_reason": "seed501 world_only n=14 (< frozen W7 minimum 15)",
                "binding_w7": "UNSCORABLE_SUPPORT_FAIL",
                "w1_w6": gates, "summaries": summaries,
                "descriptive_only_due_to_red": delta,
                "exploratory_h1": "NOT_MET_DESCRIPTIVE_ONLY" if not h1 else "MET_DESCRIPTIVE_ONLY",
                "exploratory_h3": "NOT_MET_DESCRIPTIVE_ONLY" if not h3 else "MET_DESCRIPTIVE_ONLY",
                "negative_gates": NEGATIVES,
                "whole_system_complete": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    report = audit_bytes(args.zip.read_bytes())
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()