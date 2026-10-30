#!/usr/bin/env python3
"""Read-only paired AG12 vote diagnostic from immutable Run25 and Run27 native ZIPs.

No model calls, raw prompts, source writes, or learning/age promotion. Only
aggregated correctness counts are exported; p-values are exploratory posthoc.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import zipfile

EXPECTED = {
    "run25": ("4a4b99a12cc2b60fa755aab7db5930cb9f8cd65ceea76272d8b2279e1b08331e", 27),
    "run27": ("6263b4f84060eec826cd819fdc108a6ac609b5261d84df0508d889736305d7ae", 23),
}


def open_verified(path: Path, role: str):
    expected_sha, count = EXPECTED[role]
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise ValueError("RUN30_ZIP_SHA_MISMATCH_" + role)
    z = zipfile.ZipFile(path)
    try:
        if z.testzip() is not None:
            raise ValueError("RUN30_ZIP_CRC_RED")
        lines = z.read("SHA256SUMS").decode("utf-8").splitlines()
        if len(lines) != count:
            raise ValueError("RUN30_INNER_MANIFEST_COUNT_RED")
        seen = set()
        for line in lines:
            digest, member = line.split("  ", 1)
            member = member.removeprefix("./")
            if member in seen or member == "SHA256SUMS":
                raise ValueError("RUN30_DUPLICATE_MANIFEST_RED")
            seen.add(member)
            if hashlib.sha256(z.read(member)).hexdigest() != digest:
                raise ValueError("RUN30_INNER_SHA_RED")
        if seen != set(z.namelist()) - {"SHA256SUMS"}:
            raise ValueError("RUN30_INCOMPLETE_MANIFEST_RED")
        for name in z.namelist():
            if name.endswith("_EXIT.txt") and z.read(name).decode().strip() != "0":
                raise ValueError("RUN30_STAGE_EXIT_RED:" + name)
        return z
    except Exception:
        z.close()
        raise


def paired_counts(baseline, vote):
    """Exact paired correctness by identical ordered task ID, no model quality claims."""
    if len(baseline) != 88 or len(vote) != 88:
        raise ValueError("RUN30_ROW_COUNT_RED")
    a_ids = [x["id"] for x in baseline]
    b_ids = [x["id"] for x in vote]
    if a_ids != b_ids or len(set(a_ids)) != 88:
        raise ValueError("RUN30_ROW_ALIGNMENT_RED")
    if not all(type(x["correct"]) is int and x["correct"] in (0, 1)
               for x in baseline + vote):
        raise ValueError("RUN30_CORRECTNESS_SCHEMA_RED")
    both = sum(a["correct"] == 1 and b["correct"] == 1
               for a, b in zip(baseline, vote))
    vote_only = sum(a["correct"] == 0 and b["correct"] == 1
                    for a, b in zip(baseline, vote))
    base_only = sum(a["correct"] == 1 and b["correct"] == 0
                    for a, b in zip(baseline, vote))
    neither = 88 - both - vote_only - base_only
    n = vote_only + base_only
    p = min(1., 2 * sum(math.comb(n, k) for k in
                        range(min(vote_only, base_only) + 1)) / 2 ** n) if n else 1.
    return {
        "items": 88, "baseline_correct": both + base_only,
        "vote_correct": both + vote_only, "both_correct": both,
        "both_wrong": neither, "vote_only_correct": vote_only,
        "baseline_only_correct": base_only,
        "delta_correct": vote_only - base_only,
        "mcnemar_exact_two_sided_posthoc": round(p, 6),
    }


def audit(run25: Path, run27: Path):
    z25 = open_verified(run25, "run25")
    z27 = open_verified(run27, "run27")
    try:
        m25 = json.loads(z25.read("native/REPORT.json"))
        m27 = json.loads(z27.read("native/REPORT.json"))
        if (m25["evidence_kind"] != "LINUX_NATIVE_B1_B2_AG12_ONLY"
                or m25["expected_native_calls"] != 352
                or m27["evidence_kind"] != "LINUX_NATIVE_AG12_BODYSOLVER_VOTE_ONLY"
                or m27["native_role_calls"] != 528
                or m27["voted_items"] != 176
                or m27["redmi_measured"]
                or m27["whole_system_complete"]):
            raise ValueError("RUN30_NATIVE_PROVENANCE_RED")
        out = {
            "schema": "v13.run30.ag12_native_vote_paired_readonly.v1",
            "evidence": "POSTHOC_READONLY_LINUX_NATIVE_ROW_DIAGNOSTIC",
            "sources": {role: EXPECTED[role][0] for role in EXPECTED},
            "pairs": {}, "pre_registered_utility_gate": False,
            "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "redmi_measured": False,
            "whole_system_complete": False,
        }
        for lang in ("DE", "EN"):
            vote = json.loads(z27.read(f"native/AG12_{lang}_ROWS.json"))
            if vote["status"] != "DONE" or len(vote["results"]) != 88:
                raise ValueError("RUN30_VOTE_ROWS_RED")
            for body in ("b1", "b2"):
                base = json.loads(z25.read(f"native/{body}/AG12_{lang}_ROWS.json"))
                if (base["status"] != "DONE" or
                        base["suite_hash"] != vote["suite_hash"]):
                    raise ValueError("RUN30_SUITE_HASH_RED")
                out["pairs"][f"{lang.lower()}_{body}"] = {
                    "suite_hash": vote["suite_hash"],
                    **paired_counts(base["results"], vote["results"]),
                }
        return out
    finally:
        z25.close()
        z27.close()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run25", required=True, type=Path)
    p.add_argument("--run27", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    if args.out.exists():
        raise FileExistsError("RUN30_FRESH_RESULT_REQUIRED")
    result = audit(args.run25, args.run27)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("RUN30_POSTHOC_READONLY_COMPLETE_NO_GATE_PROMOTION")


if __name__ == "__main__":
    main()
