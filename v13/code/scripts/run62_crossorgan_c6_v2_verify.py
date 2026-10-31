#!/usr/bin/env python3
"""Independent Run62 five-call B1/B2 C3 F1/F5 C5/C6 DRAFT SHADOW verifier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from v13.common import dumps
from scripts.run51_f1f5_second_attempt_native import load_fixture, FIXTURE_SHA256
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
    fixture = next(f for f in data["fixtures"] if f["id"] == "Cypress")
    report = json.loads(Path(report_path).read_text())
    errors = []

    def require(ok, reason):
        if not ok:
            errors.append(reason)

    require(report.get("schema") == "v13.run62.crossorgan_c6_v2_native_report.v1", "schema")
    require(report.get("seed") == 467 and report.get("fixture_sha256") == FIXTURE_SHA256,
            "fixture_pin")
    require(report.get("claim") == "ORIGINAL_RUN51_CYPRESS_RUN62_C6_V2_ENGINEERING_SHADOW_NOT_UTILITY",
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
    require((report.get("row_sha256") or {}).get("Cypress")
            == sha(dumps(row).encode("utf-8")), "row_sha")
    require(row.get("schema") == "v13.run62.crossorgan_c6_v2_native_row.v1", "row_schema")
    require(row.get("negative_gates") == NEGATIVE
            and row.get("semantic_utility_claim") is False, "negative_gates_row")
    require(row.get("tty_approved") is False
            and row.get("output_committed") is False
            and row.get("tool_dispatches") == 0
            and row.get("learning_authority") == 0
            and row.get("no_live_output") is True,
            "no_live_output_or_approval")
    require(row.get("native_model") is True
            and row.get("native_process_count", 0) >= 5
            and row.get("processes_reaped") is True
            and (row.get("closed_store_audit") or {}).get("ok") is True,
            "native_process_sqlite")
    events = row.get("source_events") or {}
    for phase, text in (("correction", fixture["correction_event"]),
                        ("current", fixture["followup"])):
        e = events.get(phase) or {}
        ref = e.get("source_ref") or {}
        require(e.get("text_sha256") == sha(text.encode())
                and ref.get("sha256") == sha(text.encode())
                and ref.get("char_start") == 0
                and ref.get("char_end") == len(text), "source_" + phase)
    offers = row.get("body_offers")
    require(type(offers) is list and len(offers) == 4, "body_offer_count")
    if type(offers) is not list or len(offers) != 4:
        return {"status": "STRUCTURAL_RED", "errors": errors}
    by_key = {(x.get("role"),x.get("phase")):x for x in offers}
    require(len(by_key) == 4, "body_role_phase_unique")
    captures = row.get("body_captures") or {}
    for role in ("B1_DETAIL","B2_GIST"):
        for phase in ("correction","current"):
            e = by_key.get((role,phase)) or {}
            label = role+"_"+phase
            offer = e.get("offer") or {}
            query = e.get("query") or {}
            require(e.get("event_id") == (events.get(phase) or {}).get("event_id")
                    and offer.get("event_id") == e.get("event_id")
                    and offer.get("role") == role
                    and offer.get("query_packet_id") == query.get("packet_id")
                    and query.get("target_role") == role
                    and (offer.get("provenance") or [None])[0]
                    == (events.get(phase) or {}).get("source_ref"),
                    "offer_query_binding_"+label)
            metrics = offer.get("native_metrics") or {}
            require(metrics.get("status") == "FINAL"
                    and metrics.get("actual_model") == PINS[role][1],
                    "native_body_"+label)
            expected = [] if phase=="correction" else [
                (events.get("correction") or {}).get("source_ref",{}).get("source_id")]
            require([x.get("source_id") for x in query.get("context_source_refs",[])]
                    == expected, "context_"+label)
            capture = captures.get(e.get("capture_key")) or {}
            messages = capture.get("messages") or []
            require(len(messages)==2 and capture.get("messages_sha256")
                    == sha(dumps(messages).encode()) if messages else False,
                    "body_prompt_"+label)
        first = by_key.get((role,"correction")) or {}
        second = by_key.get((role,"current")) or {}
        require(first.get("partition_key_sha256")
                == second.get("partition_key_sha256")
                and len(str(first.get("partition_key_sha256",""))) == 64,
                "partition_resume_"+role)
    c3 = row.get("c3") or {}
    metrics = c3.get("native_metrics") or {}
    require(metrics.get("status") == "FINAL"
            and metrics.get("actual_model") == PINS["C3_LANGUAGE"][1],
            "native_c3")
    require(type(c3.get("output_sha256")) is str
            and len(c3["output_sha256"]) == 64
            and type(c3.get("output_bytes")) is int and c3["output_bytes"] > 0
            and c3.get("candidate_text_stored") is False
            and "output_text" not in c3, "c3_digest_only")
    messages = c3.get("input_messages") or []
    require(len(messages)==2 and c3.get("input_sha256")
            == sha(dumps(messages).encode()) if messages else False,
            "c3_input_sha")
    if len(messages)==2:
        try:
            system, user = messages[0]["content"], messages[1]["content"]
            require("Verified user correction" in system
                    and "64 Euro" in system, "f1f5_verified_correction")
            body = json.loads(user.split("\n\n",1)[1])
            require(body["current_source"]["text"] == fixture["followup"]
                    and body["body_hypotheses_are_facts"] is False
                    and body["evidence_policy"]
                    == "CURRENT_USER_SOURCE_AND_EXACT_QUOTES_ONLY",
                    "c3_body_envelope")
            require([x["role"] for x in body["body_observations"]]
                    == ["B1_DETAIL","B2_GIST"], "c3_body_roles")
        except Exception:
            errors.append("c3_fused_prompt_parse")
    cross = row.get("crossorgan") or {}
    require(cross.get("delivery_authority") == 0
            and cross.get("output_committed") is False
            and cross.get("tool_dispatches") == 0
            and cross.get("learning_authority") == 0
            and cross.get("native_proof") is False,
            "crossorgan_authority")
    require(row.get("draft_status") == "DRAFT", "draft_only")
    if report.get("status") == "C6_V2_PREFLIGHT_ONLY_NO_APPROVAL":
        require(row.get("status") == "RECORDED_C6_V2_PREFLIGHT_ONLY"
                and cross.get("status") == "RUN61_C6_V2_PREFLIGHT_ONLY_NEEDS_REAL_TTY"
                and cross.get("c6_status") == "NEEDS_REAL_TTY_APPROVAL"
                and type(cross.get("c6_fingerprint_sha256")) is str
                and len(cross["c6_fingerprint_sha256"]) == 64,
                "c6_preflight_only")
    elif report.get("status") == "C6_V2_GROUNDING_RED":
        require(row.get("status") == "RECORDED_C6_V2_GROUNDING_RED"
                and cross.get("status") == "RUN61_C6_V2_GROUNDING_RED"
                and cross.get("c6_status") != "NEEDS_REAL_TTY_APPROVAL"
                and cross.get("c6_fingerprint_sha256") is None,
                "c6_grounding_red")
    else:
        errors.append("report_status")
    status = ("STRUCTURAL_RED" if errors else
              "C6_V2_GROUNDING_RED" if report.get("status") == "C6_V2_GROUNDING_RED"
              else "STRUCTURAL_PASS_PREFLIGHT_ONLY")
    return {"status": status, "errors": errors,
            "claim": "ORIGINAL_RUN51_CYPRESS_RUN62_C6_V2_ENGINEERING_SHADOW_NOT_UTILITY"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args()
    result = verify(a.report, a.fixture)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "STRUCTURAL_PASS_PREFLIGHT_ONLY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
