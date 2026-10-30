"""Independent source/model/native/score replay of Run14L original raw evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import run14l_c3_structured_native as t
from scripts import run13j_c3_jef_native as j
from scripts import run13j_c3_jef_native_verify as jverify
from v13.agi.c3_source_fidelity_shadow_run13m import audit_source_facts
from v13.agi.c3_structured_source_shadow_run14k import audit_slots
from v13.agi.jef_c3_shadow_prompt_run13i import PREFIX


def read_json(path):
    def reject(_):
        raise ValueError("RUN14L_NONFINITE_JSON")
    obj = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject)
    if type(obj) is not dict:
        raise ValueError("RUN14L_JSON_OBJECT_RED")
    return obj


def source_link(answer):
    return {"reason": "VERIFIED_JEF_TO_C3_SHADOW_CANDIDATE",
            "status": "SHADOW_NO_AUTHORITY", "delivery_authority": 0,
            "context_authority": 0, "native_calls": 0,
            "weight_updates": False, "answer": answer,
            "answer_sha256": t.sha(answer),
            "candidate_prompt": PREFIX + answer,
            "prompt_sha256": t.sha(PREFIX + answer)}


def verify(pilot, fixture):
    cases = t.load_fixture(fixture)
    pilot = Path(pilot)
    expected_names = {f"{i:02d}_{arm}.json" for i in range(4) for arm in t.ARMS}
    actual_names = {p.name for p in (pilot / "raw").glob("*.json")}
    if actual_names != expected_names:
        raise ValueError("RUN14L_RAW_COVERAGE_RED")
    rows, pids = [], set()
    for index, case in enumerate(cases):
        answer = jverify.expected_answer(case)
        linked = source_link(answer)
        pair = []
        for arm in t.ARMS:
            row = read_json(pilot / "raw" / f"{index:02d}_{arm}.json")
            system, prompt, schema = t.messages_for(arm, linked)
            schema_sha = t.sha(json.dumps(schema, sort_keys=True)) if schema else None
            if (row.get("schema") != t.SCHEMA or row.get("seed") != t.SEED
                    or row.get("index") != index or row.get("project") != case["project"]
                    or row.get("arm") != arm
                    or row.get("source_sha256") != t.sha(j.frozen.prompt(case))
                    or row.get("answer_sha256") != t.sha(answer)
                    or row.get("prompt_sha256") != t.sha(prompt)
                    or row.get("system_sha256") != t.sha(system)
                    or row.get("schema_sha256") != schema_sha
                    or row.get("model_sha256") != t.MODEL_SHA
                    or row.get("model_revision") != t.MODEL_REVISION
                    or any(type(row.get(k)) is not str or not row[k] for k in
                           ("source_event_id", "query_event_id", "context_plan_packet_id"))
                    or row.get("learning_mode") != "RECORD_ONLY"
                    or row.get("jepa_weight") != 0
                    or row.get("step2_status") != "UTILITY_FAIL"
                    or row.get("b3_status") != "NO_PROMOTION"
                    or row.get("body_jepa_status") != "UNAVAILABLE"
                    or row.get("redmi_measured") is not False
                    or row.get("whole_system_complete") is not False):
                raise ValueError("RUN14L_SOURCE_OR_GATE_RED")
            release = row.get("native_release")
            metrics = row.get("native_metrics")
            if (type(release) is not dict or release.get("process_reaped") is not True
                    or row.get("native_reaped") is not True
                    or row.get("native_calls") != 1
                    or row.get("native_status") != "FINAL"
                    or row.get("native_role") != "C3_LANGUAGE"
                    or type(row.get("native_pid")) is not int or row["native_pid"] <= 0
                    or type(row.get("final_output")) is not str
                    or type(metrics) is not dict or metrics.get("status") != "FINAL"
                    or metrics.get("role") != "C3_LANGUAGE"
                    or metrics.get("actual_model") != "LFM2.5-350M-QAD-Q4_0.gguf"):
                raise ValueError("RUN14L_NATIVE_RECEIPT_RED")
            if row["native_pid"] in pids:
                raise ValueError("RUN14L_PID_REUSE_RED")
            pids.add(row["native_pid"])
            output = row["final_output"]
            audit = audit_source_facts(linked, output) if arm == "COPY_BASELINE" else audit_slots(linked, output)
            success = audit["result"] in ("FACTS_EXACT", "SLOTS_EXACT")
            if arm == "COPY_BASELINE":
                score = j.score(case, output, True)
                partial = {"numeric_correct": score["numeric"]["correct"],
                           "faster_correct": score["faster_correct"],
                           "wrong_claims": 0}
            else:
                partial = t.structured_partial(case, output)
            if (row.get("strict_success") is not success
                    or row.get("audit_reason") != audit["reason"]
                    or row.get("partial") != partial):
                raise ValueError("RUN14L_SCORE_REPLAY_RED")
            rows.append(row)
            pair.append(row)
        for key in ("source_event_id", "query_event_id", "context_plan_packet_id",
                    "source_sha256", "answer_sha256", "model_sha256", "model_revision"):
            if len({r[key] for r in pair}) != 1:
                raise ValueError("RUN14L_PAIRED_SOURCE_RED:" + key)
        if pair[1]["prompt_sha256"] != pair[2]["prompt_sha256"]:
            raise ValueError("RUN14L_STRUCTURED_PROMPT_PAIR_RED")
        if pair[1]["system_sha256"] != pair[2]["system_sha256"]:
            raise ValueError("RUN14L_STRUCTURED_SYSTEM_PAIR_RED")
        if pair[1]["schema_sha256"] is not None or pair[2]["schema_sha256"] is None:
            raise ValueError("RUN14L_GRAMMAR_ABLATION_RED")
    totals = {arm: {"n": sum(row["arm"] == arm for row in rows),
                    "native_final": sum(row["arm"] == arm and row["native_status"] == "FINAL"
                                        and row["native_reaped"] for row in rows),
                    "strict": sum(row["arm"] == arm and row["strict_success"] for row in rows),
                    "numeric_correct": sum(row["partial"]["numeric_correct"]
                                           for row in rows if row["arm"] == arm),
                    "faster_correct": sum(row["partial"]["faster_correct"]
                                          for row in rows if row["arm"] == arm),
                    "wrong_claims": sum(row["partial"]["wrong_claims"]
                                        for row in rows if row["arm"] == arm)}
              for arm in t.ARMS}
    report = read_json(pilot / "report.json")
    if (report.get("schema") != t.SCHEMA or report.get("seed") != t.SEED
            or report.get("fixture_sha256") != t.FIXTURE_SHA256
            or report.get("rows") != 12 or report.get("totals") != totals
            or report.get("status") != t.verdict(totals)
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
            or report.get("production_activation") is not False
            or report.get("semantic_quality_proven") is not False):
        raise ValueError("RUN14L_REPORT_REPLAY_RED")
    return {"status": "RUN14L_ORIGINAL_NATIVE_RAW_REPLAY_VALID",
            "native_rows": len(rows), "distinct_native_pids": len(pids),
            "totals": totals, "diagnostic": report["status"],
            "utility_gate_promoted": False, "redmi_measured": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args(argv)
    print(json.dumps(verify(a.pilot, a.fixture), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
