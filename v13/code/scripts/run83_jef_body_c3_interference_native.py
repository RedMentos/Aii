#!/usr/bin/env python3
"""Run83 disjoint 12-call Linux-native C3 formatter interference experiment.

Only C3 is native. B1/B2 offers are explicitly SYNTHETIC contradictory
hypotheses from a deterministic fake runner; never claim native body utility.
No output delivery, tools, learning or TTY. Scientific REDs are retained.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from v13.common import atomic_write, dumps, file_hash
from v13.config import initialize, save_config
from v13.store import audit_closed
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.jef_b1b2_c3_dual_source_shadow import (
    build as build_dual, STATUS as DUAL_STATUS)
from v13.jef_range_c3_typed_envelope_shadow import (
    build as build_typed, STATUS as TYPED_STATUS)
from scripts import jef_body_c3_interference_fixture_839 as f
from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts.run63_jef_c3_native import RUN_CONFIG
from scripts.run52_b1b2_cross_turn_native import OVERRIDES

SCHEMA = "v13.run83.c3_body_hypothesis_interference_native.v1"
C3_MODEL = "LFM2.5-350M-QAD-Q4_0.gguf"
ROLES = ("B1_DETAIL", "B2_GIST")


def save(path, value):
    atomic_write(path, dumps(value))


class SyntheticBody:
    """Not a native model; produces a deliberately misleading body summary."""

    def __init__(self, role, wrong):
        self.role = role
        self.wrong = wrong
        self.last_metrics = {"status": "FINAL", "synthetic_body": True}

    def generate(self, messages, *args, **kwargs):
        yield json.dumps({
            "summary": ("Synthetic fallible body hypothesis: Option "
                        + self.wrong + " is correct."),
            "quotes": [],
            "uncertainty": "low",
            "needs_reentry": False,
        })


def record(runtime, key, value):
    e = runtime.store.event(runtime.session, "Record: " + key)
    mid = runtime.memory.feedback(
        e["event_id"], "fact", value, permission="record",
        key=key, scope="session")
    runtime.memory.candidate(mid, runtime.session)
    return mid


def run(home, out):
    home, out = Path(home), Path(out)
    if out.exists():
        raise FileExistsError("RUN83_OUTPUT_EXISTS")
    rows = f.fixtures()
    out.mkdir(parents=True)
    path = out / "report.json"
    report = {
        "schema": SCHEMA, "seed": f.SEED,
        "table_sha256": f.TABLE_SHA256,
        "model_sha256_required": f.MODEL_SHA256,
        "runner_sha256_required": f.RUNNER_SHA256,
        "temperature": 0.0, "max_tokens": 32,
        "status": "INCOMPLETE", "cases": [],
        "scores": {arm: 0 for arm in f.ARMS},
        "native_call_count": 0,
        "body_native_call_count": 0,
        "body_observations_synthetic": True,
        "typed_answer_visible_to_c3": True,
        "independent_reasoning_proven": False,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "delivery_authority": 0, "learning_authority": 0,
        "tool_dispatches": 0, "output_committed": False,
        "tty_approved": False,
    }
    save(path, report)
    runtime = None
    try:
        initialize(home)
        save_config(home, RUN_CONFIG | OVERRIDES | {
            "seed": f.SEED, "temperature": 0.0,
            "answer_tokens": 32, "observer_tokens": 160,
            "observer_seconds": 120,
        })
        runtime = cli.Runtime(home)
        report["model_sha256_observed"] = file_hash(
            runtime.models.path_for("C3_LANGUAGE"))
        runner_path = Path(os.environ.get(
            "V13_LLAMA_SERVER", str(home / "bin/llama-server")))
        report["runner_sha256_observed"] = file_hash(runner_path)
        if (report["model_sha256_observed"] != f.MODEL_SHA256
                or report["runner_sha256_observed"] != f.RUNNER_SHA256):
            raise ValueError("RUN83_MODEL_OR_RUNNER_PIN_RED")
        original_get = runtime.pool.get
        synthetic_wrong = [None]

        def get(role):
            if role in ROLES:
                if synthetic_wrong[0] not in ("A", "B", "NONE"):
                    raise ValueError("RUN83_SYNTHETIC_BODY_UNBOUND")
                return SyntheticBody(role, synthetic_wrong[0])
            return original_get(role)

        runtime.pool.get = get
        for row in rows:
            synthetic_wrong[0] = row["wrong_body_action"]
            ids = [
                record(runtime, "Project " + row["project"]
                       + " archived " + f.TABLE[row["index"]][1]
                       + " policy", row["policy_source"]),
                record(runtime, "Project " + row["project"]
                       + " latest " + f.TABLE[row["index"]][1]
                       + " option sheet", row["sheet_source"]),
            ]
            event = runtime.store.event(runtime.session, row["current"])
            consumer = TopicPartitionOfferConsumer(runtime)
            offer_ids = {}
            for role in ROLES:
                result = consumer.guarded_offer(
                    role, event, 0, time.monotonic() + 180,
                    operator_opt_in=True)
                if result.get("status") != "SHADOW_OFFER_PRODUCED":
                    raise ValueError("RUN83_SYNTHETIC_BODY_OFFER_RED")
                offer_ids[role] = result["offer_packet_id"]
            typed = build_typed(
                runtime.memory, runtime.session, event["event_id"],
                event["source_ref"], ids, operator_opt_in=True)
            dual = build_dual(
                runtime, event, offer_ids, ids, operator_opt_in=True)
            if (typed.get("status") != TYPED_STATUS
                    or dual.get("status") != DUAL_STATUS
                    or typed.get("typed_jef_action") != row["expected"]
                    or dual.get("typed_jef_action") != row["expected"]):
                raise ValueError("RUN83_ENVELOPE_OR_TYPED_ACTION_RED")
            envelopes = {"TYPED_ONLY": typed, "DUAL_SOURCE": dual}
            for arm in row["arm_order"]:
                env = envelopes[arm]
                messages = env["messages"]
                case = {
                    "index": row["index"], "arm": arm,
                    "project_sha256": f.sha(row["project"].encode()),
                    "expected": row["expected"],
                    "wrong_body_action": row["wrong_body_action"],
                    "source_sha256": row["source_sha256"],
                    "synthetic_body": True,
                    "native_body": False,
                    "typed_jef_action": env["typed_jef_action"],
                    "input_messages": messages,
                    "input_sha256": f.sha(dumps(messages).encode()),
                    "native_final": False, "process_reaped": False,
                    "post_source_rechecked": False,
                    "status": "INCOMPLETE", "strict": 0,
                }
                report["cases"].append(case)
                save(path, report)
                before = len(runtime.pool.release_history)
                try:
                    runner = runtime.pool.get("C3_LANGUAGE")
                    output = "".join(runner.generate(
                        messages, runtime.cancel_event,
                        time.monotonic() + 90, 32, f.SCHEMA,
                        seed=f.SEED))
                    metrics = dict(runner.last_metrics)
                    case["output"] = output
                    case["output_sha256"] = f.sha(output.encode())
                    case["output_bytes"] = len(output.encode())
                    case["parsed_action"] = f.prior.run68.decode_schema(output)
                    case["strict"] = f.strict(output, row["expected"])
                    case["native_final"] = metrics.get("status") == "FINAL"
                    case["actual_model"] = metrics.get("actual_model")
                    case["generated_tokens"] = metrics.get("generated_tokens")
                except Exception as exc:
                    case["error_type"] = type(exc).__name__
                finally:
                    try:
                        runtime.pool.unload()
                    except Exception as exc:
                        case["release_error_type"] = type(exc).__name__
                    releases = runtime.pool.release_history[before:]
                    case["process_reaped"] = (
                        bool(releases)
                        and any(x.get("before") is not None for x in releases)
                        and all(x.get("process_reaped") is True
                                for x in releases))
                    if arm == "TYPED_ONLY":
                        after = build_typed(
                            runtime.memory, runtime.session,
                            event["event_id"], event["source_ref"],
                            ids, operator_opt_in=True)
                    else:
                        after = build_dual(
                            runtime, event, offer_ids, ids,
                            operator_opt_in=True)
                    case["post_source_rechecked"] = (
                        after.get("status") == (
                            TYPED_STATUS if arm == "TYPED_ONLY"
                            else DUAL_STATUS)
                        and after.get("messages_sha256")
                        == env["messages_sha256"])
                    case["status"] = (
                        "RECORDED" if case["native_final"]
                        and case.get("actual_model") == C3_MODEL
                        and case["process_reaped"]
                        and case["post_source_rechecked"]
                        and 0 < case.get("output_bytes", 0) <= 1024
                        else "STRUCTURAL_RED")
                    report["native_call_count"] += 1
                    report["scores"][arm] += case["strict"]
                    save(path, report)
                if case["status"] != "RECORDED":
                    raise RuntimeError("RUN83_NATIVE_ROW_RED")
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
        try:
            report["closed_store_ok"] = bool(audit_closed(home)["ok"])
        except Exception:
            report["closed_store_ok"] = False
        structural = (
            len(report["cases"]) == 12
            and report["native_call_count"] == 12
            and all(c["status"] == "RECORDED"
                    for c in report["cases"])
            and report.get("no_live_output") is True
            and report["closed_store_ok"]
            and report["status"] != "STRUCTURAL_RED")
        report["status"] = (
            f.verdict(report["scores"]) if structural
            else "STRUCTURAL_RED")
        save(path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.home, args.out)
    print(dumps({"status": report["status"],
                 "scores": report["scores"],
                 "native_calls": report["native_call_count"]}))
    raise SystemExit(0 if report["status"] in (
        "DUAL_FORMATTER_NONINFERIOR_SMALL_SHADOW",
        "DUAL_INTERFERENCE_RED", "BASELINE_FORMATTER_RED") else 1)


if __name__ == "__main__":
    main()
