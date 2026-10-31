#!/usr/bin/env python3
"""Run75 independent raw native C3 formatter reparse, never a gate promoter."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import jef_range_native_fixture_773 as f
from v13.common import dumps
from v13.jef_range_c3_typed_envelope_shadow import SYSTEM

REPORT_SCHEMA = "v13.run75.jef_range_c3_native_formatter.v1"
EXPECTED_MODEL = "LFM2.5-350M-QAD-Q4_0.gguf"
PAYLOAD_KEYS = {
    "typed_jef_action", "human_source_lineage_verified",
    "source_ref_sha256", "current_source_ref_sha256",
    "rule_parser_revision",
}


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_PROMPT_KEY")
        out[key] = value
    return out


def verify(report):
    if type(report) is not dict:
        raise ValueError("RUN75_REPORT_TYPE_RED")
    if (report.get("schema") != REPORT_SCHEMA
            or report.get("seed") != f.SEED
            or report.get("temperature") != 0.0
            or report.get("max_tokens") != 32
            or report.get("table_sha256") != f.TABLE_SHA256
            or report.get("model_sha256_required") != f.MODEL_SHA256
            or report.get("runner_sha256_required") != f.RUNNER_SHA256
            or report.get("model_sha256_observed") != f.MODEL_SHA256
            or report.get("runner_sha256_observed") != f.RUNNER_SHA256
            or report.get("formatter_only") is not True
            or report.get("typed_answer_visible") is not True
            or report.get("independent_source_reasoning_proven") is not False
            or report.get("native_call_count") != 6
            or report.get("closed_store_ok") is not True
            or report.get("no_live_output") is not True
            or report.get("delivery_authority") != 0
            or report.get("tool_dispatches") != 0
            or report.get("learning_authority") != 0
            or report.get("tty_approved") is not False
            or report.get("output_committed") is not False
            or report.get("age0") != "RECORD_ONLY"
            or report.get("step2") != "UTILITY_FAIL"
            or report.get("b3") != "NO_PROMOTION"
            or report.get("body_jepa") != "UNAVAILABLE"
            or report.get("world_jepa") != "SHADOW"
            or report.get("jepa_weight") != 0
            or report.get("redmi_measured") is not False
            or report.get("whole_system_complete") is not False):
        raise ValueError("RUN75_BOUNDARY_RED")
    rows = f.fixtures()
    cases = report.get("cases")
    if type(cases) is not list or len(cases) != 6:
        raise ValueError("RUN75_CASE_COUNT_RED")
    score = 0
    for row, case in zip(rows, cases):
        if (type(case) is not dict
                or case.get("index") != row["index"]
                or case.get("project_sha256") != f.sha(row["project"].encode())
                or case.get("expected") != row["expected"]
                or case.get("typed_jef_action") != row["expected"]
                or case.get("source_sha256") != {
                    k: f.sha(row[k].encode("utf-8"))
                    for k in ("current", "policy_source", "sheet_source")}
                or case.get("native_final") is not True
                or case.get("process_reaped") is not True
                or case.get("post_source_rechecked") is not True
                or case.get("actual_model") != EXPECTED_MODEL
                or case.get("status") != "RECORDED"):
            raise ValueError("RUN75_CASE_BINDING_RED")
        messages = case.get("input_messages")
        if (type(messages) is not list or len(messages) != 2
                or messages[0] != {"role": "system", "content": SYSTEM}
                or type(messages[1]) is not dict
                or set(messages[1]) != {"role", "content"}
                or messages[1]["role"] != "user"
                or type(messages[1]["content"]) is not str
                or case.get("input_sha256") != f.sha(dumps(messages).encode())):
            raise ValueError("RUN75_PROMPT_BOUNDARY_RED")
        try:
            payload = json.loads(messages[1]["content"],
                                 object_pairs_hook=_unique)
        except (ValueError, TypeError):
            raise ValueError("RUN75_PROMPT_JSON_RED") from None
        if (type(payload) is not dict or set(payload) != PAYLOAD_KEYS
                or payload["typed_jef_action"] != row["expected"]
                or payload["human_source_lineage_verified"] is not True
                or payload["rule_parser_revision"]
                != "jef-mixed-range-policy-shadow-run73-v1"
                or type(payload["source_ref_sha256"]) is not list
                or len(payload["source_ref_sha256"]) != 2
                or any(type(h) is not str or len(h) != 64
                       for h in payload["source_ref_sha256"])
                or type(payload["current_source_ref_sha256"]) is not str
                or len(payload["current_source_ref_sha256"]) != 64
                or any(row[k] in dumps(messages)
                       for k in ("current", "policy_source", "sheet_source"))):
            raise ValueError("RUN75_PROMPT_SOURCE_RED")
        output = case.get("output")
        if (type(output) is not str
                or not 0 < len(output.encode("utf-8")) <= 1024
                or case.get("output_bytes") != len(output.encode("utf-8"))
                or case.get("output_sha256") != f.sha(output.encode("utf-8"))
                or case.get("parsed_action") != f.run68.decode_schema(output)
                or case.get("strict") != f.score(output, row["expected"])):
            raise ValueError("RUN75_NATIVE_OUTPUT_RED")
        score += case["strict"]
    if report.get("strict") != score:
        raise ValueError("RUN75_SCORE_REPARSE_RED")
    status = ("FORMATTER_SMALL_SYNTHETIC_PASS"
              if score == 6 else "FORMATTER_FIDELITY_RED")
    if report.get("status") != status:
        raise ValueError("RUN75_STATUS_REPARSE_RED")
    return {
        "status": "INDEPENDENT_RUN75_NATIVE_REPARSE_PASS",
        "registered_result": status, "strict": score,
        "native_calls": 6,
        "claim_limit": "TYPED_ACTION_VISIBLE_FORMATTER_ONLY_SIX_SYNTHETIC",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    args = p.parse_args()
    print(json.dumps(verify(json.loads(
        args.report.read_text(encoding="utf-8"))), sort_keys=True))


if __name__ == "__main__":
    main()
