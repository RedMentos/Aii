#!/usr/bin/env python3
"""Run416 independent no-model export integrity + 126-row O/P/S native receipt gate."""
import argparse
import json
import os
import re
import stat
from pathlib import Path

import run394_step2_fresh as r394
import run397_step2_resume as resume
import run413_export_receipt_gate as base
from run402_stage_restore import RUN401_EXECUTABLE_SHA256

MAX_TOTAL = 400_000_000


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def verify(export_root, run415_report):
    root = Path(export_root).expanduser().absolute()
    require(root.is_dir() and not any(p.is_symlink() for p in (root, *root.parents)),
            "UNSAFE_EXPORT_ROOT")
    require(type(run415_report) is dict and run415_report.get("run") == "Run415" and
            run415_report.get("native_execute_requested") is True and
            run415_report.get("canonical_gate_pass") is False and
            run415_report.get("step2_exit") == "UTILITY_FAIL" and
            run415_report.get("redmi_measured") is False and
            type(run415_report.get("jepa_weight")) is int and
            run415_report["jepa_weight"] == 0, "FALSE_STAGE3_GATE_PROMOTION")
    exported = run415_report.get("safe_export")
    require(type(exported) is dict and
            exported.get("status") == "EXPORT_VERIFIED_NO_MODEL_WEIGHTS" and
            exported.get("errors") == [], "STAGE3_EXPORT_NOT_GREEN")
    manifest_path = root / base.MANIFEST
    require(manifest_path.is_file() and not manifest_path.is_symlink() and
            base.sha_file(manifest_path) == exported.get("manifest_sha256"),
            "STAGE3_EXPORT_MANIFEST_SHA_MISMATCH")
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get("schema") == "RUN409_SAFE_NATIVE_EXPORT_V1" and
            manifest.get("source_run") == "Run397" and
            manifest.get("canonical_gate_pass") is False and
            manifest.get("step2_exit") == "UTILITY_FAIL", "STAGE3_EXPORT_SCHEMA_INVALID")
    copied = manifest.get("copied")
    dirs = manifest.get("directories")
    omitted = manifest.get("omitted_installed_symlinks")
    require(type(copied) is dict and bool(copied) and
            type(dirs) is list and type(omitted) is list, "STAGE3_EXPORT_INVENTORY_MISSING")
    require(len(set(omitted)) == len(omitted) and
            all(type(name) is str and
                re.fullmatch(r"attempts/(?:O|P|S)_s(?:20|21|22)/attempt-[0-9]+/.+/(?:models|bin)", name)
                for name in omitted), "STAGE3_OMITTED_LINK_INVALID")
    expected = {base.safe_rel(name) for name in copied}
    require(len(expected) == len(copied) and
            {"RUN394_PREREGISTERED_FIXTURES.json", "RUN397_PROGRESS.json"}.issubset(expected),
            "STAGE3_REQUIRED_FILES_MISSING")
    actual = set()
    observed_dirs = set()
    total = 0
    model_hashes = base.registered_model_hashes()
    for current, folders, files in os.walk(root, topdown=True, followlinks=False):
        observed_dirs.add(Path(current).relative_to(root).as_posix())
        for folder in folders:
            path = Path(current) / folder
            require(not path.is_symlink() and path.is_dir(), "STAGE3_SYMLINK_DIRECTORY")
        for filename in files:
            path = Path(current) / filename
            require(not path.is_symlink(), "STAGE3_SYMLINK_FILE")
            info = path.stat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                    "STAGE3_NONREGULAR_OR_HARDLINK")
            rel = path.relative_to(root).as_posix()
            if rel == base.MANIFEST:
                continue
            base.safe_rel(rel)
            require(rel in copied, "STAGE3_UNLISTED_FILE:" + rel)
            item = copied[rel]
            require(type(item) is dict and
                    type(item.get("bytes")) is int and
                    item["bytes"] == info.st_size and info.st_size <= base.MAX_FILE and
                    type(item.get("sha256")) is str and
                    base.HEX.fullmatch(item["sha256"]), "STAGE3_FILE_METADATA_INVALID")
            digest = base.sha_file(path)
            require(digest == item["sha256"] and digest not in model_hashes,
                    "STAGE3_FILE_HASH_OR_MODEL_MISMATCH")
            total += info.st_size
            require(total <= MAX_TOTAL, "STAGE3_EXPORT_TOO_LARGE")
            actual.add(rel)
    require(actual == expected and len(set(dirs)) == len(dirs) and
            set(dirs) == observed_dirs, "STAGE3_EXPORT_TREE_MISMATCH")
    require(exported.get("copied_files") == len(actual) and
            exported.get("copied_bytes") == total, "STAGE3_EXPORT_RECEIPT_MISMATCH")
    progress_path = root / "RUN397_PROGRESS.json"
    progress = json.loads(progress_path.read_text())
    require(progress.get("canonical_gate_pass") is False and
            progress.get("step2_exit") == "UTILITY_FAIL", "STAGE3_PROGRESS_FALSE_PROMOTION")
    completed = progress.get("completed")
    failures = progress.get("failures_preserved")
    require(type(completed) is dict and type(failures) is dict and
            {"O_s20", "P_s20"}.issubset(completed) and
            set(completed).issubset({"O_s20", "P_s20", "S_s20"}),
            "STAGE3_PROGRESS_UNEXPECTED_COMPLETED")
    prereg = json.loads((root / "RUN394_PREREGISTERED_FIXTURES.json").read_text())
    for arm in ("O", "P", "S"):
        rid = arm + "_s20"
        if rid not in completed:
            continue
        entry = completed[rid]
        require(type(entry) is dict and type(entry.get("attempt")) is str and
                type(entry.get("validated")) is dict, "STAGE3_PROGRESS_ENTRY_INVALID")
        base.safe_rel(entry["attempt"])
        require(entry["attempt"].startswith("attempts/" + rid + "/"),
                "STAGE3_ATTEMPT_SCOPE_INVALID")
        validated = resume.validate_completed(
            root / entry["attempt"], arm, 20, r394.FIXTURES, prereg,
            current_runner_sha=RUN401_EXECUTABLE_SHA256)
        require(validated == entry["validated"] and validated["rows"] == 42,
                "STAGE3_NATIVE_RECEIPT_INVALID:" + arm)
    stage = run415_report.get("status")
    if stage == "STAGE3_NATIVE_PARTIAL_NO_PROMOTION":
        require(run415_report.get("errors") == [] and
                run415_report.get("native_execute_attempted") is True and
                run415_report.get("native_execution_performed") is True and
                run415_report.get("rows_verified") == 126 and
                run415_report.get("remaining_arms") == 6 and
                run415_report.get("completed") == ["O_s20", "P_s20", "S_s20"] and
                set(completed) == {"O_s20", "P_s20", "S_s20"} and not failures and
                run415_report.get("progress_sha256") == base.sha_file(progress_path),
                "STAGE3_126_ROW_NATIVE_CLAIM_INVALID")
        status = "RUN416_STAGE3_EXPORT_VERIFIED_NO_PROMOTION"
    else:
        require(stage == "STAGE3_RED_PRESERVED" and
                type(run415_report.get("errors")) is list and
                bool(run415_report["errors"]) and
                run415_report.get("native_execution_performed") is False,
                "STAGE3_RED_EVIDENCE_INVALID")
        status = "RUN416_STAGE3_EXPORT_VERIFIED_NATIVE_RED"
    return {"status": status, "copied_files": len(actual), "copied_bytes": total,
            "manifest_sha256": base.sha_file(manifest_path),
            "native_rows_verified": 42 * len(completed),
            "completed": sorted(completed), "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL", "redmi_measured": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--export", type=Path, required=True)
    p.add_argument("--run415-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = verify(args.export, json.loads(args.run415_report.read_text()))
        rc = 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError) as exc:
        result = {"status": "RUN416_STAGE3_EXPORT_RED_PRESERVED",
                  "error": type(exc).__name__ + ": " + str(exc)[:300],
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}
        rc = 2
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
