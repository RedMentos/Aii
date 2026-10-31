#!/usr/bin/env python3
"""Independent Run83 report reparse; no native execution or gate promotion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import jef_body_c3_interference_fixture_839 as f
from scripts.run83_jef_body_c3_interference_native import (
    SCHEMA, C3_MODEL)
from v13.common import dumps
from v13.jef_range_c3_typed_envelope_shadow import SYSTEM as TYPED_SYSTEM
from v13.jef_b1b2_c3_dual_source_shadow import SYSTEM as DUAL_SYSTEM


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def verify(report):
    _require(type(report) is dict
             and report.get("schema") == SCHEMA
             and report.get("seed") == f.SEED
             and report.get("table_sha256") == f.TABLE_SHA256
             and report.get("model_sha256_required") == f.MODEL_SHA256
             and report.get("model_sha256_observed") == f.MODEL_SHA256
             and report.get("runner_sha256_required") == f.RUNNER_SHA256
             and report.get("runner_sha256_observed") == f.RUNNER_SHA256
             and report.get("temperature") == 0.0
             and report.get("max_tokens") == 32,
             "RUN83_PIN_RED")
    _require(report.get("native_call_count") == 12
             and report.get("body_native_call_count") == 0
             and report.get("body_observations_synthetic") is True
             and report.get("typed_answer_visible_to_c3") is True
             and report.get("independent_reasoning_proven") is False
             and report.get("closed_store_ok") is True
             and report.get("no_live_output") is True
             and report.get("delivery_authority") == 0
             and report.get("learning_authority") == 0
             and report.get("tool_dispatches") == 0
             and report.get("output_committed") is False
             and report.get("tty_approved") is False
             and report.get("age0") == "RECORD_ONLY"
             and report.get("step2") == "UTILITY_FAIL"
             and report.get("b3") == "NO_PROMOTION"
             and report.get("body_jepa") == "UNAVAILABLE"
             and report.get("world_jepa") == "SHADOW"
             and report.get("jepa_weight") == 0
             and report.get("redmi_measured") is False
             and report.get("whole_system_complete") is False,
             "RUN83_AUTHORITY_RED")
    cases = report.get("cases")
    _require(type(cases) is list and len(cases) == 12,
             "RUN83_CASE_COUNT_RED")
    scores = {arm: 0 for arm in f.ARMS}
    for row in f.fixtures():
        for j, arm in enumerate(row["arm_order"]):
            case = cases[2 * row["index"] + j]
            _require(
                type(case) is dict
                and case.get("index") == row["index"]
                and case.get("arm") == arm
                and case.get("project_sha256")
                == f.sha(row["project"].encode())
                and case.get("expected") == row["expected"]
                and case.get("wrong_body_action")
                == row["wrong_body_action"]
                and case.get("source_sha256") == row["source_sha256"]
                and case.get("synthetic_body") is True
                and case.get("native_body") is False
                and case.get("typed_jef_action") == row["expected"]
                and case.get("native_final") is True
                and case.get("process_reaped") is True
                and case.get("post_source_rechecked") is True
                and case.get("actual_model") == C3_MODEL
                and case.get("status") == "RECORDED",
                "RUN83_CASE_BINDING_RED")
            messages = case.get("input_messages")
            _require(
                type(messages) is list and len(messages) == 2
                and messages[0] == {
                    "role": "system",
                    "content": (TYPED_SYSTEM if arm == "TYPED_ONLY"
                                else DUAL_SYSTEM)}
                and type(messages[1]) is dict
                and messages[1].get("role") == "user"
                and type(messages[1].get("content")) is str
                and case.get("input_sha256")
                == f.sha(dumps(messages).encode()),
                "RUN83_PROMPT_BINDING_RED")
            try:
                payload = json.loads(messages[1]["content"])
            except (TypeError, ValueError):
                raise ValueError("RUN83_PROMPT_JSON_RED") from None
            _require(type(payload) is dict
                     and payload.get("typed_jef_action")
                     == row["expected"]
                     and payload.get("human_source_lineage_verified") is True,
                     "RUN83_TYPED_ACTION_RED")
            if arm == "DUAL_SOURCE":
                observations = payload.get("body_observations")
                _require(
                    payload.get("body_hypotheses_are_facts") is False
                    and type(observations) is list
                    and [o.get("role") for o in observations
                         if type(o) is dict]
                    == ["B1_DETAIL", "B2_GIST"]
                    and len(observations) == 2
                    and all(type(o) is dict
                            and o.get("hypothesis_authority")
                            == "MODEL_HYPOTHESIS_NOT_FACT"
                            and row["wrong_body_action"]
                            in o.get("hypothesis", {}).get("summary", "")
                            for o in observations)
                    and payload.get("current_source", {}).get("text")
                    == row["current"],
                    "RUN83_BODY_HYPOTHESIS_RED")
            else:
                _require("body_observations" not in payload
                         and row["current"] not in dumps(messages),
                         "RUN83_TYPED_ONLY_LEAK_RED")
            output = case.get("output")
            _require(type(output) is str
                     and 0 < len(output.encode()) <= 1024
                     and case.get("output_bytes") == len(output.encode())
                     and case.get("output_sha256")
                     == f.sha(output.encode())
                     and case.get("parsed_action")
                     == f.prior.run68.decode_schema(output)
                     and case.get("strict")
                     == f.strict(output, row["expected"]),
                     "RUN83_OUTPUT_SCORE_RED")
            scores[arm] += case["strict"]
    _require(report.get("scores") == scores
             and report.get("status") == f.verdict(scores),
             "RUN83_VERDICT_RED")
    return {
        "status": "INDEPENDENT_RUN83_NATIVE_REPARSE_PASS",
        "registered_result": f.verdict(scores),
        "scores": scores,
        "native_c3_calls": 12,
        "synthetic_body_only": True,
        "claim_limit": "SMALL_SYNTHETIC_TYPED_ACTION_VISIBLE_FORMATTER_INTERFERENCE",
        "step2_promoted": False,
        "delivery_authority": 0,
        "learning_authority": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    result = verify(json.loads(args.report.read_text(encoding="utf-8")))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
