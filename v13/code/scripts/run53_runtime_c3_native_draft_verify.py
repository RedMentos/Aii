#!/usr/bin/env python3
"""Independent closed-report structural verifier for Run53 native DRAFT smoke."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from v13.common import dumps
from scripts.run51_f1f5_second_attempt_native import load_fixture, FIXTURE_SHA256
from scripts.run47_jef_c3_typed_receiver_native import NEGATIVE

C3_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def verify(report_path, fixture_path):
    fixture = load_fixture(fixture_path)["fixtures"][0]
    report = json.loads(Path(report_path).read_text())
    errors = []
    def require(ok, name):
        if not ok:
            errors.append(name)
    require(report.get("schema") == "v13.run53.runtime_c3_native_draft_report.v1", "schema")
    require(report.get("seed") == 467 and report.get("fixture_sha256") == FIXTURE_SHA256, "fixture_pin")
    require(report.get("claim") == "ORIGINAL_RUN51_CYPRESS_STRUCTURAL_REGRESSION_NOT_UTILITY", "claim")
    require(report.get("negative_gates") == NEGATIVE, "negative_gates")
    require(report.get("installed_binding_unchanged") is True, "model_binding_unchanged")
    binding = report.get("binding") or {}
    require((binding.get("model_sha256") or {}).get("C3_LANGUAGE") == C3_SHA, "c3_model_sha")
    require(binding.get("runner_sha256") == RUNNER_SHA, "runner_sha")
    rows = report.get("rows")
    require(type(rows) is list and len(rows) == 1, "row_count")
    if type(rows) is not list or len(rows) != 1:
        return {"status": "STRUCTURAL_RED", "errors": errors}
    row = rows[0]
    require((report.get("row_sha256") or {}).get("Cypress") == sha(dumps(row).encode()), "row_hash")
    require(row.get("fixture") == fixture["id"] == "Cypress", "fixture_id")
    require(row.get("schema") == "v13.run53.runtime_c3_native_draft_row.v1", "row_schema")
    require(row.get("status") == "RECORDED", "row_status")
    require(row.get("model_calls") == 1 and row.get("native_model") is True, "one_native_call")
    require(row.get("model_revision") == (binding.get("model_revisions") or {}).get("C3_LANGUAGE"), "revision")
    require((row.get("native_c3_metrics") or {}).get("status") == "FINAL", "native_final")
    require(row.get("processes_reaped") is True, "process_reaped")
    require((row.get("closed_store_audit") or {}).get("ok") is True, "closed_sqlite")
    require(row.get("no_live_output") is True and row.get("tool_dispatches") == 0
            and row.get("weight_updates") is False, "no_delivery_tools_learning")
    require(row.get("negative_gates") == NEGATIVE, "row_negative_gates")
    require((row.get("off_control") or {}).get("status") == "OFF"
            and (row.get("off_control") or {}).get("model_called") is False, "off_control")
    require((row.get("missing_correction_control") or {}).get("status") == "CLARIFY"
            and (row.get("missing_correction_control") or {}).get("model_called") is False, "missing_correction")
    for key, text in [("current_source_ref", fixture["followup"]),
                      ("correction_source_ref", fixture["correction_event"])]:
        ref = row.get(key) or {}
        require(ref.get("sha256") == sha(text.encode())
                and ref.get("char_start") == 0
                and ref.get("char_end") == len(text), key)
    prompt = row.get("native_prompt")
    require(type(prompt) is list and len(prompt) >= 2, "native_prompt")
    if type(prompt) is list:
        require(row.get("native_prompt_sha256") == sha(dumps(prompt).encode()), "prompt_sha")
        flat = dumps(prompt)
        require(fixture["value"] in flat and "Cypress" in flat, "source_backed_prompt")
    staged = row.get("draft_result") or {}
    require(staged.get("status") == "RUNTIME_C3_DRAFT_BOUND_SHADOW_NO_COMMIT"
            and staged.get("model_called") is True
            and staged.get("runner_released") is True
            and staged.get("delivery_authority") == 0
            and staged.get("output_committed") is False
            and staged.get("native_proof") is False, "staged_no_authority")
    draft = row.get("draft_row") or {}
    answer = row.get("native_answer")
    require(type(answer) is str and bool(answer.strip()), "nonempty_answer")
    if type(answer) is str:
        require(row.get("native_answer_sha256") == sha(answer.encode())
                and staged.get("candidate_sha256") == sha(answer.encode()), "answer_digest")
    require(draft.get("text") == answer and draft.get("status") == "DRAFT"
            and draft.get("role") == "assistant"
            and draft.get("event_id") == row.get("current_event_id")
            and draft.get("session_id") == row.get("session_id")
            and draft.get("id") == staged.get("draft_message_id"), "draft_binding")
    try:
        meta = json.loads(draft.get("metadata", ""))
        require(meta.get("shadow") is True
                and meta.get("candidate_sha256") == staged.get("candidate_sha256"), "draft_metadata")
    except Exception:
        errors.append("draft_metadata_json")
    action = row.get("c5_action") or {}
    require(row.get("action_count") == 1 and row.get("draft_count") == 1
            and action.get("id") == staged.get("c5_action_id")
            and action.get("event_id") == row.get("current_event_id")
            and action.get("kind") == "TEXT_REPORT"
            and action.get("status") == "DISPATCHED", "c5_action")
    packets = row.get("c5_packets")
    require(type(packets) is list and len(packets) == 2, "two_c5_packets")
    if type(packets) is list and len(packets) == 2:
        require({p.get("kind") for p in packets} == {"ActionIntent", "CorollaryCopy"}, "packet_kinds")
        for p in packets:
            try:
                payload = json.loads(p["payload"])
                require(payload.get("action_id") == staged.get("c5_action_id")
                        and payload.get("event_id") == row.get("current_event_id")
                        and payload.get("packet_id") == p.get("id"), "packet_binding")
            except Exception:
                errors.append("packet_json")
    require(report.get("status") == "NATIVE_DRAFT_STRUCTURAL_ONLY", "report_status")
    return {"status": "STRUCTURAL_PASS" if not errors else "STRUCTURAL_RED",
            "errors": errors, "claim": "SINGLE_ORIGINAL_CYPRESS_NATIVE_DRAFT_NO_UTILITY_PROMOTION"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    result = verify(args.report, args.fixture)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "STRUCTURAL_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
