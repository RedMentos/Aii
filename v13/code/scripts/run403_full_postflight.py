#!/usr/bin/env python3
"""Run403: independent read-only FULL 378-row STEP2 postflight, no native inference/gate promotion."""
import argparse
import hashlib
import json
from pathlib import Path

import run394_step2_fresh as r394
import run397_step2_resume as r397
from run396_step2_pilot_audit import load, sha, validated_rows
from v13.models import catalog

VARIANTS = tuple(r397.VARIANTS)
ARMS = tuple(r394.ARMS)
SEEDS = tuple(r394.SEEDS)
FIXTURES = tuple(f["id"] for f in r394.FIXTURES)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def mean(values):
    require(bool(values), "EMPTY_AGGREGATE")
    return sum(values) / len(values)


def validated_failed_attempts(work, progress, ids):
    """Preserve negative history: every claimed failed attempt must still have raw bytes."""
    failures = progress.get("failures_preserved")
    require(type(failures) is dict, "FAILED_HISTORY_NOT_A_MAP")
    for rid, entries in failures.items():
        require(rid in ids and type(entries) is list and bool(entries),
                "FAILED_HISTORY_ARM_INVALID:" + str(rid))
        for entry in entries:
            require(type(entry) is dict and type(entry.get("attempt")) is str,
                    "FAILED_ATTEMPT_POINTER_INVALID:" + rid)
            rel = Path(entry["attempt"])
            require(not rel.is_absolute() and ".." not in rel.parts and
                    rel.parts[:2] == ("attempts", rid) and len(rel.parts) == 3 and
                    rel.parts[2].startswith("attempt-") and rel.parts[2][8:].isdigit(),
                    "UNSAFE_FAILED_ATTEMPT_POINTER:" + rid)
            directory = Path(work) / rel
            require(not directory.is_symlink() and directory.is_dir(),
                    "FAILED_ATTEMPT_RAW_MISSING:" + rid)
            children = list(directory.iterdir())
            require(bool(children) and not any(p.is_symlink() for p in children) and
                    any(p.is_file() for p in children),
                    "FAILED_ATTEMPT_RAW_MISSING_OR_UNSAFE:" + rid)
    return failures


