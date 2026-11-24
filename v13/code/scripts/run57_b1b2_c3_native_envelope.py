#!/usr/bin/env python3
"""Run57: five real pinned B1/B2 -> C3 source-envelope native calls, no output.

Engineering structural replay of Run52 seed479 Harbor only; no utility rescore.
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
from v13.runners import LlamaRunner
from v13.store import audit_closed
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_c3_source_envelope_candidate import build_c3_source_envelope
from scripts.run55_b1b2_topic_native_corrective import ObservedBody, persisted_offer
from scripts.run52_b1b2_cross_turn_native import load_fixture, FIXTURE_SHA256, OVERRIDES, ROLES
from scripts.run47_jef_c3_typed_receiver_native import CONFIG, NEGATIVE
from tests.integration_step2_utility import installed_artifacts, installed_links

ROLE_FILES = {
    "B1_DETAIL": "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
    "B2_GIST": "Qwen3.5-0.8B-Q4_0.gguf",
}
C3_FILE = "LFM2.5-350M-QAD-Q4_0.gguf"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run_row(home, installed, fixture):
    initialize(home)
    save_config(home, CONFIG | OVERRIDES)
    installed_links(home, installed)
    r = Runtime(home)
    row = {"schema": "v13.run57.b1b2_c3_native_row.v1",
           "status": "ERROR", "source_events": {}, "body_offers": [],
           "body_captures": {}, "c3": None, "negative_gates": NEGATIVE,
           "native_process_count": 0, "process_releases": [],
           "processes_reaped": False, "native_model": False,
           "semantic_utility_claim": False, "no_live_output": False,
           "learning_authority": 0}
    started = time.monotonic()
    try:
        row["session_id"] = r.session
        row["generation"] = r.store.generation_id
        row["config_overrides"] = dict(OVERRIDES)
        prior = r.store.event(r.session, fixture["prior"])
        current = r.store.event(r.session, fixture["current"])
        events = {"prior": prior, "current": current}
        for phase, event in events.items():
            text = fixture[phase]
            row["source_events"][phase] = {
                "event_id": event["event_id"], "source_ref": event["source_ref"],
                "text_sha256": sha(text.encode("utf-8"))}
        consumer = TopicPartitionOfferConsumer(r)
        original_get = r.pool.get
        current_key = [None]

        def get_body(role):
            runner = original_get(role)
            if not isinstance(runner, LlamaRunner) or runner.purpose != "generate":
                raise RuntimeError("RUN57_NOT_REAL_BODY_LLAMA_RUNNER")
            return ObservedBody(runner, row["body_captures"], current_key[0])

        r.pool.get = get_body
        current_ids = {}
        for role in ROLES:
            for phase in ("prior", "current"):
                event = events[phase]
                current_key[0] = role + ":" + phase
                result = consumer.guarded_offer(
                    role, event, 0, time.monotonic()+120, operator_opt_in=True)
                if result.get("status") != "SHADOW_OFFER_PRODUCED":
                    raise RuntimeError("RUN57_BODY_OFFER_RED:" + str(result.get("status")))
                offer, query = persisted_offer(
                    r.store, result, role, event, r.models.revision(role))
                row["body_offers"].append({
                    "role": role, "phase": phase,
                    "event_id": event["event_id"],
                    "partition_key_sha256": result["partition_key_sha256"],
                    "offer": offer, "query": query,
                    "capture_key": current_key[0]})
                if phase == "current":
                    current_ids[role] = result["offer_packet_id"]
                r.pool.unload()
        r.pool.get = original_get
        envelope = build_c3_source_envelope(
            r, current, current_ids, operator_opt_in=True)
        if envelope["status"] != "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL":
            raise RuntimeError("RUN57_C3_ENVELOPE_RED:" + envelope["status"])
        row["c3"] = {
            "envelope_status": envelope["status"],
            "offer_packet_ids": current_ids,
            "verified_quote_count": envelope["verified_quote_count"],
            "input_messages": envelope["messages"],
            "input_sha256": envelope["messages_sha256"],
            "output_sha256": None, "output_bytes": 0,
            "native_metrics": None,
        }
        runner = original_get("C3_LANGUAGE")
        if not isinstance(runner, LlamaRunner) or runner.purpose != "generate":
            raise RuntimeError("RUN57_NOT_REAL_C3_LLAMA_RUNNER")
        try:
            output = "".join(runner.generate(
                envelope["messages"], r.cancel_event,
                time.monotonic()+120, 96, None, seed=13))
            row["c3"]["native_metrics"] = dict(runner.last_metrics)
            row["c3"]["output_sha256"] = sha(output.encode("utf-8"))
            row["c3"]["output_bytes"] = len(output.encode("utf-8"))
        finally:
            r.pool.unload()
        row["no_live_output"] = (
            r.store.one("SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                        "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0
            and r.store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0)
        row["native_model"] = (
            len(row["body_offers"]) == 4
            and all(x["offer"]["native_metrics"].get("status") == "FINAL"
                    and x["offer"]["native_metrics"].get("actual_model")
                    == ROLE_FILES[x["role"]] for x in row["body_offers"])
            and row["c3"]["native_metrics"].get("status") == "FINAL"
            and row["c3"]["native_metrics"].get("actual_model") == C3_FILE
            and row["c3"]["output_bytes"] > 0)
        row["status"] = ("RECORDED" if row["native_model"]
                         and row["no_live_output"] else "STRUCTURAL_RED")
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
        row["native_process_count"] = sum(
            x.get("before") is not None for x in row["process_releases"])
        row["processes_reaped"] = (
            row["native_process_count"] >= 5
            and all(x.get("process_reaped") is True
                    for x in row["process_releases"]))
        try:
            row["closed_store_audit"] = audit_closed(home)
            if not row["closed_store_audit"]["ok"]:
                row["status"] = "STRUCTURAL_RED"
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
        raise FileExistsError("RUN57_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {"schema": "v13.run57.b1b2_c3_native_report.v1",
              "seed": 479, "fixture_sha256": FIXTURE_SHA256,
              "claim": "ORIGINAL_RUN52_HARBOR_B1B2_C3_STRUCTURAL_REPLAY_NOT_UTILITY",
              "binding": binding, "negative_gates": NEGATIVE,
              "rows": [], "row_sha256": {}, "status": "RUNNING"}
    atomic_write(out/"report.json", dumps(report))
    fixture = next(f for f in data["fixtures"] if f["id"] == "Harbor")
    row = run_row(out/"Harbor", installed, fixture)
    report["rows"].append(row)
    report["row_sha256"]["Harbor"] = sha(dumps(row).encode("utf-8"))
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    report["status"] = ("B1B2_C3_NATIVE_ENVELOPE_STRUCTURAL_ONLY"
                        if row["status"] == "RECORDED"
                        and report["installed_binding_unchanged"]
                        else "STRUCTURAL_RED")
    atomic_write(out/"report.json", dumps(report))
    print(dumps({"status": report["status"], "row_status": row["status"],
                 "native_process_count": row["native_process_count"]}), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args()
    print(dumps({"status": run(a.home, a.out, a.fixture)["status"]}))


if __name__ == "__main__":
    main()
