#!/usr/bin/env python3
"""Run63: six paired real C3 calls, human F1/F5 JEF typed vs raw sources.

Original P2X calibration engineering replay, not disjoint utility or output.
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
from v13.jef_c3_typed_envelope_candidate import (
    build_jef_c3_typed_envelope, verify_jef_c3_formatter_output)
from scripts import p2x_disjoint_receiver_trainset as p2x
from scripts.run47_jef_c3_typed_receiver_native import CONFIG, NEGATIVE
from scripts.run59_crossorgan_c6_native import audit_closed
from tests.integration_step2_utility import installed_artifacts, installed_links

C3_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
ARMS = ("RAW", "TYPED")
ORDER = {"A": ("RAW", "TYPED"), "B": ("TYPED", "RAW"),
         "NONE": ("RAW", "TYPED")}
RAW_SYSTEM = (
    "Use only the exact archived policy and latest option sheet to select "
    "A, B or NONE for the current project. Return exactly one uppercase "
    "token A, B or NONE. No explanation, JSON or punctuation."
)
RUN_CONFIG = CONFIG | {"answer_tokens": 32, "seed": 13, "temperature": 0.}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def cohort():
    rows = p2x.fixtures()
    p2x.validate(rows)
    calibration = [r for r in rows if r["partition"] == "calibration"]
    return [min((r for r in calibration if r["oracle_action"] == a),
                key=lambda r: r["id"]) for a in ("A", "B", "NONE")]


def raw_messages(row):
    payload = {"current_source": row["current"],
               "policy_source": row["b2_source"],
               "sheet_source": row["b1_source"],
               "candidate_authority": 0}
    return [{"role": "system", "content": RAW_SYSTEM},
            {"role": "user", "content": dumps(payload)}]


def run_row(home, installed, row, arm):
    initialize(home)
    save_config(home, RUN_CONFIG)
    installed_links(home, installed)
    r = Runtime(home)
    r.sleep.cycle.set_policy("enabled", "off")
    start = time.monotonic()
    out = {
        "schema": "v13.run63.jef_c3_native_row.v1",
        "id": row["id"], "arm": arm, "oracle_action": row["oracle_action"],
        "source_sha256": {k: sha(row[k].encode("utf-8"))
                          for k in ("current", "b1_source", "b2_source")},
        "status": "ERROR", "native_output": "", "output_sha256": None,
        "input_messages": None, "input_sha256": None,
        "native_metrics": None, "native_c3_final": False,
        "native_process_count": 0, "processes_reaped": False,
        "process_releases": [], "closed_store_audit": None,
        "no_live_output": False, "tty_approved": False,
        "output_committed": False, "tool_dispatches": 0,
        "learning_authority": 0, "candidate_authority": 0,
        "oracle_visible_to_native": False,
        "typed_source_verified": False,
        "formatter_status": None,
        "score": {"strict_correct": 0, "exact_formatter_match": 0},
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
        out["source_refs"] = {
            "current": e_current["source_ref"],
            "policy": r.memory.candidate(policy_mid, r.session)["source_ref"],
            "sheet": r.memory.candidate(sheet_mid, r.session)["source_ref"],
        }
        if arm == "TYPED":
            envelope = build_jef_c3_typed_envelope(
                r.memory, r.session, e_current["event_id"],
                e_current["source_ref"], [policy_mid, sheet_mid],
                operator_opt_in=True)
            if envelope.get("status") != "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL":
                raise ValueError("RUN63_TYPED_ENVELOPE_RED:" + envelope.get("status", ""))
            if envelope["typed_jef_action"] != p2x.decide_sources(
                    row["current"], [row["b2_source"], row["b1_source"]]):
                raise ValueError("RUN63_TYPED_SOURCE_DECISION_RED")
            out["typed_source_verified"] = True
            out["typed_jef_action"] = envelope["typed_jef_action"]
            messages = envelope["messages"]
        elif arm == "RAW":
            messages = raw_messages(row)
        else:
            raise ValueError("RUN63_ARM_RED")
        out["input_messages"] = messages
        out["input_sha256"] = sha(dumps(messages).encode("utf-8"))
        if '"oracle_action"' in dumps(messages) or '"oracle"' in dumps(messages):
            raise ValueError("RUN63_ORACLE_LEAK")
        runner = r.pool.get("C3_LANGUAGE")
        output = "".join(runner.generate(
            messages, r.cancel_event, time.monotonic() + 90,
            32, None, seed=13))
        out["native_output"] = output
        out["output_sha256"] = sha(output.encode("utf-8"))
        out["native_metrics"] = dict(runner.last_metrics)
        out["native_c3_final"] = runner.last_metrics.get("status") == "FINAL"
        r.pool.unload()
        if arm == "TYPED":
            checked = verify_jef_c3_formatter_output(envelope, output)
            out["formatter_status"] = checked["status"]
            out["score"]["exact_formatter_match"] = int(
                checked["status"] == "FORMATTER_MATCH_SHADOW")
        out["score"]["strict_correct"] = int(
            output in ("A", "B", "NONE") and output == row["oracle_action"])
        out["no_live_output"] = (
            r.store.one("SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                        "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0)
        out["status"] = (
            "RECORDED" if out["native_c3_final"] and out["no_live_output"]
            and out["native_metrics"].get("actual_model")
            == "LFM2.5-350M-QAD-Q4_0.gguf" else "STRUCTURAL_RED")
    except (Exception, KeyboardInterrupt) as exc:
        out["error_type"] = type(exc).__name__
        out["error"] = str(exc)[:500]
        out["status"] = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "ERROR"
    finally:
        try:
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
        if out["status"] != "RECORDED":
            out["score"] = {"strict_correct": 0, "exact_formatter_match": 0}
        out["elapsed_seconds"] = round(time.monotonic()-start, 3)
    return out


def run(installed, out):
    if out.exists():
        raise FileExistsError("RUN63_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    if (binding["model_sha256"]["C3_LANGUAGE"] != C3_SHA256
            or binding["runner_sha256"] != RUNNER_SHA256):
        raise ValueError("RUN63_NATIVE_BINDING_RED")
    report = {
        "schema": "v13.run63.jef_c3_native_report.v1",
        "seed": p2x.SEED, "model_seed": 13,
        "claim": "P2X_CALIBRATION_JEF_C3_ENGINEERING_NOT_DISJOINT_UTILITY",
        "binding": binding, "negative_gates": NEGATIVE,
        "selected_ids": [r["id"] for r in cohort()],
        "rows": [], "row_sha256": {}, "status": "RUNNING",
    }
    atomic_write(out/"report.json", dumps(report))
    for row in cohort():
        for arm in ORDER[row["oracle_action"]]:
            key = row["id"] + "/" + arm
            result = run_row(out/key.replace("/", "_"), installed, row, arm)
            report["rows"].append(result)
            report["row_sha256"][key] = sha(dumps(result).encode("utf-8"))
            atomic_write(out/"report.json", dumps(report))
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    scores = {arm: sum(r["score"]["strict_correct"] for r in report["rows"]
                       if r["arm"] == arm) for arm in ARMS}
    report["scores"] = scores
    structural = (
        report["installed_binding_unchanged"]
        and len(report["rows"]) == 6
        and all(r["status"] == "RECORDED"
                and r["native_c3_final"] and r["processes_reaped"]
                and r["closed_store_audit"]["ok"] and r["no_live_output"]
                for r in report["rows"]))
    report["status"] = (
        "STRUCTURAL_RED" if not structural else
        "RECEIVER_PILOT_PASS" if scores["TYPED"] == 3
        and scores["TYPED"] > scores["RAW"]
        and all(r["score"]["exact_formatter_match"] == 1
                for r in report["rows"] if r["arm"] == "TYPED")
        else "RECEIVER_PILOT_RED")
    atomic_write(out/"report.json", dumps(report))
    print(dumps({"status": report["status"], "scores": scores,
                 "native_rows": len(report["rows"])}), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    print(dumps({"status": run(a.home, a.out)["status"]}))


if __name__ == "__main__":
    main()
