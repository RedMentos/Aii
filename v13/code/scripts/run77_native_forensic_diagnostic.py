#!/usr/bin/env python3
"""Read-only first-failure diagnosis for frozen Run77 native report.

Engineering forensics only: original seed797, scorer, native runner and
verifier remain immutable. Never converts scientific RED to PASS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import jef_b1b2_context_fixture_797 as f
from scripts import run77_b1b2_context_verify as original
from v13.common import dumps

SCHEMA = "v13.run77.forensic_diagnostic.v1"
MAX_FINDINGS = 30


def diagnose(report):
    findings = []

    def issue(code, row=None, role=None, phase=None):
        if len(findings) < MAX_FINDINGS:
            findings.append({"code": code, "row": row,
                             "role": role, "phase": phase})

    if type(report) is not dict:
        return {"schema": SCHEMA, "status": "FORENSIC_INPUT_RED",
                "findings": [{"code": "REPORT_NOT_DICT"}]}
    if report.get("schema") != original.SCHEMA or report.get("seed") != f.SEED:
        issue("HEADER_PIN_RED")
    if report.get("table_sha256") != f.TABLE_SHA256:
        issue("TABLE_HASH_RED")
    binding = report.get("binding") or {}
    if (type(binding) is not dict
            or binding.get("model_sha256", {}).get("B1_DETAIL") != f.B1_SHA256
            or binding.get("model_sha256", {}).get("B2_GIST") != f.B2_SHA256
            or binding.get("runner_sha256") != f.RUNNER_SHA256):
        issue("MODEL_OR_RUNNER_PIN_RED")
    rows = report.get("rows")
    if type(rows) is not list:
        issue("ROWS_NOT_LIST")
        rows = []
    if len(rows) != 12:
        issue("ROW_COUNT_RED")
    scores = {role: {arm: 0 for arm in f.ARMS} for role in f.ROLES}
    b2_evidence = 0
    call_count = 0
    for i, fixture in enumerate(f.fixtures()):
        for j, arm in enumerate(f.ARMS):
            index = i * 2 + j
            if index >= len(rows):
                issue("ROW_MISSING", index)
                continue
            row = rows[index]
            if type(row) is not dict:
                issue("ROW_NOT_DICT", index)
                continue
            expected_count = 4 if arm == "WITH_PRIOR" else 2
            if (row.get("project") != fixture["project"]
                    or row.get("arm") != arm):
                issue("ROW_IDENTITY_RED", index)
            if row.get("status") != "RECORDED":
                issue("ROW_STATUS_RED", index)
            if row.get("source_sha256") != fixture["source_sha256"]:
                issue("ROW_SOURCE_HASH_RED", index)
            if (row.get("closed_store_ok") is not True
                    or row.get("processes_reaped") is not True
                    or row.get("no_live_output") is not True):
                issue("ROW_LIFECYCLE_RED", index)
            if row.get("native_call_count") != expected_count:
                issue("ROW_CALL_COUNT_RED", index)
            entries = row.get("offers")
            if type(entries) is not list:
                issue("OFFERS_NOT_LIST", index)
                continue
            if len(entries) != expected_count:
                issue("OFFER_COUNT_RED", index)
            expected_seq = ([(role, "prior") for role in f.ROLES]
                            if arm == "WITH_PRIOR" else [])
            expected_seq += [(role, "current") for role in f.ROLES]
            if [(e.get("role"), e.get("phase"))
                    for e in entries if type(e) is dict] != expected_seq:
                issue("OFFER_ORDER_RED", index)
            current = row.get("current_source_ref")
            prior = row.get("prior_source_ref")
            if (type(current) is not dict
                    or current.get("sha256") != fixture["source_sha256"]["current"]):
                issue("CURRENT_REF_RED", index)
            if arm == "WITH_PRIOR":
                if (type(prior) is not dict
                        or prior.get("sha256") != fixture["source_sha256"]["prior"]):
                    issue("PRIOR_REF_RED", index)
            elif prior is not None:
                issue("ABLATION_PRIOR_LEAK_RED", index)
            for entry in entries:
                if type(entry) is not dict:
                    issue("OFFER_NOT_DICT", index)
                    continue
                call_count += 1
                role, phase = entry.get("role"), entry.get("phase")
                expected = prior if phase == "prior" else current
                offer, query = entry.get("offer"), entry.get("query")
                if (entry.get("status") != "RECORDED"
                        or entry.get("guarded_status")
                        != "SHADOW_LATEST_USER_OFFER_PRODUCED"
                        or entry.get("process_reaped") is not True):
                    issue("ENTRY_STATUS_OR_RELEASE_RED", index, role, phase)
                if entry.get("source_ref") != expected:
                    issue("ENTRY_SOURCE_REF_RED", index, role, phase)
                if type(offer) is not dict or type(query) is not dict:
                    issue("PACKET_MISSING", index, role, phase)
                    continue
                if (offer.get("event_id") != entry.get("event_id")
                        or query.get("event_id") != entry.get("event_id")
                        or offer.get("role") != role
                        or query.get("target_role") != role
                        or query.get("source_refs") != [expected]):
                    issue("PACKET_BINDING_RED", index, role, phase)
                metrics = offer.get("native_metrics") or {}
                if (metrics.get("status") != "FINAL"
                        or metrics.get("actual_model") != original.MODELS.get(role)):
                    issue("NATIVE_METRICS_RED", index, role, phase)
                capture = (row.get("captures") or {}).get(str(role) + ":" + str(phase))
                if (type(capture) is not dict
                        or capture.get("messages_sha256")
                        != f.sha(dumps(capture.get("messages")).encode())):
                    issue("PROMPT_CAPTURE_RED", index, role, phase)
                context_refs = query.get("context_source_refs")
                wanted = [prior] if phase == "current" and arm == "WITH_PRIOR" else []
                if context_refs != wanted:
                    issue("CONTEXT_TRANSPORT_RED", index, role, phase)
                if phase != "current":
                    continue
                summary = (offer.get("offer") or {}).get("summary")
                strict = f.strict_summary(summary, fixture["action"], fixture["remaining"])
                if (entry.get("summary") != summary
                        or entry.get("strict") != strict
                        or entry.get("context_source_refs_verified") is not True):
                    issue("SEMANTIC_SCORE_RECORD_RED", index, role, phase)
                if role in scores:
                    scores[role][arm] += strict
                if role == "B2_GIST" and arm == "WITH_PRIOR" and type(prior) is dict:
                    verified = any(
                        type(ref) is dict
                        and ref.get("source_id") == prior.get("source_id")
                        and ref.get("sha256") == fixture["source_sha256"]["prior"]
                        and type(ref.get("char_start")) is int
                        and type(ref.get("char_end")) is int
                        and 0 <= ref["char_start"] < ref["char_end"] <= len(fixture["prior"])
                        and fixture["prior"][ref["char_start"]:ref["char_end"]]
                        in (offer.get("offer") or {}).get("quotes", [])
                        for ref in offer.get("evidence_refs", []))
                    b2_evidence += int(verified)
                    if entry.get("prior_evidence_refs_verified") is not verified:
                        issue("B2_EVIDENCE_PREDICATE_DIVERGENCE", index, role, phase)
    if call_count != report.get("native_call_count") or call_count != 36:
        issue("TOTAL_NATIVE_COUNT_RED")
    if report.get("scores") != scores:
        issue("AGGREGATE_SCORES_RED")
    if report.get("b2_prior_evidence") != b2_evidence:
        issue("AGGREGATE_B2_EVIDENCE_RED")
    try:
        original_result = original.verify(report)
        original_status = original_result["status"]
        original_error = None
    except Exception as exc:
        original_status = "ORIGINAL_VERIFIER_RED"
        original_error = type(exc).__name__ + ":" + str(exc)[:100]
    if original_error and not findings:
        issue("UNCLASSIFIED_ORIGINAL_VERIFIER_RED")
    return {
        "schema": SCHEMA, "status": original_status,
        "original_error": original_error,
        "original_scientific_status": report.get("status"),
        "native_calls_observed": call_count,
        "registered_calls": 36,
        "findings": findings,
        "diagnostic_only": True,
        "production_authority": 0,
        "learning_authority": 0,
        "step2_promoted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = diagnose(json.loads(args.report.read_text(encoding="utf-8")))
    content = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.write_text(content, encoding="utf-8")
    print(content, end="")
    # Diagnostic execution is successful even if the original verifier is RED.
    # A separate workflow receipt preserves original verifier's exit status.


if __name__ == "__main__":
    main()
