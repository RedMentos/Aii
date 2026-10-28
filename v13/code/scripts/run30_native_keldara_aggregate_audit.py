"""Read-only, source-bound aggregate audit of the original Run26 native ZIP.

No model execution, mutation, raw prompt/answer export, or gate promotion.
Only aggregate fixed-field correctness masks may leave the private evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import zipfile

HEAD = "03c664c6a70eebe943ec6a0384a24814ca59c0c5"
ZIP_SHA256 = "989abb8ac7b8fcd91ec047f97b735c9c8f84342e49251855b3375f7b3519762b"
RAW_SHA256 = "0a1ce865d590adb5c4ead5007f42c202dbe6f24140a562ebdbc44bcb9f39baf3"
FIXTURE_SHA256 = "a57c93c230db4fb8118662c97c5bd3f0bea2ded1cbb481d87ec593371205df73"
SOURCE_BLOB = "635e5727a42cb1eac4f84441afda2977b0c8109c"
VARIANTS = ("b1_only", "b2_only", "both_none", "both_exact",
            "both_control", "same_policy_dual", "prompt_only_dual")
FIELDS = frozenset(("project", "action", "A.cost", "A.remaining",
                    "A.days", "A.local", "A.eligible", "B.cost",
                    "B.remaining", "B.days", "B.local", "B.eligible"))
MODEL_ROLES = {"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _canonical(row):
    return json.dumps(row, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def audit_zip(path, *, expected_zip_sha=ZIP_SHA256, expected_head=HEAD,
              expected_raw_sha=RAW_SHA256):
    """Reject unsealed/mutated native proof; return no private source or answer."""
    path = Path(path)
    if _sha(path.read_bytes()) != expected_zip_sha:
        raise ValueError("native_zip_sha_mismatch")
    with zipfile.ZipFile(path) as z:
        members = z.namelist()
        if (not members or len(members) != len(set(members)) or
                any("/" in name or "\\" in name or name.startswith(".")
                    for name in members) or
                sum(i.file_size for i in z.infolist()) > 20_000_000 or
                z.testzip() is not None):
            raise ValueError("native_zip_members_or_crc")
        lines = z.read("SHA256SUMS.txt").decode("utf-8").splitlines()
        sums = {}
        for line in lines:
            sha, separator, name = line.partition("  ")
            name = name.removeprefix("./")
            if (not separator or len(sha) != 64 or name in sums or
                    name == "SHA256SUMS.txt"):
                raise ValueError("native_inner_manifest_invalid")
            sums[name] = sha
        if set(sums) != set(members) - {"SHA256SUMS.txt"}:
            raise ValueError("native_inner_manifest_incomplete")
        for name, sha in sums.items():
            if _sha(z.read(name)) != sha:
                raise ValueError("native_inner_sha_mismatch")
        if z.read("HEAD.txt").decode("ascii").strip() != expected_head:
            raise ValueError("native_head_mismatch")
        raw = z.read("STEP2_RAW.json")
        if _sha(raw) != expected_raw_sha:
            raise ValueError("native_raw_sha_mismatch")
        report = json.loads(raw)
        receipt = json.loads(z.read("RECEIPT.json"))

    if (receipt.get("schema") != "v13.step2.run16.keldara.native_pilot.v1" or
            receipt.get("status") != "PASS_SCOPED_ONE_FIXTURE_NATIVE_NO_UTILITY_GATE" or
            receipt.get("fixture_id") != "Keldara" or
            receipt.get("fixture_limit") != 1 or
            receipt.get("fixture_sha256") != FIXTURE_SHA256 or
            receipt.get("fixture_source_git_blob") != SOURCE_BLOB or
            receipt.get("raw_report_sha256") != expected_raw_sha or
            receipt.get("arm") != "CQ" or receipt.get("seed") != 20261114 or
            receipt.get("model_hashes_unchanged") is not True or
            receipt.get("runner_unchanged") is not True or
            receipt.get("model_hashes_before") != receipt.get("model_hashes_after") or
            receipt.get("runner_sha256_before") != receipt.get("runner_sha256_after") or
            set(receipt.get("model_hashes_before", {})) != MODEL_ROLES or
            receipt.get("native_offer_counts") != {"offers": 12, "with_question": 12} or
            receipt.get("rows") != 7 or receipt.get("native_consumer_final") != 7 or
            receipt.get("canonical_gate_pass") is not False or
            receipt.get("whole_system_complete") is not False or
            receipt.get("age_authority") != 0 or receipt.get("jepa_weight") != 0 or
            receipt.get("weight_updates") is not False or
            receipt.get("redmi_measured") is not False or
            report.get("fixture_sha256") != FIXTURE_SHA256 or
            report.get("canonical_gate_pass") is not False or
            report.get("phone_measured") is not False or
            report.get("all_structural_checks_passed") is not True):
        raise ValueError("native_receipt_or_scope_mismatch")

    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != len(VARIANTS):
        raise ValueError("native_rows_missing")
    expected_keys = {"Keldara:" + v for v in VARIANTS}
    if set(report.get("row_sha256", {})) != expected_keys:
        raise ValueError("native_row_hash_index_invalid")
    scores = {}
    failures = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("native_row_not_dict")
        variant = row.get("variant")
        if (variant not in VARIANTS or variant in scores or
                row.get("fixture") != "Keldara" or
                row.get("status") != "RECORDED" or
                row.get("processes_reaped") is not True or
                row.get("oracle_visible_to_native") is not False or
                row.get("native_consumer_metrics", {}).get("status") != "FINAL" or
                _sha(_canonical(row)) != report["row_sha256"]["Keldara:" + variant]):
            raise ValueError("native_row_integrity_invalid")
        score = row.get("score", {})
        checks = score.get("field_checks", {})
        if (not isinstance(checks, dict) or set(checks) != FIELDS or
                any(type(v) is not bool for v in checks.values())):
            raise ValueError("native_field_checks_invalid")
        bad = sorted(k for k, ok in checks.items() if not ok)
        if (set(score.get("contradictions", [])) != set(bad) or
                score.get("contradiction_count") != len(bad) or
                score.get("scored_fields") != len(FIELDS) or
                score.get("exact") is not (not bad) or
                not isinstance(score.get("utility"), (int, float)) or
                not math.isclose(score["utility"],
                                 (len(FIELDS) - len(bad)) / len(FIELDS),
                                 abs_tol=1e-12)):
            raise ValueError("native_field_score_inconsistent")
        scores[variant] = score["utility"]
        failures[variant] = bad
    if set(scores) != set(VARIANTS):
        raise ValueError("native_variants_incomplete")

    return {
        "schema": "v13.run30.keldara.native.aggregate.v1",
        "evidence_level": "LINUX_NATIVE_ONE_FIXTURE_ORIGINAL_RAW_AUDIT",
        "source_run_id": 40715223545,
        "source_head": expected_head,
        "raw_sha256": expected_raw_sha,
        "zip_sha256": expected_zip_sha,
        "variant_utility": {v: scores[v] for v in VARIANTS},
        "variant_failed_fields": {v: failures[v] for v in VARIANTS},
        "common_failed_fields": sorted(set.intersection(
            *(set(failures[v]) for v in VARIANTS))),
        "both_exact_minus_b1_only": scores["both_exact"] - scores["b1_only"],
        "all_variants_exact": all(not failures[v] for v in VARIANTS),
        "canonical_gate_pass": False,
        "phone_measured": False,
        "jepa_weight": 0,
        "whole_system_complete": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_native_zip")
    args = parser.parse_args(argv)
    print(json.dumps(audit_zip(args.private_native_zip),
                     sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
