#!/usr/bin/env python3
"""Run85 real B1/B2 + authenticated JEF + C3 native engineering replay.

One already registered Run83 Juniper case, NOT a new scientific cohort.
No output, tools, TTY, learning, C5 staging or promotion. All model calls
are serial. Raw failures and process release evidence are retained.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import time

from v13.common import atomic_write, dumps, file_hash
from v13.config import initialize, save_config
from v13.store import audit_closed
from v13.runners import LlamaRunner
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.jef_b1b2_c3_dual_source_shadow import build as dual_build, STATUS as DUAL_READY
from v13.jef_range_c3_typed_envelope_shadow import build as typed_build, STATUS as TYPED_READY
from v13.jef_b1b2_c3_postgen_shadow import evaluate as guarded_c3
from scripts import jef_body_c3_interference_fixture_839 as fixture
from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts.run63_jef_c3_native import RUN_CONFIG
from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from scripts.run55_b1b2_topic_native_corrective import ObservedBody, persisted_offer

SCHEMA = "v13.run85.real_bodies_jef_c3_engineering.v1"
MODELS = {
    "B1_DETAIL": ("LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
                  "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1"),
    "B2_GIST": ("Qwen3.5-0.8B-Q4_0.gguf",
                "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"),
    "C3_LANGUAGE": ("LFM2.5-350M-QAD-Q4_0.gguf", fixture.MODEL_SHA256),
}
ROLES = ("B1_DETAIL", "B2_GIST")


def save(path, report):
    atomic_write(path, dumps(report))


def record(runtime, key, value):
    event = runtime.store.event(runtime.session, "Record: " + key)
    mid = runtime.memory.feedback(
        event["event_id"], "fact", value, permission="record",
        key=key, scope="session")
    runtime.memory.candidate(mid, runtime.session)
    return mid


def reaped(releases):
    return (bool(releases)
            and any(x.get("before") is not None for x in releases)
            and all(x.get("process_reaped") is True for x in releases))


def run(home, out):
    home, out = Path(home), Path(out)
    if out.exists():
        raise FileExistsError("RUN85_OUTPUT_EXISTS")
    row = fixture.fixtures()[0]
    out.mkdir(parents=True)
    path = out / "report.json"
    report = {
        "schema": SCHEMA, "status": "INCOMPLETE",
        "evidence": "LINUX_NATIVE_ENGINEERING_HISTORICAL_FIXTURE_NOT_NEW_SCIENCE",
        "seed": fixture.SEED, "table_sha256": fixture.TABLE_SHA256,
        "fixture_index": 0, "project_sha256": fixture.sha(row["project"].encode()),
        "source_sha256": row["source_sha256"],
        "expected": row["expected"],
        "models_required": {role: {"file": name, "sha256": digest}
                            for role, (name, digest) in MODELS.items()},
        "runner_sha256_required": fixture.RUNNER_SHA256,
        "models_observed": {}, "runner_sha256_observed": None,
        "native_body_calls": 0, "native_c3_calls": 0,
        "body_offers": [], "body_captures": {}, "c3": [],
        "process_releases": [], "no_live_output": False,
        "closed_store_ok": False,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "delivery_authority": 0, "learning_authority": 0,
        "tool_dispatches": 0, "tty_approved": False,
        "output_committed": False, "native_body": False,
        "independent_reasoning_proven": False,
    }
    save(path, report)
    runtime = None
    try:
        initialize(home)
        save_config(home, RUN_CONFIG | OVERRIDES | {
            "seed": fixture.SEED, "temperature": 0.0,
            "answer_tokens": 32, "observer_tokens": 160,
            "observer_seconds": 120,
        })
        runtime = cli.Runtime(home)
        for role, (name, expected_sha) in MODELS.items():
            actual = file_hash(runtime.models.path_for(role))
            report["models_observed"][role] = {
                "file": name, "sha256": actual}
            if actual != expected_sha:
                raise ValueError("RUN85_MODEL_PIN_RED_" + role)
        runner = Path(os.environ.get(
            "V13_LLAMA_SERVER", str(home / "bin/llama-server")))
        report["runner_sha256_observed"] = file_hash(runner)
        if report["runner_sha256_observed"] != fixture.RUNNER_SHA256:
            raise ValueError("RUN85_RUNNER_PIN_RED")
        ids = [
            record(runtime, "Project Juniper archived " + fixture.TABLE[0][1]
                   + " policy", row["policy_source"]),
            record(runtime, "Project Juniper latest " + fixture.TABLE[0][1]
                   + " option sheet", row["sheet_source"]),
        ]
        event = runtime.store.event(runtime.session, row["current"])
        report["current_source_ref_sha256"] = fixture.sha(
            dumps(event["source_ref"]).encode())
        consumer = TopicPartitionOfferConsumer(runtime)
        original_get = runtime.pool.get
        key = [None]

        def get(role):
            native = original_get(role)
            if role in ROLES:
                if (not isinstance(native, LlamaRunner)
                        or native.purpose != "generate"):
                    raise ValueError("RUN85_BODY_NOT_REAL_LLAMA")
                return ObservedBody(native, report["body_captures"], key[0])
            return native

        runtime.pool.get = get
        offers = {}
        for role in ROLES:
            key[0] = role
            before = len(runtime.pool.release_history)
            try:
                result = consumer.guarded_offer(
                    role, event, 0, time.monotonic() + 180,
                    operator_opt_in=True)
                if result.get("status") != "SHADOW_OFFER_PRODUCED":
                    raise ValueError("RUN85_NATIVE_BODY_OFFER_RED_" + role)
                offer, query = persisted_offer(
                    runtime.store, result, role, event,
                    runtime.models.revision(role))
                metrics = offer.get("native_metrics") or {}
                if (metrics.get("status") != "FINAL"
                        or metrics.get("actual_model") != MODELS[role][0]):
                    raise ValueError("RUN85_NATIVE_BODY_METRICS_RED_" + role)
                report["body_offers"].append({
                    "role": role, "offer": offer, "query": query,
                    "offer_packet_id": result["offer_packet_id"],
                    "query_packet_id": result["query_packet_id"]})
                offers[role] = result["offer_packet_id"]
                report["native_body_calls"] += 1
            finally:
                runtime.pool.unload()
                releases = runtime.pool.release_history[before:]
                report["body_offers"][-1]["process_reaped"] = reaped(
                    releases) if report["body_offers"] else False
                save(path, report)
        runtime.pool.get = original_get
        report["native_body"] = (
            len(report["body_offers"]) == 2
            and all(x.get("process_reaped") for x in report["body_offers"]))
        if not report["native_body"]:
            raise ValueError("RUN85_BODY_RELEASE_RED")
        typed = typed_build(
            runtime.memory, runtime.session, event["event_id"],
            event["source_ref"], ids, operator_opt_in=True)
        dual = dual_build(runtime, event, offers, ids, operator_opt_in=True)
        if (typed.get("status") != TYPED_READY
                or dual.get("status") != DUAL_READY
                or typed.get("typed_jef_action") != row["expected"]
                or dual.get("typed_jef_action") != row["expected"]):
            raise ValueError("RUN85_JEF_DUAL_SOURCE_RED")
        for arm in ("TYPED_ONLY", "DUAL_SOURCE"):
            env = typed if arm == "TYPED_ONLY" else dual
            case = {
                "arm": arm, "input_messages": env["messages"],
                "input_sha256": env["messages_sha256"],
                "expected": row["expected"], "output": None,
                "status": "INCOMPLETE", "native_final": False,
                "process_reaped": False, "post_source_rechecked": False,
            }
            report["c3"].append(case)
            save(path, report)
            before = len(runtime.pool.release_history)

            def generate(messages, schema):
                runner = original_get("C3_LANGUAGE")
                if (not isinstance(runner, LlamaRunner)
                        or runner.purpose != "generate"):
                    raise ValueError("RUN85_C3_NOT_REAL_LLAMA")
                try:
                    output = "".join(runner.generate(
                        messages, runtime.cancel_event,
                        time.monotonic() + 120, 32, schema,
                        seed=fixture.SEED))
                    metrics = dict(runner.last_metrics)
                    case["output"] = output
                    case["output_sha256"] = fixture.sha(output.encode())
                    case["output_bytes"] = len(output.encode())
                    case["actual_model"] = metrics.get("actual_model")
                    case["generated_tokens"] = metrics.get("generated_tokens")
                    case["native_final"] = metrics.get("status") == "FINAL"
                    return output
                finally:
                    runtime.pool.unload()
                    case["process_reaped"] = reaped(
                        runtime.pool.release_history[before:])

            if arm == "DUAL_SOURCE":
                verdict = guarded_c3(
                    runtime, event, offers, ids, generate,
                    operator_opt_in=True, callback_opt_in=True)
                case["postgen_guard"] = verdict
                case["post_source_rechecked"] = (
                    verdict.get("source_rechecked") is True
                    and verdict.get("messages_sha256") == env["messages_sha256"])
            else:
                generate(env["messages"], fixture.SCHEMA)
                after = typed_build(
                    runtime.memory, runtime.session, event["event_id"],
                    event["source_ref"], ids, operator_opt_in=True)
                case["post_source_rechecked"] = (
                    after.get("status") == TYPED_READY
                    and after.get("messages_sha256") == env["messages_sha256"])
            report["native_c3_calls"] += 1
            case["parsed_action"] = fixture.prior.run68.decode_schema(
                case.get("output") or "")
            case["strict"] = fixture.strict(
                case.get("output") or "", row["expected"])
            case["status"] = (
                "RECORDED" if case["native_final"]
                and case.get("actual_model") == MODELS["C3_LANGUAGE"][0]
                and case["process_reaped"] and case["post_source_rechecked"]
                and 0 < case.get("output_bytes", 0) <= 1024
                else "STRUCTURAL_RED")
            save(path, report)
            if case["status"] != "RECORDED":
                raise ValueError("RUN85_C3_ROW_STRUCTURAL_RED")
        report["no_live_output"] = (
            runtime.store.one(
                "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0
            and runtime.store.one(
                "SELECT COUNT(*) AS n FROM actions")["n"] == 0)
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["status"] = "STRUCTURAL_RED"
    finally:
        if runtime is not None:
            try:
                runtime.close()
            except Exception as exc:
                report["close_error_type"] = type(exc).__name__
                report["status"] = "STRUCTURAL_RED"
            report["process_releases"] = list(runtime.pool.release_history)
        try:
            report["closed_store_ok"] = bool(audit_closed(home)["ok"])
        except Exception:
            report["closed_store_ok"] = False
        structural = (
            report["status"] != "STRUCTURAL_RED"
            and report["native_body"]
            and report["native_body_calls"] == 2
            and report["native_c3_calls"] == 2
            and len(report["c3"]) == 2
            and all(x["status"] == "RECORDED" for x in report["c3"])
            and report["no_live_output"] and report["closed_store_ok"])
        report["status"] = (
            "REAL_BODIES_JEF_C3_STRUCTURAL_PASS_FORMATTER_MATCH"
            if structural and all(x["strict"] == 1 for x in report["c3"])
            else "REAL_BODIES_JEF_C3_STRUCTURAL_PASS_FORMATTER_RED"
            if structural else "STRUCTURAL_RED")
        save(path, report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = run(args.home, args.out)
    print(dumps({"status": result["status"],
                 "body_calls": result["native_body_calls"],
                 "c3_calls": result["native_c3_calls"]}))
    raise SystemExit(1 if result["status"] == "STRUCTURAL_RED" else 0)


if __name__ == "__main__":
    main()
