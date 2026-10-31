#!/usr/bin/env python3
"""Run53 single-case pinned Linux-native C3 -> Runtime F1/F5 -> atomic DRAFT.

A structural integration regression on existing Run51 Cypress input, not a
new utility cohort or a rescore of any registered experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from v13.common import atomic_write, dumps
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.store import audit_closed
from v13.runtime_c3_atomic_draft_candidate import stage_runtime_c3_draft
from scripts.run51_f1f5_second_attempt_native import load_fixture, FIXTURE_SHA256
from scripts.run47_jef_c3_typed_receiver_native import CONFIG, NEGATIVE
from tests.integration_step2_utility import installed_artifacts, installed_links


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ObservedC3:
    def __init__(self, native, row):
        self.native = native
        self.row = row

    @property
    def last_metrics(self):
        return self.native.last_metrics

    def generate(self, messages, *args, **kwargs):
        self.row["model_calls"] += 1
        self.row["native_prompt"] = messages
        self.row["native_prompt_sha256"] = sha(dumps(messages).encode())
        return self.native.generate(messages, *args, **kwargs)


def run_row(home, installed, fixture):
    initialize(home)
    save_config(home, CONFIG)
    installed_links(home, installed)
    r = Runtime(home)
    row = {"schema": "v13.run53.runtime_c3_native_draft_row.v1",
           "fixture": fixture["id"], "status": "ERROR", "model_calls": 0,
           "native_model": False, "native_prompt": None,
           "native_answer": None, "draft_result": None,
           "process_releases": [], "processes_reaped": False,
           "no_live_output": False, "tool_dispatches": 0,
           "weight_updates": False, "negative_gates": NEGATIVE}
    started = time.monotonic()
    native = []
    try:
        row["model_revision"] = r.models.revision("C3_LANGUAGE")
        current = r.store.event(r.session, fixture["followup"])
        row["current_event_id"] = current["event_id"]
        row["session_id"] = r.session
        row["current_source_ref"] = current["source_ref"]
        deadline = time.monotonic() + 90
        row["off_control"] = stage_runtime_c3_draft(
            r, current["event_id"], deadline, operator_opt_in=False,
            model_call_opt_in=True)
        row["missing_correction_control"] = stage_runtime_c3_draft(
            r, current["event_id"], deadline, operator_opt_in=True,
            model_call_opt_in=True)
        correction = r.store.event(r.session, fixture["correction_event"])
        row["correction_source_ref"] = correction["source_ref"]
        row["memory_id"] = r.memory.feedback(
            correction["event_id"], "fact", fixture["value"],
            permission="record", key=fixture["key"], scope="session")
        original_get = r.pool.get
        def get(role):
            if role != "C3_LANGUAGE":
                raise RuntimeError("RUN53_WRONG_NATIVE_ROLE")
            real = original_get(role)
            native.append(real)
            return ObservedC3(real, row)
        r.pool.get = get
        row["draft_result"] = stage_runtime_c3_draft(
            r, current["event_id"], time.monotonic()+90,
            operator_opt_in=True, model_call_opt_in=True, max_tokens=96)
        row["native_model"] = bool(native)
        row["native_c3_metrics"] = dict(native[0].last_metrics) if native else {}
        staged = row["draft_result"]
        if staged["status"] == "RUNTIME_C3_DRAFT_BOUND_SHADOW_NO_COMMIT":
            mid = staged["draft_message_id"]
            row["draft_row"] = r.store.one(
                "SELECT id,session_id,event_id,role,text,status,metadata "
                "FROM messages WHERE id=?", (mid,))
            row["native_answer"] = row["draft_row"]["text"]
            row["native_answer_sha256"] = sha(row["native_answer"].encode())
            row["c5_action"] = r.store.one(
                "SELECT id,event_id,kind,status,corollary_id,expected "
                "FROM actions WHERE id=?", (staged["c5_action_id"],))
            row["c5_packets"] = r.store.rows(
                "SELECT id,kind,event_id,generation_id,payload FROM packets "
                "WHERE event_id=? AND kind IN ('ActionIntent','CorollaryCopy')",
                (current["event_id"],))
        row["no_live_output"] = r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0
        row["action_count"] = r.store.one(
            "SELECT COUNT(*) AS n FROM actions")["n"]
        row["draft_count"] = r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status='DRAFT'")["n"]
        row["status"] = "RECORDED" if (
            row["off_control"]["status"] == "OFF"
            and row["missing_correction_control"]["status"] == "CLARIFY"
            and row["model_calls"] == 1
            and row["native_model"]
            and row["native_c3_metrics"].get("status") == "FINAL"
            and staged["status"] == "RUNTIME_C3_DRAFT_BOUND_SHADOW_NO_COMMIT"
            and staged["runner_released"] is True
            and row["native_answer_sha256"] == staged["candidate_sha256"]
            and row["draft_row"]["status"] == "DRAFT"
            and row["action_count"] == 1 and row["draft_count"] == 1
            and len(row["c5_packets"]) == 2
            and row["no_live_output"]) else "STRUCTURAL_RED"
    except (Exception, KeyboardInterrupt) as exc:
        row["error_type"] = type(exc).__name__
        row["error"] = str(exc)[:500]
        row["status"] = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "ERROR"
    finally:
        try:
            r.close()
        except Exception as exc:
            row["close_error_type"] = type(exc).__name__
            row["status"] = "STRUCTURAL_RED"
        row["process_releases"] = list(r.pool.release_history)
        row["processes_reaped"] = bool(row["process_releases"]) and all(
            x.get("process_reaped") is True for x in row["process_releases"])
        try:
            row["closed_store_audit"] = audit_closed(home)
        except Exception as exc:
            row["closed_store_audit_error"] = type(exc).__name__
            row["status"] = "STRUCTURAL_RED"
        if row["status"] == "RECORDED" and not row["processes_reaped"]:
            row["status"] = "STRUCTURAL_RED"
        row["elapsed_seconds"] = round(time.monotonic()-started, 3)
    return row


def run(installed, out, fixture_path):
    data = load_fixture(fixture_path)
    if out.exists():
        raise FileExistsError("RUN53_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {"schema": "v13.run53.runtime_c3_native_draft_report.v1",
              "seed": 467, "fixture_sha256": FIXTURE_SHA256,
              "claim": "ORIGINAL_RUN51_CYPRESS_STRUCTURAL_REGRESSION_NOT_UTILITY",
              "binding": binding, "rows": [], "row_sha256": {},
              "negative_gates": NEGATIVE, "status": "RUNNING"}
    atomic_write(out/"report.json", dumps(report))
    fixture = data["fixtures"][0]
    if fixture["id"] != "Cypress":
        raise ValueError("RUN53_FIXTURE_ID_RED")
    row = run_row(out/"Cypress", installed, fixture)
    report["rows"].append(row)
    report["row_sha256"]["Cypress"] = sha(dumps(row).encode())
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    report["status"] = ("NATIVE_DRAFT_STRUCTURAL_ONLY" if
                        row["status"] == "RECORDED"
                        and report["installed_binding_unchanged"] else
                        "STRUCTURAL_RED")
    atomic_write(out/"report.json", dumps(report))
    print(dumps({"status": report["status"], "row_status": row["status"],
                 "model_calls": row["model_calls"]}), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    print(dumps({"status": run(args.home,args.out,args.fixture)["status"]}))


if __name__ == "__main__":
    main()