def _audit(work):
    work = Path(work)
    expected_manifest = r394.manifest(r394.FIXTURES, False, list(ARMS), list(SEEDS))
    manifest_path = work / "RUN394_PREREGISTERED_FIXTURES.json"
    manifest = load(manifest_path)
    require(manifest == expected_manifest and manifest.get("stage") == "FULL",
            "FULL_FROZEN_MANIFEST_MISMATCH")
    progress_path = work / "RUN397_PROGRESS.json"
    progress = load(progress_path)
    ids = {f"{arm}_s{seed}" for seed in SEEDS for arm in ARMS}
    failed_history = validated_failed_attempts(work, progress, ids)
    require(progress.get("status") == "ALL_ARMS_STRUCTURALLY_RECORDED" and
            set(progress.get("completed", {})) == ids, "FULL_COHORT_INCOMPLETE")
    require(progress.get("canonical_gate_pass") is False and
            progress.get("step2_exit") == "UTILITY_FAIL" and
            progress.get("native_success_does_not_promote_step2") is True,
            "FALSE_GATE_PROMOTION")
    require(progress.get("manifest_sha256") == sha(manifest_path),
            "PROGRESS_MANIFEST_HASH_MISMATCH")
    expected_rows = {(fixture, variant) for fixture in FIXTURES for variant in VARIANTS}
    runner_sha = catalog()["runner"]["linux_binaries"]["linux-x86_64"]["sha256"]
    all_rows = {}
    bound = {}
    for seed in SEEDS:
        for arm in ARMS:
            rid = f"{arm}_s{seed}"
            info = progress["completed"][rid]
            require(type(info) is dict and type(info.get("attempt")) is str,
                    "INVALID_ATTEMPT_POINTER:" + rid)
            rel = Path(info["attempt"])
            require(not rel.is_absolute() and ".." not in rel.parts and
                    rel.parts[:2] == ("attempts", rid) and
                    len(rel.parts) == 3 and rel.parts[2].startswith("attempt-"),
                    "UNSAFE_ATTEMPT_POINTER:" + rid)
            attempt = work / rel
            require(not attempt.is_symlink() and attempt.is_dir(),
                    "ATTEMPT_MISSING:" + rid)
            verified = r397.validate_completed(attempt, arm, seed, r394.FIXTURES,
                                                manifest, current_runner_sha=runner_sha)
            require(verified == info.get("validated") and verified["rows"] == 42,
                    "ATTEMPT_VALIDATION_MISMATCH:" + rid)
            receipt = load(attempt / "RUN397_ATTEMPT.json")
            require(receipt.get("schema") == r397.SCHEMA and
                    receipt.get("status") == "COMPLETE" and
                    receipt.get("arm") == arm and receipt.get("seed") == seed and
                    receipt.get("validated") == verified, "RECEIPT_MISMATCH:" + rid)
            tool = load(attempt / f"tool_{rid}.json")
            rows = validated_rows(tool, expected_rows, rid + ":tool")
            all_rows[(arm, seed)] = {key: rows[key]["score"]["utility"]
                                      for key in expected_rows}
            bound[rid] = {"attempt": str(rel), "validated": verified,
                          "receipt_sha256": sha(attempt / "RUN397_ATTEMPT.json"),
                          "tool_sha256": sha(attempt / f"tool_{rid}.json")}
    require(len(all_rows) == 9 and
            sum(len(v) for v in all_rows.values()) == 378, "ROW_COVERAGE_INCOMPLETE")
    arm_mean = {arm: {v: mean([all_rows[(arm, s)][(f, v)] for s in SEEDS for f in FIXTURES])
                      for v in VARIANTS} for arm in ARMS}
    paired = {}
    for label, a, b in (("pointer_minus_off", "P", "O"),
                        ("pointer_minus_shared_body", "P", "S")):
        paired[label] = {}
        for v in VARIANTS:
            by_seed_fixture = {str(s): {f: all_rows[(a, s)][(f, v)] -
                                            all_rows[(b, s)][(f, v)] for f in FIXTURES}
                               for s in SEEDS}
            values = [by_seed_fixture[str(s)][f] for s in SEEDS for f in FIXTURES]
            paired[label][v] = {
                "mean": mean(values), "paired_count": len(values),
                "by_seed": {str(s): mean(list(by_seed_fixture[str(s)].values())) for s in SEEDS},
                "by_fixture": {f: mean([by_seed_fixture[str(s)][f] for s in SEEDS])
                               for f in FIXTURES},
                "by_seed_fixture": by_seed_fixture}
    return {"run": "Run403", "status": "FULL_POSTFLIGHT_VERIFIED_NO_GATE_PROMOTION",
            "evidence_level": "REPORT_STRUCTURE_ONLY_ORIGIN_REQUIRES_EXTERNAL_NATIVE_ARTIFACT",
            "source_run": "Run397", "native_rerun": False,
            "fixture_ids": list(FIXTURES), "seeds": list(SEEDS), "arms": list(ARMS),
            "variants": list(VARIANTS), "rows_verified": 378,
            "completed_attempts": 9, "arm_mean_utility": arm_mean,
            "paired_differences": paired, "attempts": bound,
            "failed_attempts_preserved": failed_history,
            "manifest_sha256": sha(manifest_path), "progress_sha256": sha(progress_path),
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "redmi_measured": False, "jepa_weight": 0,
            "claim_limit": "All 378 structurally verified reports; native provenance external. "
                           "No STEP2/B3/Body-JEPA/Age/V13 gate promotion."}


def audit(work):
    try:
        return _audit(work)
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError) as exc:
        return {"run": "Run403", "status": "FULL_INCOMPLETE_OR_RED",
                "errors": [type(exc).__name__ + ": " + str(exc)[:350]],
                "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                "redmi_measured": False, "jepa_weight": 0, "native_rerun": False,
                "evidence_level": "NO_COMPLETE_COHORT_PROOF"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = audit(args.work)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "rows": report.get("rows_verified", 0),
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(0 if report["status"] == "FULL_POSTFLIGHT_VERIFIED_NO_GATE_PROMOTION" else 2)


if __name__ == "__main__":
    main()
