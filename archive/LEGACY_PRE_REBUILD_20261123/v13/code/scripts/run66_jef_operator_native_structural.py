#!/usr/bin/env python3
"""Pinned JEF operator CLI native engineering replay; SHADOW only, redacted raw."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3

from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts.run63_jef_c3_native import cohort, RUN_CONFIG
from v13.config import initialize, save_config

SCHEMA = "v13.jef.operator.native.structural_replay.v1"
COHORT_N = 3
EXPECTED_C3_SHA256 = cli.C3_SHA256
EXPECTED_RUNNER_SHA256 = cli.RUNNER_SHA256


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _db(home):
    path = Path(home) / "data/db/brain.sqlite3"
    conn = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
    try:
        state = conn.execute(
            "SELECT version,payload FROM states WHERE key='SLEEP_POLICY'").fetchone()
        return {
            "sleep_policy": state,
            "assistant_drafts": conn.execute(
                "SELECT COUNT(*) FROM messages WHERE role='assistant' AND status='DRAFT'"
            ).fetchone()[0],
            "assistant_committed": conn.execute(
                "SELECT COUNT(*) FROM messages WHERE role='assistant' "
                "AND status IN ('FINAL','OUTPUT_COMMITTED')"
            ).fetchone()[0],
        }
    finally:
        conn.close()


def _safe_fields(result):
    # Never persist the operator's sources, model output, prompt or local home.
    keys = ("status", "input_sha256", "native_model_called",
            "native_process_reaped", "native_final", "native_model_sha256",
            "runner_sha256", "source_only_fallback",
            "model_formatter_status", "c6_status", "preflight_only",
            "no_live_output", "delivery_authority", "output_committed",
            "tool_dispatches", "learning_authority", "age0",
            "native_output_sha256", "error_type")
    return {k: result.get(k) for k in keys}


def run(home, out, input_root):
    home, out, input_root = Path(home), Path(out), Path(input_root)
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise ValueError("RUN66_LINUX_NATIVE_ONLY")
    if out.exists() or input_root.exists():
        raise FileExistsError("RUN66_FRESH_OUTPUT_PATHS")
    rows = cohort()
    if len(rows) != COHORT_N:
        raise ValueError("RUN66_ORIGINAL_COHORT_MUTATED")
    input_root.mkdir(parents=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": SCHEMA, "evidence_kind": "LINUX_NATIVE_C3_REAL_OPERATOR_CLI_SHADOW",
        "registered": True, "replay_not_disjoint": True,
        "cohort_count": COHORT_N, "status": "INCOMPLETE",
        "c3_model_sha256_required": EXPECTED_C3_SHA256,
        "runner_sha256_required": EXPECTED_RUNNER_SHA256,
        "cases": [], "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "world_jepa_authority": "SHADOW",
        "delivery_authority": 0, "learning_authority": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }

    def save():
        out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")

    try:
        # Match the original frozen Run63/Run65 seed13, temperature0,
        # max32 native decoding. This is a fresh isolated bootstrap home.
        initialize(home)
        save_config(home, RUN_CONFIG)
        # The policy is intentionally enabled/nondefault so the CLI cannot
        # accidentally pass a no-mutation check against a default OFF home.
        runtime = cli.Runtime(home)
        try:
            runtime.sleep.cycle.set_policy("enabled", "on")
            runtime.sleep.cycle.set_policy("tick_seconds", "7")
        finally:
            runtime.close()
        policy_before = _db(home)["sleep_policy"]
        if policy_before is None:
            raise ValueError("RUN66_POLICY_PRECONDITION")
        report["policy_seeded_and_enabled"] = True
        for i, row in enumerate(rows):
            data = {
                "project": row["id"], "domain": row["domain"],
                "policy_source": row["b2_source"],
                "sheet_source": row["b1_source"],
                "current": row["current"],
            }
            path = input_root / ("case-" + str(i) + ".json")
            raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            result = cli.run(home, path, "native",
                             operator_opt_in=True, callback_opt_in=True)
            snap = _db(home)
            case = {
                "index": i, "case_id_sha256": _sha(row["id"].encode()),
                "input_matches_sha256": result.get("input_sha256") == _sha(raw),
                "policy_unchanged": snap["sleep_policy"] == policy_before,
                "assistant_drafts": snap["assistant_drafts"],
                "assistant_committed": snap["assistant_committed"],
                **_safe_fields(result),
            }
            report["cases"].append(case)
            save()
        # Restart recovery invalidates all uncommitted DRAFTs; never FINAL.
        runtime = cli.Runtime(home)
        try:
            after = _db(home)
        finally:
            runtime.close()
        report["restart_drafts_zero"] = after["assistant_drafts"] == 0
        report["restart_no_committed"] = after["assistant_committed"] == 0
        report["restart_policy_unchanged"] = after["sleep_policy"] == policy_before
        report["strict_formatter_matches_observed"] = sum(
            x["model_formatter_status"] == "FORMATTER_MATCH_SHADOW"
            for x in report["cases"])
        report["source_only_fallbacks_observed"] = sum(
            x["source_only_fallback"] is True for x in report["cases"])
        valid = (
            len(report["cases"]) == COHORT_N
            and report["restart_drafts_zero"]
            and report["restart_no_committed"]
            and report["restart_policy_unchanged"]
            and all(
                c["status"] == "SHADOW_DRAFT_PREFLIGHT_READY"
                and c["input_matches_sha256"] and c["policy_unchanged"]
                and c["native_model_called"] is True
                and c["native_process_reaped"] is True
                and c["native_final"] is True
                and c["native_model_sha256"] == EXPECTED_C3_SHA256
                and c["runner_sha256"] == EXPECTED_RUNNER_SHA256
                and c["assistant_committed"] == 0
                and c["assistant_drafts"] == 1
                and c["c6_status"] == "NEEDS_REAL_TTY_APPROVAL"
                and c["preflight_only"] is True
                and c["no_live_output"] is True
                and c["delivery_authority"] == 0
                and c["output_committed"] is False
                and c["tool_dispatches"] == 0
                and c["learning_authority"] == 0
                and c["age0"] == "RECORD_ONLY"
                for c in report["cases"])
        )
        report["status"] = ("STRUCTURAL_SHADOW_PASS_NO_PROMOTION"
                            if valid else "STRUCTURAL_SHADOW_RED")
    except Exception as exc:
        report["status"] = "RUN66_ERROR_RED"
        report["error_type"] = type(exc).__name__
    finally:
        save()
    if report["status"] != "STRUCTURAL_SHADOW_PASS_NO_PROMOTION":
        raise RuntimeError("RUN66_NATIVE_STRUCTURAL_RED; raw report preserved")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--input-root", required=True, type=Path)
    a = p.parse_args()
    r = run(a.home, a.out, a.input_root)
    print(r["status"], "cases", len(r["cases"]),
          "strict", r["strict_formatter_matches_observed"],
          "fallbacks", r["source_only_fallbacks_observed"])


if __name__ == "__main__":
    main()
