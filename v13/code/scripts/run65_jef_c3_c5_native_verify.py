#!/usr/bin/env python3
"""Independent Run65 three-call native source-only DRAFT structural verifier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from v13.common import dumps
from scripts import p2x_disjoint_receiver_trainset as p2x
from scripts.run63_jef_c3_native import C3_SHA256, RUNNER_SHA256, cohort
from scripts.run47_jef_c3_typed_receiver_native import NEGATIVE


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(path):
    report = json.loads(Path(path).read_text())
    errors = []

    def need(ok, label):
        if not ok:
            errors.append(label)

    need(report.get("schema") == "v13.run65.jef_c3_c5_native_report.v1",
         "schema")
    need(report.get("seed") == p2x.SEED
         and report.get("model_seed") == 13, "seeds")
    need(report.get("claim")
         == "P2X_CALIBRATION_C3_C5_C6_STRUCTURAL_NOT_DISJOINT_UTILITY",
         "claim")
    need(report.get("negative_gates") == NEGATIVE, "negative_gates")
    binding = report.get("binding") or {}
    need((binding.get("model_sha256") or {}).get("C3_LANGUAGE")
         == C3_SHA256 and binding.get("runner_sha256") == RUNNER_SHA256
         and report.get("installed_binding_unchanged") is True, "binding")
    fixtures = cohort()
    need(report.get("selected_ids") == [r["id"] for r in fixtures], "cohort")
    rows = report.get("rows")
    if type(rows) is not list or len(rows) != 3:
        return {"status": "STRUCTURAL_RED", "errors": errors+["row_count"]}
    strict_count = fallback_count = 0
    for i, (fixture, row) in enumerate(zip(fixtures, rows)):
        need((report.get("row_sha256") or {}).get(fixture["id"])
             == sha(dumps(row).encode("utf-8")), "row_hash_"+str(i))
        need(row.get("schema") == "v13.run65.jef_c3_c5_native_row.v1"
             and row.get("id") == fixture["id"]
             and row.get("oracle_action") == fixture["oracle_action"],
             "identity_"+str(i))
        need(row.get("source_sha256") == {
            k: sha(fixture[k].encode("utf-8"))
            for k in ("current", "b1_source", "b2_source")},
            "source_"+str(i))
        refs = row.get("source_refs") or {}
        for name, field in (("current", "current"), ("policy", "b2_source"),
                            ("sheet", "b1_source")):
            ref = refs.get(name) or {}
            need(ref.get("sha256") == sha(fixture[field].encode("utf-8"))
                 and ref.get("char_start") == 0
                 and ref.get("char_end") == len(fixture[field])
                 and ref.get("modality") == "text",
                 "ref_"+name+"_"+str(i))
        need(len({(refs.get(k) or {}).get("source_id")
                  for k in ("current", "policy", "sheet")}) == 3,
             "distinct_refs_"+str(i))
        messages = row.get("input_messages")
        need(type(messages) is list and len(messages) == 2
             and row.get("input_sha256")
             == sha(dumps(messages).encode("utf-8")) if type(messages) is list
             else False, "prompt_hash_"+str(i))
        if type(messages) is list and len(messages) == 2:
            try:
                need([m["role"] for m in messages] == ["system", "user"],
                     "roles_"+str(i))
                payload = json.loads(messages[1]["content"])
                need(payload.get("current_source") == fixture["current"]
                     and payload.get("policy_source") == fixture["b2_source"]
                     and payload.get("sheet_source") == fixture["b1_source"]
                     and payload.get("typed_jef_action")
                     == fixture["oracle_action"]
                     and len(payload.get("source_ref_sha256", [])) == 2
                     and payload.get("candidate_authority") == 0
                     and "oracle_action" not in payload and "oracle" not in payload,
                     "typed_sources_"+str(i))
            except Exception:
                errors.append("prompt_parse_"+str(i))
        need(row.get("typed_jef_action") == fixture["oracle_action"],
             "jef_action_"+str(i))
        output = row.get("native_output")
        need(type(output) is str
             and row.get("output_sha256") == sha(output.encode("utf-8"))
             if type(output) is str else False, "output_hash_"+str(i))
        correct = int(type(output) is str
                      and output in ("A", "B", "NONE")
                      and output == fixture["oracle_action"])
        strict_count += correct
        fallback_count += 1-correct
        need(row.get("native_strict_correct") == correct
             and row.get("source_only_fallback") is (not bool(correct)),
             "frozen_strict_"+str(i))
        metrics = row.get("native_metrics") or {}
        need(row.get("native_c3_final") is True
             and metrics.get("status") == "FINAL"
             and metrics.get("actual_model")
             == "LFM2.5-350M-QAD-Q4_0.gguf", "native_model_"+str(i))
        need(row.get("native_process_count", 0) >= 1
             and row.get("processes_reaped") is True
             and bool(row.get("process_releases"))
             and all(x.get("process_reaped") is True
                     for x in row.get("process_releases", [])),
             "processes_"+str(i))
        staged = row.get("staged") or {}
        expected_formatter = ("FORMATTER_MATCH_SHADOW" if correct
                              else "FORMATTER_MISMATCH_RED")
        expected_origin = ("MODEL_EXACT_SHADOW" if correct
                           else "SOURCE_ONLY_FALLBACK_C3_RED")
        need(staged.get("status") == "JEF_C5_SOURCE_ONLY_DRAFT_STAGED_SHADOW"
             and staged.get("source_action") == fixture["oracle_action"]
             and staged.get("candidate_sha256")
             == sha(fixture["oracle_action"].encode("utf-8"))
             and staged.get("candidate_bytes")
             == len(fixture["oracle_action"].encode("utf-8"))
             and staged.get("model_formatter_status") == expected_formatter
             and staged.get("draft_origin") == expected_origin
             and staged.get("source_only_fallback") is (not bool(correct))
             and staged.get("c3_receiver_success") is False
             and staged.get("delivery_authority") == 0
             and staged.get("output_committed") is False
             and staged.get("tool_dispatches") == 0
             and staged.get("learning_authority") == 0
             and staged.get("native_proof") is False
             and staged.get("real_tty_approved") is False,
             "staged_"+str(i))
        draft = row.get("draft_snapshot") or {}
        need(draft.get("id") == staged.get("draft_message_id")
             and draft.get("role") == "assistant"
             and draft.get("text") == fixture["oracle_action"]
             and draft.get("status") == "DRAFT"
             and draft.get("text_sha256")
             == sha(fixture["oracle_action"].encode("utf-8")),
             "draft_"+str(i))
        try:
            meta = json.loads(draft["metadata"])
            need(meta == {
                "shadow": True, "origin": expected_origin,
                "source_action": fixture["oracle_action"],
                "source_ref_sha256": staged["source_ref_sha256"],
                "prompt_sha256": staged["prompt_sha256"],
                "candidate_sha256": staged["candidate_sha256"],
                "model_formatter_status": expected_formatter,
            }, "draft_metadata_"+str(i))
        except Exception:
            errors.append("draft_metadata_parse_"+str(i))
        c6 = row.get("c6") or {}
        need(c6.get("status") == "NEEDS_REAL_TTY_APPROVAL"
             and c6.get("preflight_only") is True
             and c6.get("source_rechecked") is True
             and c6.get("c5_binding_verified") is True
             and c6.get("candidate_sha256") == staged.get("candidate_sha256")
             and c6.get("source_only_fallback") is (not bool(correct))
             and c6.get("delivery_authority") == 0
             and c6.get("output_committed") is False
             and c6.get("tool_dispatches") == 0
             and c6.get("learning_authority") == 0
             and c6.get("native_proof") is False
             and c6.get("real_tty_approved") is False,
             "c6_"+str(i))
        need(row.get("status") == "RECORDED"
             and row.get("draft_count") == 1
             and row.get("no_live_output") is True
             and (row.get("closed_store_audit") or {}).get("ok") is True
             and row.get("negative_gates") == NEGATIVE
             and row.get("tty_approved") is False
             and row.get("output_committed") is False
             and row.get("tool_dispatches") == 0
             and row.get("learning_authority") == 0
             and row.get("candidate_authority") == 0
             and row.get("oracle_visible_to_native") is False,
             "negative_gates_"+str(i))
    need(report.get("native_strict_count") == strict_count
         and report.get("source_only_fallback_count") == fallback_count,
         "summary_counts")
    need(report.get("status") == "SOURCE_ONLY_DRAFT_STRUCTURAL_PASS",
         "report_status")
    return {
        "status": ("STRUCTURAL_RED" if errors
                   else "SOURCE_ONLY_DRAFT_STRUCTURAL_PASS"),
        "errors": errors, "native_calls": len(rows),
        "native_strict_count": strict_count,
        "source_only_fallback_count": fallback_count,
        "claim": "P2X_CALIBRATION_ENGINEERING_ONLY_NO_C3_PROMOTION",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    result = verify(a.report)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "SOURCE_ONLY_DRAFT_STRUCTURAL_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
