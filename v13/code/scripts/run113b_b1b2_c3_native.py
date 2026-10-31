#!/usr/bin/env python3
"""Run113B: disjoint one-case B1/B2 native source-bound C3 SHADOW pilot.

No production Runtime integration, no native C2/JEF proof, no learning,
no output or tool authority, and no STEP2 promotion.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import time
from unittest.mock import patch

from v13.common import atomic_write, dumps, file_hash
from v13.config import DEFAULTS
from v13.cognition import scaffold_route
from v13.b1b2_latest_user_offer_candidate import _bound_latest
from v13.models import ModelManager
from v13.runtime import Runtime
from v13.store import audit_closed
from v13 import context_os as ctxos
from scripts.run111_c3_b2_context_native import _prepare_home, score, SCHEMA, SYSTEM

FIXTURE_SHA = "ff1720b73cdfa1cb2bdc91de165c0f85299c71dd02456728de6ea73e782e32ca"
B1_SHA = "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1"
B1_REV = "6767265158422fb8a19c62ceb45f16f05363615b"
B2_SHA = "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"
B2_REV = "8fea620810c4afa23dd6443f999a48574c1611a3"
C3_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
C3_REV = "657e078c94084481950a2d555a941481f715536b"
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
MODELS = {"B1_DETAIL": ("LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf", B1_REV),
          "B2_GIST": ("Qwen3.5-0.8B-Q4_0.gguf", B2_REV)}
SEED = 919


def fixture(path):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError("RUN113B_FROZEN_FIXTURE_SHA_RED")
    row = json.loads(raw)
    if (set(row) != {"schema", "seed", "project", "prior", "current",
                     "prior_quote", "current_quote", "expected"}
            or row["schema"] != "v13.run113b.native_b1b2_c3_seed919.v1"
            or type(row["seed"]) is not int or row["seed"] != SEED
            or row["project"] != "Aster" or row["expected"] != "A"
            or row["prior_quote"] not in row["prior"]
            or row["current_quote"] not in row["current"]
            or not row["prior"].startswith("Project Aster archived ")
            or not row["current"].startswith("Project Aster latest ")):
        raise ValueError("RUN113B_FROZEN_FIXTURE_FIELDS_RED")
    return row


def _config():
    return DEFAULTS | {
        "seed": SEED, "temperature": 0.0, "learning_mode": "RECORD_ONLY",
        "observer_tokens": 256, "observer_seconds": 120,
        "answer_tokens": 32, "deadline_seconds": 180,
        "history_turns": 0, "memory_top_k": 0,
        "b2_control": "two_body", "b2_quote_select": "pointer",
        "offer_quote_context_chars": 400, "b2_offer_body_state": False,
        "b2_state_slots": 2, "b2_context_chars": 1500,
        "memory_threshold": 0.0,
    }


def _fake_runner(row, role, phase):
    """Explicitly synthetic observer, used ONLY in model-free preflight."""
    def generate(messages, *args, **kwargs):
        if role == "B1_DETAIL":
            quotes = [row["current_quote"]]
        else:
            payload = json.loads(messages[-1]["content"])
            matches = [x["id"] for x in payload.get("quote_choices", [])
                       if x.get("text") == row["prior_quote"]]
            if len(matches) != 1:
                raise ValueError("RUN113B_SYNTHETIC_B2_PRIOR_POINTER_MISSING")
            quotes = matches
        return iter([dumps({"summary": "Source-bound observer hypothesis.",
                            "quotes": quotes, "uncertainty": "",
                            "needs_reentry": False})])
    return SimpleNamespace(generate=generate,
                           last_metrics={"status": "FINAL", "synthetic": True})


def _reaped(history):
    return (bool(history)
            and any(x.get("before") is not None for x in history)
            and all(x.get("process_reaped") is True for x in history))


def _pin_models(installed):
    models = ModelManager(installed)
    for role, digest, revision in (
            ("B1_DETAIL", B1_SHA, B1_REV),
            ("B2_GIST", B2_SHA, B2_REV),
            ("C3_LANGUAGE", C3_SHA, C3_REV)):
        if (file_hash(models.path_for(role)) != digest
                or models.revision(role) != revision):
            raise ValueError("RUN113B_PINNED_MODEL_RED_" + role)
    if file_hash(installed / "bin/llama-server") != RUNNER_SHA:
        raise ValueError("RUN113B_PINNED_RUNNER_RED")


def run(fixture_path, work, out, *, installed=None):
    row = fixture(fixture_path)
    work, out = Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError("RUN113B_FRESH_WORK_AND_REPORT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    native = installed is not None
    installed = Path(installed).resolve() if native else None
    report = {
        "schema": "v13.run113b.b1b2_c3_source_native.v1",
        "fixture_sha256": FIXTURE_SHA, "seed": SEED,
        "status": "INCOMPLETE", "native_b1": native, "native_b2": native,
        "native_c3": native, "native_c2": False, "native_jef": False,
        "synthetic_observers": not native, "offers": [],
        "native_body_calls": 0, "native_c3_calls": 0,
        "b1_current_verified": False, "b2_prior_verified": False,
        "source_decision_correct": None,
        "age0": "RECORD_ONLY", "step2_exit": "EVIDENCE_NOT_PASSING",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "output_committed": False, "tool_dispatches": 0,
        "learning_authority": 0, "delivery_authority": 0,
    }
    path = out / "report.json"
    def save():
        atomic_write(path, dumps(report))
    save()
    home = work / "home"
    runtime = None
    try:
        if native:
            _pin_models(installed)
        _prepare_home(home, installed, _config())
        runtime = Runtime(home)
        route_prompt = "Compare the current options under the earlier policy: " + row["current"]
        report["route_source"] = "DETERMINISTIC_SCAFFOLD_EXPLICIT_COMPARISON"
        report["scaffold_route"] = scaffold_route(route_prompt)
        if report["scaffold_route"] != "both":
            raise ValueError("RUN113B_SCAFFOLD_ROUTE_RED")
        prior = runtime.store.event(runtime.session, row["prior"])
        report["prior_source_ref"] = prior["source_ref"]

        def observe(role, event, phase):
            entry = {"role": role, "phase": phase, "status": "INCOMPLETE",
                     "source_ref": event["source_ref"]}
            report["offers"].append(entry)
            save()
            before = len(runtime.pool.release_history)
            try:
                if native:
                    offer = runtime.cognition.offer(
                        role, event, 0, time.monotonic() + 120)
                    report["native_body_calls"] += 1
                else:
                    with patch.object(runtime.pool, "get",
                                      return_value=_fake_runner(row, role, phase)):
                        offer = runtime.cognition.offer(
                            role, event, 0, time.monotonic() + 30)
                entry["packet_id"] = offer["packet_id"]
                entry["model_revision"] = offer.get("model_revision")
                entry["native_metrics"] = offer.get("native_metrics")
                entry["evidence_refs"] = offer.get("evidence_refs")
                entry["quotes"] = offer.get("offer", {}).get("quotes")
                entry["status"] = "RECORDED"
                if native:
                    metric = entry["native_metrics"] or {}
                    if (metric.get("status") != "FINAL"
                            or metric.get("actual_model") != MODELS[role][0]
                            or entry["model_revision"] != MODELS[role][1]):
                        entry["status"] = "STRUCTURAL_RED"
            finally:
                if native:
                    runtime.pool.unload()
                    entry["process_reaped"] = _reaped(
                        runtime.pool.release_history[before:])
                    if not entry["process_reaped"]:
                        entry["status"] = "STRUCTURAL_RED"
                save()
            if entry["status"] != "RECORDED":
                raise ValueError("RUN113B_BODY_NATIVE_STRUCTURAL_RED")
            return offer

        observe("B2_GIST", prior, "prior")
        current = runtime.store.event(runtime.session, row["current"])
        report["current_source_ref"] = current["source_ref"]
        b1 = observe("B1_DETAIL", current, "current")
        b2 = observe("B2_GIST", current, "current")
        _bound_latest(runtime, "B1_DETAIL", current)
        rendered = runtime.cognition.analyst_context([b1, b2], current, 0)
        if [x["role"] for x in rendered] != ["B1_DETAIL", "B2_GIST"]:
            raise ValueError("RUN113B_BODY_ORDER_RED")
        report["verified_quotes"] = rendered
        b1_quotes = rendered[0]["verified_quotes"]
        b2_quotes = rendered[1]["verified_quotes"]
        report["b1_current_verified"] = any(
            q["source_ref"]["source_id"] == current["source_ref"]["source_id"]
            and row["current_quote"] in q["text"] for q in b1_quotes)
        report["b2_prior_verified"] = any(
            q["source_ref"]["source_id"] == prior["source_ref"]["source_id"]
            and row["prior"] in q["text"] for q in b2_quotes)
        if not report["b1_current_verified"] or not report["b2_prior_verified"]:
            raise ValueError("RUN113B_NATIVE_TWO_SOURCE_QUOTE_RED")
        volatile = [("HYPOTHESES",
                     "\nSource-bound hypotheses, not facts: ", rendered)]
        plan = ctxos.controller(runtime).plan(
            current["event_id"], "C3_LANGUAGE", SYSTEM, volatile, [],
            row["current"], provenance=[current["source_ref"],
                                         prior["source_ref"]])
        if plan["applied"] is not False or plan["plan"]["mode"] != "SHADOW":
            raise ValueError("RUN113B_CONTEXT_AUTHORITY_RED")
        messages = plan["messages"]
        text = "\n".join(m["content"] for m in messages)
        if (row["prior"] not in text or row["current_quote"] not in text
                or '"expected"' in dumps(messages)):
            raise ValueError("RUN113B_C3_SOURCE_PLAN_RED")
        report["c3_input_sha256"] = sha256(dumps(messages).encode()).hexdigest()
        report["c3_messages"] = messages
        save()
        _bound_latest(runtime, "B1_DETAIL", current)
        if native:
            before = len(runtime.pool.release_history)
            try:
                runner = runtime.pool.get("C3_LANGUAGE")
                report["native_c3_calls"] = 1
                output = "".join(runner.generate(
                    messages, runtime.cancel_event, time.monotonic() + 90,
                    32, SCHEMA, seed=SEED))
                metric = dict(runner.last_metrics)
                report["c3_output"] = output
                report["c3_native_metrics"] = metric
                report["c3_score"] = score(output, row["expected"])
                report["source_decision_correct"] = bool(
                    report["c3_score"]["correct"])
            finally:
                runtime.pool.unload()
                report["c3_process_reaped"] = _reaped(
                    runtime.pool.release_history[before:])
                save()
            _bound_latest(runtime, "B1_DETAIL", current)
            if (metric.get("status") != "FINAL"
                    or metric.get("actual_model") !=
                    "LFM2.5-350M-QAD-Q4_0.gguf"
                    or not report["c3_process_reaped"]):
                raise ValueError("RUN113B_C3_NATIVE_STRUCTURAL_RED")
            report["status"] = "NATIVE_B1_B2_C3_STRUCTURAL_PASS"
        else:
            report["status"] = "MODEL_FREE_TWO_SOURCE_PREFLIGHT_PASS"
    except Exception as exc:
        report["status"] = "STRUCTURAL_RED"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:320]
    finally:
        if runtime is not None:
            try:
                report["no_live_output"] = (
                    runtime.store.one(
                        "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                        "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0
                    and runtime.store.one(
                        "SELECT COUNT(*) AS n FROM actions")["n"] == 0)
                if not report["no_live_output"]:
                    report["status"] = "STRUCTURAL_RED"
            except Exception:
                report["status"] = "STRUCTURAL_RED"
            runtime.close()
            try:
                report["closed_store_ok"] = bool(audit_closed(home)["ok"])
            except Exception:
                report["closed_store_ok"] = False
            if not report["closed_store_ok"]:
                report["status"] = "STRUCTURAL_RED"
        save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--installed", type=Path)
    a = p.parse_args()
    r = run(a.fixture, a.work, a.out, installed=a.installed)
    print(dumps({"status": r["status"], "native_body_calls": r["native_body_calls"],
                 "native_c3_calls": r["native_c3_calls"],
                 "b1_current_verified": r["b1_current_verified"],
                 "b2_prior_verified": r["b2_prior_verified"],
                 "source_decision_correct": r["source_decision_correct"]}))
    return 0 if r["status"] in (
        "MODEL_FREE_TWO_SOURCE_PREFLIGHT_PASS",
        "NATIVE_B1_B2_C3_STRUCTURAL_PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
