#!/usr/bin/env python3
"""Independent read-only Run32 original ZIP audit. No model calls or raw export."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import zipfile

ZIP_SHA = "adda55e8d4d4fd5aabd328b8f79d03c08d2b6804fb2c48daea4043f1052faecb"
SOURCE_HEAD = "550185a74e9daddaea27860f6244c1209d376af2"
SEEDS = (201, 202, 203)
STAGES = ("PINS", "VENV", "DEPS", "TEST", "REALFILE",
          "REPORT_CHECK", "COMPILE", "PRIVACY", "DIFF")
W7_KEYS = ("W7a_both_world_action_gain",
           "W7b_none_self_action_gain",
           "W7c_four_class_macro_action_gain")
CLASSES = ("own_only_self", "world_only_world", "both_world", "none_self")
ORIGINAL_GATES = {
    "W1_cf_retrieval_covered": False, "W2_controls_fail": True,
    "W3_no_collapse": True, "W4_confidence_tracks_error": False,
    "W5_attribution_jepa": False, "W6_no_action_attribution_worse": False,
}
SLOT_GATES = {k: (k != "W6_no_action_attribution_worse")
              for k in ORIGINAL_GATES}
SOURCE_BLOBS = {
    "original_world_jepa_blob": "99a686a131a1bdc89efe0d0cf9610ec54cbd853b",
    "original_z12b_experiment_blob": "2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4",
    "slot_candidate_blob": "67e14e0d03c50c4767b74d5b02a819a95c6cc262",
    "slot_runner_blob": "dbf3af3f8bc61a846eb542c7db3cc034e94f5bd7",
}


def fail(reason):
    raise ValueError("RUN34_" + reason + "_RED")


def strict_json(raw):
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                fail("DUPLICATE_JSON_KEY")
            d[k] = v
        return d

    def invalid(value):
        fail("NONFINITE_JSON_" + value)

    obj = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)

    def check(value):
        if isinstance(value, float) and not math.isfinite(value):
            fail("NONFINITE_VALUE")
        if isinstance(value, dict):
            for v in value.values():
                check(v)
        elif isinstance(value, list):
            for v in value:
                check(v)
    check(obj)
    return obj


def verify_manifest(z):
    names = z.namelist()
    if len(names) != 131 or len(set(names)) != len(names):
        fail("ZIP_MEMBERS")
    if z.testzip() is not None:
        fail("ZIP_CRC")
    if "SHA256SUMS" not in names:
        fail("NO_MANIFEST")
    lines = z.read("SHA256SUMS").decode("utf-8").splitlines()
    if len(lines) != 130:
        fail("MANIFEST_COUNT")
    seen = set()
    for line in lines:
        if "  " not in line:
            fail("MANIFEST_FORMAT")
        digest, name = line.split("  ", 1)
        name = name.removeprefix("./")
        pp = PurePosixPath(name)
        if (not re.fullmatch(r"[0-9a-f]{64}", digest) or
                name in seen or name == "SHA256SUMS" or
                pp.is_absolute() or ".." in pp.parts or name not in names):
            fail("MANIFEST_MEMBER")
        seen.add(name)
        if hashlib.sha256(z.read(name)).hexdigest() != digest:
            fail("INNER_SHA")
    if seen != set(names) - {"SHA256SUMS"}:
        fail("MANIFEST_INCOMPLETE")
    for stage in STAGES:
        if z.read(stage + "_EXIT.txt").decode("utf-8").strip() != "0":
            fail("STAGE_" + stage)
    if z.read("HEAD.txt").decode("utf-8").strip() != SOURCE_HEAD:
        fail("SOURCE_HEAD")
    return len(seen)


def close(x, y, label):
    if (type(x) not in (int, float) or type(y) not in (int, float)
            or not math.isclose(x, y, abs_tol=0.0002, rel_tol=0.)):
        fail("ROUNDING_" + label)


def recompute_w7(slot_arm, saved):
    if len(slot_arm) != 3 or len(saved.get("per_seed", [])) != 3:
        fail("W7_SEED_COUNT")
    rows = []
    for seed, arm, prior in zip(SEEDS, slot_arm, saved["per_seed"]):
        if arm["seed"] != seed or prior["seed"] != seed:
            fail("W7_SEED_ID")
        a = arm["attribution"]["jepa"]
        b = arm["attribution"]["no_action"]
        counts = a["n"]
        if counts != b["n"] or any(type(counts[k]) is not int or counts[k] < 15
                                   for k in ("own_only", "world_only", "both", "none")):
            fail("W7_CLASS_COVERAGE")
        if counts != prior["class_counts"]:
            fail("W7_CLASS_COUNT_BINDING")
        if any(type(a[k]) not in (int, float) or type(b[k]) not in (int, float)
               or not 0 <= a[k] <= 1 or not 0 <= b[k] <= 1
               for k in CLASSES):
            fail("W7_RATE_RANGE")
        both = a["both_world"] - b["both_world"]
        none = a["none_self"] - b["none_self"]
        macro_j = sum(a[k] for k in CLASSES) / 4
        macro_z = sum(b[k] for k in CLASSES) / 4
        macro = macro_j - macro_z
        for key, value in (("both_world_gap", both),
                           ("none_self_gap", none),
                           ("four_class_macro_gap", macro),
                           ("jepa_four_class_macro", macro_j),
                           ("zero_four_class_macro", macro_z)):
            close(prior[key], value, key)
        rows.append((both, none, macro))
    means = [sum(row[i] for row in rows) / 3 for i in range(3)]
    for key, val in zip(("mean_both_world_gap", "mean_none_self_gap",
                         "mean_four_class_macro_gap"), means):
        close(saved[key], val, key)
    gates = {
        W7_KEYS[0]: means[0] >= .20 and all(r[0] >= .10 for r in rows),
        W7_KEYS[1]: means[1] >= .05 and all(r[1] >= 0 for r in rows),
        W7_KEYS[2]: means[2] >= .08 and all(r[2] >= .04 for r in rows),
    }
    return gates, means


def audit(path, expected_sha=ZIP_SHA):
    path = Path(path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != expected_sha:
        fail("OUTER_SHA")
    with zipfile.ZipFile(path) as z:
        count = verify_manifest(z)
        r = strict_json(z.read("RESULT.json"))
        if (r.get("schema") != "v13.run32.world_jepa_disjoint_attribution.v1"
                or r.get("evidence_kind") != "REAL_FILE_LINUX_SHADOW_DISJOINT_EXPLORATORY"
                or r.get("registered") is not True
                or r.get("seeds") != list(SEEDS)
                or r.get("args") != {"train": 4000, "cf": 150, "attr": 300, "steps": 3000}
                or any(r.get(k) != v for k, v in SOURCE_BLOBS.items())):
            fail("REGISTRATION")
        if (r.get("status") != "SHADOW_CANDIDATE_FAIL"
                or r.get("original_gates") != ORIGINAL_GATES
                or r.get("slot_original_gates") != SLOT_GATES
                or r.get("capacity_confounded") is not True
                or r.get("exact_paired_transitions") is not False
                or r.get("world_jepa_authority") != "SHADOW"
                or r.get("age0") != "RECORD_ONLY"
                or r.get("step2") != "UTILITY_FAIL"
                or r.get("b3") != "NO_PROMOTION"
                or r.get("body_jepa") != "UNAVAILABLE"
                or r.get("jepa_weight") != 0
                or r.get("redmi_measured") is not False
                or r.get("whole_system_complete") is not False):
            fail("NEGATIVE_GATE")
        for key, prefix in (("original_arm", "original"), ("slot_arm", "slot")):
            arm = r.get(key)
            if type(arm) is not list or len(arm) != 3:
                fail("ARM_COUNT")
            for seed, entry in zip(SEEDS, arm):
                if entry.get("seed") != seed:
                    fail("ARM_SEED")
                source = strict_json(z.read(f"work/{prefix}-{seed}-RESULT.json"))
                source.pop("_conf_err", None)
                if source != entry:
                    fail("PER_SEED_CHECKPOINT_BINDING")
        gates, means = recompute_w7(r["slot_arm"], r["w7_summary"])
        if gates != r.get("w7_gates") or gates != {
                W7_KEYS[0]: True, W7_KEYS[1]: False, W7_KEYS[2]: False}:
            fail("W7_GATE_RECOMPUTATION")
        return {
            "schema": "v13.run34.run32_original_zip_independent_readonly.v1",
            "source_head": SOURCE_HEAD, "original_zip_sha256": sha,
            "manifest_members_verified": count, "stage_exit_zero": len(STAGES),
            "seed_count_each_arm": 3, "registered_seed_ids": list(SEEDS),
            "original_gates": ORIGINAL_GATES, "slot_original_gates": SLOT_GATES,
            "w7_gates": gates,
            "w7_mean_gaps": dict(zip(("both_world", "none_self", "macro"), [
                round(x, 6) for x in means])),
            "status": "SHADOW_CANDIDATE_FAIL", "age0": "RECORD_ONLY",
            "step2": "UTILITY_FAIL", "b3": "NO_PROMOTION",
            "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
            "world_jepa_authority": "SHADOW", "redmi_measured": False,
            "whole_system_complete": False,
            "capacity_confounded": True, "exact_paired_transitions": False,
        }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-zip", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    if args.out.exists():
        fail("FRESH_OUTPUT_REQUIRED")
    result = audit(args.original_zip)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2,
                                   allow_nan=False) + "\n", encoding="utf-8")
    print("RUN34_ORIGINAL_RUN32_RAW_W7_RECOMPUTED_FAIL_NO_PROMOTION")


if __name__ == "__main__":
    main()
