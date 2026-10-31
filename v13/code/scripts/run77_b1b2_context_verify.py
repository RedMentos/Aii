#!/usr/bin/env python3
"""Run77 independent native B1/B2 paired-context raw reparse, no promotion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import jef_b1b2_context_fixture_797 as f
from v13.common import dumps

SCHEMA = "v13.run77.b1b2_disjoint_context_native.v1"
MODELS = {
    "B1_DETAIL": "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
    "B2_GIST": "Qwen3.5-0.8B-Q4_0.gguf",
}


def _require(ok, code):
    if not ok:
        raise ValueError(code)


def verify(report):
    _require(type(report) is dict and report.get("schema") == SCHEMA
             and report.get("seed") == f.SEED
             and report.get("table_sha256") == f.TABLE_SHA256,
             "RUN77_REPORT_PIN_RED")
    binding = report.get("binding")
    _require(type(binding) is dict
             and binding.get("model_sha256", {}).get("B1_DETAIL")
             == f.B1_SHA256
             and binding.get("model_sha256", {}).get("B2_GIST")
             == f.B2_SHA256
             and binding.get("runner_sha256") == f.RUNNER_SHA256,
             "RUN77_NATIVE_MODEL_PIN_RED")
    _require(
        report.get("native_call_count") == 36
        and report.get("independent_utility_proven") is False
        and report.get("delivery_authority") == 0
        and report.get("learning_authority") == 0
        and report.get("output_committed") is False
        and report.get("tool_dispatches") == 0
        and report.get("age0") == "RECORD_ONLY"
        and report.get("step2") == "UTILITY_FAIL"
        and report.get("b3") == "NO_PROMOTION"
        and report.get("body_jepa") == "UNAVAILABLE"
        and report.get("world_jepa") == "SHADOW"
        and report.get("jepa_weight") == 0
        and report.get("redmi_measured") is False
        and report.get("whole_system_complete") is False,
        "RUN77_AUTHORITY_RED")
    rows = report.get("rows")
    _require(type(rows) is list and len(rows) == 12,
             "RUN77_ROWS_RED")
    scores = {role: {arm: 0 for arm in f.ARMS} for role in f.ROLES}
    b2_prior_evidence = 0
    native_calls = 0
    for fixture_index, fixture in enumerate(f.fixtures()):
        for arm_index, arm in enumerate(f.ARMS):
            row = rows[fixture_index * 2 + arm_index]
            _require(
                type(row) is dict
                and row.get("project") == fixture["project"]
                and row.get("arm") == arm
                and row.get("status") == "RECORDED"
                and row.get("source_sha256") == fixture["source_sha256"]
                and row.get("closed_store_ok") is True
                and row.get("processes_reaped") is True
                and row.get("no_live_output") is True
                and row.get("native_call_count")
                == (4 if arm == "WITH_PRIOR" else 2),
                "RUN77_ROW_BOUNDARY_RED")
            entries = row.get("offers")
            _require(type(entries) is list
                     and len(entries) == row["native_call_count"],
                     "RUN77_OFFER_COUNT_RED")
            expected_sequence = (
                [(role, "prior") for role in f.ROLES]
                if arm == "WITH_PRIOR" else [])
            expected_sequence += [(role, "current") for role in f.ROLES]
            _require([(e.get("role"), e.get("phase")) for e in entries]
                     == expected_sequence, "RUN77_OFFER_ORDER_RED")
            current_ref = row.get("current_source_ref")
            prior_ref = row.get("prior_source_ref")
            _require(type(current_ref) is dict
                     and current_ref.get("sha256")
                     == fixture["source_sha256"]["current"],
                     "RUN77_CURRENT_REF_RED")
            if arm == "WITH_PRIOR":
                _require(type(prior_ref) is dict
                         and prior_ref.get("sha256")
                         == fixture["source_sha256"]["prior"],
                         "RUN77_PRIOR_REF_RED")
            else:
                _require(prior_ref is None, "RUN77_ABLATION_PRIOR_REF_RED")
            for entry in entries:
                native_calls += 1
                role, phase = entry["role"], entry["phase"]
                expected_ref = prior_ref if phase == "prior" else current_ref
                offer, query = entry.get("offer"), entry.get("query")
                _require(
                    entry.get("status") == "RECORDED"
                    and entry.get("guarded_status")
                    == "SHADOW_LATEST_USER_OFFER_PRODUCED"
                    and entry.get("process_reaped") is True
                    and entry.get("source_ref") == expected_ref
                    and type(offer) is dict and type(query) is dict
                    and offer.get("event_id") == entry.get("event_id")
                    and query.get("event_id") == entry.get("event_id")
                    and offer.get("role") == role
                    and query.get("target_role") == role
                    and query.get("source_refs") == [expected_ref]
                    and offer.get("native_metrics", {}).get("status")
                    == "FINAL"
                    and offer.get("native_metrics", {}).get("actual_model")
                    == MODELS[role],
                    "RUN77_NATIVE_OFFER_BINDING_RED")
                capture = row.get("captures", {}).get(role + ":" + phase)
                _require(type(capture) is dict
                         and capture.get("messages_sha256")
                         == f.sha(dumps(capture.get("messages")).encode()),
                         "RUN77_NATIVE_PROMPT_CAPTURE_RED")
                refs = query.get("context_source_refs")
                if phase == "prior" or arm == "CURRENT_ONLY":
                    _require(refs == [], "RUN77_ABLATION_CONTEXT_RED")
                else:
                    _require(refs == [prior_ref],
                             "RUN77_PRIOR_CONTEXT_TRANSPORT_RED")
                if phase == "current":
                    summary = offer.get("offer", {}).get("summary")
                    strict = f.strict_summary(
                        summary, fixture["action"], fixture["remaining"])
                    _require(entry.get("summary") == summary
                             and entry.get("strict") == strict
                             and entry.get("context_source_refs_verified")
                             is True, "RUN77_SEMANTIC_SCORE_RED")
                    scores[role][arm] += strict
                    if role == "B2_GIST" and arm == "WITH_PRIOR":
                        refs = offer.get("evidence_refs", [])
                        verified = any(
                            type(ref) is dict
                            and ref.get("source_id")
                            == prior_ref.get("source_id")
                            and ref.get("sha256")
                            == fixture["source_sha256"]["prior"]
                            and type(ref.get("char_start")) is int
                            and type(ref.get("char_end")) is int
                            and 0 <= ref["char_start"] < ref["char_end"]
                            <= len(fixture["prior"])
                            and fixture["prior"][
                                ref["char_start"]:ref["char_end"]]
                            in offer.get("offer", {}).get("quotes", [])
                            for ref in refs)
                        _require(entry.get("prior_evidence_refs_verified")
                                 is verified, "RUN77_B2_PRIOR_EVIDENCE_RED")
                        b2_prior_evidence += int(verified)
    _require(native_calls == 36
             and report.get("scores") == scores
             and report.get("b2_prior_evidence") == b2_prior_evidence,
             "RUN77_AGGREGATE_SCORE_RED")
    status = f.scientific_verdict(scores, b2_prior_evidence)
    _require(report.get("status") == status,
             "RUN77_SCIENTIFIC_STATUS_RED")
    return {
        "status": "INDEPENDENT_RUN77_NATIVE_REPARSE_PASS",
        "scientific_result": status,
        "scores": scores,
        "b2_prior_evidence": b2_prior_evidence,
        "native_calls": native_calls,
        "claim_limit": "SIX_DISJOINT_SYNTHETIC_LINUX_NATIVE_SHADOW_ONLY",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    args = p.parse_args()
    print(json.dumps(verify(json.loads(
        args.report.read_text(encoding="utf-8"))), sort_keys=True))


if __name__ == "__main__":
    main()
