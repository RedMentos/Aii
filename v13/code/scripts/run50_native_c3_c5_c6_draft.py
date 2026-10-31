#!/usr/bin/env python3
"""Run50: four fresh Linux-native C3 -> real C5/C6 DRAFT SHADOW rows."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from v13.common import atomic_write, dumps
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.agi.jef_eligibility_source_shadow_run46b import propose
from v13.agi.jef_c3_c5_c6_draft_shadow_run49 import check_draft
from scripts.run47_jef_c3_typed_receiver_native import (
    CONFIG, SCHEMA, ARMS, messages, score, sha, NEGATIVE)
from tests.integration_step2_utility import installed_artifacts, installed_links

FIXTURE_SHA256 = "7e05d20beb53653c86fe0ed83c12befba766ec0110be03ce9ea58569865e350c"
PROJECTS = ("Pine", "Orchid", "Slate", "Amber")


def load_fixture(path):
    raw = Path(path).read_bytes()
    if sha(raw) != FIXTURE_SHA256:
        raise ValueError("RUN50_FIXTURE_SHA")
    data = json.loads(raw)
    if (data.get("schema") != "v13.run50.native_c3_c5_c6_draft_seed443.v1"
            or data.get("seed") != 443
            or [f.get("id") for f in data.get("fixtures", [])] != list(PROJECTS)):
        raise ValueError("RUN50_COHORT")
    for f in data["fixtures"]:
        if (set(f) != {"id", "prior", "current", "oracle"}
                or not f["prior"].startswith("Project " + f["id"] + ".")
                or not f["current"].startswith("Project " + f["id"] + ".")
                or set(f["oracle"]) != {"choice", "remaining"}):
            raise ValueError("RUN50_FIXTURE_SHAPE")
    return data


def run_row(home, installed, fixture):
    initialize(home)
    save_config(home, CONFIG)
    installed_links(home, installed)
    r = Runtime(home)
    row = {"fixture": fixture["id"], "arm": ARMS[1], "status": "ERROR",
           "prior_sha256": sha(fixture["prior"].encode("utf-8")),
           "current_sha256": sha(fixture["current"].encode("utf-8")),
           "oracle_visible_to_native": False, "native_answer": "",
           "native_c3_final": False, "process_releases": [],
           "processes_reaped": False, "draft_result": None,
           "score": {"correct": 0, "valid_json": False, "parsed": None}}
    start = time.monotonic()
    try:
        prior = r.store.event(r.session, fixture["prior"])
        current = r.store.event(r.session, fixture["current"])
        row["prior_source_ref"] = prior["source_ref"]
        row["current_source_ref"] = current["source_ref"]
        row["current_event_id"] = current["event_id"]
        row["session_id"] = r.session
        jef = propose(r.store, prior["source_ref"], current["source_ref"])
        row["jef_candidate"] = jef
        msgs = messages(ARMS[1], fixture, jef)
        row["native_prompt"] = msgs
        row["native_prompt_sha256"] = sha(dumps(msgs).encode("utf-8"))
        runner = r.pool.get("C3_LANGUAGE")
        row["native_answer"] = "".join(runner.generate(
            msgs, r.cancel_event, time.monotonic() + 90, 96, SCHEMA, seed=13))
        row["native_c3_metrics"] = dict(runner.last_metrics)
        row["native_c3_final"] = runner.last_metrics.get("status") == "FINAL"
        r.pool.unload()
        row["score"] = score(row["native_answer"], fixture["oracle"])
        row["jef_matches_oracle"] = jef["candidate"] == fixture["oracle"]
        row["c5_action_id"] = r.store.start_action(
            current["event_id"], current["brain_generation_id"])
        row["c6_draft_id"] = r.store.message(
            r.session, current["event_id"], "assistant", row["native_answer"], "DRAFT")
        row["c5_action"] = r.store.one(
            "SELECT id,event_id,kind,status,corollary_id,expected FROM actions WHERE id=?",
            (row["c5_action_id"],))
        row["c5_packets"] = r.store.rows(
            "SELECT id,kind,event_id,generation_id,payload FROM packets "
            "WHERE event_id=? AND kind IN ('ActionIntent','CorollaryCopy')",
            (current["event_id"],))
        changes = r.store.db.total_changes
        row["draft_result"] = check_draft(
            r.store, prior["source_ref"], current["source_ref"],
            current["event_id"], r.session, row["native_answer"],
            row["c6_draft_id"], row["c5_action_id"])
        row["draft_preflight_writes"] = r.store.db.total_changes - changes
        row["c6_draft_row"] = r.store.one(
            "SELECT id,session_id,event_id,role,text,status,metadata FROM messages WHERE id=?",
            (row["c6_draft_id"],))
        row["draft_still_uncommitted"] = row["c6_draft_row"]["status"] == "DRAFT"
        row["status"] = ("RECORDED" if row["native_c3_final"]
                         and row["jef_matches_oracle"]
                         and row["draft_result"]["result"] == "DRAFT_BOUND_SHADOW_NO_COMMIT"
                         and row["draft_preflight_writes"] == 0
                         and row["draft_still_uncommitted"] else "STRUCTURAL_FAIL")
    except (Exception, KeyboardInterrupt) as exc:
        row["error_type"] = type(exc).__name__
        row["error"] = str(exc)[:500]
        row["status"] = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "ERROR"
    finally:
        try:
            r.close()
        except Exception as exc:
            row["close_error_type"] = type(exc).__name__
            row["status"] = "STRUCTURAL_FAIL"
        row["process_releases"] = list(r.pool.release_history)
        row["processes_reaped"] = bool(row["process_releases"]) and all(
            x.get("process_reaped") is True for x in row["process_releases"])
        if row["status"] == "RECORDED" and not row["processes_reaped"]:
            row["status"] = "STRUCTURAL_FAIL"
        if row["status"] != "RECORDED":
            row["score"]["correct"] = 0
        row["elapsed_seconds"] = round(time.monotonic() - start, 3)
    return row


def run(installed, out, fixture_path):
    data = load_fixture(fixture_path)
    if out.exists():
        raise FileExistsError("RUN50_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {"schema": "v13.run50.native_c3_c5_c6_draft_result.v1",
              "fixture_sha256": FIXTURE_SHA256, "seed": 443,
              "binding": binding, "registered": True, "rows": [],
              "row_sha256": {}, "status": "RUNNING", "negative_gates": NEGATIVE}
    atomic_write(out / "report.json", dumps(report))
    for f in data["fixtures"]:
        home = out / f["id"]
        if home.exists():
            raise FileExistsError("RUN50_HOME_EXISTS")
        row = run_row(home, installed, f)
        report["rows"].append(row)
        report["row_sha256"][f["id"]] = sha(dumps(row).encode("utf-8"))
        atomic_write(out / "report.json", dumps(report))
        print(dumps({"fixture": f["id"], "status": row["status"],
                     "correct": row["score"]["correct"]}), flush=True)
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    structural = all(r["status"] == "RECORDED" for r in report["rows"])
    correct = sum(r["score"]["correct"] for r in report["rows"])
    report["native_draft_copy_signal"] = (structural and correct >= 3
                                          and report["installed_binding_unchanged"])
    report["status"] = ("NATIVE_DRAFT_COPY_SIGNAL_ONLY" if report["native_draft_copy_signal"]
                        else "UTILITY_FAIL" if structural else "STRUCTURAL_RED")
    atomic_write(out / "report.json", dumps(report))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    report = run(args.home, args.out, args.fixture)
    print(dumps({"status": report["status"],
                 "native_draft_copy_signal": report["native_draft_copy_signal"]}))


if __name__ == "__main__":
    main()