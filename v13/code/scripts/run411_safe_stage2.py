#!/usr/bin/env python3
"""Run411: opt-in one-arm STEP2 P_s20 continuation with safe native work export.

The original Run401 ZIP is verified by Run408. No inference without --execute.
No canonical gate promotion; failures remain RED and safe export is attempted.
"""
import argparse
import json
from pathlib import Path

import run394_step2_fresh as r394
import run397_step2_resume as resume
import run408_filtered_stage1 as filtered
import run409_safe_export as safe
from run402_stage_restore import RUN401_EXECUTABLE_SHA256
from run396_step2_pilot_audit import load, sha
from v13.models import catalog


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def stage2(archive, expected_sha, work, installed=None, execute=False, export_dest=None):
    report = {"run": "Run411", "status": "STAGE2_RED_PRESERVED",
              "errors": [], "native_execute_requested": bool(execute),
              "native_execute_attempted": False, "native_execution_performed": False,
              "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
              "redmi_measured": False, "jepa_weight": 0}
    if execute and (installed is None or export_dest is None):
        report["errors"].append("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE")
        return report
    restored = False
    try:
        first_stage = filtered.audit_or_restore(archive, expected_sha, work)
        require(first_stage["status"] == "FILTERED_STAGE1_VERIFIED_NO_PROMOTION",
                "STAGE1_FILTERED_ARCHIVE_NOT_VERIFIED:" +
                ";".join(first_stage.get("errors", [])))
        restored = True
        report["stage1"] = {"original_zip_sha256": first_stage["original_zip_sha256"],
                            "members_verified": first_stage["members_verified"],
                            "omitted_registered_models": first_stage["omitted_registered_models"],
                            "unlisted_binary_hashes": first_stage["unlisted_binary_hashes"],
                            "all_member_sha_checked": first_stage["all_member_sha_checked"],
                            "zip_crc_checked": first_stage["zip_crc_checked"]}
        work = Path(work)
        manifest = load(work / "RUN394_PREREGISTERED_FIXTURES.json")
        runner_sha = RUN401_EXECUTABLE_SHA256
        first, failed = resume.previous_success(work, "O", 20, r394.FIXTURES,
                                                manifest, current_runner_sha=runner_sha)
        require(first is not None and not failed and first["validated"]["rows"] == 42,
                "STAGE1_RECEIPT_NOT_REUSABLE")
        report["stage1_receipt"] = first
        report["restored_work"] = str(work)
        if not execute:
            report["status"] = "STAGE2_READY_NO_NATIVE"
            report["completed"] = ["O_s20"]
            report["rows_verified"] = 42
            report["remaining_arms"] = 8
        else:
            require(sha(Path(installed) / "bin/llama-server") == runner_sha,
                    "INSTALLED_RUNNER_EXECUTABLE_SHA_MISMATCH")
            report["native_execute_attempted"] = True
            out = resume.run(work, installed, pilot=False, execute=True, max_new_arms=1)
            require(out.get("status") == "INCOMPLETE" and
                    set(out.get("completed", {})) == {"O_s20", "P_s20"},
                    "STAGE2_NEXT_ARM_NOT_COMPLETE")
            require(out.get("canonical_gate_pass") is False and
                    out.get("step2_exit") == "UTILITY_FAIL", "FALSE_GATE_PROMOTION")
            require(not out.get("failures_preserved"),
                    "STAGE2_FAILURES_PRESERVED_REVIEW_REQUIRED")
            for arm in ("O", "P"):
                rid = arm + "_s20"
                info = out["completed"][rid]
                verified = resume.validate_completed(
                    work / info["attempt"], arm, 20, r394.FIXTURES, manifest,
                    current_runner_sha=runner_sha)
                require(verified == info["validated"] and verified["rows"] == 42,
                        "STAGE2_RECEIPT_INVALID:" + rid)
            report["status"] = "STAGE2_NATIVE_PARTIAL_NO_PROMOTION"
            report["native_execution_performed"] = True
            report["completed"] = ["O_s20", "P_s20"]
            report["rows_verified"] = 84
            report["remaining_arms"] = 7
            report["progress_sha256"] = sha(work / "RUN397_PROGRESS.json")
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, IndexError,
            json.JSONDecodeError) as exc:
        report["errors"].append(type(exc).__name__ + ": " + str(exc)[:350])
    finally:
        # Even if native fails, export every original regular file and failed attempt.
        if restored and installed is not None and export_dest is not None:
            exported = safe.export(work, installed, export_dest)
            report["safe_export"] = exported
            if exported["status"] != "EXPORT_VERIFIED_NO_MODEL_WEIGHTS":
                report["errors"].append("SAFE_EXPORT_RED:" +
                                        ";".join(exported.get("errors", [])))
                report["status"] = "STAGE2_RED_PRESERVED"
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--work", type=Path, required=True, help="fresh private native work tree")
    p.add_argument("--installed-home", type=Path)
    p.add_argument("--export-destination", type=Path, help="fresh private no-model work export")
    p.add_argument("--execute", action="store_true", help="explicit one real native P_s20 arm")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = stage2(args.archive, args.expected_sha256, args.work,
                    installed=args.installed_home, execute=args.execute,
                    export_dest=args.export_destination)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "errors": result["errors"],
                      "rows": result.get("rows_verified", 0),
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(0 if result["status"] in
                     ("STAGE2_READY_NO_NATIVE", "STAGE2_NATIVE_PARTIAL_NO_PROMOTION") else 2)


if __name__ == "__main__":
    main()
