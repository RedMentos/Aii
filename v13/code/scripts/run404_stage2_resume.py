#!/usr/bin/env python3
"""Run404: explicit stage2 P_s20 native continuation after exact Run401 archive restore."""
import argparse
import json
from pathlib import Path

import run394_step2_fresh as r394
import run397_step2_resume as resume
import run402_stage_restore as restore
from run396_step2_pilot_audit import load, sha


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def stage2(archive, expected_sha, work, installed=None, execute=False):
    """Preview never runs models or changes restored work. Execute calls Run397 exactly once."""
    report = {"run": "Run404", "status": "STAGE2_RED_PRESERVED",
              "native_execute_requested": bool(execute), "native_execute_attempted": False,
              "native_execution_performed": False, "native_rerun": False,
              "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
              "redmi_measured": False, "jepa_weight": 0, "errors": []}
    if execute and installed is None:
        report["errors"].append("INSTALLED_HOME_REQUIRED_FOR_EXECUTE")
        return report
    try:
        restored = restore.restore_archive(archive, expected_sha, work)
        require(restored["status"] == "STAGE1_RESTORE_VERIFIED",
                "STAGE1_ARCHIVE_NOT_VERIFIED:" + ";".join(restored.get("errors", [])))
        work = Path(work)
        manifest = load(work / "RUN394_PREREGISTERED_FIXTURES.json")
        # Run401 stage1 attests the actual installed executable, not the\n        # downloadable runner release archive. Run402 already verifies this\n        # pinned executable SHA and its original raw installed-runner log.\n        runner_sha = restore.RUN401_EXECUTABLE_SHA256
        first, failed = resume.previous_success(work, "O", 20, r394.FIXTURES,
                                                manifest, current_runner_sha=runner_sha)
        require(first is not None and not failed and first["validated"]["rows"] == 42,
                "STAGE1_RECEIPT_NOT_REUSABLE")
        report["stage1"] = first
        report["restored_work"] = str(work)
        if not execute:
            report["status"] = "STAGE2_READY_NO_NATIVE"
            report["completed"] = ["O_s20"]
            report["rows_verified"] = 42
            report["remaining_arms"] = 8
            return report
        report["native_execute_attempted"] = True
        out = resume.run(work, installed, pilot=False, execute=True, max_new_arms=1)
        require(out.get("status") == "INCOMPLETE" and
                set(out.get("completed", {})) == {"O_s20", "P_s20"},
                "STAGE2_NEXT_ARM_NOT_COMPLETE")
        require(out.get("canonical_gate_pass") is False and
                out.get("step2_exit") == "UTILITY_FAIL", "FALSE_GATE_PROMOTION")
        require(not out.get("failures_preserved"), "STAGE2_FAILURES_PRESERVED_REVIEW_REQUIRED")
        for arm in ("O", "P"):
            rid = arm + "_s20"
            info = out["completed"][rid]
            validated = resume.validate_completed(
                work / info["attempt"], arm, 20, r394.FIXTURES, manifest,
                current_runner_sha=runner_sha)
            require(validated == info["validated"] and validated["rows"] == 42,
                    "STAGE2_RECEIPT_INVALID:" + rid)
        report["status"] = "STAGE2_NATIVE_PARTIAL_NO_GATE_PROMOTION"
        report["native_execution_performed"] = True
        report["completed"] = ["O_s20", "P_s20"]
        report["rows_verified"] = 84
        report["remaining_arms"] = 7
        report["progress_sha256"] = sha(work / "RUN397_PROGRESS.json")
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, IndexError,
            json.JSONDecodeError) as exc:
        report["errors"].append(type(exc).__name__ + ": " + str(exc)[:350])
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--work", type=Path, required=True, help="fresh private destination")
    p.add_argument("--installed-home", type=Path)
    p.add_argument("--execute", action="store_true", help="explicit real native P_s20 execution")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = stage2(args.archive, args.expected_sha256, args.work,
                    installed=args.installed_home, execute=args.execute)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "errors": result["errors"],
                      "rows": result.get("rows_verified", 0),
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(0 if result["status"] in
                     ("STAGE2_READY_NO_NATIVE", "STAGE2_NATIVE_PARTIAL_NO_GATE_PROMOTION") else 2)


if __name__ == "__main__":
    main()
