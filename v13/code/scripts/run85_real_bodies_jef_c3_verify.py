#!/usr/bin/env python3
"""Independent Run85 original native report verifier (structural only).

A historical one-case engineering replay cannot promote scientific utility.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import jef_body_c3_interference_fixture_839 as f
from scripts.run85_real_bodies_jef_c3_native import SCHEMA, MODELS
from v13.common import dumps
from v13.jef_c3_schema_draft_candidate import decode_action
from v13.jef_b1b2_c3_postgen_shadow import STATUS as GUARD_MATCH


def require(ok, code):
    if not ok:
        raise ValueError(code)


def verify(r):
    row = f.fixtures()[0]
    require(type(r) is dict and r.get("schema") == SCHEMA
            and r.get("seed") == f.SEED
            and r.get("table_sha256") == f.TABLE_SHA256
            and r.get("fixture_index") == 0
            and r.get("project_sha256") == f.sha(row["project"].encode())
            and r.get("source_sha256") == row["source_sha256"]
            and r.get("expected") == row["expected"],
            "RUN85_FIXTURE_PIN_RED")
    require(r.get("runner_sha256_required") == f.RUNNER_SHA256
            and r.get("runner_sha256_observed") == f.RUNNER_SHA256
            and r.get("models_required") == {
                role: {"file": name, "sha256": digest}
                for role, (name, digest) in MODELS.items()}
            and r.get("models_observed") == {
                role: {"file": name, "sha256": digest}
                for role, (name, digest) in MODELS.items()},
            "RUN85_NATIVE_MODEL_PIN_RED")
    require(r.get("age0") == "RECORD_ONLY"
            and r.get("step2") == "UTILITY_FAIL"
            and r.get("b3") == "NO_PROMOTION"
            and r.get("body_jepa") == "UNAVAILABLE"
            and r.get("world_jepa") == "SHADOW"
            and r.get("jepa_weight") == 0
            and r.get("redmi_measured") is False
            and r.get("whole_system_complete") is False
            and r.get("delivery_authority") == 0
            and r.get("learning_authority") == 0
            and r.get("tool_dispatches") == 0
            and r.get("tty_approved") is False
            and r.get("output_committed") is False
            and r.get("independent_reasoning_proven") is False,
            "RUN85_AUTHORITY_RED")
    require(r.get("native_body") is True
            and r.get("native_body_calls") == 2
            and r.get("native_c3_calls") == 2
            and r.get("no_live_output") is True
            and r.get("closed_store_ok") is True,
            "RUN85_NATIVE_STRUCTURE_RED")
    offers = r.get("body_offers")
    captures = r.get("body_captures")
    require(type(offers) is list and len(offers) == 2
            and type(captures) is dict and set(captures) == set(MODELS)-{"C3_LANGUAGE"},
            "RUN85_NATIVE_BODIES_RED")
    for i, role in enumerate(("B1_DETAIL", "B2_GIST")):
        entry = offers[i]
        offer = entry.get("offer")
        query = entry.get("query")
        cap = captures[role]
        require(entry.get("role") == role
                and entry.get("status") == "RECORDED"
                and entry.get("process_reaped") is True
                and type(offer) is dict
                and offer.get("role") == role
                and offer.get("packet_id") == entry.get("offer_packet_id")
                and offer.get("query_packet_id") == entry.get("query_packet_id")
                and type(query) is dict
                and query.get("packet_id") == entry.get("query_packet_id")
                and offer.get("native_metrics", {}).get("status") == "FINAL"
                and offer.get("native_metrics", {}).get("actual_model")
                == MODELS[role][0]
                and type(cap) is dict
                and cap.get("messages_sha256")
                == f.sha(dumps(cap.get("messages")).encode()),
                "RUN85_NATIVE_BODY_BINDING_RED")
    cases = r.get("c3")
    require(type(cases) is list and len(cases) == 2
            and [x.get("arm") for x in cases] == ["TYPED_ONLY", "DUAL_SOURCE"],
            "RUN85_C3_ARM_ORDER_RED")
    for c in cases:
        output = c.get("output")
        require(c.get("status") == "RECORDED"
                and c.get("native_final") is True
                and c.get("process_reaped") is True
                and c.get("post_source_rechecked") is True
                and c.get("actual_model") == MODELS["C3_LANGUAGE"][0]
                and c.get("expected") == row["expected"]
                and c.get("input_sha256")
                == f.sha(dumps(c.get("input_messages")).encode())
                and type(output) is str
                and 0 < len(output.encode()) <= 1024
                and c.get("output_sha256") == f.sha(output.encode())
                and c.get("output_bytes") == len(output.encode())
                and c.get("parsed_action") == f.prior.run68.decode_schema(output)
                and c.get("strict") == f.strict(output, row["expected"]),
                "RUN85_NATIVE_C3_BINDING_RED")
        if c["arm"] == "DUAL_SOURCE":
            g = c.get("postgen_guard")
            expected_status = (GUARD_MATCH if decode_action(output) == row["expected"]
                               else "FORMATTER_JSON_RED" if decode_action(output) is None
                               else "FORMATTER_ACTION_MISMATCH_RED")
            require(type(g) is dict
                    and g.get("status") == expected_status
                    and g.get("callback_invoked") is True
                    and g.get("source_rechecked") is True
                    and g.get("messages_sha256") == c["input_sha256"]
                    and g.get("typed_jef_action") == row["expected"]
                    and g.get("delivery_authority") == 0
                    and g.get("learning_authority") == 0
                    and g.get("output_committed") is False,
                    "RUN85_POSTGEN_GUARD_RED")
    releases = r.get("process_releases")
    require(type(releases) is list
            and sum(x.get("before") is not None for x in releases) >= 4
            and all(x.get("process_reaped") is True for x in releases),
            "RUN85_PROCESS_RELEASE_RED")
    expected = (
        "REAL_BODIES_JEF_C3_STRUCTURAL_PASS_FORMATTER_MATCH"
        if all(c["strict"] == 1 for c in cases)
        else "REAL_BODIES_JEF_C3_STRUCTURAL_PASS_FORMATTER_RED")
    require(r.get("status") == expected, "RUN85_VERDICT_RED")
    return {"status": "RUN85_INDEPENDENT_NATIVE_ENGINEERING_REPARSE_PASS",
            "native_body_calls": 2, "native_c3_calls": 2,
            "diagnostic_result": expected,
            "science": "HISTORICAL_FIXTURE_ENGINEERING_ONLY",
            "step2_promoted": False, "delivery_authority": 0,
            "learning_authority": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    a = p.parse_args()
    print(json.dumps(verify(json.loads(a.report.read_text(encoding="utf-8"))),
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
