#!/usr/bin/env python3
"""Run77 disjoint seed797 B1/B2 paired prior-context native utility probe.

36 serialized native offers on six synthetic projects. No C3, visible output,
training, production consumer or gate promotion. REDs are retained verbatim.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import time

from v13.common import atomic_write, dumps
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.runners import LlamaRunner
from v13.store import audit_closed
from v13.b1b2_latest_user_offer_candidate import LatestUserOfferConsumer
from scripts import jef_b1b2_context_fixture_797 as f
from scripts.run55_b1b2_topic_native_corrective import (
    ObservedBody, persisted_offer)
from scripts.run47_jef_c3_typed_receiver_native import CONFIG
from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.integration_step2_utility import installed_artifacts, installed_links

SCHEMA = "v13.run77.b1b2_disjoint_context_native.v1"
ROLE_MODELS = {
    "B1_DETAIL": "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
    "B2_GIST": "Qwen3.5-0.8B-Q4_0.gguf",
}


def _save(path, value):
    atomic_write(path, dumps(value))


def run_arm(home, installed, fixture, arm, save):
    initialize(home)
    cfg = CONFIG | OVERRIDES | {
        "seed": f.SEED, "observer_tokens": 96,
        "observer_seconds": 120,
    }
    save_config(home, cfg)
    installed_links(home, installed)
    runtime = Runtime(home)
    result = {
        "project": fixture["project"], "arm": arm,
        "status": "INCOMPLETE", "offers": [], "captures": {},
        "source_sha256": fixture["source_sha256"],
        "no_live_output": False, "closed_store_ok": False,
        "processes_reaped": False, "native_call_count": 0,
        "b2_prior_evidence": False,
    }
    try:
        consumer = LatestUserOfferConsumer(runtime)
        original_get = runtime.pool.get
        current_key = [None]

        def get(role):
            real = original_get(role)
            if not isinstance(real, LlamaRunner) or real.purpose != "generate":
                raise RuntimeError("RUN77_NOT_REAL_NATIVE_BODY")
            return ObservedBody(real, result["captures"], current_key[0])

        runtime.pool.get = get

        def offer(role, event, phase):
            key = role + ":" + phase
            current_key[0] = key
            before = len(runtime.pool.release_history)
            entry = {
                "role": role, "phase": phase, "status": "INCOMPLETE",
                "event_id": event["event_id"],
                "source_ref": event["source_ref"],
            }
            result["offers"].append(entry)
            save(result)
            try:
                guarded = consumer.guarded_offer(
                    role, event, 0, time.monotonic() + 120,
                    operator_opt_in=True)
                entry["guarded_status"] = guarded.get("status")
                if guarded.get("status") != "SHADOW_LATEST_USER_OFFER_PRODUCED":
                    raise ValueError("RUN77_LATEST_USER_OFFER_RED")
                # The frozen Run55 persistence verifier expects the original
                # topic-consumer status; the packet IDs are unchanged.
                stored, query = persisted_offer(
                    runtime.store,
                    dict(guarded, status="SHADOW_OFFER_PRODUCED"),
                    role, event, runtime.models.revision(role))
                entry["offer"] = stored
                entry["query"] = query
                entry["status"] = "RECORDED"
            except Exception as exc:
                entry["error_type"] = type(exc).__name__
                entry["status"] = "STRUCTURAL_RED"
            finally:
                try:
                    runtime.pool.unload()
                except Exception as exc:
                    entry["release_error_type"] = type(exc).__name__
                    entry["status"] = "STRUCTURAL_RED"
                releases = runtime.pool.release_history[before:]
                entry["process_reaped"] = (
                    bool(releases)
                    and any(x.get("before") is not None for x in releases)
                    and all(x.get("process_reaped") is True for x in releases))
                if not entry["process_reaped"]:
                    entry["status"] = "STRUCTURAL_RED"
                save(result)
            if entry["status"] != "RECORDED":
                raise RuntimeError("RUN77_NATIVE_OFFER_RED")
            return entry

        prior_event = None
        if arm == "WITH_PRIOR":
            prior_event = runtime.store.event(
                runtime.session, fixture["prior"])
            result["prior_source_ref"] = prior_event["source_ref"]
            for role in f.ROLES:
                offer(role, prior_event, "prior")
        current_event = runtime.store.event(
            runtime.session, fixture["current"])
        result["current_source_ref"] = current_event["source_ref"]
        for role in f.ROLES:
            entry = offer(role, current_event, "current")
            stored, query = entry["offer"], entry["query"]
            metrics = stored.get("native_metrics") or {}
            if (metrics.get("status") != "FINAL"
                    or metrics.get("actual_model") != ROLE_MODELS[role]):
                raise RuntimeError("RUN77_NATIVE_MODEL_OR_FINAL_RED")
            context_refs = query.get("context_source_refs", [])
            if arm == "WITH_PRIOR":
                if (len(context_refs) != 1
                        or context_refs[0] != prior_event["source_ref"]):
                    raise RuntimeError("RUN77_PRIOR_SOURCE_TRANSPORT_RED")
            elif context_refs:
                raise RuntimeError("RUN77_ABLATION_PRIOR_LEAK_RED")
            entry["context_source_refs_verified"] = True
            entry["summary"] = stored["offer"]["summary"]
            entry["strict"] = f.strict_summary(
                entry["summary"], fixture["action"],
                fixture["remaining"])
            if role == "B2_GIST" and prior_event is not None:
                entry["prior_evidence_refs_verified"] = any(
                    ref.get("source_id")
                    == prior_event["source_ref"]["source_id"]
                    and runtime.store.read_source(ref)
                    in fixture["prior"]
                    for ref in stored.get("evidence_refs", []))
                result["b2_prior_evidence"] = (
                    entry["prior_evidence_refs_verified"])
            save(result)
        result["no_live_output"] = (
            runtime.store.one(
                "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0
            and runtime.store.one(
                "SELECT COUNT(*) AS n FROM actions")["n"] == 0)
        result["status"] = "RECORDED" if result["no_live_output"] else "STRUCTURAL_RED"
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["status"] = "STRUCTURAL_RED"
    finally:
        try:
            runtime.close()
        except Exception as exc:
            result["close_error_type"] = type(exc).__name__
            result["status"] = "STRUCTURAL_RED"
        try:
            result["closed_store_ok"] = bool(audit_closed(home)["ok"])
        except Exception:
            result["closed_store_ok"] = False
        result["native_call_count"] = len(result["offers"])
        result["processes_reaped"] = all(
            entry.get("process_reaped") is True
            for entry in result["offers"])
        if (not result["closed_store_ok"] or not result["processes_reaped"]
                or result["native_call_count"]
                != (4 if arm == "WITH_PRIOR" else 2)):
            result["status"] = "STRUCTURAL_RED"
        save(result)
    return result


def run(installed, out):
    installed, out = Path(installed), Path(out)
    if out.exists():
        raise FileExistsError("RUN77_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {
        "schema": SCHEMA, "seed": f.SEED,
        "table_sha256": f.TABLE_SHA256,
        "binding": binding,
        "status": "INCOMPLETE", "rows": [],
        "scores": {role: {arm: 0 for arm in f.ARMS} for role in f.ROLES},
        "b2_prior_evidence": 0, "native_call_count": 0,
        "independent_utility_proven": False,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "delivery_authority": 0, "learning_authority": 0,
        "output_committed": False, "tool_dispatches": 0,
    }
    path = out / "report.json"
    _save(path, report)
    try:
        if (binding["model_sha256"]["B1_DETAIL"] != f.B1_SHA256
                or binding["model_sha256"]["B2_GIST"] != f.B2_SHA256
                or binding["runner_sha256"] != f.RUNNER_SHA256):
            raise ValueError("RUN77_NATIVE_MODEL_PINS_RED")
        for fixture in f.fixtures():
            for arm in f.ARMS:
                folder = out / (fixture["project"] + "_" + arm)
                row = run_arm(folder, installed, fixture, arm,
                              lambda value, folder=folder: _save(
                                  folder / "raw_row.json", value))
                report["rows"].append(row)
                report["native_call_count"] += row["native_call_count"]
                for entry in row["offers"]:
                    if entry["phase"] == "current":
                        report["scores"][entry["role"]][arm] += entry.get(
                            "strict", 0)
                if arm == "WITH_PRIOR":
                    report["b2_prior_evidence"] += int(
                        row["b2_prior_evidence"])
                _save(path, report)
                if row["status"] != "RECORDED":
                    raise RuntimeError("RUN77_NATIVE_ARM_RED")
        if (report["native_call_count"] != 36
                or len(report["rows"]) != 12
                or installed_artifacts(installed) != binding):
            raise ValueError("RUN77_NATIVE_COUNTS_OR_PINS_RED")
        report["status"] = f.scientific_verdict(
            report["scores"], report["b2_prior_evidence"])
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["status"] = "STRUCTURAL_RED"
    _save(path, report)
    print(dumps({"status": report["status"],
                 "native_call_count": report["native_call_count"],
                 "scores": report["scores"],
                 "b2_prior_evidence": report["b2_prior_evidence"]}),
          flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = run(args.home, args.out)
    raise SystemExit(0 if report["status"] in (
        "B1B2_SMALL_CONTEXT_UTILITY_SIGNAL_SHADOW",
        "B1B2_CONTEXT_UTILITY_SCIENTIFIC_RED") else 1)


if __name__ == "__main__":
    main()
