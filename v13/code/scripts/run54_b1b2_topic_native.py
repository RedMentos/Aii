#!/usr/bin/env python3
"""Run54 pinned B1/B2 native topic-partition source transport regression.

Original Run52 Harbor/Willow seed479 reused only for structural integration,
not independent utility, scoring or promotion.
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
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from scripts.run52_b1b2_cross_turn_native import load_fixture, FIXTURE_SHA256, OVERRIDES, ROLES
from scripts.run47_jef_c3_typed_receiver_native import CONFIG, NEGATIVE
from tests.integration_step2_utility import installed_artifacts, installed_links


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run_row(home, installed, fixtures):
    initialize(home)
    save_config(home, CONFIG | OVERRIDES)
    installed_links(home, installed)
    r = Runtime(home)
    row = {"schema": "v13.run54.b1b2_topic_native_row.v1",
           "status": "ERROR", "offers": [], "events": {},
           "negative_gates": NEGATIVE, "off_control": None,
           "ambiguous_control": None, "replay_control": None,
           "process_releases": [], "native_process_count": 0,
           "processes_reaped": False, "no_live_output": False,
           "native_model": False, "semantic_utility_claim": False}
    started = time.monotonic()
    try:
        row["session_id"] = r.session
        row["generation"] = r.store.generation_id
        row["config_overrides"] = dict(OVERRIDES)
        consumer = TopicPartitionOfferConsumer(r)
        sequence = [("Harbor","prior"), ("Willow","prior"),
                    ("Harbor","current"), ("Willow","current")]
        for project, phase in sequence:
            e = r.store.event(r.session, fixtures[project][phase])
            row["events"][project+"_"+phase] = {
                "event_id": e["event_id"], "source_ref": e["source_ref"],
                "text_sha256": sha(fixtures[project][phase].encode())}
        first = row["events"]["Harbor_prior"]
        event_map = {}
        for project, phase in sequence:
            name = project+"_"+phase
            event_map[name] = r.store.one(
                "SELECT packet FROM events WHERE id=?",
                (row["events"][name]["event_id"],))
            event_map[name] = json.loads(event_map[name]["packet"])
        before = r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind IN ('QueryPacket','OfferPacket')")["n"]
        row["off_control"] = consumer.guarded_offer(
            "B1_DETAIL", event_map["Harbor_prior"], 0,
            time.monotonic()+30, operator_opt_in=False)
        ambiguous = r.store.event(
            r.session, "Project Harbor and Project Willow both have separate budgets.")
        row["ambiguous_control"] = consumer.guarded_offer(
            "B1_DETAIL", ambiguous, 0, time.monotonic()+30,
            operator_opt_in=True)
        row["pre_native_packet_count"] = r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind IN ('QueryPacket','OfferPacket')")["n"]
        row["controls_no_packets"] = row["pre_native_packet_count"] == before
        for role in ROLES:
            for project, phase in sequence:
                name = project+"_"+phase
                event = event_map[name]
                result = consumer.guarded_offer(
                    role, event, 0, time.monotonic()+120,
                    operator_opt_in=True)
                entry = {"role": role, "project": project, "phase": phase,
                         "event_id": event["event_id"], "status": result["status"],
                         "topic_partitioned": result.get("topic_partitioned"),
                         "partition_key_sha256": result.get("partition_key_sha256")}
                if result["status"] == "SHADOW_OFFER_PRODUCED":
                    offer = result["offer"]
                    qrow = r.store.one(
                        "SELECT payload FROM packets WHERE id=? AND kind='QueryPacket'",
                        (offer["query_packet_id"],))
                    if qrow is None:
                        raise ValueError("RUN54_MISSING_QUERY")
                    entry["query"] = json.loads(qrow["payload"])
                    entry["offer"] = offer
                row["offers"].append(entry)
                r.pool.unload()
        row["replay_control"] = consumer.guarded_offer(
            "B1_DETAIL", event_map["Harbor_prior"], 0,
            time.monotonic()+30, operator_opt_in=True)
        row["post_replay_packet_count"] = r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind IN ('QueryPacket','OfferPacket')")["n"]
        row["no_live_output"] = r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0
        entries = row["offers"]
        row["native_model"] = (len(entries) == 8 and all(
            e.get("offer",{}).get("native_metrics",{}).get("status") == "FINAL"
            and e["offer"]["native_metrics"].get("actual_model")
            == "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf"
            for e in entries))
        row["status"] = "RECORDED" if (
            row["native_model"] and row["controls_no_packets"]
            and row["off_control"]["status"] == "OFF"
            and row["ambiguous_control"]["status"] == "TOPIC_SCOPE_RED"
            and row["replay_control"]["status"] == "STALE_REPLAY_NO_OFFER"
            and row["post_replay_packet_count"] == before+16
            and row["no_live_output"]) else "STRUCTURAL_RED"
    except (Exception, KeyboardInterrupt) as exc:
        row["error_type"] = type(exc).__name__
        row["error"] = str(exc)[:500]
        row["status"] = "INTERRUPTED" if isinstance(exc,KeyboardInterrupt) else "ERROR"
    finally:
        try:
            r.close()
        except Exception as exc:
            row["close_error_type"] = type(exc).__name__
            row["status"] = "STRUCTURAL_RED"
        row["process_releases"] = list(r.pool.release_history)
        row["native_process_count"] = sum(
            x.get("before") is not None for x in row["process_releases"])
        row["processes_reaped"] = (row["native_process_count"] >= 8
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
        row["elapsed_seconds"] = round(time.monotonic()-started,3)
    return row


def run(installed, out, fixture_path):
    data = load_fixture(fixture_path)
    if out.exists():
        raise FileExistsError("RUN54_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {"schema": "v13.run54.b1b2_topic_native_report.v1",
              "seed": 479, "fixture_sha256": FIXTURE_SHA256,
              "claim": "ORIGINAL_RUN52_HARBOR_WILLOW_STRUCTURAL_REGRESSION_NOT_UTILITY",
              "binding": binding, "negative_gates": NEGATIVE,
              "rows": [], "row_sha256": {}, "status": "RUNNING"}
    atomic_write(out/"report.json", dumps(report))
    fixtures = {f["id"]: f for f in data["fixtures"]}
    row = run_row(out/"Harbor_Willow", installed, fixtures)
    report["rows"].append(row)
    report["row_sha256"]["Harbor_Willow"] = sha(dumps(row).encode())
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    report["status"] = ("TOPIC_PARTITION_NATIVE_STRUCTURAL_ONLY"
                        if row["status"] == "RECORDED"
                        and report["installed_binding_unchanged"]
                        else "STRUCTURAL_RED")
    atomic_write(out/"report.json", dumps(report))
    print(dumps({"status": report["status"],
                 "row_status": row["status"],
                 "native_process_count": row["native_process_count"]}),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--fixture",type=Path,required=True)
    a=p.parse_args()
    print(dumps({"status":run(a.home,a.out,a.fixture)["status"]}))


if __name__ == "__main__":
    main()
