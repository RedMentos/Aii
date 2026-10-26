#!/usr/bin/env python3
"""Run465: independently verify 336 native rows through P_s22 (eight receipts).

No inference, no model downloads and no gate promotion. Does not mutate work.
Derived conservatively from Run460 seven-receipt verifier (Git blob SHA1 2a61c2ae8600cede90900a323e22e1f5a723a3ea).
"""
import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path

import run394_step2_fresh as r394
import run397_step2_resume as r397
import run413_export_receipt_gate as gate
from run402_stage_restore import RUN401_EXECUTABLE_SHA256

PREFIX = ("O_s20", "P_s20", "S_s20", "O_s21", "P_s21", "S_s21", "O_s22", "P_s22")
ROWS = 42 * len(PREFIX)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_report(report):
    require(type(report) is dict and report.get("run") == "Run462" and
            report.get("status") == "STAGE8_NATIVE_PARTIAL_NO_PROMOTION" and
            report.get("errors") == [] and
            report.get("native_execute_requested") is True and
            report.get("native_execute_attempted") is True and
            report.get("native_execution_performed") is True and
            report.get("rows_verified") == ROWS and
            report.get("completed") == list(PREFIX) and
            report.get("remaining_arms") == 1 and
            report.get("canonical_gate_pass") is False and
            report.get("step2_exit") == "UTILITY_FAIL" and
            report.get("redmi_measured") is False and
            type(report.get("jepa_weight")) is int and
            report["jepa_weight"] == 0, "RUN465_NATIVE_336_NOT_GREEN")
    exported = report.get("safe_export")
    require(type(exported) is dict and
            exported.get("status") == "EXPORT_VERIFIED_NO_MODEL_WEIGHTS" and
            exported.get("errors") == [], "RUN453_SAFE_EXPORT_NOT_GREEN")
    return exported


