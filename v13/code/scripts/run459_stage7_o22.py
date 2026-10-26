#!/usr/bin/env python3
"""Run459: verified 252-row Run453 export -> exact next O_s22 (42 rows).

Source-only preview by default. Actual native execution is explicit and requires
the exact pinned installed runner/models, a fresh destination and a separate
safe no-model export. Import/verify all six prior receipts before any native
work. Never promote STEP2/B3/Body-JEPA/Redmi/weights from partial results.
"""
import argparse
import json
import re
from pathlib import Path

import run394_step2_fresh as r394
import run397_step2_resume as resume
import run409_safe_export as safe
import run458_import_stage6_artifact as stage6_import
from run402_stage_restore import RUN401_EXECUTABLE_SHA256

PREFIX = ("O_s20", "P_s20", "S_s20", "O_s21", "P_s21", "S_s21")
NEXT = "O_s22"
ALL = PREFIX + (NEXT,)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def verify_previous(work):
    root = Path(work).absolute()
    manifest = json.loads((root / "RUN394_PREREGISTERED_FIXTURES.json").read_text())
    require(manifest == r394.manifest(r394.FIXTURES, False, list(r394.ARMS),
                                      list(r394.SEEDS)), "STAGE7_FROZEN_MANIFEST_MISMATCH")
    progress = json.loads((root / "RUN397_PROGRESS.json").read_text())
    require(progress.get("canonical_gate_pass") is False and
            progress.get("step2_exit") == "UTILITY_FAIL" and
            set(progress.get("completed", {})) == set(PREFIX) and
            not progress.get("failures_preserved"),
            "STAGE7_PREVIOUS_PROGRESS_INVALID")
    for rid in PREFIX:
        arm, seed = rid.split("_s")
        info = progress["completed"][rid]
        require(type(info) is dict and type(info.get("attempt")) is str and
                re.fullmatch(r"attempts/" + rid + r"/attempt-[0-9]+",
                             info["attempt"]) is not None,
                "STAGE7_PREVIOUS_ATTEMPT_PATH_INVALID")
        directory = root / info["attempt"]
        require(not directory.is_symlink() and
                directory.resolve().is_relative_to(root.resolve()),
                "STAGE7_PREVIOUS_ATTEMPT_ESCAPE")
        actual = resume.validate_completed(
            directory, arm, int(seed), r394.FIXTURES, manifest,
            current_runner_sha=RUN401_EXECUTABLE_SHA256)
        require(actual == info.get("validated") and actual["rows"] == 42,
                "STAGE7_PREVIOUS_RECEIPT_INVALID:" + rid)
    return {"status": "STAGE7_PREVIOUS_252_ROWS_VERIFIED",
            "completed": list(PREFIX), "rows_verified": 252,
            "runner_sha256": RUN401_EXECUTABLE_SHA256,
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}


def stage7(archive, expected_sha256, stage6_report, work, installed=None,
           execute=False, export_dest=None):
    report = {"run": "Run459", "status": "STAGE7_RED_PRESERVED",
              "errors": [], "native_execute_requested": bool(execute),
              "native_execute_attempted": False, "native_execution_performed": False,
              "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
              "redmi_measured": False, "jepa_weight": 0}
    if execute and (installed is None or export_dest is None):
        report["errors"].append("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE")
        return report
    restored = False
    try:
        imported = stage6_import.import_stage6(
            archive, expected_sha256, stage6_report, work)
        require(imported["status"] == "RUN458_NATIVE252_IMPORTED_UTILITY_DESCRIPTIVE" and
                imported["rows_verified"] == 252 and
                imported["canonical_gate_pass"] is False,
                "STAGE7_252_IMPORT_NOT_VERIFIED")
        restored = True
        report["stage6"] = imported
        report["restored_work"] = str(Path(work).absolute())
        report["completed"] = list(PREFIX)
        report["rows_verified"] = 252
        report["remaining_arms"] = 3
        report["preflight"] = verify_previous(work)
        if not execute:
            report["status"] = "STAGE7_READY_NO_NATIVE"
        else:
            installed = Path(installed)
            require(safe.sha_file(installed / "bin/llama-server") ==
                    RUN401_EXECUTABLE_SHA256, "INSTALLED_RUNNER_SHA_MISMATCH")
            report["native_execute_attempted"] = True
            result = resume.run(work, installed, pilot=False, execute=True,
                                max_new_arms=1)
            require(result.get("status") == "INCOMPLETE" and
                    set(result.get("completed", {})) == set(ALL) and
                    not result.get("failures_preserved"),
                    "STAGE7_NEXT_ARM_NOT_COMPLETE")
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
                        "STAGE7_RECEIPT_INVALID:" + rid)
            report.update(status="STAGE7_NATIVE_PARTIAL_NO_PROMOTION",
                          native_execution_performed=True,
                          completed=list(ALL), rows_verified=294,
                          remaining_arms=2,
                          progress_sha256=safe.sha_file(
                              Path(work) / "RUN397_PROGRESS.json"))
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, IndexError,
            json.JSONDecodeError) as exc:
        report["errors"].append(type(exc).__name__ + ": " + str(exc)[:350])
    finally:
        if execute and restored and installed is not None and export_dest is not None:
            try:
                exported = safe.export(work, installed, export_dest)
                report["safe_export"] = exported
                if exported["status"] != "EXPORT_VERIFIED_NO_MODEL_WEIGHTS":
                    report["errors"].append("SAFE_EXPORT_RED:" +
                                            ";".join(exported.get("errors", [])))
                    report["status"] = "STAGE7_RED_PRESERVED"
            except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
                report["errors"].append("SAFE_EXPORT_EXCEPTION:" +
                                        type(exc).__name__ + ": " + str(exc)[:250])
                report["status"] = "STAGE7_RED_PRESERVED"
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--stage6-report", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--installed-home", type=Path)
    p.add_argument("--export-destination", type=Path)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        previous = json.loads(a.stage6_report.read_text())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        previous = {"status": "STAGE7_RED_PRESERVED",
                    "errors": [type(exc).__name__ + ": " + str(exc)[:180]]}
    result = stage7(a.archive, a.expected_sha256, previous, a.work,
                    a.installed_home, a.execute, a.export_destination)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "errors": result["errors"],
                      "rows": result.get("rows_verified", 0),
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(0 if result["status"] in
                     ("STAGE7_READY_NO_NATIVE", "STAGE7_NATIVE_PARTIAL_NO_PROMOTION")
                     else 2)


if __name__ == "__main__":
    main()
