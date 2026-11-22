#!/usr/bin/env python3
"""Independent Run57 five-call native B1/B2 -> C3 structural verifier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from v13.common import dumps
from scripts.run52_b1b2_cross_turn_native import load_fixture, FIXTURE_SHA256, ROLES
from scripts.run47_jef_c3_typed_receiver_native import NEGATIVE

PINS = {
    "B1_DETAIL": ("bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
                  "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf"),
    "B2_GIST": ("57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
                "Qwen3.5-0.8B-Q4_0.gguf"),
    "C3_LANGUAGE": ("3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
                    "LFM2.5-350M-QAD-Q4_0.gguf"),
}
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(report_path, fixture_path):
    data = load_fixture(fixture_path)
    fixture = next(f for f in data["fixtures"] if f["id"] == "Harbor")
    report = json.loads(Path(report_path).read_text())
    errors = []

    def require(ok, reason):
        if not ok:
            errors.append(reason)

    require(report.get("schema") == "v13.run57.b1b2_c3_native_report.v1", "schema")
    require(report.get("seed") == 479 and report.get("fixture_sha256") == FIXTURE_SHA256,
            "fixture_pin")
    require(report.get("claim") == "ORIGINAL_RUN52_HARBOR_B1B2_C3_STRUCTURAL_REPLAY_NOT_UTILITY",
            "claim")
    require(report.get("negative_gates") == NEGATIVE, "negative_gates")
    require(report.get("installed_binding_unchanged") is True, "binding_unchanged")
    binding = report.get("binding") or {}
    for role, (digest, _) in PINS.items():
        require((binding.get("model_sha256") or {}).get(role) == digest,
                "model_sha_" + role)
    require(binding.get("runner_sha256") == RUNNER_SHA, "runner_sha")
    rows = report.get("rows")
    require(type(rows) is list and len(rows) == 1, "row_count")
    if type(rows) is not list or len(rows) != 1:
        return {"status": "STRUCTURAL_RED", "errors": errors}
    row = rows[0]
    require((report.get("row_sha256") or {}).get("Harbor")
            == sha(dumps(row).encode("utf-8")), "row_sha")
    require(row.get("schema") == "v13.run57.b1b2_c3_native_row.v1", "row_schema")
    require(row.get("status") == "RECORDED", "row_status")
    require(row.get("native_model") is True
            and row.get("semantic_utility_claim") is False
            and row.get("learning_authority") == 0, "claim_boundary")
    require(row.get("negative_gates") == NEGATIVE, "row_negative_gates")
    require(row.get("no_live_output") is True, "no_live_output")
    require(row.get("native_process_count", 0) >= 5
            and row.get("processes_reaped") is True
            and (row.get("closed_store_audit") or {}).get("ok") is True,
            "process_sqlite")
    events = row.get("source_events") or {}
    for phase in ("prior", "current"):
        e = events.get(phase) or {}
        ref = e.get("source_ref") or {}
        text = fixture[phase]
        require(e.get("text_sha256") == sha(text.encode())
                and ref.get("sha256") == sha(text.encode())
                and ref.get("char_start") == 0
                and ref.get("char_end") == len(text), "source_" + phase)
    offers = row.get("body_offers")
    require(type(offers) is list and len(offers) == 4, "body_offer_count")
    if type(offers) is not list or len(offers) != 4:
        return {"status": "STRUCTURAL_RED", "errors": errors}
    by_key = {(x.get("role"), x.get("phase")): x for x in offers}
    require(len(by_key) == 4, "body_role_phase_unique")
    captures = row.get("body_captures") or {}
    for role in ROLES:
        for phase in ("prior", "current"):
            entry = by_key.get((role, phase)) or {}
            label = role + "_" + phase
            offer = entry.get("offer") or {}
            query = entry.get("query") or {}
            require(entry.get("event_id") == (events.get(phase) or {}).get("event_id")
                    and offer.get("event_id") == entry.get("event_id")
                    and offer.get("role") == role
                    and offer.get("query_packet_id") == query.get("packet_id")
                    and query.get("event_id") == entry.get("event_id")
                    and query.get("target_role") == role
                    and (offer.get("provenance") or [None])[0]
                    == (events.get(phase) or {}).get("source_ref"),
                    "offer_query_binding_" + label)
            metrics = offer.get("native_metrics") or {}
            require(metrics.get("status") == "FINAL"
                    and metrics.get("actual_model") == PINS[role][1],
                    "native_body_" + label)
            expected = [] if phase == "prior" else [
                (events.get("prior") or {}).get("source_ref", {}).get("source_id")]
            require([x.get("source_id") for x in
                     query.get("context_source_refs", [])] == expected,
                    "context_refs_" + label)
            capture = captures.get(entry.get("capture_key")) or {}
            messages = capture.get("messages") or []
            require(len(messages) == 2 and capture.get("messages_sha256")
                    == sha(dumps(messages).encode()) if messages else False,
                    "body_prompt_" + label)
        prior = by_key.get((role, "prior")) or {}
        current = by_key.get((role, "current")) or {}
        require(type(prior.get("partition_key_sha256")) is str
                and len(prior["partition_key_sha256"]) == 64
                and prior["partition_key_sha256"] == current.get("partition_key_sha256"),
                "partition_resume_" + role)
    c3 = row.get("c3") or {}
    require(c3.get("envelope_status") == "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL",
            "envelope_status")
    ids = c3.get("offer_packet_ids") or {}
    require(set(ids) == set(ROLES)
            and all(ids.get(role) == (by_key.get((role, "current")) or {})
                    .get("offer", {}).get("packet_id") for role in ROLES),
            "envelope_offer_ids")
    messages = c3.get("input_messages") or []
    require(len(messages) == 2 and c3.get("input_sha256")
            == sha(dumps(messages).encode()) if messages else False,
            "c3_prompt_sha")
    if len(messages) == 2:
        try:
            payload = json.loads(messages[1]["content"])
            source = payload.get("current_source") or {}
            require(source.get("text") == fixture["current"]
                    and source.get("source_ref") == events["current"]["source_ref"],
                    "c3_current_source")
            require(payload.get("evidence_policy")
                    == "CURRENT_USER_SOURCE_AND_EXACT_QUOTES_ONLY"
                    and payload.get("body_hypotheses_are_facts") is False,
                    "c3_hypothesis_boundary")
            bodies = payload.get("body_observations") or []
            require([x.get("role") for x in bodies] == list(ROLES),
                    "c3_body_roles")
            for body in bodies:
                require(body.get("hypothesis_authority") == "MODEL_HYPOTHESIS_NOT_FACT",
                        "c3_hypothesis_" + str(body.get("role")))
                for q in body.get("verified_quotes") or []:
                    ref = q.get("source_ref") or {}
                    match = any(
                        ref.get("source_id") == events[phase]["source_ref"]["source_id"]
                        and q.get("text") in fixture[phase]
                        and q.get("semantic_truth_authority") is False
                        for phase in ("prior", "current"))
                    require(match, "c3_verified_quote")
        except Exception:
            errors.append("c3_prompt_json")
    metrics = c3.get("native_metrics") or {}
    require(metrics.get("status") == "FINAL"
            and metrics.get("actual_model") == PINS["C3_LANGUAGE"][1],
            "c3_native")
    require(type(c3.get("output_sha256")) is str
            and len(c3["output_sha256"]) == 64
            and type(c3.get("output_bytes")) is int
            and c3["output_bytes"] > 0
            and "output_text" not in c3, "c3_output_digest_only")
    require(report.get("status") == "B1B2_C3_NATIVE_ENVELOPE_STRUCTURAL_ONLY",
            "report_status")
    return {"status": "STRUCTURAL_PASS" if not errors else "STRUCTURAL_RED",
            "errors": errors,
            "claim": "ORIGINAL_RUN52_HARBOR_B1B2_C3_STRUCTURAL_REPLAY_NOT_UTILITY"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args()
    result = verify(a.report, a.fixture)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "STRUCTURAL_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
