#!/usr/bin/env python3
"""Run415: hash-verified atomic restore of Run413 no-model work, optional S_s20.

Never reads or uploads original model-bearing ZIP. No inference without --execute.
Preserves all native receipts and failed attempts; every canonical gate stays RED.
"""
import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path

import run394_step2_fresh as r394
import run397_step2_resume as resume
import run409_safe_export as safe
import run413_export_receipt_gate as gate
from run402_stage_restore import RUN401_EXECUTABLE_SHA256


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _copy_checked(source, dest, expected):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(source, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                "RESTORE_NONREGULAR_OR_HARDLINK")
        require(before.st_size == expected["bytes"], "RESTORE_SOURCE_SIZE_MISMATCH")
        digest = hashlib.sha256()
        with os.fdopen(os.dup(fd), "rb") as reader, dest.open("xb") as writer:
            while True:
                block = reader.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
                writer.write(block)
            writer.flush()
            os.fsync(writer.fileno())
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                "RESTORE_SOURCE_CHANGED_DURING_COPY")
        require(digest.hexdigest() == expected["sha256"] and
                safe.sha_file(dest) == expected["sha256"], "RESTORE_SHA_MISMATCH")
    finally:
        os.close(fd)


def restore(export_root, run411_report, destination):
    """Verify source, atomically restore all regular files except export manifest."""
    checked = gate.verify(export_root, run411_report)
    require(checked["status"] == "RUN413_EXPORT_VERIFIED_NATIVE_PARTIAL",
            "P_S20_NATIVE_84_ROWS_NOT_VERIFIED")
    source = Path(export_root).expanduser().absolute()
    dest = Path(destination).expanduser().absolute()
    require(dest.parent.is_dir() and not dest.exists() and not dest.is_symlink(),
            "DESTINATION_NOT_FRESH")
    require(not any(p.is_symlink() for p in (source, *source.parents, dest, *dest.parents)),
            "SOURCE_OR_DESTINATION_PARENT_SYMLINK")
    manifest = json.loads((source / gate.MANIFEST).read_text())
    with tempfile.TemporaryDirectory(prefix="run415-stage3-", dir=dest.parent) as td:
        stage = Path(td) / "work"
        stage.mkdir()
        for name in sorted(manifest["directories"], key=lambda n: (n.count("/"), n)):
            if name == ".":
                continue
            gate.safe_rel(name)
            (stage / name).mkdir(parents=True, exist_ok=False)
        for name, info in sorted(manifest["copied"].items()):
            gate.safe_rel(name)
            target = stage / name
            require(target.parent.is_dir(), "RESTORE_PARENT_DIRECTORY_MISSING")
            _copy_checked(source / name, target, info)
        require(not (stage / gate.MANIFEST).exists(), "EXPORT_MANIFEST_MUST_NOT_ENTER_WORK")
        safe._rename_noreplace(stage, dest)
    return {"restored_work": str(dest), "files_restored": len(manifest["copied"]),
            "export_manifest_sha256": safe.sha_file(source / gate.MANIFEST),
            "source_run413_status": checked["status"], "rows_verified": 84,
            "completed": ["O_s20", "P_s20"], "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL", "redmi_measured": False}



def verify_restored_native_receipts(work, runner_sha):
    """Fail closed before scheduling any native arm: O/P must really be reusable."""
    root = Path(work).absolute()
    manifest = json.loads((root / "RUN394_PREREGISTERED_FIXTURES.json").read_text())
    expected = r394.manifest(r394.FIXTURES, False, list(r394.ARMS), list(r394.SEEDS))
    require(manifest == expected, "STAGE3_FROZEN_MANIFEST_MISMATCH")
    progress = json.loads((root / "RUN397_PROGRESS.json").read_text())
    require(progress.get("canonical_gate_pass") is False and
            progress.get("step2_exit") == "UTILITY_FAIL" and
            set(progress.get("completed", {})) == {"O_s20", "P_s20"} and
            not progress.get("failures_preserved"), "STAGE3_PREVIOUS_PROGRESS_INVALID")
    for arm in ("O", "P"):
        info = progress["completed"][arm + "_s20"]
        require(type(info) is dict and type(info.get("attempt")) is str and
                re.fullmatch(r"attempts/" + arm + r"_s20/attempt-[0-9]+",
                             info["attempt"]) is not None,
                "STAGE3_PREVIOUS_ATTEMPT_PATH_INVALID")
        directory = root / info["attempt"]
        require(not directory.is_symlink() and
                directory.resolve().is_relative_to(root.resolve()),
                "STAGE3_PREVIOUS_ATTEMPT_ESCAPE")
        actual = resume.validate_completed(
            directory, arm, 20, r394.FIXTURES, manifest,
            current_runner_sha=runner_sha)
        require(actual == info.get("validated") and actual["rows"] == 42,
                "STAGE3_PREFLIGHT_RECEIPT_INVALID:" + arm)
    return {"status": "STAGE3_PREVIOUS_84_ROWS_VERIFIED",
            "completed": ["O_s20", "P_s20"], "rows_verified": 84,
            "runner_sha256": runner_sha, "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL"}


