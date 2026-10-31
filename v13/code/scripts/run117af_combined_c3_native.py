#!/usr/bin/env python3
"""Run117AF: preregistered disjoint seed1067 two-arm pinned native C3.

Synthetic B1/B2 offers are persisted in a real SQLite Store. Deterministic
JEF-only and combined ContextOS prompts are both *actually* sent to pinned
native C3; this is not native Body/JEF/C2 or live V13 output.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import time

from scripts.run111_c3_b2_context_native import _prepare_home
from scripts.run113b_b1b2_c3_native import _reaped
from scripts.run115j_typed_jef_role_native import (
    C3_FILE, C3_SHA, C3_REV, RUNNER_SHA, SCHEMA,
)
from scripts.run117w_c3_arithmetic_native import CONFIG as BASE_CONFIG
from scripts.run47_jef_c3_typed_receiver_native import score
from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from tests.test_run117af_combined_c3_native_preflight import (
    ARMS, IDS, SHA as FIXTURE_SHA, frozen_rows,
)
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_jef_span_c3_bridge_candidate import build_b1b2_jef_span_c3_bridge
from v13.common import atomic_write, dumps, file_hash
from v13.jef_span_budget_shadow_candidate import build_jef_span_budget_shadow
from v13.models import ModelManager
from v13.runtime import Runtime
from v13.store import audit_closed

SEED = 1067
CONFIG = BASE_CONFIG | {"seed": SEED}
RED = "STRUCTURAL_RED"
COMPLETE = "NATIVE_COMPLETE_EXPLORATORY_PAIRED_COMPARISON"


def _pin(installed):
    m = ModelManager(installed)
    if (file_hash(m.path_for("C3_LANGUAGE")) != C3_SHA
            or m.revision("C3_LANGUAGE") != C3_REV
            or file_hash(installed / "bin/llama-server") != RUNNER_SHA):
        raise ValueError("RUN117AF_PINNED_C3_OR_RUNNER_RED")


def _prompts(row, fake_home):
    fake = QuoteRuntime(fake_home, row)
    fake.cfg.update(OVERRIDES)
    result = {}
    try:
        prior = fake.store.event(fake.session, row["prior"])
        current = fake.store.event(fake.session, row["current"])
        jef = build_jef_span_budget_shadow(
            fake, prior, current, operator_opt_in=True)
        if (jef.get("status") != "SHADOW_SOURCE_BOUND_JEF_BUDGET_VERIFIED"
                or jef.get("typed_jef_candidate") != row["oracle"]):
            raise ValueError("RUN117AF_JEF_STORE_ORACLE_RED")
        consumer = TopicPartitionOfferConsumer(fake)
        ids = {}
        for role in ("B1_DETAIL", "B2_GIST"):
            offer = consumer.guarded_offer(
                role, current, 0, time.monotonic()+30,
                operator_opt_in=True)
            if offer.get("status") != "SHADOW_OFFER_PRODUCED":
                raise ValueError("RUN117AF_PERSISTED_OFFER_RED")
            ids[role] = offer["offer_packet_id"]
        bridge = build_b1b2_jef_span_c3_bridge(
            fake, prior, current, ids, operator_opt_in=True)
        if (bridge.get("status") !=
                "SHADOW_B1B2_JEF_SPAN_C3_BRIDGE_VERIFIED"
                or bridge.get("typed_jef_candidate") != row["oracle"]
                or bridge.get("source_refs") != jef.get("source_refs")
                or bridge.get("output_committed") is not False
                or bridge.get("tool_dispatches") != 0
                or bridge.get("learning_authority") != 0
                or bridge.get("delivery_authority") != 0
                or bridge.get("jepa_weight") != 0):
            raise ValueError("RUN117AF_COMBINED_BRIDGE_RED")
        messages = {ARMS[0]: jef["messages"], ARMS[1]: bridge["messages"]}
        for arm, prompt in messages.items():
            if ([m["role"] for m in prompt] != ["system", "user"]
                    or row["policy_span"] in prompt[0]["content"]
                    or row["option_span"] in prompt[0]["content"]
                    or '"oracle"' in prompt[1]["content"]):
                raise ValueError("RUN117AF_ROLE_OR_ORACLE_LEAK_RED_" + arm)
        if "body_observations" in messages[ARMS[0]][1]["content"]:
            raise ValueError("RUN117AF_BASE_BODY_LEAK_RED")
        if "body_observations" not in messages[ARMS[1]][1]["content"]:
            raise ValueError("RUN117AF_COMBINED_BODY_MISSING_RED")
        result = {
            "messages": messages,
            "source_refs": jef["source_refs"],
            "offer_packet_ids": ids,
            "context_plan_packet_id": bridge["context_plan_packet_id"],
            "verified_quote_count": bridge["verified_quote_count"],
            "synthetic_body_calls": dict(fake.calls),
            "typed_candidate": jef["typed_jef_candidate"],
            "no_live_output": fake.store.one(
                "SELECT COUNT(*) AS n FROM actions")["n"] == 0 and
                fake.store.one(
                    "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"] == 0,
        }
    finally:
        fake.close()
    result["closed_store_ok"] = bool(audit_closed(fake_home)["ok"])
    if not result["closed_store_ok"] or not result["no_live_output"]:
        raise ValueError("RUN117AF_FAKE_STORE_OR_OUTPUT_RED")
    return result


def _summarize(report):
    if (len(report["rows"]) != len(IDS)
            or report["native_c3_calls"] != 12
            or report["native_body_calls"] != 0
            or report["native_jef_calls"] != 0
            or report["native_c2_calls"] != 0):
        return RED
    scores = {arm:0 for arm in ARMS}
    for row in report["rows"]:
        if (row.get("status") != "RECORDED"
                or row.get("closed_native_store_ok") is not True
                or row.get("closed_fake_store_ok") is not True
                or len(row.get("arms", [])) != 2):
            return RED
        for item in row["arms"]:
            if (item.get("status") != "RECORDED"
                    or item.get("native_final") is not True
                    or item.get("process_reaped") is not True
                    or item.get("native_metrics", {}).get("actual_model") != C3_FILE
                    or type(item.get("score", {}).get("correct")) is not int):
                return RED
            scores[item["arm"]] += item["score"]["correct"]
    report["scores"] = scores
    report["paired_difference"] = scores[ARMS[1]] - scores[ARMS[0]]
    return COMPLETE


def run(fixture_path, installed, work, out):
    if sha256(Path(fixture_path).read_bytes()).hexdigest() != FIXTURE_SHA:
        raise ValueError("RUN117AF_FIXTURE_SHA_RED")
    rows = frozen_rows()
    installed, work, out = Path(installed).resolve(), Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError("RUN117AF_FRESH_WORK_OUT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    report = {
        "schema":"v13.run117af.combined_c3_native_seed1067.v1",
        "seed":SEED, "fixture_sha256":FIXTURE_SHA,
        "status":"INCOMPLETE", "native_c3":True,
        "native_c3_calls":0, "native_body_calls":0,
        "native_jef_calls":0, "native_c2_calls":0,
        "body_offers_synthetic":True, "rows":[],
        "scores":{arm:0 for arm in ARMS},
        "output_committed":False, "tool_dispatches":0,
        "learning_authority":0, "delivery_authority":0,
        "age0":"RECORD_ONLY", "step2_exit":"EVIDENCE_NOT_PASSING",
        "b3":"NO_PROMOTION", "body_jepa":"UNAVAILABLE",
        "jepa_weight":0, "redmi_measured":False,
        "whole_system_complete":False,
    }
    def save():
        atomic_write(out / "report.json", dumps(report))
    save()
    try:
        _pin(installed)
        for index, row in enumerate(rows):
            home = work / row["id"]
            fake_home = home / "fake"
            native_home = home / "native"
            home.mkdir()
            entry = {
                "id":row["id"], "status":"INCOMPLETE",
                "arms":[], "closed_fake_store_ok":False,
                "closed_native_store_ok":False, "no_live_output":False,
            }
            report["rows"].append(entry)
            save()
            try:
                prep = _prompts(row, fake_home)
                entry.update(
                    source_refs=prep["source_refs"],
                    offer_packet_ids=prep["offer_packet_ids"],
                    context_plan_packet_id=prep["context_plan_packet_id"],
                    verified_quote_count=prep["verified_quote_count"],
                    synthetic_body_calls=prep["synthetic_body_calls"],
                    closed_fake_store_ok=prep["closed_store_ok"],
                    no_live_output=prep["no_live_output"],
                )
                save()
                _prepare_home(native_home, installed, CONFIG)
                native = Runtime(native_home)
                try:
                    order = ARMS[index % 2:] + ARMS[:index % 2]
                    for arm in order:
                        messages = prep["messages"][arm]
                        item = {
                            "arm":arm, "status":"INCOMPLETE",
                            "messages":messages,
                            "messages_sha256":sha256(dumps(messages).encode()).hexdigest(),
                            "native_final":False, "process_reaped":False,
                            "score":None,
                        }
                        entry["arms"].append(item)
                        save()
                        before = len(native.pool.release_history)
                        try:
                            runner = native.pool.get("C3_LANGUAGE")
                            report["native_c3_calls"] += 1
                            save()
                            output = "".join(runner.generate(
                                messages, native.cancel_event,
                                time.monotonic()+120, 96, SCHEMA, seed=SEED))
                            item["output"] = output
                            item["native_metrics"] = dict(runner.last_metrics)
                            item["native_final"] = (
                                item["native_metrics"].get("status") == "FINAL")
                            item["score"] = score(output, row["oracle"])
                        except Exception as exc:
                            item["error_type"] = type(exc).__name__
                            item["error"] = str(exc)[:240]
                        finally:
                            native.pool.unload()
                            item["process_reaped"] = _reaped(
                                native.pool.release_history[before:])
                            item["status"] = ("RECORDED" if item["native_final"]
                                and item["process_reaped"]
                                and item.get("native_metrics", {}).get(
                                    "actual_model") == C3_FILE else RED)
                            save()
                    entry["status"] = (
                        "RECORDED" if all(a["status"] == "RECORDED"
                                          for a in entry["arms"]) else RED)
                finally:
                    native.close()
                entry["closed_native_store_ok"] = bool(
                    audit_closed(native_home)["ok"])
            except Exception as exc:
                entry["status"] = RED
                entry["error_type"] = type(exc).__name__
                entry["error"] = str(exc)[:240]
            if (not entry["closed_native_store_ok"]
                    or not entry["closed_fake_store_ok"]
                    or not entry["no_live_output"]):
                entry["status"] = RED
            save()
        report["status"] = _summarize(report)
    except Exception as exc:
        report["status"] = RED
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:240]
    save()
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fixture",type=Path,required=True)
    p.add_argument("--installed",type=Path,required=True)
    p.add_argument("--work",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    r=run(args.fixture,args.installed,args.work,args.out)
    print(dumps({"status":r["status"],"scores":r["scores"],
                 "native_c3_calls":r["native_c3_calls"]}))
    return 0 if r["status"] == COMPLETE else 2


if __name__=="__main__":
    raise SystemExit(main())
