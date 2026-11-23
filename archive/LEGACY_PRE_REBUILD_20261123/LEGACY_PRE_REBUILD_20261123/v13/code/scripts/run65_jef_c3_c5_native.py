#!/usr/bin/env python3
"""Run65: three pinned real C3 JEF->C5/F3 DRAFT->C6 structural calls.

Original P2X calibration engineering, NOT disjoint utility or native receiver
promotion. The frozen Run63 pilot RED is not rescored.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import time

from v13.common import atomic_write, dumps
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.jef_c3_typed_envelope_candidate import build_jef_c3_typed_envelope
from v13.jef_c3_c5_c6_fallback_draft_candidate import stage, preflight, STAGED
from scripts import p2x_disjoint_receiver_trainset as p2x
from scripts.run63_jef_c3_native import (
    C3_SHA256, RUNNER_SHA256, RUN_CONFIG, cohort)
from scripts.run47_jef_c3_typed_receiver_native import NEGATIVE
from scripts.run59_crossorgan_c6_native import audit_closed
from tests.integration_step2_utility import installed_artifacts, installed_links


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run_row(home, installed, row):
    initialize(home)
    save_config(home, RUN_CONFIG)
    installed_links(home, installed)
    r = Runtime(home)
    r.sleep.cycle.set_policy("enabled", "off")
    start = time.monotonic()
    out = {
        "schema": "v13.run65.jef_c3_c5_native_row.v1",
        "id": row["id"], "oracle_action": row["oracle_action"],
        "source_sha256": {k: sha(row[k].encode("utf-8"))
                          for k in ("current", "b1_source", "b2_source")},
        "source_refs": None, "input_messages": None, "input_sha256": None,
        "status": "ERROR", "native_output": None, "output_sha256": None,
        "native_metrics": None, "native_c3_final": False,
        "native_process_count": 0, "processes_reaped": False,
        "process_releases": [], "closed_store_audit": None,
        "no_live_output": False, "draft_count": 0,
        "staged": None, "c6": None, "draft_snapshot": None,
        "native_strict_correct": 0, "source_only_fallback": False,
        "tty_approved": False, "output_committed": False,
        "tool_dispatches": 0, "learning_authority": 0,
        "candidate_authority": 0, "oracle_visible_to_native": False,
        "negative_gates": NEGATIVE,
    }
    try:
        domain, project = row["domain"], row["id"]
        policy_key = f"Project {project} archived {domain} policy"
        sheet_key = f"Project {project} latest {domain} option sheet"
        e_policy = r.store.event(r.session, "Record: " + policy_key)
        policy_mid = r.memory.feedback(
            e_policy["event_id"], "fact", row["b2_source"],
            permission="record", key=policy_key, scope="session")
        r.memory.candidate(policy_mid, r.session)
        e_sheet = r.store.event(r.session, "Record: " + sheet_key)
        sheet_mid = r.memory.feedback(
            e_sheet["event_id"], "fact", row["b1_source"],
            permission="record", key=sheet_key, scope="session")
        r.memory.candidate(sheet_mid, r.session)
        e_current = r.store.event(r.session, row["current"])
        ids = [policy_mid, sheet_mid]
        out["source_refs"] = {
            "current": e_current["source_ref"],
            "policy": r.memory.candidate(policy_mid, r.session)["source_ref"],
            "sheet": r.memory.candidate(sheet_mid, r.session)["source_ref"],
        }
        env = build_jef_c3_typed_envelope(
            r.memory, r.session, e_current["event_id"],
            e_current["source_ref"], ids, operator_opt_in=True)
        if env.get("status") != "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL":
            raise ValueError("RUN65_TYPED_SOURCE_RED")
        if env["typed_jef_action"] != p2x.decide_sources(
                row["current"], [row["b2_source"], row["b1_source"]]):
            raise ValueError("RUN65_SOURCE_DECISION_RED")
        out["typed_jef_action"] = env["typed_jef_action"]
        out["input_messages"] = env["messages"]
        out["input_sha256"] = sha(dumps(env["messages"]).encode("utf-8"))
        if '"oracle_action"' in dumps(env["messages"]) or '"oracle"' in dumps(env["messages"]):
            raise ValueError("RUN65_ORACLE_LEAK")

        def native(messages):
            if dumps(messages) != dumps(env["messages"]):
                raise ValueError("RUN65_CALLBACK_PROMPT_DRIFT")
            runner = r.pool.get("C3_LANGUAGE")
            output = "".join(runner.generate(
                messages, r.cancel_event, time.monotonic() + 90,
                32, None, seed=13))
            out["native_output"] = output
            out["output_sha256"] = sha(output.encode("utf-8"))
            out["native_metrics"] = dict(runner.last_metrics)
            out["native_c3_final"] = runner.last_metrics.get("status") == "FINAL"
            return output

        staged = stage(
            r.memory, r.session, e_current["event_id"],
            e_current["source_ref"], ids, native,
            operator_opt_in=True, callback_opt_in=True)
        out["staged"] = staged
        if staged.get("status") == STAGED:
            out["c6"] = preflight(
                r.memory, r.session, e_current["event_id"],
                e_current["source_ref"], ids, staged, operator_opt_in=True)
            message = r.store.one(
                "SELECT id,role,text,status,metadata FROM messages WHERE id=?",
                (staged["draft_message_id"],))
            if message:
                out["draft_snapshot"] = {
                    "id": message["id"], "role": message["role"],
                    "text": message["text"], "status": message["status"],
                    "metadata": message["metadata"],
                    "text_sha256": sha(message["text"].encode("utf-8")),
                }
        r.pool.unload()
        out["native_strict_correct"] = int(
            out["native_output"] in ("A", "B", "NONE")
            and out["native_output"] == row["oracle_action"])
        out["source_only_fallback"] = bool(staged.get("source_only_fallback"))
        out["draft_count"] = r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE event_id=? "
            "AND role='assistant' AND status='DRAFT'",
            (e_current["event_id"],))["n"]
        out["no_live_output"] = (
            r.store.one(
                "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0)
        out["status"] = (
            "RECORDED" if out["native_c3_final"]
            and (out["native_metrics"] or {}).get("actual_model")
            == "LFM2.5-350M-QAD-Q4_0.gguf"
            and staged.get("status") == STAGED
            and (out["c6"] or {}).get("status") == "NEEDS_REAL_TTY_APPROVAL"
            and out["draft_count"] == 1 and out["no_live_output"]
            and staged.get("source_action") == row["oracle_action"]
            and staged.get("c3_receiver_success") is False
            else "STRUCTURAL_RED")
    except (Exception, KeyboardInterrupt) as exc:
        out["error_type"] = type(exc).__name__
        out["error"] = str(exc)[:500]
        out["status"] = ("INTERRUPTED" if isinstance(exc, KeyboardInterrupt)
                         else "ERROR")
    finally:
        try:
            r.pool.unload()
            r.close()
        except Exception as exc:
            out["close_error_type"] = type(exc).__name__
            out["status"] = "STRUCTURAL_RED"
        out["process_releases"] = list(r.pool.release_history)
        out["native_process_count"] = sum(
            x.get("before") is not None for x in out["process_releases"])
        out["processes_reaped"] = (
            out["native_process_count"] >= 1
            and all(x.get("process_reaped") is True
                    for x in out["process_releases"]))
        try:
            out["closed_store_audit"] = audit_closed(home)
            if not out["closed_store_audit"]["ok"]:
                out["status"] = "STRUCTURAL_RED"
        except Exception as exc:
            out["closed_store_audit_error"] = type(exc).__name__
            out["status"] = "STRUCTURAL_RED"
        if out["status"] == "RECORDED" and not out["processes_reaped"]:
            out["status"] = "STRUCTURAL_RED"
        out["elapsed_seconds"] = round(time.monotonic() - start, 3)
    return out


def run(installed, out):
    if out.exists():
        raise FileExistsError("RUN65_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    if (binding["model_sha256"]["C3_LANGUAGE"] != C3_SHA256
            or binding["runner_sha256"] != RUNNER_SHA256):
        raise ValueError("RUN65_NATIVE_BINDING_RED")
    report = {
        "schema": "v13.run65.jef_c3_c5_native_report.v1",
        "seed": p2x.SEED, "model_seed": 13,
        "claim": "P2X_CALIBRATION_C3_C5_C6_STRUCTURAL_NOT_DISJOINT_UTILITY",
        "binding": binding, "negative_gates": NEGATIVE,
        "selected_ids": [r["id"] for r in cohort()],
        "rows": [], "row_sha256": {}, "status": "RUNNING",
    }
    atomic_write(out/"report.json", dumps(report))
    for row in cohort():
        result = run_row(out/row["id"], installed, row)
        report["rows"].append(result)
        report["row_sha256"][row["id"]] = sha(dumps(result).encode("utf-8"))
        atomic_write(out/"report.json", dumps(report))
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    report["native_strict_count"] = sum(
        r["native_strict_correct"] for r in report["rows"])
    report["source_only_fallback_count"] = sum(
        int(r["source_only_fallback"]) for r in report["rows"])
    report["status"] = (
        "SOURCE_ONLY_DRAFT_STRUCTURAL_PASS"
        if report["installed_binding_unchanged"]
        and len(report["rows"]) == 3
        and all(r["status"] == "RECORDED" and r["processes_reaped"]
                and r["closed_store_audit"]["ok"]
                for r in report["rows"])
        else "STRUCTURAL_RED")
    atomic_write(out/"report.json", dumps(report))
    print(dumps({"status": report["status"],
                 "native_calls": len(report["rows"]),
                 "strict_c3": report["native_strict_count"],
                 "fallbacks": report["source_only_fallback_count"]}), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    print(dumps({"status": run(a.home, a.out)["status"]}))


if __name__ == "__main__":
    main()
