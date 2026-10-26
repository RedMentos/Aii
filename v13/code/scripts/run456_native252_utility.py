#!/usr/bin/env python3
"""Run456: descriptive paired STEP2 utility on six actual S20/S21 native receipts.

No inference or training. Independently require Run453 six-receipt/252-row
safe-export verification first. Pair by frozen fixture, variant and seed;
do not infer causal gain or promote STEP2 from partial cohort statistics.
"""
import argparse
import hashlib
import json
import math
import os
import stat
from pathlib import Path

import run394_step2_fresh as r394
import run397_step2_resume as r397
import run453_verify_native252 as verified252
from run396_step2_pilot_audit import validated_rows

ARMS = ("O", "P", "S")
SEEDS = (20, 21)
VARIANTS = tuple(r397.VARIANTS)
FIXTURES = tuple(f["id"] for f in r394.FIXTURES)
IDS = tuple((a, s) for s in SEEDS for a in ARMS)
EXPECTED = {(f, v) for f in FIXTURES for v in VARIANTS}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def mean(values):
    require(bool(values), "EMPTY_UTILITY_AGGREGATE")
    return math.fsum(values) / len(values)


def aggregate(scores):
    """Exact six-arm, frozen 42-key matrix -> paired descriptive differences."""
    require(type(scores) is dict and set(scores) == set(IDS),
            "SIX_ARM_MATRIX_REQUIRED")
    for key, values in scores.items():
        require(type(values) is dict and set(values) == EXPECTED,
                "FROZEN_UTILITY_KEYS_REQUIRED:" + str(key))
        for value in values.values():
            require(type(value) in (int, float) and math.isfinite(value) and
                    0. <= value <= 1., "UTILITY_NOT_FINITE_IN_UNIT_INTERVAL")
    arm_mean = {a: {v: mean([scores[(a, s)][(f, v)] for s in SEEDS for f in FIXTURES])
                    for v in VARIANTS} for a in ARMS}
    paired = {}
    for label, a, b in (("pointer_minus_off", "P", "O"),
                        ("pointer_minus_shared_body", "P", "S"),
                        ("shared_body_minus_off", "S", "O")):
        paired[label] = {}
        for variant in VARIANTS:
            by_seed_fixture = {
                str(seed): {fixture: scores[(a, seed)][(fixture, variant)] -
                                      scores[(b, seed)][(fixture, variant)]
                            for fixture in FIXTURES}
                for seed in SEEDS}
            values = [by_seed_fixture[str(seed)][fixture]
                      for seed in SEEDS for fixture in FIXTURES]
            paired[label][variant] = {
                "mean": mean(values),
                "paired_count": len(values),
                "by_seed": {str(seed): mean(list(by_seed_fixture[str(seed)].values()))
                            for seed in SEEDS},
                "by_fixture": {fixture: mean([by_seed_fixture[str(seed)][fixture]
                                              for seed in SEEDS])
                               for fixture in FIXTURES},
                "by_seed_fixture": by_seed_fixture}
    return {"arm_mean_utility": arm_mean, "paired_differences": paired,
            "seeds": list(SEEDS), "arms": list(ARMS),
            "variants": list(VARIANTS), "fixture_ids": list(FIXTURES),
            "rows": len(IDS) * len(EXPECTED)}



def read_pinned(root, rel, expected_sha, expected_bytes=None):
    """Read an already-attested export member without following swapped links.

    The independent Run453 verifier checks the full tree first. Every value
    subsequently consumed for utility must still match that verifier's pinned
    manifest. Open each path component relative to directory descriptors so
    post-verification symlink swaps cannot redirect reads outside the export.
    """
    gate = verified252.gate
    gate.safe_rel(rel)
    require(type(expected_sha) is str and gate.HEX.fullmatch(expected_sha),
            "PINNED_READ_SHA_REQUIRED")
    require(expected_bytes is None or
            (type(expected_bytes) is int and 0 <= expected_bytes <= gate.MAX_FILE),
            "PINNED_READ_SIZE_INVALID")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    directories = []
    try:
        directories.append(os.open(root, flags | os.O_DIRECTORY))
        parts = rel.split("/")
        for part in parts[:-1]:
            directories.append(os.open(part, flags | os.O_DIRECTORY,
                                       dir_fd=directories[-1]))
        fd = os.open(parts[-1], flags, dir_fd=directories[-1])
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
                    info.st_size <= gate.MAX_FILE,
                    "PINNED_READ_FILE_UNSAFE")
            require(expected_bytes is None or info.st_size == expected_bytes,
                    "PINNED_READ_SIZE_CHANGED")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(gate.MAX_FILE + 1)
            require(len(data) == info.st_size and
                    hashlib.sha256(data).hexdigest() == expected_sha,
                    "PINNED_READ_HASH_CHANGED")
            return data
        finally:
            os.close(fd)
    finally:
        for directory in reversed(directories):
            os.close(directory)


def analyze(export_root, stage6_report):
    """Read-only; the independent 252 verifier authenticates source receipts."""
    checked = verified252.verify(export_root, stage6_report)
    require(checked["status"] == "RUN453_NATIVE_252_INDEPENDENTLY_VERIFIED" and
            checked["rows_verified"] == 252, "INDEPENDENT_252_NOT_VERIFIED")
    root = Path(export_root).absolute()
    manifest = json.loads(read_pinned(root, verified252.gate.MANIFEST,
                                      checked["manifest_sha256"]))
    copied = manifest["copied"]
    progress = json.loads(read_pinned(root, "RUN397_PROGRESS.json",
                                      checked["progress_sha256"],
                                      copied["RUN397_PROGRESS.json"]["bytes"]))
    scores = {}
    for arm, seed in IDS:
        rid = f"{arm}_s{seed}"
        info = progress["completed"][rid]
        rel = info["attempt"] + f"/tool_{rid}.json"
        member = copied[verified252.gate.safe_rel(rel)]
        tool = json.loads(read_pinned(root, rel, member["sha256"],
                                      member["bytes"]))
        rows = validated_rows(tool, EXPECTED, rid + ":tool")
        scores[(arm, seed)] = {key: rows[key]["score"]["utility"]
                               for key in EXPECTED}
    result = aggregate(scores)
    result.update({
        "run": "Run456", "status": "RUN456_NATIVE252_UTILITY_DESCRIPTIVE_NO_GATE_PROMOTION",
        "rows_verified": 252, "completed_attempts": 6,
        "independent_receipts": checked["receipt_sha256"],
        "manifest_sha256": checked["manifest_sha256"],
        "progress_sha256": checked["progress_sha256"],
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "redmi_measured": False, "jepa_weight": 0, "native_rerun": False,
        "claim_limit": "Two-seed descriptive paired utility only. Not the frozen three-seed 378-row STEP2 gate, not causal complementarity, no B3/Body-JEPA/Age/Redmi promotion."})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--export", type=Path, required=True)
    p.add_argument("--stage6-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        result = analyze(a.export, json.loads(a.stage6_report.read_text()))
        rc = 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError) as exc:
        result = {"run": "Run456", "status": "RUN456_NATIVE252_UTILITY_RED_PRESERVED",
                  "errors": [type(exc).__name__ + ": " + str(exc)[:350]],
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                  "redmi_measured": False, "jepa_weight": 0, "native_rerun": False}
        rc = 2
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"],
                      "rows": result.get("rows_verified", 0),
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
