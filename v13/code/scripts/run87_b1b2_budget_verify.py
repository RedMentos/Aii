#!/usr/bin/env python3
"""Independent Run87 48-call B1/B2 budget report reparse; no promotion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import jef_b1b2_budget_fixture_877 as f
from v13.common import dumps

SCHEMA = "v13.run87.b1b2_budget_ablation_native.v1"
MODELS = {
    "B1_DETAIL": "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
    "B2_GIST": "Qwen3.5-0.8B-Q4_0.gguf",
}


def require(ok, code):
    if not ok:
        raise ValueError(code)


def verify(report):
    require(type(report) is dict and report.get("schema") == SCHEMA
            and report.get("seed") == f.SEED
            and report.get("table_sha256") == f.TABLE_SHA256,
            "RUN87_REPORT_PIN_RED")
    binding = report.get("binding")
    require(type(binding) is dict
            and binding.get("model_sha256", {}).get("B1_DETAIL") == f.B1_SHA256
            and binding.get("model_sha256", {}).get("B2_GIST") == f.B2_SHA256
            and binding.get("runner_sha256") == f.RUNNER_SHA256,
            "RUN87_NATIVE_MODEL_PIN_RED")
    gates = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
             "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
             "world_jepa": "SHADOW", "jepa_weight": 0,
             "redmi_measured": False, "whole_system_complete": False,
             "independent_utility_proven": False,
             "delivery_authority": 0, "learning_authority": 0,
             "output_committed": False, "tool_dispatches": 0}
    require(all(type(report.get(k)) is type(v) and report[k] == v
                for k, v in gates.items()), "RUN87_AUTHORITY_RED")
    rows = report.get("rows")
    require(type(rows) is list and len(rows) == 12
            and report.get("native_call_count") == 48,
            "RUN87_ROW_COUNT_RED")
    scores = {role: {arm: 0 for arm in f.ARMS} for role in f.ROLES}
    b2_long_evidence = 0
    native_calls = 0
    for fixture in f.fixtures():
        for arm_index, arm in enumerate(fixture["arm_order"]):
            row = rows[2 * fixture["index"] + arm_index]
            require(type(row) is dict
                    and row.get("project") == fixture["project"]
                    and row.get("arm") == arm
                    and row.get("source_sha256") == fixture["source_sha256"]
                    and row.get("status") == "RECORDED"
                    and row.get("closed_store_ok") is True
                    and row.get("processes_reaped") is True
                    and row.get("no_live_output") is True
                    and row.get("native_call_count") == 4
                    and row.get("observer_tokens") == f.OBSERVER_TOKENS[arm]
                    and row.get("quote_min_chars") == f.QUOTE_MIN_CHARS
                    and row.get("expected_summary_max_chars") == f.summary_cap(f.OBSERVER_TOKENS[arm]),
                    "RUN87_ROW_BOUNDARY_RED")
            prior_ref = row.get("prior_source_ref")
            current_ref = row.get("current_source_ref")
            require(type(prior_ref) is dict and type(current_ref) is dict
                    and prior_ref.get("sha256") == fixture["source_sha256"]["prior"]
                    and current_ref.get("sha256") == fixture["source_sha256"]["current"],
                    "RUN87_SOURCE_REF_RED")
            entries = row.get("offers")
            captures = row.get("captures")
            require(type(entries) is list and len(entries) == 4
                    and type(captures) is dict and len(captures) == 4,
                    "RUN87_OFFER_COUNT_RED")
            expected_sequence = [(role, phase)
                                 for phase in ("prior", "current")
                                 for role in f.ROLES]
            require([(e.get("role"), e.get("phase")) for e in entries]
                    == expected_sequence, "RUN87_OFFER_ORDER_RED")
            saturation = {}
            b2_prior_verified = False
            for entry in entries:
                role, phase = entry["role"], entry["phase"]
                expected_ref = prior_ref if phase == "prior" else current_ref
                offer, query = entry.get("offer"), entry.get("query")
                require(entry.get("status") == "RECORDED"
                        and entry.get("guarded_status") == "SHADOW_LATEST_USER_OFFER_PRODUCED"
                        and entry.get("process_reaped") is True
                        and entry.get("source_ref") == expected_ref
                        and type(offer) is dict and type(query) is dict
                        and offer.get("event_id") == entry.get("event_id")
                        and query.get("event_id") == entry.get("event_id")
                        and offer.get("role") == role
                        and query.get("target_role") == role
                        and query.get("source_refs") == [expected_ref]
                        and offer.get("native_metrics", {}).get("status") == "FINAL"
                        and offer.get("native_metrics", {}).get("actual_model") == MODELS[role],
                        "RUN87_NATIVE_OFFER_BINDING_RED")
                cap = captures.get(role + ":" + phase)
                require(type(cap) is dict
                        and cap.get("messages_sha256") == f.sha(dumps(cap.get("messages")).encode())
                        and cap.get("schema_sha256") == f.sha(dumps(cap.get("schema")).encode())
                        and cap.get("observer_tokens") == f.OBSERVER_TOKENS[arm]
                        and cap.get("summary_max_chars") == f.summary_cap(f.OBSERVER_TOKENS[arm])
                        and cap.get("schema", {}).get("properties", {}).get(
                            "summary", {}).get("maxLength") == cap["summary_max_chars"],
                        "RUN87_NATIVE_SCHEMA_CAPTURE_RED")
                summary = offer.get("offer", {}).get("summary")
                require(type(summary) is str
                        and len(summary) <= cap["summary_max_chars"]
                        and entry.get("summary") == summary
                        and entry.get("summary_length") == len(summary)
                        and entry.get("summary_saturated") is (len(summary) == cap["summary_max_chars"]),
                        "RUN87_SUMMARY_CAP_RED")
                if phase == "prior":
                    require(query.get("context_source_refs") == [],
                            "RUN87_PRIOR_CONTEXT_LEAK_RED")
                else:
                    require(query.get("context_source_refs") == [prior_ref]
                            and entry.get("context_source_refs_verified") is True,
                            "RUN87_CONTEXT_TRANSPORT_RED")
                    strict = f.strict_summary(summary, fixture["action"], fixture["remaining"])
                    require(type(entry.get("strict")) is int and entry["strict"] == strict,
                            "RUN87_STRICT_SCORE_RED")
                    scores[role][arm] += strict
                    saturation[role] = entry["summary_saturated"]
                    if role == "B2_GIST":
                        verified = any(
                            type(ref) is dict
                            and ref.get("source_id") == prior_ref.get("source_id")
                            and ref.get("sha256") == fixture["source_sha256"]["prior"]
                            and type(ref.get("char_start")) is int
                            and type(ref.get("char_end")) is int
                            and 0 <= ref["char_start"] < ref["char_end"] <= len(fixture["prior"])
                            and fixture["prior"][ref["char_start"]:ref["char_end"]]
                            in offer.get("offer", {}).get("quotes", [])
                            for ref in offer.get("evidence_refs", []))
                        require(entry.get("prior_evidence_refs_verified") is verified,
                                "RUN87_B2_PRIOR_EVIDENCE_RED")
                        b2_prior_verified = verified
                native_calls += 1
            require(row.get("summary_saturation") == saturation
                    and row.get("b2_prior_evidence") is b2_prior_verified,
                    "RUN87_ROW_AGGREGATE_RED")
            if arm == "LONG_160":
                b2_long_evidence += int(b2_prior_verified)
    require(native_calls == 48
            and report.get("scores") == scores
            and report.get("b2_long_prior_evidence") == b2_long_evidence,
            "RUN87_AGGREGATE_SCORE_RED")
    expected = f.verdict(scores, b2_long_evidence)
    require(report.get("status") == expected, "RUN87_REGISTERED_VERDICT_RED")
    return {"status": "INDEPENDENT_RUN87_NATIVE_REPARSE_PASS",
            "diagnostic_result": expected,
            "scores": scores, "b2_long_prior_evidence": b2_long_evidence,
            "native_calls": 48,
            "claim_limit": "DISJOINT_SIX_PROJECT_BUDGET_ONLY_LINUX_NATIVE_SHADOW",
            "prior_context_causal_utility_proven": False,
            "step2_promoted": False, "delivery_authority": 0,
            "learning_authority": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    args = p.parse_args()
    print(json.dumps(verify(json.loads(args.report.read_text(encoding="utf-8"))),
                     sort_keys=True, indent=2))

if __name__ == "__main__":
    main()
