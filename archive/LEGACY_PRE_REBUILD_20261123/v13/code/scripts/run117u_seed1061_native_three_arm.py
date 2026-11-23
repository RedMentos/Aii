#!/usr/bin/env python3
"""Run117U frozen seed1061: actual native B1/B2 salient source -> C3 arms.

Review-only isolated SHADOW experiment. The deterministic source selector is a
baseline, Body quotes are fallible, and no answer/oracle is sent to C3.
Native execution is proven only by original pinned model and runner receipts.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

from scripts.run111_c3_b2_context_native import _prepare_home
from scripts.run113b_b1b2_c3_native import _config, _pin_models, _reaped, MODELS
from scripts.run115j_typed_jef_role_native import C3_FILE, SCHEMA
from scripts.run47_jef_c3_typed_receiver_native import score
from scripts.run117s_body_complementarity_preflight import (
    ARMS, SEED, FIXTURE_SHA, SYSTEM, fixture, _span, _messages,
)
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_c3_source_envelope_candidate import (
    build_c3_source_envelope, _latest_authoritative_user,
)
from v13.b2_salient_source_excerpt_shadow_candidate import guarded_salient_b2_offer
from v13.common import atomic_write, dumps
from v13.runtime import Runtime
from v13.store import audit_closed

CONFIG = _config() | {
    "seed": SEED, "temperature": 0.0, "threads": 2,
    "learning_mode": "RECORD_ONLY", "observer_mode": "off",
    "answer_tokens": 96, "observer_tokens": 256,
    "observer_seconds": 120, "deadline_seconds": 180,
    "history_turns": 0, "memory_top_k": 0,
    "body_residency_mb": 0, "teacher_enabled": False,
    "offer_quote_context_chars": 200, "b2_quote_select": "pointer",
    "b2_state_slots": 2, "b2_context_chars": 1500,
    "b2_offer_body_state": False,
}
SCHEMA_NAME = "v13.run117u.seed1061_native_three_arm.v1"
GOOD = ("NATIVE_COMPLETE_EXPLORATORY_BODY_SELECTION_SIGNAL",
        "NATIVE_COMPLETE_NO_ATTRIBUTABLE_BODY_SELECTION_GAIN")
BODY_RED = "PARTIAL_BODY_QUOTE_RED"
STRUCTURAL_RED = "STRUCTURAL_RED"


def _source_messages(runtime, prior, current, row):
    refs = [prior["source_ref"], current["source_ref"]]
    texts = [runtime.store.read_source(ref) for ref in refs]
    if texts != [row["prior"], row["current"]]:
        raise ValueError("FROZEN_ORIGINAL_USER_SOURCE_RED")
    raw = {"schema": "v13.run117s.raw_two_source.v1",
           "sources": [{"text": t, "source_ref": r,
                        "origin": "STORE_EXACT_USER_NOT_MODEL_QUOTE"}
                       for t, r in zip(texts, refs)]}
    selected = {"schema": "v13.run117s.source_only_selector.v1",
                "spans": [
                    _span(runtime.store, refs[0], texts[0], row["policy_span"]),
                    _span(runtime.store, refs[1], texts[1], row["option_span"]),
                ]}
    return {ARMS[0]: _messages(raw)["messages"],
            ARMS[1]: _messages(selected)["messages"]}


def _body_messages(runtime, current, ids, row):
    env = build_c3_source_envelope(
        runtime, current, ids, operator_opt_in=True)
    if env.get("status") != "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL":
        return None, "BODY_SOURCE_ENVELOPE_RED"
    try:
        obs = json.loads(env["messages"][1]["content"])["body_observations"]
        if ([x["role"] for x in obs] != ["B1_DETAIL", "B2_GIST"]
                or any(x["hypothesis_authority"] !=
                       "MODEL_HYPOTHESIS_NOT_FACT" for x in obs)):
            return None, "BODY_HYPOTHESIS_AUTHORITY_RED"
        quotes = [q for x in obs for q in x["verified_quotes"]]
        if (not any(row["policy_span"] in q["text"] for q in quotes)
                or not any(row["option_span"] in q["text"] for q in quotes)
                or any(q["semantic_truth_authority"] is not False
                       for q in quotes)):
            return None, "BODY_POLICY_OR_OPTIONS_QUOTE_MISSING_RED"
        payload = {"schema": "v13.run117s.body_verified_quote_selector.v1",
                   "verified_quotes": quotes,
                   "body_hypotheses_are_facts": False,
                   "quote_semantic_truth_authority": False,
                   "body_hypotheses_not_forwarded": True}
        return _messages(payload)["messages"], None
    except (KeyError, TypeError, ValueError, IndexError):
        return None, "BODY_QUOTE_PAYLOAD_INTEGRITY_RED"


def _safe_messages(messages, row, arm):
    if (arm not in ARMS or type(messages) is not list or len(messages) != 2
            or [m.get("role") for m in messages] != ["system", "user"]
            or messages[0].get("content") != SYSTEM):
        raise ValueError("C3_ROLE_BOUNDARY_RED")
    system = messages[0]["content"]
    user = messages[1]["content"]
    if (row["prior"] in system or row["current"] in system
            or '"oracle"' in user or "typed_jef_candidate" in user
            or '"answer"' in user or '"approved"' in user):
        raise ValueError("C3_ANSWER_OR_SYSTEM_LEAK_RED")
    payload = json.loads(user)
    if arm == ARMS[0]:
        if ([x["text"] for x in payload.get("sources", [])] !=
                [row["prior"], row["current"]]):
            raise ValueError("RAW_SOURCE_MISMATCH_RED")
    elif arm == ARMS[1]:
        if ([x["text"] for x in payload.get("spans", [])] !=
                [row["policy_span"], row["option_span"]]
                or row["prior"] in user):
            raise ValueError("DETERMINISTIC_SOURCE_SPAN_RED")
    else:
        if (payload.get("body_hypotheses_are_facts") is not False
                or payload.get("quote_semantic_truth_authority") is not False
                or payload.get("body_hypotheses_not_forwarded") is not True
                or "body_observations" in payload or "sources" in payload
                or row["prior"] in user):
            raise ValueError("BODY_HYPOTHESIS_OR_SOURCE_LEAK_RED")
    return sha256(dumps(messages).encode()).hexdigest()


def _score_summary(report):
    scores = {arm: 0 for arm in ARMS}
    recorded = {arm: 0 for arm in ARMS}
    body_offers_ok = True
    closed = len(report["rows"]) == 6
    for row in report["rows"]:
        closed &= row.get("closed_store_ok") is True
        closed &= row.get("no_live_output") is True
        closed &= len(row.get("offers", [])) == 3
        for offer in row.get("offers", []):
            body_offers_ok &= (offer.get("status") == "RECORDED"
                               and offer.get("process_reaped") is True
                               and offer.get("native_metrics", {}).get("status")
                               == "FINAL")
        for arm in row.get("arms", []):
            name = arm.get("arm")
            if name not in ARMS:
                closed = False
                continue
            if (arm.get("status") == "RECORDED"
                    and arm.get("native_final") is True
                    and arm.get("process_reaped") is True):
                recorded[name] += 1
                scores[name] += arm.get("score", {}).get("correct", 0)
    report["scores"] = scores
    report["recorded_by_arm"] = recorded
    controls_ok = closed and all(recorded[a] == 6 for a in ARMS[:2])
    body_ok = (controls_ok and body_offers_ok
               and recorded[ARMS[2]] == 6
               and report["native_body_calls"] == 18
               and report["native_c3_calls"] == 18)
    if body_ok:
        no_false_none = all(
            next(a for a in row["arms"] if a["arm"] == ARMS[2])
            ["score"]["parsed"] == {"choice": "NONE", "remaining": None}
            for row in report["rows"] if row["id"] in ("Cinder", "Flux"))
        signal = (scores[ARMS[2]] >= scores[ARMS[1]] + 2
                  and scores[ARMS[2]] >= scores[ARMS[0]] + 1
                  and no_false_none)
        report["exploratory_body_selection_signal"] = signal
        return GOOD[0] if signal else GOOD[1]
    if (controls_ok and body_offers_ok
            and all(r.get("body_path") == "BODY_QUOTE_RED"
                    or any(a.get("arm") == ARMS[2] and
                           a.get("status") == "RECORDED"
                           for a in r["arms"])
                    for r in report["rows"])):
        return BODY_RED
    return STRUCTURAL_RED


def _observe(runtime, event, role, phase, entry, report, save, *, salient=False):
    item = {"role": role, "phase": phase, "status": "INCOMPLETE",
            "source_ref": event["source_ref"], "process_reaped": False}
    entry["offers"].append(item)
    save()
    before = len(runtime.pool.release_history)
    try:
        if salient:
            result = guarded_salient_b2_offer(
                runtime, event, 0, time.monotonic() + 180,
                operator_opt_in=True)
            expected_status = "SHADOW_SALIENT_B2_OFFER_PRODUCED"
        else:
            result = TopicPartitionOfferConsumer(runtime).guarded_offer(
                role, event, 0, time.monotonic() + 180,
                operator_opt_in=True)
            expected_status = "SHADOW_OFFER_PRODUCED"
        item["component_status"] = result.get("status")
        if result.get("model_called") is True or result.get("runner_called") is True:
            report["native_body_calls"] += 1
        if result.get("status") != expected_status:
            raise ValueError("BODY_OFFER_REFUSED_" + str(result.get("status")))
        item["packet_id"] = result["offer_packet_id"]
        item["query_packet_id"] = result["query_packet_id"]
        stored = runtime.store.one(
            "SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",
            (item["packet_id"],))
        if stored is None:
            raise ValueError("BODY_OFFER_PACKET_MISSING_RED")
        offer = json.loads(stored["payload"])
        item["native_metrics"] = offer.get("native_metrics")
        item["model_revision"] = offer.get("model_revision")
        item["source_quote_count"] = len(offer.get("offer", {}).get("quotes", []))
        metrics = item["native_metrics"] or {}
        if (metrics.get("status") != "FINAL"
                or metrics.get("actual_model") != MODELS[role][0]
                or item["model_revision"] != MODELS[role][1]):
            raise ValueError("BODY_PINNED_MODEL_OR_FINAL_RED")
        item["status"] = "RECORDED"
    except Exception as exc:
        item["status"] = "STRUCTURAL_RED"
        item["error_type"] = type(exc).__name__
        item["error"] = str(exc)[:280]
    finally:
        runtime.pool.unload()
        item["process_reaped"] = _reaped(
            runtime.pool.release_history[before:])
        if not item["process_reaped"]:
            item["status"] = "STRUCTURAL_RED"
        save()
    return item


def _run_row(row, index, work, report, save, installed):
    home = work / row["id"]
    _prepare_home(home, installed, CONFIG)
    runtime = Runtime(home)
    entry = {"id": row["id"], "status": "INCOMPLETE", "offers": [],
             "arms": [], "body_path": "UNTESTED",
             "closed_store_ok": False, "no_live_output": False}
    report["rows"].append(entry)
    save()
    try:
        prior = runtime.store.event(runtime.session, row["prior"])
        entry["prior_source_ref"] = prior["source_ref"]
        # Preserve actual causal turn order: native prior B2 inference precedes
        # the durable current USER event, as in the frozen Run117S preflight.
        prior_offer = _observe(runtime, prior, "B2_GIST", "prior",
                               entry, report, save)
        current = runtime.store.event(runtime.session, row["current"])
        entry["current_source_ref"] = current["source_ref"]
        prompts = _source_messages(runtime, prior, current, row)
        entry["source_prompt_sha256"] = {
            arm: _safe_messages(messages, row, arm)
            for arm, messages in prompts.items()}
        # The Body path may fail independently; do not lose the two controls.
        b1 = _observe(runtime, current, "B1_DETAIL", "current",
                      entry, report, save)
        b2 = _observe(runtime, current, "B2_GIST", "current",
                      entry, report, save, salient=True)
        if all(x["status"] == "RECORDED" for x in (prior_offer, b1, b2)):
            ids = {"B1_DETAIL": b1["packet_id"],
                   "B2_GIST": b2["packet_id"]}
            body_messages, error = _body_messages(runtime, current, ids, row)
            if body_messages is None:
                entry["body_path"] = "BODY_QUOTE_RED"
                entry["body_quote_error"] = error
            else:
                prompts[ARMS[2]] = body_messages
                entry["body_prompt_sha256"] = _safe_messages(
                    body_messages, row, ARMS[2])
                entry["body_path"] = "QUOTE_READY"
        else:
            entry["body_path"] = "BODY_OFFER_STRUCTURAL_RED"
        order = ARMS[index % 3:] + ARMS[:index % 3]
        for arm in order:
            if arm not in prompts:
                entry["arms"].append({
                    "arm": arm, "status": "BODY_QUOTE_UNAVAILABLE",
                    "native_final": False, "process_reaped": False,
                    "score": None})
                save()
                continue
            messages = prompts[arm]
            item = {"arm": arm, "status": "INCOMPLETE",
                    "messages": messages,
                    "messages_sha256": _safe_messages(messages, row, arm),
                    "native_final": False, "process_reaped": False,
                    "score": None}
            entry["arms"].append(item)
            save()
            before = len(runtime.pool.release_history)
            try:
                # Fail closed on a later USER correction before C3 starts.
                if (_latest_authoritative_user(
                        runtime.store, runtime.session) !=
                        current["event_id"]):
                    raise ValueError("CURRENT_USER_SOURCE_STALE_RED")
                if (runtime.store.read_source(prior["source_ref"]) !=
                        row["prior"]
                        or runtime.store.read_source(current["source_ref"]) !=
                        row["current"]):
                    raise ValueError("USER_SOURCE_CHANGED_RED")
                runner = runtime.pool.get("C3_LANGUAGE")
                report["native_c3_calls"] += 1
                save()
                output = "".join(runner.generate(
                    messages, runtime.cancel_event,
                    time.monotonic() + 120, 96, SCHEMA, seed=SEED))
                item["output"] = output
                item["native_metrics"] = dict(runner.last_metrics)
                item["native_final"] = (
                    item["native_metrics"].get("status") == "FINAL")
                item["score"] = score(output, row["oracle"])
            except Exception as exc:
                item["error_type"] = type(exc).__name__
                item["error"] = str(exc)[:280]
            finally:
                runtime.pool.unload()
                item["process_reaped"] = _reaped(
                    runtime.pool.release_history[before:])
                item["status"] = (
                    "RECORDED" if item["native_final"]
                    and item["process_reaped"]
                    and item.get("native_metrics", {}).get("actual_model") ==
                    C3_FILE else "STRUCTURAL_RED")
                save()
        entry["status"] = (
            "RECORDED" if all(a["status"] == "RECORDED"
                              for a in entry["arms"]) and
            entry["body_path"] == "QUOTE_READY" else
            "PARTIAL_BODY_QUOTE_RED" if
            entry["body_path"] == "BODY_QUOTE_RED" and
            all(a["status"] == "RECORDED" for a in entry["arms"]
                if a["arm"] in ARMS[:2]) else "STRUCTURAL_RED")
    except Exception as exc:
        entry["status"] = "STRUCTURAL_RED"
        entry["error_type"] = type(exc).__name__
        entry["error"] = str(exc)[:280]
    finally:
        try:
            entry["no_live_output"] = (
                runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0
                and runtime.store.one(
                    "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"] == 0)
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


def run(fixture_path, work, out, *, installed):
    rows = fixture(fixture_path)
    work, out, installed = Path(work), Path(out), Path(installed).resolve()
    if work.exists() or out.exists():
        raise FileExistsError("RUN117U_FRESH_WORK_AND_REPORT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    report = {
        "schema": SCHEMA_NAME, "seed": SEED, "fixture_sha256": FIXTURE_SHA,
        "status": "INCOMPLETE", "native": True,
        "synthetic_body_observers": False,
        "native_body_calls": 0, "native_c3_calls": 0,
        "native_jef_calls": 0, "native_c2_calls": 0,
        "scores": {arm: 0 for arm in ARMS}, "recorded_by_arm": {},
        "exploratory_body_selection_signal": False,
        "rows": [], "age0": "RECORD_ONLY",
        "step2_exit": "EVIDENCE_NOT_PASSING", "b3": "NO_PROMOTION",
        "body_jepa": "UNAVAILABLE", "world_jepa": "SHADOW",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False, "output_committed": False,
        "tool_dispatches": 0, "learning_authority": 0,
        "delivery_authority": 0,
    }
    path = out / "report.json"
    def save():
        atomic_write(path, dumps(report))
    save()
    try:
        _pin_models(installed)
        for i, row in enumerate(rows):
            _run_row(row, i, work, report, save, installed)
        report["status"] = _score_summary(report)
    except Exception as exc:
        report["status"] = STRUCTURAL_RED
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:280]
    save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--installed", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = run(args.fixture, args.work, args.out, installed=args.installed)
    print(dumps({"status": result["status"],
                 "native_body_calls": result["native_body_calls"],
                 "native_c3_calls": result["native_c3_calls"],
                 "scores": result["scores"],
                 "recorded_by_arm": result["recorded_by_arm"]}))
    return 0 if result["status"] in GOOD else 2


if __name__ == "__main__":
    raise SystemExit(main())