def stage3(export_root, run411_report, work, installed=None, execute=False, export_dest=None):
    report = {"run": "Run415", "status": "STAGE3_RED_PRESERVED",
              "errors": [], "native_execute_requested": bool(execute),
              "native_execute_attempted": False, "native_execution_performed": False,
              "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
              "redmi_measured": False, "jepa_weight": 0}
    if execute and (installed is None or export_dest is None):
        report["errors"].append("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE")
        return report
    restored = False
    try:
        stage = restore(export_root, run411_report, work)
        report["stage2"] = stage
        report["restored_work"] = stage["restored_work"]
        report["completed"] = ["O_s20", "P_s20"]
        report["rows_verified"] = 84
        report["remaining_arms"] = 7
        restored = True
        if not execute:
            report["status"] = "STAGE3_READY_NO_NATIVE"
        else:
            installed = Path(installed)
            require(safe.sha_file(installed / "bin/llama-server") ==
                    RUN401_EXECUTABLE_SHA256, "INSTALLED_RUNNER_SHA_MISMATCH")
            report["native_preflight"] = verify_restored_native_receipts(
                work, RUN401_EXECUTABLE_SHA256)
            report["native_execute_attempted"] = True
            result = resume.run(work, installed, pilot=False, execute=True, max_new_arms=1)
            require(result.get("status") == "INCOMPLETE" and
                    set(result.get("completed", {})) == {"O_s20", "P_s20", "S_s20"} and
                    not result.get("failures_preserved"), "STAGE3_NEXT_ARM_NOT_COMPLETE")
            require(result.get("canonical_gate_pass") is False and
                    result.get("step2_exit") == "UTILITY_FAIL", "FALSE_GATE_PROMOTION")
            manifest = json.loads((Path(work) / "RUN394_PREREGISTERED_FIXTURES.json").read_text())
            for arm in ("O", "P", "S"):
                info = result["completed"][arm + "_s20"]
                actual = resume.validate_completed(
                    Path(work) / info["attempt"], arm, 20, r394.FIXTURES, manifest,
                    current_runner_sha=RUN401_EXECUTABLE_SHA256)
                require(actual == info["validated"] and actual["rows"] == 42,
                        "STAGE3_RECEIPT_INVALID:" + arm)
            report.update(status="STAGE3_NATIVE_PARTIAL_NO_PROMOTION",
                          native_execution_performed=True,
                          completed=["O_s20", "P_s20", "S_s20"],
                          rows_verified=126, remaining_arms=6,
                          progress_sha256=safe.sha_file(Path(work) / "RUN397_PROGRESS.json"))
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, IndexError,
            json.JSONDecodeError) as exc:
        report["errors"].append(type(exc).__name__ + ": " + str(exc)[:350])
    finally:
        if restored and installed is not None and export_dest is not None:
            exported = safe.export(work, installed, export_dest)
            report["safe_export"] = exported
            if exported["status"] != "EXPORT_VERIFIED_NO_MODEL_WEIGHTS":
                report["errors"].append("SAFE_EXPORT_RED:" +
                                        ";".join(exported.get("errors", [])))
                report["status"] = "STAGE3_RED_PRESERVED"
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--export", type=Path, required=True)
    p.add_argument("--run411-report", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True, help="fresh private work tree")
    p.add_argument("--installed-home", type=Path)
    p.add_argument("--export-destination", type=Path)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        source_report = json.loads(args.run411_report.read_text())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        source_report = {"run": "Run411", "status": "STAGE2_RED_PRESERVED",
                         "errors": [str(exc)[:180]]}
    result = stage3(args.export, source_report, args.work, args.installed_home,
                    args.execute, args.export_destination)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "errors": result["errors"],
                      "rows": result.get("rows_verified", 0),
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(0 if result["status"] in
                     ("STAGE3_READY_NO_NATIVE", "STAGE3_NATIVE_PARTIAL_NO_PROMOTION") else 2)


if __name__ == "__main__":
    main()
