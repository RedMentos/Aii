#!/usr/bin/env python3
"""Run62: five real B1/B2/C3 native calls into temporal C5/C6 DRAFT SHADOW.

Same Run51 Cypress seed467 engineering replay, not disjoint utility. No TTY,
output commit, FINAL, external tool dispatch or learning.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import time

from v13.common import atomic_write, dumps
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.runners import LlamaRunner
from v13.store import audit_closed
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.run61_crossorgan_c6_v2_shadow_candidate import stage_run61_crossorgan_c6_v2_shadow
from scripts.run55_b1b2_topic_native_corrective import ObservedBody, persisted_offer
from scripts.run51_f1f5_second_attempt_native import load_fixture, FIXTURE_SHA256
from scripts.run52_b1b2_cross_turn_native import OVERRIDES, ROLES
from scripts.run47_jef_c3_typed_receiver_native import CONFIG, NEGATIVE
from tests.integration_step2_utility import installed_artifacts, installed_links

ROLE_FILES = {"B1_DETAIL": "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
              "B2_GIST": "Qwen3.5-0.8B-Q4_0.gguf"}
C3_FILE = "LFM2.5-350M-QAD-Q4_0.gguf"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run_row(home, installed, fixture):
    initialize(home)
    save_config(home, CONFIG | OVERRIDES)
    installed_links(home, installed)
    r = Runtime(home)
    row = {"schema": "v13.run62.crossorgan_c6_v2_native_row.v1",
           "status": "ERROR", "source_events": {}, "body_offers": [],
           "body_captures": {}, "c3": None, "crossorgan": None,
           "native_model": False, "native_process_count": 0,
           "process_releases": [], "processes_reaped": False,
           "no_live_output": False, "semantic_utility_claim": False,
           "tty_approved": False, "output_committed": False,
           "tool_dispatches": 0, "learning_authority": 0,
           "negative_gates": NEGATIVE}
    started = time.monotonic()
    try:
        row["session_id"] = r.session
        row["generation"] = r.store.generation_id
        correction = r.store.event(r.session, fixture["correction_event"])
        mid = r.memory.feedback(
            correction["event_id"], "fact", fixture["value"],
            permission="record", key=fixture["key"], scope="session")
        current = r.store.event(r.session, fixture["followup"])
        events = {"correction": correction, "current": current}
        row["memory_id"] = mid
        for phase, event in events.items():
            text = fixture["correction_event" if phase == "correction" else "followup"]
            row["source_events"][phase] = {
                "event_id": event["event_id"], "source_ref": event["source_ref"],
                "text_sha256": sha(text.encode("utf-8"))}
        consumer = TopicPartitionOfferConsumer(r)
        original_get = r.pool.get
        current_key = [None]

        def get_body(role):
            runner = original_get(role)
            if not isinstance(runner, LlamaRunner) or runner.purpose != "generate":
                raise RuntimeError("RUN62_NOT_REAL_BODY_LLAMA_RUNNER")
            return ObservedBody(runner, row["body_captures"], current_key[0])

        r.pool.get = get_body
        current_ids = {}
        for role in ROLES:
            for phase in ("correction", "current"):
                event = events[phase]
                current_key[0] = role + ":" + phase
                result = consumer.guarded_offer(
                    role, event, 0, time.monotonic()+120, operator_opt_in=True)
                if result.get("status") != "SHADOW_OFFER_PRODUCED":
                    raise RuntimeError("RUN62_BODY_OFFER_RED:" + str(result.get("status")))
                offer, query = persisted_offer(
                    r.store, result, role, event, r.models.revision(role))
                row["body_offers"].append({
                    "role": role, "phase": phase, "event_id": event["event_id"],
                    "offer": offer, "query": query,
                    "partition_key_sha256": result["partition_key_sha256"],
                    "capture_key": current_key[0]})
                if phase == "current":
                    current_ids[role] = result["offer_packet_id"]
                r.pool.unload()
        r.pool.get = original_get
        row["c3"] = {
            "native_metrics": None, "input_messages": None,
            "input_sha256": None, "output_sha256": None,
            "output_bytes": 0, "candidate_text_stored": False}

        def c3_generate(body_messages, f1f5_messages):
            fused = [
                {"role": "system", "content":
                    f1f5_messages[0]["content"] + "\n\n" + body_messages[0]["content"]},
                {"role": "user", "content":
                    f1f5_messages[1]["content"] + "\n\n" + body_messages[1]["content"]},
            ]
            row["c3"]["input_messages"] = fused
            row["c3"]["input_sha256"] = sha(dumps(fused).encode("utf-8"))
            runner = original_get("C3_LANGUAGE")
            if not isinstance(runner, LlamaRunner) or runner.purpose != "generate":
                raise RuntimeError("RUN62_NOT_REAL_C3_LLAMA_RUNNER")
            try:
                output = "".join(runner.generate(
                    fused, r.cancel_event, time.monotonic()+120, 96, None, seed=13))
                row["c3"]["native_metrics"] = dict(runner.last_metrics)
                row["c3"]["output_sha256"] = sha(output.encode("utf-8"))
                row["c3"]["output_bytes"] = len(output.encode("utf-8"))
                return output
            finally:
                r.pool.unload()

        result = stage_run61_crossorgan_c6_v2_shadow(
            r, current, current_ids, c3_generate,
            operator_opt_in=True, callback_opt_in=True)
        row["crossorgan"] = result
        row["no_live_output"] = (
            r.store.one("SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                        "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0)
        if result.get("draft_message_id"):
            draft = r.store.one("SELECT status FROM messages WHERE id=?",
                                (result["draft_message_id"],))
            row["draft_status"] = draft["status"] if draft else None
        else:
            row["draft_status"] = None
        row["native_model"] = (
            len(row["body_offers"]) == 4
            and all(x["offer"]["native_metrics"].get("status") == "FINAL"
                    and x["offer"]["native_metrics"].get("actual_model")
                    == ROLE_FILES[x["role"]] for x in row["body_offers"])
            and row["c3"]["native_metrics"] is not None
            and row["c3"]["native_metrics"].get("status") == "FINAL"
            and row["c3"]["native_metrics"].get("actual_model") == C3_FILE
            and row["c3"]["output_bytes"] > 0)
        if row["native_model"] and row["no_live_output"]:
            if (result["status"] == "RUN61_C6_V2_PREFLIGHT_ONLY_NEEDS_REAL_TTY"
                    and row["draft_status"] == "DRAFT"):
                row["status"] = "RECORDED_C6_V2_PREFLIGHT_ONLY"
            elif (result["status"] == "RUN61_C6_V2_GROUNDING_RED"
                  and row["draft_status"] == "DRAFT"):
                row["status"] = "RECORDED_C6_V2_GROUNDING_RED"
            else:
                row["status"] = "STRUCTURAL_RED"
        else:
            row["status"] = "STRUCTURAL_RED"
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
            and all(x.get("process_reaped") is True for x in row["process_releases"]))
        try:
            row["closed_store_audit"] = audit_closed(home)
            if not row["closed_store_audit"]["ok"]:
                row["status"] = "STRUCTURAL_RED"
        except Exception as exc:
            row["closed_store_audit_error"] = type(exc).__name__
            row["status"] = "STRUCTURAL_RED"
        if row["status"].startswith("RECORDED") and not row["processes_reaped"]:
            row["status"] = "STRUCTURAL_RED"
        row["elapsed_seconds"] = round(time.monotonic()-started, 3)
    return row


def run(installed, out, fixture_path):
    data = load_fixture(fixture_path)
    if out.exists():
        raise FileExistsError("RUN62_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {"schema": "v13.run62.crossorgan_c6_v2_native_report.v1",
              "seed": 467, "fixture_sha256": FIXTURE_SHA256,
              "claim": "ORIGINAL_RUN51_CYPRESS_RUN62_C6_V2_ENGINEERING_SHADOW_NOT_UTILITY",
              "binding": binding, "negative_gates": NEGATIVE,
              "rows": [], "row_sha256": {}, "status": "RUNNING"}
    atomic_write(out/"report.json", dumps(report))
    fixture = next(f for f in data["fixtures"] if f["id"] == "Cypress")
    row = run_row(out/"Cypress", installed, fixture)
    report["rows"].append(row)
    report["row_sha256"]["Cypress"] = sha(dumps(row).encode("utf-8"))
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    report["status"] = (
        "C6_V2_PREFLIGHT_ONLY_NO_APPROVAL" if row["status"] == "RECORDED_C6_V2_PREFLIGHT_ONLY"
        else "C6_V2_GROUNDING_RED" if row["status"] == "RECORDED_C6_V2_GROUNDING_RED"
        else "STRUCTURAL_RED")
    if not report["installed_binding_unchanged"]:
        report["status"] = "STRUCTURAL_RED"
    atomic_write(out/"report.json", dumps(report))
    print(dumps({"status": report["status"], "row_status": row["status"],
                 "native_process_count": row["native_process_count"],
                 "c6_status": (row.get("crossorgan") or {}).get("c6_status")}), flush=True)
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
