#!/usr/bin/env python3
"""Independent Run63 original six-call C3 receiver report verifier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from v13.common import dumps
from scripts import p2x_disjoint_receiver_trainset as p2x
from scripts.run47_jef_c3_typed_receiver_native import NEGATIVE

C3_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
ORDER = {"A": ("RAW", "TYPED"), "B": ("TYPED", "RAW"),
         "NONE": ("RAW", "TYPED")}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def selected():
    rows = p2x.fixtures()
    p2x.validate(rows)
    calibration = [r for r in rows if r["partition"] == "calibration"]
    return [min((r for r in calibration if r["oracle_action"] == a),
                key=lambda r: r["id"]) for a in ("A", "B", "NONE")]


def verify(path):
    report = json.loads(Path(path).read_text())
    errors = []
    def need(ok, name):
        if not ok:
            errors.append(name)

    need(report.get("schema") == "v13.run63.jef_c3_native_report.v1", "schema")
    need(report.get("seed") == p2x.SEED
         and report.get("model_seed") == 13, "seeds")
    need(report.get("claim")
         == "P2X_CALIBRATION_JEF_C3_ENGINEERING_NOT_DISJOINT_UTILITY", "claim")
    need(report.get("negative_gates") == NEGATIVE, "negative_gates")
    binding = report.get("binding") or {}
    need((binding.get("model_sha256") or {}).get("C3_LANGUAGE")
         == C3_SHA and binding.get("runner_sha256") == RUNNER_SHA
         and report.get("installed_binding_unchanged") is True, "binding")
    cohort = selected()
    need(report.get("selected_ids") == [r["id"] for r in cohort], "cohort")
    rows = report.get("rows")
    if type(rows) is not list or len(rows) != 6:
        return {"status": "STRUCTURAL_RED", "errors": errors+["row_count"]}
    expected = [(r,arm) for r in cohort for arm in ORDER[r["oracle_action"]]]
    counts = {"RAW": 0, "TYPED": 0}
    for i, ((fixture,arm),row) in enumerate(zip(expected, rows)):
        key = fixture["id"] + "/" + arm
        need((report.get("row_sha256") or {}).get(key)
             == sha(dumps(row).encode("utf-8")), "row_hash_"+str(i))
        need(row.get("schema") == "v13.run63.jef_c3_native_row.v1"
             and row.get("id") == fixture["id"] and row.get("arm") == arm
             and row.get("oracle_action") == fixture["oracle_action"],
             "row_identity_"+str(i))
        need(row.get("source_sha256") == {
            k:sha(fixture[k].encode("utf-8"))
            for k in ("current","b1_source","b2_source")}, "source_"+str(i))
        refs = row.get("source_refs") or {}
        for label, field in (("current","current"),("policy","b2_source"),
                             ("sheet","b1_source")):
            ref = refs.get(label) or {}
            need(ref.get("sha256") == sha(fixture[field].encode("utf-8"))
                 and ref.get("char_start") == 0
                 and ref.get("char_end") == len(fixture[field])
                 and ref.get("modality") == "text",
                 "source_ref_"+label+"_"+str(i))
        need(len({(refs.get(k) or {}).get("source_id")
                  for k in ("current","policy","sheet")}) == 3,
             "source_ref_distinct_"+str(i))
        need(row.get("negative_gates") == NEGATIVE
             and row.get("tty_approved") is False
             and row.get("output_committed") is False
             and row.get("tool_dispatches") == 0
             and row.get("learning_authority") == 0
             and row.get("candidate_authority") == 0
             and row.get("oracle_visible_to_native") is False
             and row.get("no_live_output") is True, "no_authority_"+str(i))
        need(row.get("status") == "RECORDED"
             and row.get("native_c3_final") is True
             and row.get("native_process_count",0) >= 1
             and row.get("processes_reaped") is True
             and (row.get("closed_store_audit") or {}).get("ok") is True,
             "native_store_"+str(i))
        need(bool(row.get("process_releases"))
             and all(x.get("process_reaped") is True
                     for x in row.get("process_releases",[])),
             "native_reaped_"+str(i))
        metrics = row.get("native_metrics") or {}
        need(metrics.get("status") == "FINAL"
             and metrics.get("actual_model")
             == "LFM2.5-350M-QAD-Q4_0.gguf", "native_model_"+str(i))
        output = row.get("native_output")
        need(type(output) is str
             and row.get("output_sha256") == sha(output.encode("utf-8")),
             "output_hash_"+str(i))
        messages = row.get("input_messages")
        need(type(messages) is list and len(messages) == 2
             and row.get("input_sha256")
             == sha(dumps(messages).encode("utf-8")) if type(messages) is list else False,
             "prompt_hash_"+str(i))
        if type(messages) is list and len(messages) == 2:
            try:
                need([x["role"] for x in messages] == ["system","user"],
                     "prompt_roles_"+str(i))
                payload = json.loads(messages[1]["content"])
                need(payload.get("current_source") == fixture["current"]
                     and payload.get("policy_source") == fixture["b2_source"]
                     and payload.get("sheet_source") == fixture["b1_source"]
                     and payload.get("candidate_authority") == 0
                     and "oracle" not in payload and "oracle_action" not in payload,
                     "prompt_sources_"+str(i))
                if arm == "TYPED":
                    need(row.get("typed_source_verified") is True
                         and row.get("typed_jef_action") == fixture["oracle_action"]
                         and payload.get("typed_jef_action") == fixture["oracle_action"]
                         and len(payload.get("source_ref_sha256",[])) == 2,
                         "typed_source_"+str(i))
                else:
                    need(row.get("typed_source_verified") is False
                         and "typed_jef_action" not in payload,
                         "raw_source_"+str(i))
            except Exception:
                errors.append("prompt_parse_"+str(i))
        correct = int(type(output) is str and output in ("A","B","NONE")
                      and output == fixture["oracle_action"])
        match = correct if arm == "TYPED" else 0
        need(row.get("score") == {
            "strict_correct": correct, "exact_formatter_match": match},
            "frozen_score_"+str(i))
        if arm == "TYPED":
            need(row.get("formatter_status") ==
                 ("FORMATTER_MATCH_SHADOW" if match else "FORMATTER_MISMATCH_RED"),
                 "formatter_"+str(i))
        counts[arm] += correct
    need(report.get("scores") == counts, "summary_scores")
    passing = (counts["TYPED"] == 3 and counts["TYPED"] > counts["RAW"]
               and all(r["score"]["exact_formatter_match"] == 1
                       for r in rows if r["arm"] == "TYPED"))
    expected_status = "RECEIVER_PILOT_PASS" if passing else "RECEIVER_PILOT_RED"
    need(report.get("status") == expected_status, "report_status")
    status = "STRUCTURAL_RED" if errors else expected_status
    return {"status": status, "errors": errors,
            "scores": counts, "native_calls": len(rows),
            "claim": "P2X_CALIBRATION_ENGINEERING_ONLY"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    result = verify(a.report)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "RECEIVER_PILOT_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
