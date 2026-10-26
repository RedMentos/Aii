#!/usr/bin/env python3
"""Run412: independent fail-closed contract for the observed Run410 stage1 report.

Source-only report verification. The original 1.46GB model-bearing ZIP is never
loaded here; Run408 separately streams and checks its original SHA/CRC/receipts.
"""
import argparse
import json
import re
from pathlib import Path

ORIGINAL_ZIP_SHA256 = "65ac00a8cd2013ebab76828ed3bc25dee5433d1d55a995573387f19de29b530a"
HEX = re.compile(r"[0-9a-f]{64}\Z")
BIN_PREFIX = "run401-full/attempts/O_s20/attempt-0001/O_s20-home/bin/"
MODEL_PREFIX = "run401-full/attempts/O_s20/attempt-0001/O_s20-home/models/"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _safe_path(value, prefix):
    require(type(value) is str and value.startswith(prefix), "UNEXPECTED_INVENTORY_PATH")
    suffix = value[len(prefix):]
    require(bool(suffix) and "\\" not in suffix and
            all(part not in ("", ".", "..") for part in suffix.split("/")),
            "UNSAFE_INVENTORY_PATH")
    return value


def verify(report, expected_sha=ORIGINAL_ZIP_SHA256):
    require(type(report) is dict, "INVALID_REPORT")
    require(type(expected_sha) is str and HEX.fullmatch(expected_sha) and
            expected_sha == ORIGINAL_ZIP_SHA256, "ORIGINAL_ZIP_IDENTITY_MISMATCH")
    require(report.get("status") == "FILTERED_STAGE1_VERIFIED_NO_PROMOTION" and
            report.get("errors") == [], "ORIGINAL_STAGE1_AUDIT_RED")
    require(report.get("original_zip_sha256") == expected_sha and
            report.get("members_verified") == 107 and
            report.get("rows_verified") == 42 and
            report.get("remaining_arms") == 8, "FROZEN_STAGE1_COUNTS_MISMATCH")
    native = report.get("native")
    require(type(native) is dict and native.get("completed") == ["O_s20"] and
            native.get("rows_verified") == 42 and
            native.get("remaining_arms") == 8, "NATIVE_RECEIPT_SCOPE_MISMATCH")
    require(report.get("all_member_sha_checked") is True and
            report.get("zip_crc_checked") is True and
            report.get("original_raw_retained_external") is True,
            "RAW_INTEGRITY_NOT_VERIFIED")
    require(report.get("native_inference_started") is False and
            report.get("redmi_measured") is False and
            report.get("canonical_gate_pass") is False and
            report.get("step2_exit") == "UTILITY_FAIL" and
            type(report.get("jepa_weight")) is int and report["jepa_weight"] == 0,
            "FALSE_EVIDENCE_PROMOTION")

    models = report.get("omitted_registered_models")
    unlisted_models = report.get("omitted_unlisted_in_manifest")
    binaries = report.get("unlisted_binary_members")
    binary_hashes = report.get("unlisted_binary_hashes")
    require(type(models) is list and type(unlisted_models) is list and
            type(binaries) is list and type(binary_hashes) is dict,
            "INVENTORY_MISSING_OR_WRONG_TYPE")
    # Run406 predicted 64 binaries; the actual hash-closed Run410 raw report has 63.
    require(len(models) == 7 and len(unlisted_models) == 7 and
            len(binaries) == 63 and len(binary_hashes) == 63 and
            len(models) + len(binaries) == 70, "OBSERVED_MEMBER_PARTITION_MISMATCH")
    model_paths = []
    for item in models:
        require(type(item) is dict, "INVALID_REGISTERED_MODEL_ENTRY")
        model_paths.append(_safe_path(item.get("path"), MODEL_PREFIX))
        require(type(item.get("size")) is int and item["size"] > 0 and
                type(item.get("sha256")) is str and HEX.fullmatch(item["sha256"]) and
                type(item.get("registered_roles")) is list and
                bool(item["registered_roles"]) and
                all(type(role) is str and role for role in item["registered_roles"]),
                "INVALID_REGISTERED_MODEL_IDENTITY")
    require(len(set(model_paths)) == 7 and
            set(model_paths) == set(unlisted_models) and
            len(set(unlisted_models)) == 7, "REGISTERED_MODEL_SET_MISMATCH")
    require(len(set(binaries)) == 63 and
            set(binaries) == set(binary_hashes) and
            set(binaries).isdisjoint(model_paths), "BINARY_MEMBER_SET_MISMATCH")
    for path in binaries:
        _safe_path(path, BIN_PREFIX)
        info = binary_hashes[path]
        require(type(info) is dict and
                type(info.get("bytes")) is int and info["bytes"] > 0 and
                type(info.get("sha256")) is str and HEX.fullmatch(info["sha256"]) and
                info.get("provenance") == "ORIGINAL_ZIP_SHA_ONLY_NOT_EXECUTED",
                "UNLISTED_BINARY_HASH_OR_PROVENANCE_INVALID")
    return {"status": "RUN412_INVENTORY_CONTRACT_VERIFIED_NO_PROMOTION",
            "original_zip_sha256": expected_sha, "members": 107,
            "registered_models_omitted": 7, "unlisted_binary_members": 63,
            "native_rows": 42, "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL", "redmi_measured": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--expected-sha256", default=ORIGINAL_ZIP_SHA256)
    args = p.parse_args()
    try:
        result = verify(json.loads(args.report.read_text()), args.expected_sha256)
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "RUN412_INVENTORY_RED_PRESERVED",
                          "error": str(exc)[:300], "canonical_gate_pass": False,
                          "step2_exit": "UTILITY_FAIL"}, sort_keys=True))
        raise SystemExit(2)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
