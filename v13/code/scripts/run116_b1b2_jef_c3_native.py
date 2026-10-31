#!/usr/bin/env python3
"""Run116 seed1019: pinned native B1/B2 -> exact USER/JEF -> native C3.

Three registered source-role arms; model-free body stubs are synthetic.
No live output, tools, learning, age promotion, or native JEF/C2.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time
from types import SimpleNamespace
from unittest.mock import patch

from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_jef_c3_source_role_bridge_candidate import (
    build_b1b2_jef_c3_source_role_bridge,
)
from v13.common import atomic_write, dumps
from v13.runtime import Runtime
from v13.store import audit_closed
from v13.two_source_c3_role_boundary_candidate import (
    SYSTEM, build_role_separated_c3_shadow,
)
from v13.jef_two_source_role_formatter_candidate import (
    build_typed_jef_role_formatter,
)
from scripts.run111_c3_b2_context_native import _prepare_home
from scripts.run113b_b1b2_c3_native import (
    _config, _pin_models, _reaped, MODELS,
)
from scripts.run115j_typed_jef_role_native import (
    C3_FILE, SCHEMA, TASK,
)
from scripts.run47_jef_c3_typed_receiver_native import score

SEED = 1019
FIXTURE_SHA = "e31e2d68331cc4280e161b2dbdbd022f493325ca234f050cda06065fa6775a69"
IDS = ("Ardent", "Birch", "Cetus", "Dawn", "Eider", "Fjord")
EXPECTED = (("A", 20), ("B", 60), ("NONE", None),
            ("A", 40), ("B", 60), ("NONE", None))
ARMS = ("RAW_TWO_SOURCE_ROLE", "TYPED_JEF_ROLE",
        "TYPED_JEF_WITH_BODY_ROLE")
CONFIG = _config() | {
    "seed": SEED, "temperature": 0.0, "threads": 2,
    "learning_mode": "RECORD_ONLY", "observer_mode": "off",
    "answer_tokens": 96, "deadline_seconds": 180,
    "history_turns": 0, "memory_top_k": 0,
    "body_residency_mb": 0, "teacher_enabled": False,
    "offer_quote_context_chars": 200, "b2_quote_select": "pointer",
}


def fixture(path):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError("RUN116_FROZEN_FIXTURE_SHA_RED")
    data = json.loads(raw)
    if (set(data) != {"schema", "seed", "arms", "rows"}
            or data["schema"] != "v13.run116.b1b2_jef_c3_seed1019.v1"
            or type(data["seed"]) is not int or data["seed"] != SEED
            or data["arms"] != list(ARMS)
            or type(data["rows"]) is not list or len(data["rows"]) != 6
            or [r.get("id") for r in data["rows"]] != list(IDS)
            or [(r.get("oracle", {}).get("choice"),
                 r.get("oracle", {}).get("remaining"))
                for r in data["rows"]] != list(EXPECTED)):
        raise ValueError("RUN116_FROZEN_COHORT_RED")
    for row in data["rows"]:
        if (set(row) != {"id", "prior", "current", "oracle"}
                or not row["prior"].startswith("Project " + row["id"] + ". ")
                or not row["current"].startswith("Project " + row["id"] + ". ")
                or '"oracle"' in dumps(row["prior"]) + dumps(row["current"])):
            raise ValueError("RUN116_SOURCE_SHAPE_RED")
    return data["rows"]


def _fake_body(role):
    """Explicit synthetic wrong summary and nonexistent quote, preflight only."""
    def generate(messages, *args, **kwargs):
        return iter([dumps({
            "summary": "Option B definitely wins (SYNTHETIC WRONG HYPOTHESIS)",
            "quotes": ["THIS_QUOTE_IS_NOT_IN_THE_SOURCE"],
            "uncertainty": "high", "needs_reentry": True,
        })])
    return SimpleNamespace(generate=generate,
                           last_metrics={"status": "FINAL", "synthetic": True})


def _build_prompts(runtime, prior, current, ids, row):
    refs = [prior["source_ref"], current["source_ref"]]
    raw = build_role_separated_c3_shadow(
        runtime, prior, current, operator_opt_in=True)
    typed = build_typed_jef_role_formatter(
        runtime, prior, current, operator_opt_in=True)
    body = build_b1b2_jef_c3_source_role_bridge(
        runtime, prior, current, ids, operator_opt_in=True)
    if (raw.get("status") != "SHADOW_C3_DATA_ROLE_BOUNDARY_VERIFIED"
            or typed.get("status") != "SHADOW_TYPED_JEF_ROLE_FORMATTER_VERIFIED"
            or body.get("status") != "SHADOW_B1B2_JEF_C3_ROLE_BRIDGE_VERIFIED"
            or any(x.get("source_refs") != refs for x in (raw, typed, body))
            or typed.get("typed_jef_candidate") != row["oracle"]
            or body.get("typed_jef_candidate") != row["oracle"]
            or any(x.get("delivery_authority") != 0
                   or x.get("learning_authority") != 0
                   or x.get("output_committed") is not False
                   for x in (raw, typed, body))
            or body.get("body_model_quote_verified") is not False
            or body.get("native_c3_calls") != 0
            or body.get("native_jef_calls") != 0):
        raise ValueError("RUN116_CROSSORGAN_BOUNDARY_RED")
    prompts = {
        ARMS[0]: [
            {"role": "system", "content": SYSTEM + "\n" + TASK},
            {"role": "user", "content": raw["messages"][1]["content"]},
        ],
        ARMS[1]: typed["messages"],
        ARMS[2]: body["messages"],
    }
    for arm, messages in prompts.items():
        if ([m["role"] for m in messages] != ["system", "user"]
                or row["prior"] in messages[0]["content"]
                or row["current"] in messages[0]["content"]
                or '"oracle"' in dumps(messages).lower()):
            raise ValueError("RUN116_SYSTEM_ROLE_OR_ORACLE_LEAK_RED")
        payload = json.loads(messages[1]["content"])
        if ([s["text"] for s in payload["sources"]] !=
                [row["prior"], row["current"]]
                or [s["source_ref"] for s in payload["sources"]] != refs
                or payload.get("body_model_quote_verified") is not False):
            raise ValueError("RUN116_EXACT_USER_SOURCES_RED")
        if arm == ARMS[0]:
            if "typed_jef_candidate" in payload or "body_observations" in payload:
                raise ValueError("RUN116_RAW_CONTROL_CONTAMINATION_RED")
        else:
            if (payload.get("typed_jef_candidate") != row["oracle"]
                    or payload.get("typed_candidate_authority") != 0):
                raise ValueError("RUN116_TYPED_JEF_PAYLOAD_RED")
            if arm == ARMS[1] and "body_observations" in payload:
                raise ValueError("RUN116_TYPED_ONLY_CONTAMINATION_RED")
            if arm == ARMS[2]:
                obs = payload.get("body_observations")
                if (type(obs) is not list or len(obs) != 2
                        or [x["role"] for x in obs] !=
                        ["B1_DETAIL", "B2_GIST"]
                        or any(x["hypothesis_authority"] !=
                               "MODEL_HYPOTHESIS_NOT_FACT"
                               or any(q["semantic_truth_authority"] is not False
                                      for q in x["verified_quotes"])
                               for x in obs)):
                    raise ValueError("RUN116_BODY_HYPOTHESIS_AUTHORITY_RED")
    return prompts, {
        "raw": raw["context_plan_packet_id"],
        "typed": typed["context_plan_packet_id"],
        "body": body["context_plan_packet_id"],
    }, body["verified_quote_count"]


def _run_row(row, index, work, report, save, installed):
    native = installed is not None
    home = work / row["id"]
    _prepare_home(home, installed, CONFIG)
    runtime = Runtime(home)
    entry = {"id": row["id"], "status": "INCOMPLETE",
             "offers": [], "arms": [], "closed_store_ok": False,
             "no_live_output": False, "verified_quote_count": None}
    report["rows"].append(entry)
    save()
    try:
        consumer = TopicPartitionOfferConsumer(runtime)
        prior = runtime.store.event(runtime.session, row["prior"])
        entry["prior_source_ref"] = prior["source_ref"]

        def observe(role, event, phase):
            item = {"role": role, "phase": phase, "status": "INCOMPLETE",
                    "source_ref": event["source_ref"],
                    "process_reaped": False}
            entry["offers"].append(item)
            save()
            before = len(runtime.pool.release_history)
            try:
                if native:
                    result = consumer.guarded_offer(
                        role, event, 0, time.monotonic() + 180,
                        operator_opt_in=True)
                    report["native_body_calls"] += 1
                else:
                    with patch.object(runtime.pool, "get",
                                      return_value=_fake_body(role)):
                        result = consumer.guarded_offer(
                            role, event, 0, time.monotonic() + 30,
                            operator_opt_in=True)
                if result.get("status") != "SHADOW_OFFER_PRODUCED":
                    raise ValueError("RUN116_OFFER_REFUSED_" + str(result.get("status")))
                item["packet_id"] = result["offer_packet_id"]
                item["query_packet_id"] = result["query_packet_id"]
                stored = runtime.store.one(
                    "SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",
                    (item["packet_id"],))
                if stored is None:
                    raise ValueError("RUN116_STORED_OFFER_MISSING")
                offer = json.loads(stored["payload"])
                item["native_metrics"] = offer.get("native_metrics")
                item["model_revision"] = offer.get("model_revision")
                item["source_quote_count"] = len(offer.get("offer", {}).get("quotes", []))
                item["status"] = "RECORDED"
                if native:
                    metrics = item["native_metrics"] or {}
                    if (metrics.get("status") != "FINAL"
                            or metrics.get("actual_model") != MODELS[role][0]
                            or item["model_revision"] != MODELS[role][1]):
                        raise ValueError("RUN116_NATIVE_BODY_FINAL_OR_MODEL_RED")
            finally:
                if native:
                    runtime.pool.unload()
                    item["process_reaped"] = _reaped(
                        runtime.pool.release_history[before:])
                    if not item["process_reaped"]:
                        item["status"] = "STRUCTURAL_RED"
                else:
                    item["process_reaped"] = True  # synthetic; not native proof
                save()
            if item["status"] != "RECORDED":
                raise ValueError("RUN116_BODY_REAP_RED")
            return item

        observe("B2_GIST", prior, "prior")
        current = runtime.store.event(runtime.session, row["current"])
        entry["current_source_ref"] = current["source_ref"]
        observe("B1_DETAIL", current, "current")
        observe("B2_GIST", current, "current")
        ids = {x["role"]: x["packet_id"] for x in entry["offers"]
               if x["phase"] == "current"}
        prompts, entry["context_plan_packet_ids"], entry["verified_quote_count"] = (
            _build_prompts(runtime, prior, current, ids, row))
        order = ARMS[index % 3:] + ARMS[:index % 3]
        for arm in order:
            messages = prompts[arm]
            item = {"arm": arm, "status": "INCOMPLETE",
                    "messages": messages,
                    "messages_sha256": sha256(dumps(messages).encode()).hexdigest(),
                    "native_final": False, "process_reaped": False,
                    "score": None}
            entry["arms"].append(item)
            save()
            if native:
                before = len(runtime.pool.release_history)
                try:
                    runner = runtime.pool.get("C3_LANGUAGE")
                    report["native_c3_calls"] += 1
                    save()
                    output = "".join(runner.generate(
                        messages, runtime.cancel_event,
                        time.monotonic() + 120, 96, SCHEMA, seed=SEED))
                    item["output"] = output
                    item["native_metrics"] = dict(runner.last_metrics)
                    item["score"] = score(output, row["oracle"])
                    item["native_final"] = (
                        item["native_metrics"].get("status") == "FINAL")
                finally:
                    runtime.pool.unload()
                    item["process_reaped"] = _reaped(
                        runtime.pool.release_history[before:])
                    save()
                item["status"] = (
                    "RECORDED" if item["native_final"] and
                    item["process_reaped"] and
                    item["native_metrics"].get("actual_model") == C3_FILE
                    else "STRUCTURAL_RED")
                if item["status"] != "RECORDED":
                    raise ValueError("RUN116_NATIVE_C3_FINAL_OR_REAP_RED")
            else:
                item["status"] = "MODEL_FREE_PROMPT_VERIFIED"
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
                and runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0)
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


def run(fixture_path, work, out, *, installed=None):
    rows = fixture(fixture_path)
    work, out = Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError("RUN116_FRESH_WORK_AND_REPORT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    native = installed is not None
    installed = Path(installed).resolve() if native else None
    report = {
        "schema": "v13.run116.b1b2_jef_c3_native.v1",
        "seed": SEED, "fixture_sha256": FIXTURE_SHA,
        "status": "INCOMPLETE", "native": native,
        "native_body_calls": 0, "native_c3_calls": 0,
        "native_c2_calls": 0, "native_jef_calls": 0,
        "synthetic_body_observers": not native,
        "rows": [], "scores": {arm: 0 for arm in ARMS},
        "exploratory_noninterference_signal": False,
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
            _run_row(row, i, work, report, save, installed)
        structural = len(report["rows"]) == 6 and all(
            r["status"] == ("RECORDED" if native else "MODEL_FREE_PREFLIGHT_PASS")
            and r["closed_store_ok"] and r["no_live_output"]
            and len(r["offers"]) == 3 and len(r["arms"]) == 3
            and set(x["arm"] for x in r["arms"]) == set(ARMS)
            and all(x["status"] == "RECORDED" and x["process_reaped"]
                    for x in r["offers"])
            and all(x["status"] ==
                    ("RECORDED" if native else "MODEL_FREE_PROMPT_VERIFIED")
                    for x in r["arms"])
            for r in report["rows"])
        if not structural:
            report["status"] = "STRUCTURAL_RED"
        elif not native:
            report["status"] = "MODEL_FREE_SIX_CASE_PREFLIGHT_PASS"
        elif report["native_body_calls"] != 18 or report["native_c3_calls"] != 18:
            report["status"] = "STRUCTURAL_RED"
        else:
            for row in report["rows"]:
                for arm in row["arms"]:
                    report["scores"][arm["arm"]] += arm["score"]["correct"]
            full = report["scores"][ARMS[2]]
            typed = report["scores"][ARMS[1]]
            none_rows = [r for r in report["rows"] if r["id"] in ("Cetus", "Fjord")]
            no_false_none = all(
                next(a for a in r["arms"] if a["arm"] == ARMS[2])
                ["score"]["parsed"] == {"choice": "NONE", "remaining": None}
                for r in none_rows)
            report["exploratory_noninterference_signal"] = (
                full >= 5 and full >= typed - 1 and no_false_none)
            report["status"] = (
                "NATIVE_COMPLETE_NONINTERFERENCE_SIGNAL"
                if report["exploratory_noninterference_signal"]
                else "NATIVE_COMPLETE_NO_NONINTERFERENCE_SIGNAL")
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
    result = run(a.fixture, a.work, a.out, installed=a.installed)
    print(dumps({
        "status": result["status"], "rows": len(result["rows"]),
        "native_body_calls": result["native_body_calls"],
        "native_c3_calls": result["native_c3_calls"],
        "scores": result["scores"],
        "exploratory_noninterference_signal":
            result["exploratory_noninterference_signal"],
    }))
    return 0 if result["status"] in (
        "MODEL_FREE_SIX_CASE_PREFLIGHT_PASS",
        "NATIVE_COMPLETE_NONINTERFERENCE_SIGNAL",
        "NATIVE_COMPLETE_NO_NONINTERFERENCE_SIGNAL") else 2


if __name__ == "__main__":
    raise SystemExit(main())
