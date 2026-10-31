#!/usr/bin/env python3
"""Run49 seed431 source->JEF->real C3->final event agreement SHADOW end-to-end."""
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
from v13.agi.jef_c3_final_agreement_shadow_run48 import check
from tests.integration_step2_utility import installed_artifacts, installed_links
from scripts.run47_jef_c3_typed_receiver_native import CONFIG, SCHEMA, ARMS, messages, score

FIXTURE_SHA = "d0f9dc7b6dabdeec0cd5343be18517c7813071abbb104b78469e695cccd6c21d"
IDS = ("Alder", "Beacon", "Grove", "Haze", "Lumen", "Reef")
NEGATIVE = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "world_jepa_authority": "SHADOW",
            "redmi_measured": False, "whole_system_complete": False}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_fixture(path):
    raw = Path(path).read_bytes()
    if sha(raw) != FIXTURE_SHA:
        raise ValueError("RUN49_FIXTURE_HASH")
    data = json.loads(raw)
    if (data.get("schema") != "v13.run49.jef_c3_final_shadow_native_seed431.v1"
            or data.get("seed") != 431
            or tuple(x["id"] for x in data.get("fixtures", [])) != IDS):
        raise ValueError("RUN49_COHORT")
    for f in data["fixtures"]:
        if (set(f) != {"id", "prior", "current", "oracle"}
                or not f["prior"].startswith("Project " + f["id"] + ".")
                or not f["current"].startswith("Project " + f["id"] + ".")
                or set(f["oracle"]) != {"choice", "remaining"}):
            raise ValueError("RUN49_FIXTURE_SHAPE")
    return data


def _counts(store):
    return {name: store.one("SELECT COUNT(*) AS n FROM " + name)["n"]
            for name in ("events", "sources", "messages", "packets")}


def run_row(home, installed, fixture):
    initialize(home)
    save_config(home, CONFIG)
    installed_links(home, installed)
    r = Runtime(home)
    row = {"fixture": fixture["id"], "status": "ERROR",
           "prior_sha256": sha(fixture["prior"].encode("utf-8")),
           "current_sha256": sha(fixture["current"].encode("utf-8")),
           "oracle_visible_to_native": False,
           "native_answer": "", "native_c3_final": False,
           "process_releases": [], "processes_reaped": False,
           "native_score": {"correct": 0, "valid_json": False, "parsed": None}}
    start = time.monotonic()
    try:
        prior = r.store.event(r.session, fixture["prior"])
        current = r.store.event(r.session, fixture["current"])
        p, c = prior["source_ref"], current["source_ref"]
        row["prior_source_ref"], row["current_source_ref"] = p, c
        row["current_event_id"] = current["event_id"]
        row["session_id"] = r.session
        jef = propose(r.store, p, c)
        row["jef_candidate"] = jef
        msgs = messages(ARMS[1], fixture, jef)
        row["native_prompt"] = msgs
        row["native_prompt_sha256"] = sha(dumps(msgs).encode("utf-8"))
        native = r.pool.get("C3_LANGUAGE")
        row["native_answer"] = "".join(native.generate(
            msgs, r.cancel_event, time.monotonic() + 90, 96, SCHEMA, seed=13))
        row["native_c3_metrics"] = dict(native.last_metrics)
        row["native_c3_final"] = native.last_metrics.get("status") == "FINAL"
        r.pool.unload()
        row["native_score"] = score(row["native_answer"], fixture["oracle"])
        row["jef_matches_oracle"] = jef["candidate"] == fixture["oracle"]
        before = _counts(r.store)
        row["final_agreement"] = check(r.store, p, c, current["event_id"],
                                       r.session, row["native_answer"])
        row["gate_store_unchanged"] = before == _counts(r.store)
        row["status"] = ("RECORDED" if row["native_c3_final"]
                         and row["jef_matches_oracle"] and row["gate_store_unchanged"]
                         else "STRUCTURAL_FAIL")
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
            row["native_score"]["correct"] = 0
        row["elapsed_seconds"] = round(time.monotonic() - start, 3)
    return row


def summary(rows):
    return {"rows": len(rows),
            "structural": sum(r["status"] == "RECORDED" for r in rows),
            "native_correct": sum(r["native_score"]["correct"] for r in rows),
            "gate_matched": sum(r.get("final_agreement", {}).get("result")
                                == "MATCHED_NO_AUTHORITY" for r in rows)}


def run(installed, out, fixture_path):
    fixture = load_fixture(fixture_path)
    if out.exists():
        raise FileExistsError("RUN49_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {"schema": "v13.run49.jef_c3_final_shadow_native_result.v1",
              "fixture_sha256": FIXTURE_SHA, "seed": 431, "registered": True,
              "binding": binding, "rows": [], "row_sha256": {},
              "status": "RUNNING", "negative_gates": NEGATIVE}
    atomic_write(out / "report.json", dumps(report))
    for f in fixture["fixtures"]:
        home = out / f["id"]
        if home.exists():
            raise FileExistsError("RUN49_HOME_EXISTS")
        row = run_row(home, installed, f)
        report["rows"].append(row)
        report["row_sha256"][f["id"]] = sha(dumps(row).encode("utf-8"))
        report["summary"] = summary(report["rows"])
        atomic_write(out / "report.json", dumps(report))
        print(dumps({"fixture": f["id"], "status": row["status"],
                     "native_correct": row["native_score"]["correct"],
                     "gate": row.get("final_agreement", {}).get("result")}), flush=True)
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    s = report["summary"]
    report["end_to_end_shadow_signal"] = (
        s["rows"] == s["structural"] == s["native_correct"] == s["gate_matched"] == 6
        and report["installed_binding_unchanged"])
    report["status"] = ("END_TO_END_SHADOW_SIGNAL_ONLY" if report["end_to_end_shadow_signal"]
                        else "UTILITY_FAIL" if s["structural"] == 6
                        else "STRUCTURAL_RED")
    atomic_write(out / "report.json", dumps(report))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    report = run(args.home, args.out, args.fixture)
    print(dumps({"status": report["status"], "summary": report["summary"],
                 "end_to_end_shadow_signal": report["end_to_end_shadow_signal"]}))


if __name__ == "__main__":
    main()
