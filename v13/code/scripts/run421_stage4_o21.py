#!/usr/bin/env python3
"""Run421: from independently verified 126-row S_s20 export to one O_s21 arm.

Source-only by default. Requires actual Run415 report + Run419 verification;
native execution requires explicit --execute, pinned installed models/runner,
exact previous receipts and a fresh no-model export destination. No STEP2
promotion, no model-bearing artifact upload and no silent arm retries.
"""
import argparse
import json
import re
import tempfile
from pathlib import Path

import run394_step2_fresh as r394
import run397_step2_resume as resume
import run409_safe_export as safe
import run413_export_receipt_gate as gate
import run415_stage3_no_model_restore as stage3
import run419_verify_stage3_native as audit
from run402_stage_restore import RUN401_EXECUTABLE_SHA256

PREFIX = ("O_s20", "P_s20", "S_s20")
NEXT = "O_s21"
ALL = PREFIX + (NEXT,)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def restore(export_root, stage3_report, destination):
    checked = audit.verify(export_root, stage3_report)
    require(checked["status"] == "RUN419_NATIVE_126_INDEPENDENTLY_VERIFIED",
            "STAGE3_126_NOT_VERIFIED")
    source = Path(export_root).expanduser().absolute()
    dest = Path(destination).expanduser().absolute()
    require(dest.parent.is_dir() and not dest.exists() and not dest.is_symlink(),
            "DESTINATION_NOT_FRESH")
    require(not any(p.is_symlink() for p in (source, *source.parents,
                                            dest, *dest.parents)),
            "SOURCE_OR_DESTINATION_PARENT_SYMLINK")
    manifest = json.loads((source / gate.MANIFEST).read_text())
    with tempfile.TemporaryDirectory(prefix="run421-stage4-", dir=dest.parent) as td:
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
            stage3._copy_checked(source / name, target, info)
        require(not (stage / gate.MANIFEST).exists(),
                "EXPORT_MANIFEST_MUST_NOT_ENTER_WORK")
        safe._rename_noreplace(stage, dest)
    return {"restored_work": str(dest), "files_restored": len(manifest["copied"]),
            "export_manifest_sha256": safe.sha_file(source / gate.MANIFEST),
            "source_run419_status": checked["status"], "rows_verified": 126,
            "completed": list(PREFIX), "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL"}


def verify_previous(work, runner_sha):
    root = Path(work).absolute()
    manifest = json.loads((root / "RUN394_PREREGISTERED_FIXTURES.json").read_text())
    require(manifest == r394.manifest(r394.FIXTURES, False, list(r394.ARMS),
                                      list(r394.SEEDS)), "STAGE4_FROZEN_MANIFEST_MISMATCH")
    progress = json.loads((root / "RUN397_PROGRESS.json").read_text())
    require(progress.get("canonical_gate_pass") is False and
            progress.get("step2_exit") == "UTILITY_FAIL" and
            set(progress.get("completed", {})) == set(PREFIX) and
            not progress.get("failures_preserved"),
            "STAGE4_PREVIOUS_PROGRESS_INVALID")
    for rid in PREFIX:
        arm, seed = rid.split("_s")
        info = progress["completed"][rid]
        require(type(info) is dict and type(info.get("attempt")) is str and
                re.fullmatch(r"attempts/" + rid + r"/attempt-[0-9]+",
                             info["attempt"]) is not None,
                "STAGE4_PREVIOUS_ATTEMPT_PATH_INVALID")
        directory = root / info["attempt"]
        require(not directory.is_symlink() and
                directory.resolve().is_relative_to(root.resolve()),
                "STAGE4_PREVIOUS_ATTEMPT_ESCAPE")
        actual = resume.validate_completed(
            directory, arm, int(seed), r394.FIXTURES, manifest,
            current_runner_sha=runner_sha)
        require(actual == info.get("validated") and actual["rows"] == 42,
                "STAGE4_PREFLIGHT_RECEIPT_INVALID:" + rid)
    return {"status": "STAGE4_PREVIOUS_126_ROWS_VERIFIED",
            "completed": list(PREFIX), "rows_verified": 126,
            "runner_sha256": runner_sha, "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL"}


def stage4(export_root, stage3_report, work, installed=None, execute=False,
           export_dest=None):
    report = {"run": "Run421", "status": "STAGE4_RED_PRESERVED",
              "errors": [], "native_execute_requested": bool(execute),
              "native_execute_attempted": False, "native_execution_performed": False,
              "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
              "redmi_measured": False, "jepa_weight": 0}
    if execute and (installed is None or export_dest is None):
        report["errors"].append("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE")
        return report
    restored = False
    try:
        previous = restore(export_root, stage3_report, work)
        report["stage3"] = previous
        report["restored_work"] = previous["restored_work"]
        report["completed"] = list(PREFIX)
        report["rows_verified"] = 126
        report["remaining_arms"] = 6
        restored = True
        if not execute:
            report["status"] = "STAGE4_READY_NO_NATIVE"
        else:
            installed = Path(installed)
            require(safe.sha_file(installed / "bin/llama-server") ==
                    RUN401_EXECUTABLE_SHA256, "INSTALLED_RUNNER_SHA_MISMATCH")
            report["native_preflight"] = verify_previous(
                work, RUN401_EXECUTABLE_SHA256)
            report["native_execute_attempted"] = True
            result = resume.run(work, installed, pilot=False, execute=True,
                                max_new_arms=1)
            require(result.get("status") == "INCOMPLETE" and
                    set(result.get("completed", {})) == set(ALL) and
                    not result.get("failures_preserved"),
                    "STAGE4_NEXT_ARM_NOT_COMPLETE")
            require(result.get("canonical_gate_pass") is False and
                    result.get("step2_exit") == "UTILITY_FAIL",
                    "FALSE_GATE_PROMOTION")
            manifest = json.loads((Path(work) /
                                   "RUN394_PREREGISTERED_FIXTURES.json").read_text())
            for rid in ALL:
                arm, seed = rid.split("_s")
                info = result["completed"][rid]
                actual = resume.validate_completed(
                    Path(work) / info["attempt"], arm, int(seed),
                    r394.FIXTURES, manifest,
                    current_runner_sha=RUN401_EXECUTABLE_SHA256)
                require(actual == info["validated"] and actual["rows"] == 42,
                        "STAGE4_RECEIPT_INVALID:" + rid)
            report.update(status="STAGE4_NATIVE_PARTIAL_NO_PROMOTION",
                          native_execution_performed=True,
                          completed=list(ALL), rows_verified=168,
                          remaining_arms=5,
                          progress_sha256=safe.sha_file(
                              Path(work) / "RUN397_PROGRESS.json"))
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
                report["status"] = "STAGE4_RED_PRESERVED"
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--export", type=Path, required=True)
    p.add_argument("--stage3-report", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--installed-home", type=Path)
    p.add_argument("--export-destination", type=Path)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        previous = json.loads(args.stage3_report.read_text())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        previous = {"run": "Run415", "status": "STAGE3_RED_PRESERVED",
                    "errors": [str(exc)[:180]]}
    result = stage4(args.export, previous, args.work, args.installed_home,
                    args.execute, args.export_destination)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "errors": result["errors"],
                      "rows": result.get("rows_verified", 0),
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(0 if result["status"] in
                     ("STAGE4_READY_NO_NATIVE", "STAGE4_NATIVE_PARTIAL_NO_PROMOTION")
                     else 2)


if __name__ == "__main__":
    main()
