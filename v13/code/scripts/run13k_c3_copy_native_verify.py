"""Run13K independent raw verifier; read-only, fail closed, no model call."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import run13k_c3_copy_native as k
from scripts import run13j_c3_jef_native as j
from scripts.run13j_c3_jef_native_verify import expected_answer
from v13.agi.jef_c3_shadow_prompt_run13i import PREFIX


def strict_json(path):
    def reject(value):
        raise ValueError("RUN13K_NONFINITE_JSON")
    value = json.loads(Path(path).read_text(encoding="utf-8"),
                       parse_constant=reject)
    if type(value) is not dict:
        raise ValueError("RUN13K_JSON_OBJECT_RED")
    return value


def verify(pilot, fixture):
    cases = k.load_fixture(fixture)
    pilot = Path(pilot)
    expected = {f"{i:02d}_{arm}.json"
                for i in range(6) for arm in k.ARMS}
    actual = {p.name for p in (pilot / "raw").glob("*.json")}
    if expected != actual:
        raise ValueError("RUN13K_RAW_COVERAGE_RED")
    rows = []
    pids = set()
    for i, case in enumerate(cases):
        pair = []
        answer = expected_answer(case)
        for arm in k.ARMS:
            row = strict_json(pilot / "raw" / f"{i:02d}_{arm}.json")
            prompt = (PREFIX + answer if arm == "ORIGINAL_SHADOW"
                      else k.COPY_PREFIX + answer + k.COPY_SUFFIX)
            if (row.get("schema") != k.SCHEMA
                    or row.get("seed") != k.SEED
                    or row.get("index") != i
                    or row.get("project") != case["project"]
                    or row.get("arm") != arm
                    or row.get("source_sha256") != k.sha(j.frozen.prompt(case))
                    or row.get("answer_sha256") != k.sha(answer)
                    or row.get("prompt_sha256") != k.sha(prompt)
                    or row.get("model_sha256") != k.MODEL_SHA
                    or row.get("model_revision") != k.MODEL_REVISION
                    or any(type(row.get(field)) is not str or not row[field]
                           for field in ("source_event_id", "query_event_id",
                                         "context_plan_packet_id"))
                    or row.get("learning_mode") != "RECORD_ONLY"
                    or row.get("jepa_weight") != 0
                    or row.get("step2_status") != "UTILITY_FAIL"
                    or row.get("b3_status") != "NO_PROMOTION"
                    or row.get("body_jepa_status") != "UNAVAILABLE"
                    or row.get("redmi_measured") is not False
                    or row.get("whole_system_complete") is not False):
                raise ValueError("RUN13K_SOURCE_OR_GATE_RED")
            release = row.get("native_release")
            if (type(release) is not dict
                    or release.get("process_reaped") is not True
                    or row.get("native_reaped") is not True
                    or row.get("native_calls") != 1
                    or row.get("native_status") != "FINAL"
                    or row.get("native_role") != "C3_LANGUAGE"
                    or type(row.get("native_pid")) is not int
                    or row["native_pid"] <= 0
                    or type(row.get("final_output")) is not str):
                raise ValueError("RUN13K_NATIVE_PROOF_RED")
            metrics = row.get("native_metrics")
            if (type(metrics) is not dict
                    or metrics.get("status") != "FINAL"
                    or metrics.get("role") != "C3_LANGUAGE"
                    or metrics.get("actual_model") != "LFM2.5-350M-QAD-Q4_0.gguf"):
                raise ValueError("RUN13K_NATIVE_METRICS_RED")
            if row["native_pid"] in pids:
                raise ValueError("RUN13K_NATIVE_PID_REUSED_RED")
            pids.add(row["native_pid"])
            output = row["final_output"]
            if (row.get("score") != j.score(case, output, True)
                    or row.get("exact_copy") is not (output == answer)):
                raise ValueError("RUN13K_SCORE_OR_COPY_RED")
            pair.append(row)
            rows.append(row)
        if any(pair[0][field] != pair[1][field]
               for field in ("source_event_id", "query_event_id",
                             "context_plan_packet_id", "source_sha256",
                             "answer_sha256", "model_sha256", "model_revision")):
            raise ValueError("RUN13K_PAIR_MISMATCH_RED")
    totals = {arm: {
        "n": sum(r["arm"] == arm for r in rows),
        "native_final": sum(r["arm"] == arm and r["native_status"] == "FINAL"
                            and r["native_reaped"] for r in rows),
        "exact_copy": sum(r["arm"] == arm and r["exact_copy"] for r in rows),
        "numeric_correct": sum(r["score"]["numeric"]["correct"]
                               for r in rows if r["arm"] == arm),
        "faster_correct": sum(r["score"]["faster_correct"]
                              for r in rows if r["arm"] == arm),
        "strict_full": sum(r["score"]["strict_full"]
                           for r in rows if r["arm"] == arm),
        "literal_abstain_dot": sum(r["arm"] == arm
                                  and r["final_output"] == "ABSTAIN."
                                  for r in rows),
    } for arm in k.ARMS}
    report = strict_json(pilot / "report.json")
    if (report.get("schema") != k.SCHEMA
            or report.get("seed") != k.SEED
            or report.get("fixture_sha256") != k.FIXTURE_SHA256
            or report.get("rows") != 12
            or report.get("totals") != totals
            or report.get("all_native_final") is not True
            or report.get("all_native_reaped") is not True
            or report.get("learning_mode") != "RECORD_ONLY"
            or report.get("step2_status") != "UTILITY_FAIL"
            or report.get("b3_status") != "NO_PROMOTION"
            or report.get("body_jepa_status") != "UNAVAILABLE"
            or report.get("jepa_weight") != 0
            or report.get("redmi_measured") is not False
            or report.get("utility_gate_promoted") is not False
            or report.get("whole_system_complete") is not False
            or report.get("semantic_quality_proven") is not False):
        raise ValueError("RUN13K_REPORT_RED")
    return {"status": "RUN13K_RAW_REPLAY_VALID", "rows": len(rows),
            "distinct_native_pids": len(pids), "totals": totals,
            "step2_status": "UTILITY_FAIL", "jepa_weight": 0,
            "whole_system_complete": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args(argv)
    print(json.dumps(verify(a.pilot, a.fixture), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
