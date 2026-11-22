"""Run13J independent posthoc verifier: exact source/arm/score/reaping lineage.

Synthetic tests of this verifier do not count as native evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts import run13j_c3_jef_native as j
from scripts import c2_body_disjoint_paired181_run11v as frozen
from v13.agi.budget_answer_shadow_run13b import _render
from v13.agi.jef_c3_shadow_prompt_run13i import PREFIX

MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
MODEL_REVISION = "657e078c94084481950a2d555a941481f715536b"


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def expected_answer(case):
    return _render({
        "project": case["project"], "option_a": case["a"],
        "option_b": case["b"],
        "remaining_a_eur": case["budget"] - case["a_cost"],
        "remaining_b_eur": case["budget"] - case["b_cost"],
        "faster_option": (case["a"] if case["a_days"] < case["b_days"]
                          else case["b"]),
    })


def _strict_object(path):
    def reject(value):
        raise ValueError("NONFINITE_JSON_LITERAL")
    obj = json.loads(Path(path).read_text(encoding="utf-8"),
                     parse_constant=reject)
    if type(obj) is not dict:
        raise ValueError("RUN13J_JSON_OBJECT_REQUIRED")
    return obj


def verify(pilot, fixture):
    cases = j.load_fixture(fixture)
    pilot = Path(pilot)
    expected_files = {
        f"{i:02d}_{arm}.json"
        for i in range(len(cases)) for arm in j.ARMS
    }
    actual_files = {p.name for p in (pilot / "raw").glob("*.json")}
    if actual_files != expected_files:
        raise ValueError("RUN13J_RAW_COVERAGE_RED")
    rows = []
    for i, case in enumerate(cases):
        pair = []
        for arm in j.ARMS:
            row = _strict_object(pilot / "raw" / f"{i:02d}_{arm}.json")
            source = frozen.prompt(case)
            answer = expected_answer(case)
            prompt = (source + "\n" + j.query(case) if arm == "RAW_C3"
                      else PREFIX + answer)
            if (row.get("index") != i or row.get("project") != case["project"]
                    or row.get("arm") != arm or row.get("seed") != j.SEED
                    or row.get("native_role") != "C3_LANGUAGE"
                    or row.get("model_sha256") != MODEL_SHA
                    or row.get("model_revision") != MODEL_REVISION
                    or row.get("source_sha256") != _sha(source)
                    or row.get("prompt_sha256") != _sha(prompt)
                    or row.get("jef_answer_sha256") != _sha(answer)
                    or any(type(row.get(k)) is not str or not row[k]
                           for k in ("source_event_id", "query_event_id",
                                     "context_plan_packet_id"))
                    or row.get("learning_mode") != "RECORD_ONLY"
                    or row.get("jepa_weight") != 0
                    or row.get("step2_status") != "UTILITY_FAIL"
                    or row.get("b3_status") != "NO_PROMOTION"
                    or row.get("body_jepa_status") != "UNAVAILABLE"
                    or row.get("redmi_measured") is not False
                    or row.get("whole_system_complete") is not False):
                raise ValueError("RUN13J_SOURCE_MODEL_OR_GATE_RED")
            release = row.get("native_release")
            if (type(release) is not dict
                    or release.get("process_reaped") is not True
                    or row.get("native_reaped") is not True):
                raise ValueError("RUN13J_NATIVE_RELEASE_RED")
            if row.get("native_calls") not in (0, 1):
                raise ValueError("RUN13J_NATIVE_CALL_COUNT_RED")
            valid = (row.get("native_status") == "FINAL"
                     and row.get("native_calls") == 1
                     and type(row.get("final_output")) is str
                     and type(row.get("native_pid")) is int
                     and row["native_pid"] > 0)
            if row.get("native_status") == "FINAL" and not valid:
                raise ValueError("RUN13J_FALSE_NATIVE_FINAL")
            output = row.get("final_output") or ""
            if row.get("score") != j.score(case, output, valid):
                raise ValueError("RUN13J_FROZEN_SCORE_MISMATCH")
            expected_copy = ("EXACT_COPY" if output == answer else "NOT_VERIFIED"
                             if valid and arm == "JEF_C3" else "NOT_APPLICABLE")
            if arm == "JEF_C3" and valid:
                expected_copy = "EXACT_COPY" if output == answer else "NOT_VERIFIED"
            else:
                expected_copy = "NOT_APPLICABLE"
            if row.get("exact_copy") != expected_copy:
                raise ValueError("RUN13J_EXACT_COPY_MISMATCH")
            pair.append(row)
            rows.append(row)
        if any(pair[0][k] != pair[1][k] for k in (
                "source_event_id", "query_event_id", "context_plan_packet_id",
                "model_sha256", "model_revision", "jef_answer_sha256")):
            raise ValueError("RUN13J_PAIRED_SOURCE_MISMATCH")
    report = _strict_object(pilot / "report.json")
    totals = {arm: {
        "n": sum(r["arm"] == arm for r in rows),
        "native_final": sum(r["arm"] == arm and r["native_status"] == "FINAL"
                            and r["native_reaped"] for r in rows),
        "numeric_correct": sum(r["score"]["numeric"]["correct"]
                               for r in rows if r["arm"] == arm),
        "faster_correct": sum(r["score"]["faster_correct"]
                              for r in rows if r["arm"] == arm),
        "strict_full": sum(r["score"]["strict_full"]
                           for r in rows if r["arm"] == arm),
    } for arm in j.ARMS}
    if (report.get("schema") != j.SCHEMA
            or report.get("seed") != j.SEED
            or report.get("fixture_sha256") != j.FIXTURE_SHA256
            or report.get("rows") != 12 or report.get("totals") != totals
            or report.get("jef_exact_copy") != sum(
                r["exact_copy"] == "EXACT_COPY" for r in rows)
            or report.get("all_native_reaped") != all(
                r["native_reaped"] for r in rows)
            or report.get("all_native_final") != all(
                r["native_status"] == "FINAL" for r in rows)
            or report.get("learning_mode") != "RECORD_ONLY"
            or report.get("jepa_weight") != 0
            or report.get("step2_status") != "UTILITY_FAIL"
            or report.get("b3_status") != "NO_PROMOTION"
            or report.get("body_jepa_status") != "UNAVAILABLE"
            or report.get("redmi_measured") is not False
            or report.get("whole_system_complete") is not False
            or report.get("utility_gate_promoted") is not False
            or report.get("semantic_quality_proven") is not False):
        raise ValueError("RUN13J_REPORT_REPLAY_MISMATCH")
    return {
        "status": "RAW_REPLAY_VALID", "rows": len(rows),
        "totals": totals, "all_native_final": report["all_native_final"],
        "all_native_reaped": report["all_native_reaped"],
        "utility_gate_promoted": False,
        "step2_status": "UTILITY_FAIL", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", required=True, type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    args = parser.parse_args(argv)
    result = verify(args.pilot, args.fixture)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