def verify(root, report):
    root = Path(root).expanduser().absolute()
    require(root.is_dir() and not root.is_symlink() and
            not any(p.is_symlink() for p in root.parents),
            "EXPORT_ROOT_UNSAFE")
    exported = validate_report(report)
    manifest_path = root / gate.MANIFEST
    require(manifest_path.is_file() and not manifest_path.is_symlink() and
            manifest_path.stat().st_nlink == 1, "EXPORT_MANIFEST_UNSAFE")
    require(sha_file(manifest_path) == exported.get("manifest_sha256"),
            "EXPORT_MANIFEST_SHA_MISMATCH")
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get("schema") == "RUN409_SAFE_NATIVE_EXPORT_V1" and
            manifest.get("source_run") == "Run397" and
            manifest.get("canonical_gate_pass") is False and
            manifest.get("step2_exit") == "UTILITY_FAIL",
            "EXPORT_MANIFEST_INVALID")
    copied = manifest.get("copied")
    dirs = manifest.get("directories")
    omitted = manifest.get("omitted_installed_symlinks")
    require(type(copied) is dict and bool(copied) and
            type(dirs) is list and type(omitted) is list and
            len(set(dirs)) == len(dirs) and
            len(set(omitted)) == len(omitted), "EXPORT_INVENTORY_INVALID")
    require(all(type(x) is str and re.fullmatch(
            r"attempts/(?:O|P|S)_s(?:20|21|22)/attempt-[0-9]+/.+/(?:models|bin)", x)
            for x in omitted), "UNEXPECTED_OMITTED_SYMLINK")
    expected = {gate.safe_rel(name) for name in copied}
    require(len(expected) == len(copied) and
            {"RUN397_PROGRESS.json", "RUN394_PREREGISTERED_FIXTURES.json"} <= expected,
            "FROZEN_PROGRESS_MISSING")
    observed, observed_dirs, total = set(), set(), 0
    models = gate.registered_model_hashes()
    for current, folders, files in os.walk(root, topdown=True, followlinks=False):
        here = Path(current)
        observed_dirs.add(here.relative_to(root).as_posix())
        for name in folders:
            p = here / name
            require(p.is_dir() and not p.is_symlink(), "EXPORT_SYMLINK_DIRECTORY")
        for name in files:
            p = here / name
            require(not p.is_symlink(), "EXPORT_SYMLINK_FILE")
            info = p.stat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                    "EXPORT_NONREGULAR_OR_HARDLINK")
            rel = p.relative_to(root).as_posix()
            if rel == gate.MANIFEST:
                continue
            gate.safe_rel(rel)
            require(rel in copied, "UNLISTED_EXPORT_FILE")
            record = copied[rel]
            require(type(record) is dict and
                    type(record.get("bytes")) is int and
                    record["bytes"] == info.st_size and
                    info.st_size <= gate.MAX_FILE and
                    type(record.get("sha256")) is str and
                    gate.HEX.fullmatch(record["sha256"]),
                    "EXPORT_FILE_METADATA_INVALID")
            actual = sha_file(p)
            require(actual == record["sha256"] and actual not in models,
                    "EXPORT_HASH_OR_MODEL_IDENTITY_MISMATCH")
            total += info.st_size
            require(total <= gate.MAX_TOTAL, "EXPORT_TOTAL_EXCEEDS_BUDGET")
            observed.add(rel)
    require(observed == expected and set(dirs) == observed_dirs,
            "EXPORT_INVENTORY_MISMATCH")
    require(exported.get("copied_files") == len(observed) and
            exported.get("copied_bytes") == total, "EXPORT_RECEIPT_MISMATCH")
    progress_path = root / "RUN397_PROGRESS.json"
    require(sha_file(progress_path) == report.get("progress_sha256"),
            "PROGRESS_SHA_MISMATCH")
    progress = json.loads(progress_path.read_text())
    require(progress.get("canonical_gate_pass") is False and
            progress.get("step2_exit") == "UTILITY_FAIL" and
            progress.get("native_success_does_not_promote_step2") is True and
            set(progress.get("completed", {})) == set(PREFIX) and
            progress.get("failures_preserved") == {},
            "PROGRESS_NOT_NATIVE_336_GREEN")
    frozen_path = root / "RUN394_PREREGISTERED_FIXTURES.json"
    frozen = json.loads(frozen_path.read_text())
    require(frozen == r394.manifest(r394.FIXTURES, False, list(r394.ARMS),
                                    list(r394.SEEDS)), "FROZEN_MANIFEST_MISMATCH")
    verified = {}
    for rid in PREFIX:
        arm, seed = rid.split("_s")
        info = progress["completed"][rid]
        require(type(info) is dict and type(info.get("attempt")) is str and
                re.fullmatch(r"attempts/" + rid + r"/attempt-[0-9]+",
                             info["attempt"]) is not None,
                "STAGE8_ATTEMPT_PATH_INVALID:" + rid)
        attempt = root / info["attempt"]
        require(not attempt.is_symlink() and
                attempt.resolve().is_relative_to(root.resolve()),
                "STAGE8_ATTEMPT_ESCAPE:" + rid)
        actual = r397.validate_completed(
            attempt, arm, int(seed), r394.FIXTURES, frozen,
            current_runner_sha=RUN401_EXECUTABLE_SHA256)
        require(actual == info.get("validated") and actual["rows"] == 42,
                "STAGE8_NATIVE_RECEIPT_INVALID:" + rid)
        verified[rid] = actual["sha256"]
    return {"run": "Run465", "status": "RUN465_NATIVE_336_INDEPENDENTLY_VERIFIED",
            "verified_arms": list(PREFIX), "rows_verified": ROWS,
            "receipt_sha256": verified, "copied_files": len(observed),
            "copied_bytes": total, "manifest_sha256": sha_file(manifest_path),
            "progress_sha256": sha_file(progress_path),
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "redmi_measured": False, "jepa_weight": 0,
            "native_execution_performed": False,
            "claim_limit": "Linux-native 336/378 structural rows; no full STEP2/B3/Body-JEPA/Age/Redmi promotion."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--export", type=Path, required=True)
    p.add_argument("--stage6-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        result = verify(a.export, json.loads(a.stage6_report.read_text()))
        code = 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError) as exc:
        result = {"run": "Run465", "status": "RUN465_NATIVE_336_RED_PRESERVED",
                  "errors": [type(exc).__name__ + ": " + str(exc)[:350]],
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                  "redmi_measured": False, "jepa_weight": 0,
                  "native_execution_performed": False}
        code = 2
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"],
                      "rows": result.get("rows_verified", 0),
                      "canonical_gate_pass": False,
                      "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
