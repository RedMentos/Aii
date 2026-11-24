"""Assemble 12 independently sealed STEP2 native arm checkpoints, read-only inputs.

No native execution. Never turns a diagnostic or software fixture into a
canonical STEP2 PASS. Manifest is written last to a fresh destination.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from scripts import step2_longnote_staged12_native as stage
from scripts import step2_longnote_fourarm_io as io
from scripts import step2_longnote_fourarm_analysis as analysis
from scripts.step2_fourarm_native_collector_candidate import (
    canonical, sha, write_new, verify_native_reports,
)
from v13.common import digest, dumps

MAX_RECEIPT = 4 * 1024 * 1024


def require(ok, message):
    if not ok:
        raise ValueError(message)


def _open_directory(path, dir_fd=None):
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    return os.open(os.fspath(path), flags, dir_fd=dir_fd)


def read_stage(rootfd, arm, seed, expected_source):
    """Read one immutable per-arm checkpoint without following input symlinks."""
    rid = f"{arm}_s{seed}"
    fd = _open_directory(rid, dir_fd=rootfd)
    try:
        receipt_bytes = io._read(fd, "RECEIPT.json", MAX_RECEIPT)
        summary_bytes = io._read(fd, "SEALED_SUMMARY.json", io.MAX_SUMMARY)
        raw = io._read(fd, "RAW_PAIR.bin", io.MAX_RAW)
    finally:
        os.close(fd)
    receipt = io._json(receipt_bytes)
    summary = io._json(summary_bytes)
    require(type(receipt) is dict and type(summary) is dict and
            receipt_bytes == canonical(receipt) and
            summary_bytes == canonical(summary),
            "Noncanonical or malformed staged receipt/summary: " + rid)
    require(receipt.get("schema") == "v13.step2.staged12.single_arm.v1" and
            receipt.get("status") == "PASS_SCOPED_ONE_OF_TWELVE_NO_CANON_GATE" and
            receipt.get("arm") == arm and receipt.get("seed") == seed and
            receipt.get("fixture_ids") == list(stage.FIXTURE_IDS) and
            receipt.get("registration_sha256") == stage.REGISTRATION_SHA256 and
            receipt.get("source_sha256") == expected_source and
            receipt.get("source_model_runner_unchanged") is True and
            receipt.get("native_rows") == receipt.get("tool_rows") == 70 and
            receipt.get("native_c3_final") == receipt.get("tool_c3_final") == 70 and
            receipt.get("all_native_processes_reaped") is True and
            receipt.get("model_hashes_before") == receipt.get("model_hashes_after") and
            receipt.get("age_authority") == 0 and
            receipt.get("jepa_weight") == 0 and
            receipt.get("weight_updates") is False and
            receipt.get("redmi_measured") is False and
            receipt.get("canonical_gate_pass") is False and
            receipt.get("whole_system_complete") is False,
            "Incomplete or promoted staged receipt: " + rid)
    require(summary.get("arm") == arm and summary.get("seed") == seed and
            summary.get("source_sha256") == expected_source and
            summary.get("registration_sha256") == stage.REGISTRATION_SHA256 and
            summary.get("fixture_sha256") == stage.FIXTURE_SHA256 and
            summary.get("runner_sha256") == stage.RUNNER_SHA256 and
            summary.get("evidence_kind") == "LINUX_NATIVE" and
            summary.get("canonical_gate_pass") is False and
            summary.get("step2_gate_promoted") is False and
            summary.get("jepa_weight") == 0 and
            summary.get("redmi_measured") is False and
            summary.get("whole_system_complete") is False,
            "Staged native summary identity/gates changed: " + rid)
    require(receipt.get("raw_pair_sha256") == sha(raw) ==
            summary.get("raw_sha256") and
            receipt.get("sealed_summary_sha256") == sha(summary_bytes),
            "Staged raw/summary receipt hash mismatch: " + rid)
    base = receipt.get("installed_artifacts_before")
    require(type(base) is dict and
            base.get("runner_sha256") == stage.RUNNER_SHA256 and
            base.get("model_sha256") == receipt.get("model_hashes_before") and
            summary.get("model_sha256") ==
                stage.expected_models(arm, base["model_sha256"]),
            "Staged model/runner identity mismatch: " + rid)
    source_bytes, tool_bytes = io._native_pair(raw)
    source, tool = verify_native_reports(
        source_bytes, tool_bytes, stage.FIXTURE_IDS, stage.FIXTURE_SHA256)
    actual = dict(base)
    actual["model_sha256"] = stage.expected_models(arm, base["model_sha256"])
    actual["model_revisions"] = dict(base["model_revisions"])
    if arm.startswith("S"):
        actual["model_revisions"]["B2_GIST"] = actual["model_revisions"]["B1_DETAIL"]
    require(source.get("installed_artifacts") == actual and
            source.get("distinct_bodies") is arm.startswith("T"),
            "Staged source uses wrong model revision/control: " + rid)
    source_rows = {r["fixture"] + ":" + r["variant"]: r for r in source["rows"]}
    tool_rows = {r["fixture"] + ":" + r["variant"]: r for r in tool["rows"]}
    require(len(source_rows) == len(tool_rows) == 70,
            "Incomplete staged native/tool rows: " + rid)
    for key, row in source_rows.items():
        other = tool_rows[key]
        require(row.get("processes_reaped") is True and
                row.get("restart_state_identical") is True and
                row.get("oracle_visible_to_native") is False and
                row.get("native_consumer_metrics", {}).get("status") == "FINAL" and
                other.get("oracle_visible_to_native") is False and
                other.get("consumer_metrics", {}).get("status") == "FINAL" and
                other.get("consumer_messages_sha256") ==
                    digest(dumps(row["consumer_messages"])),
                "Staged C3 source-message binding failed: " + rid + ":" + key)
    # Existing independent raw scorer replays original fixture bytes, 70
    # utilities and both complementary error profiles; never trusts summary.
    io._bind_native(raw, summary, stage.FIXTURE_IDS)
    return {"raw_sha256": sha(raw), "summary_sha256": sha(summary_bytes),
            "summary": summary, "receipt_sha256": sha(receipt_bytes)}


def assemble(runs_root, out):
    stage.prereg("TP", 27)
    runs_root, out = Path(runs_root).absolute(), Path(out).absolute()
    require(runs_root.is_dir() and not runs_root.is_symlink() and
            not out.exists() and out.parent.is_dir() and
            not out.is_relative_to(runs_root),
            "Existing unsymlinked input and fresh separate output required")
    ids = [(a, s) for a in analysis.ARMS for s in analysis.SEEDS]
    expected_names = {f"{a}_s{s}" for a, s in ids}
    require(set(os.listdir(runs_root)) == expected_names,
            "Exactly twelve named staged arm/seed directories required")
    source_pin = stage.source_hashes()
    rootfd = _open_directory(runs_root)
    try:
        first = {(a, s): read_stage(rootfd, a, s, source_pin) for a, s in ids}
        summaries = [first[a, s]["summary"] for a, s in ids]
        analysis.validate(summaries, stage.FIXTURE_IDS)
        # Do not create any output before the full twelve-way source, model
        # and registered-control cross-check has succeeded.
        out.mkdir(mode=0o700)
        entries = []
        for arm, seed in ids:
            record = first[arm, seed]
            second = read_stage(rootfd, arm, seed, source_pin)
            require(second["raw_sha256"] == record["raw_sha256"] and
                    second["summary_sha256"] == record["summary_sha256"] and
                    second["receipt_sha256"] == record["receipt_sha256"],
                    "Staged source changed between validation and copying")
            fd = _open_directory(f"{arm}_s{seed}", dir_fd=rootfd)
            try:
                raw = io._read(fd, "RAW_PAIR.bin", io.MAX_RAW)
                summary_bytes = io._read(fd, "SEALED_SUMMARY.json", io.MAX_SUMMARY)
            finally:
                os.close(fd)
            require(sha(raw) == record["raw_sha256"] and
                    sha(summary_bytes) == record["summary_sha256"],
                    "Staged source changed while copying")
            rid = f"{arm}_s{seed}"
            raw_name, summary_name = rid + ".raw", rid + ".json"
            write_new(out / raw_name, raw)
            write_new(out / summary_name, summary_bytes)
            entries.append({"arm": arm, "seed": seed, "raw": raw_name,
                            "raw_sha256": record["raw_sha256"],
                            "summary": summary_name,
                            "summary_sha256": record["summary_sha256"]})
        manifest = {"schema": io.SCHEMA, "fixture_ids": list(stage.FIXTURE_IDS),
                    "runs": entries}
        manifest_bytes = canonical(manifest)
        manifest_sha = sha(manifest_bytes)
        write_new(out / "manifest.json", manifest_bytes)
        result = io.load(out, "manifest.json", manifest_sha,
                         stage.FIXTURE_IDS, stage.FIXTURE_SHA256)
        require(result.get("status") == "FOUR_ARM_DIAGNOSTIC_ONLY" and
                result.get("canonical_gate_pass") is False and
                result.get("step2_gate_promoted") is False,
                "Original four-arm scorer unexpectedly promoted a gate")
        verdict = {"schema": "v13.step2.staged12.assembled.v1",
                   "status": "VERIFIED_CLOSED_TWELVE_RUN_DIAGNOSTIC_ONLY",
                   "manifest_sha256": manifest_sha,
                   "runs": 12, "fixture_sha256": stage.FIXTURE_SHA256,
                   "source_sha256": source_pin,
                   "canonical_gate_pass": False,
                   "step2_gate_promoted": False,
                   "jepa_weight": 0, "redmi_measured": False,
                   "whole_system_complete": False,
                   "analysis": result}
        write_new(out / "VERDICT.json", canonical(verdict))
        return verdict
    finally:
        os.close(rootfd)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runs-root", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    result = assemble(args.runs_root, args.out)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("source_sha256", "analysis")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
