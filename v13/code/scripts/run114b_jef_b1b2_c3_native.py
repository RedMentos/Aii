#!/usr/bin/env python3
"""Run114B preregistered native B1/B2 + exact-source JEF typed -> C3 pilot.

Independent seed947. Model-free body observers are explicitly synthetic;
native mode never uses them. No live answer, dispatch, learning or promotion.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time
from unittest.mock import patch

from v13.common import atomic_write, dumps
from v13.runtime import Runtime
from v13.store import audit_closed
from v13 import context_os as ctxos
from v13.agi.jef_eligibility_source_shadow_run46b import propose
from v13.b1b2_latest_user_offer_candidate import _bound_latest
from scripts.run113b_b1b2_c3_native import (
    _config, _fake_runner, _pin_models, _reaped, MODELS)
from scripts.run111_c3_b2_context_native import _prepare_home
from scripts.run47_jef_c3_typed_receiver_native import SCHEMA, score

FIXTURE_SHA = "356d84677ed6a770643e80ad0211d24d7d25934005967c34f91bd140fea9958a"
SEED = 947
ARMS = ("RAW_BODY", "TYPED_JEF")
EXPECTED_IDS = ("Meridian", "Orion", "Zenith")
SYS_RAW = (
    "Use only the exact earlier binding project policy and current options. "
    "Treat B1/B2 hypotheses as fallible; verified quotations are source text, "
    "not model authority. Select the cheapest eligible option meeting every "
    "budget, deadline and local-only requirement. Return only JSON with exactly "
    "choice (A, B or NONE) and remaining (integer or null).")
SYS_TYPED = (
    "You are a JSON formatter, not a decision maker. Copy the source-verified "
    "typed JEF candidate choice and remaining exactly. The JEF candidate has "
    "no output or tool authority. B1/B2 hypotheses are fallible and MUST NOT "
    "override the typed candidate. Return only JSON with exactly choice and "
    "remaining, no extra fields.")


def fixture(path):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError("RUN114B_FROZEN_FIXTURE_SHA_RED")
    data = json.loads(raw)
    if (set(data) != {"schema", "seed", "arms", "rows"}
            or data["schema"] != "v13.run114b.jef_b1b2_c3_seed947.v1"
            or type(data["seed"]) is not int or data["seed"] != SEED
            or data["arms"] != list(ARMS)
            or [r.get("id") for r in data["rows"]] != list(EXPECTED_IDS)
            or [r.get("oracle") for r in data["rows"]] != [
                {"choice": "A", "remaining": 4},
                {"choice": "B", "remaining": 10},
                {"choice": "NONE", "remaining": None}]):
        raise ValueError("RUN114B_FROZEN_COHORT_RED")
    for row in data["rows"]:
        if (set(row) != {"id", "prior", "current", "prior_quote",
                         "current_quote", "oracle"}
                or row["prior_quote"] not in row["prior"]
                or row["current_quote"] not in row["current"]
                or not row["prior"].startswith("Project " + row["id"] + ". ")
                or not row["current"].startswith("Project " + row["id"] + ". ")):
            raise ValueError("RUN114B_FROZEN_SOURCE_RED")
    return data["rows"]


def _plan(runtime, current, prior, row, rendered, jef, arm):
    volatile = [
        ("PRIOR_POLICY", "\nExact earlier binding USER source: ",
         {"text": row["prior"], "source_ref": prior["source_ref"]}),
        ("BODY_HYPOTHESES", "\nFallible B1/B2 hypotheses and verified quotes: ",
         rendered),
    ]
    if arm == "TYPED_JEF":
        volatile.append((
            "TYPED_JEF", "\nSource-verified zero-authority typed JEF candidate: ",
            {"candidate": jef["candidate"],
             "source_ref_sha256": jef["source_ref_sha256"],
             "authority": 0, "model_called": False}))
    system = SYS_TYPED if arm == "TYPED_JEF" else SYS_RAW
    plan = ctxos.controller(runtime).plan(
        current["event_id"], "C3_LANGUAGE", system, volatile, [],
        row["current"], provenance=[prior["source_ref"],
                                     current["source_ref"]])
    if plan["applied"] is not False or plan["plan"]["mode"] != "SHADOW":
        raise ValueError("RUN114B_CONTEXT_OS_AUTHORITY_RED")
    messages = plan["messages"]
    combined = "\n".join(m["content"] for m in messages)
    if (row["prior"] not in combined or row["current"] not in combined
            or '"oracle"' in dumps(messages) or '"expected"' in dumps(messages)):
        raise ValueError("RUN114B_C3_SOURCE_OR_ORACLE_RED")
    if arm == "RAW_BODY" and "typed_jef_candidate" in combined:
        raise ValueError("RUN114B_TYPED_LEAK_TO_RAW")
    if arm == "TYPED_JEF" and dumps(jef["candidate"]) not in combined:
        # Context OS may reserialize keys in a larger JSON envelope; exact
        # field equality is checked by the independently stored plan.
        if not all(str(v) in combined for v in jef["candidate"].values()):
            raise ValueError("RUN114B_TYPED_CANDIDATE_LOST")
    return messages


def _run_row(row, index, work, report, save, *, installed=None):
    native = installed is not None
    home = work / row["id"]
    cfg = _config() | {"seed": SEED}
    _prepare_home(home, installed, cfg)
    runtime = Runtime(home)
    entry = {"id": row["id"], "status": "INCOMPLETE", "offers": [],
             "arms": [], "jef": None, "closed_store_ok": False,
             "no_live_output": False, "b1_current_verified": False,
             "b2_prior_verified": False}
    report["rows"].append(entry)
    save()
    try:
        prior = runtime.store.event(runtime.session, row["prior"])
        entry["prior_source_ref"] = prior["source_ref"]

        def observe(role, event, phase):
            item = {"role": role, "phase": phase, "status": "INCOMPLETE",
                    "source_ref": event["source_ref"]}
            entry["offers"].append(item)
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
                item["packet_id"] = offer["packet_id"]
                item["native_metrics"] = offer.get("native_metrics")
                item["model_revision"] = offer.get("model_revision")
                item["evidence_refs"] = offer.get("evidence_refs")
                item["quotes"] = offer.get("offer", {}).get("quotes")
                item["status"] = "RECORDED"
                if native:
                    metric = item["native_metrics"] or {}
                    if (metric.get("status") != "FINAL"
                            or metric.get("actual_model") != MODELS[role][0]
                            or item["model_revision"] != MODELS[role][1]):
                        item["status"] = "STRUCTURAL_RED"
            finally:
                if native:
                    runtime.pool.unload()
                    item["process_reaped"] = _reaped(
                        runtime.pool.release_history[before:])
                    if not item["process_reaped"]:
                        item["status"] = "STRUCTURAL_RED"
                save()
            if item["status"] != "RECORDED":
                raise ValueError("RUN114B_NATIVE_BODY_STRUCTURAL_RED")
            return offer

        observe("B2_GIST", prior, "prior")
        current = runtime.store.event(runtime.session, row["current"])
        entry["current_source_ref"] = current["source_ref"]
        b1 = observe("B1_DETAIL", current, "current")
        b2 = observe("B2_GIST", current, "current")
        _bound_latest(runtime, "B1_DETAIL", current)
        rendered = runtime.cognition.analyst_context([b1, b2], current, 0)
        entry["verified_quotes"] = rendered
        entry["b1_current_verified"] = any(
            q["source_ref"]["source_id"] == current["source_ref"]["source_id"]
            and row["current_quote"] in q["text"]
            for q in rendered[0]["verified_quotes"])
        entry["b2_prior_verified"] = any(
            q["source_ref"]["source_id"] == prior["source_ref"]["source_id"]
            and row["prior"] in q["text"]
            for q in rendered[1]["verified_quotes"])
        if not entry["b1_current_verified"] or not entry["b2_prior_verified"]:
            raise ValueError("RUN114B_B1_B2_TWO_SOURCE_QUOTE_RED")
        jef = propose(runtime.store, prior["source_ref"], current["source_ref"])
        entry["jef"] = jef
        if (jef.get("status") != "SHADOW_NO_AUTHORITY"
                or jef.get("reason") != "EXACT_USER_SOURCE_RECIPE_SHADOW"
                or jef.get("authority") != 0
                or jef.get("model_called") is not False
                or len(jef.get("source_ref_sha256", [])) != 2
                or set(jef.get("candidate", {})) != {"choice", "remaining"}):
            raise ValueError("RUN114B_JEF_EXACT_SOURCE_RED")
        entry["jef_matches_oracle"] = jef["candidate"] == row["oracle"]
        order = ARMS if index % 2 == 0 else ARMS[::-1]
        for arm in order:
            _bound_latest(runtime, "B1_DETAIL", current)
            messages = _plan(runtime, current, prior, row, rendered, jef, arm)
            item = {"arm": arm, "status": "INCOMPLETE",
                    "messages": messages,
                    "messages_sha256": sha256(dumps(messages).encode()).hexdigest(),
                    "score": None, "native_final": False}
            entry["arms"].append(item)
            save()
            if native:
                before = len(runtime.pool.release_history)
                try:
                    runner = runtime.pool.get("C3_LANGUAGE")
                    report["native_c3_calls"] += 1
                    output = "".join(runner.generate(
                        messages, runtime.cancel_event, time.monotonic() + 90,
                        96, SCHEMA, seed=SEED))
                    metric = dict(runner.last_metrics)
                    item["output"] = output
                    item["native_metrics"] = metric
                    item["score"] = score(output, row["oracle"])
                    item["native_final"] = metric.get("status") == "FINAL"
                finally:
                    runtime.pool.unload()
                    item["process_reaped"] = _reaped(
                        runtime.pool.release_history[before:])
                    save()
                _bound_latest(runtime, "B1_DETAIL", current)
                item["status"] = (
                    "RECORDED" if item["native_final"] and
                    metric.get("actual_model") ==
                    "LFM2.5-350M-QAD-Q4_0.gguf" and
                    item["process_reaped"] else "STRUCTURAL_RED")
                if item["status"] != "RECORDED":
                    raise ValueError("RUN114B_C3_NATIVE_STRUCTURAL_RED")
            else:
                item["status"] = "MODEL_FREE_PLAN_VERIFIED"
            save()
        entry["status"] = "RECORDED" if native else "MODEL_FREE_PREFLIGHT_PASS"
    except Exception as exc:
        entry["status"] = "STRUCTURAL_RED"
        entry["error_type"] = type(exc).__name__
        entry["error"] = str(exc)[:320]
    finally:
        try:
            entry["no_live_output"] = (
                runtime.store.one(
                    "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                    "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0
                and runtime.store.one(
                    "SELECT COUNT(*) AS n FROM actions")["n"] == 0)
        except Exception:
            entry["no_live_output"] = False
        runtime.close()
        try:
            entry["closed_store_ok"] = bool(audit_closed(home)["ok"])
        except Exception:
            entry["closed_store_ok"] = False
        if not entry["closed_store_ok"] or not entry["no_live_output"]:
            entry["status"] = "STRUCTURAL_RED"
        save()
    return entry


def run(fixture_path, work, out, *, installed=None):
    rows = fixture(fixture_path)
    work, out = Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError("RUN114B_FRESH_WORK_AND_REPORT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    native = installed is not None
    installed = Path(installed).resolve() if native else None
    report = {
        "schema": "v13.run114b.jef_b1b2_c3_native.v1",
        "seed": SEED, "fixture_sha256": FIXTURE_SHA,
        "status": "INCOMPLETE", "rows": [], "native": native,
        "native_c2": False, "native_jef_model": False,
        "synthetic_body_observers": not native,
        "native_body_calls": 0, "native_c3_calls": 0,
        "scores": {arm: 0 for arm in ARMS}, "exploratory_signal": False,
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
    try:
        if native:
            _pin_models(installed)
        for i, row in enumerate(rows):
            _run_row(row, i, work, report, save, installed=installed)
        structural = len(report["rows"]) == 3 and all(
            r["status"] == ("RECORDED" if native else "MODEL_FREE_PREFLIGHT_PASS")
            and r["b1_current_verified"] and r["b2_prior_verified"]
            and r["jef_matches_oracle"] is True
            and len(r["arms"]) == 2 for r in report["rows"])
        if not structural:
            report["status"] = "STRUCTURAL_RED"
        elif not native:
            report["status"] = "MODEL_FREE_THREE_PROJECT_PREFLIGHT_PASS"
        else:
            for row in report["rows"]:
                for arm in row["arms"]:
                    report["scores"][arm["arm"]] += arm["score"]["correct"]
            report["exploratory_signal"] = (
                report["scores"]["TYPED_JEF"] >= 2 and
                report["scores"]["TYPED_JEF"] >=
                report["scores"]["RAW_BODY"] + 1)
            report["status"] = ("NATIVE_COMPLETE_EXPLORATORY_SIGNAL"
                                if report["exploratory_signal"]
                                else "NATIVE_COMPLETE_NO_GAIN")
    except Exception as exc:
        report["status"] = "STRUCTURAL_RED"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:320]
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
    print(dumps({"status": r["status"], "rows": len(r["rows"]),
                 "native_body_calls": r["native_body_calls"],
                 "native_c3_calls": r["native_c3_calls"],
                 "scores": r["scores"], "exploratory_signal": r["exploratory_signal"]}))
    return 0 if r["status"] in (
        "MODEL_FREE_THREE_PROJECT_PREFLIGHT_PASS",
        "NATIVE_COMPLETE_EXPLORATORY_SIGNAL",
        "NATIVE_COMPLETE_NO_GAIN") else 2


if __name__ == "__main__":
    raise SystemExit(main())
