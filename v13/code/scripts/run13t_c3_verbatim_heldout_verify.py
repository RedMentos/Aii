"""Independent source/score/reaping replay of original Run13T native raw."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import run13t_c3_verbatim_heldout as t
from scripts import run13j_c3_jef_native as j
from scripts import run13j_c3_jef_native_verify as jverify
from scripts import run13k_c3_copy_native as k
from v13.agi.c3_source_fidelity_shadow_run13m import audit_source_facts
from v13.agi.jef_c3_shadow_prompt_run13i import PREFIX


def read_json(path):
    def reject(_):
        raise ValueError("RUN13T_NONFINITE_JSON")
    obj = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject)
    if type(obj) is not dict:
        raise ValueError("RUN13T_JSON_OBJECT_RED")
    return obj


def source_link(answer):
    return {
        "reason": "VERIFIED_JEF_TO_C3_SHADOW_CANDIDATE",
        "status": "SHADOW_NO_AUTHORITY", "delivery_authority": 0,
        "context_authority": 0, "native_calls": 0,
        "weight_updates": False, "answer": answer,
        "answer_sha256": t.sha(answer),
        "candidate_prompt": PREFIX + answer,
        "prompt_sha256": t.sha(PREFIX + answer),
    }


def verify(pilot, fixture):
    cases = t.load_fixture(fixture)
    pilot = Path(pilot)
    expected = {f"{i:02d}_{arm}.json" for i in range(8) for arm in t.ARMS}
    actual = {p.name for p in (pilot / "raw").glob("*.json")}
    if expected != actual:
        raise ValueError("RUN13T_RAW_COVERAGE_RED")
    rows, pids = [], set()
    for i, case in enumerate(cases):
        answer = jverify.expected_answer(case)
        prompt = k.COPY_PREFIX + answer + k.COPY_SUFFIX
        linked = source_link(answer)
        pair = []
        for arm in t.ARMS:
            row = read_json(pilot / "raw" / f"{i:02d}_{arm}.json")
            if (row.get("schema") != t.SCHEMA or row.get("seed") != t.SEED
                    or row.get("index") != i or row.get("project") != case["project"]
                    or row.get("arm") != arm
                    or row.get("source_sha256") != t.sha(j.frozen.prompt(case))
                    or row.get("answer_sha256") != t.sha(answer)
                    or row.get("prompt_sha256") != t.sha(prompt)
                    or row.get("system_sha256") != t.sha(t.system_for(arm))
                    or row.get("model_sha256") != t.MODEL_SHA
                    or row.get("model_revision") != t.MODEL_REVISION
                    or any(type(row.get(k)) is not str or not row[k]
                           for k in ("source_event_id", "query_event_id", "context_plan_packet_id"))
                    or row.get("learning_mode") != "RECORD_ONLY"
                    or row.get("jepa_weight") != 0
                    or row.get("step2_status") != "UTILITY_FAIL"
                    or row.get("b3_status") != "NO_PROMOTION"
                    or row.get("body_jepa_status") != "UNAVAILABLE"
                    or row.get("redmi_measured") is not False
                    or row.get("whole_system_complete") is not False):
                raise ValueError("RUN13T_SOURCE_OR_GATE_RED")
            release = row.get("native_release")
            if (type(release) is not dict or release.get("process_reaped") is not True
                    or row.get("native_reaped") is not True
                    or row.get("native_calls") != 1
                    or row.get("native_status") != "FINAL"
                    or row.get("native_role") != "C3_LANGUAGE"
                    or type(row.get("native_pid")) is not int or row["native_pid"] <= 0
                    or type(row.get("final_output")) is not str):
                raise ValueError("RUN13T_NATIVE_PROOF_RED")
            metrics = row.get("native_metrics")
            if (type(metrics) is not dict or metrics.get("status") != "FINAL"
                    or metrics.get("role") != "C3_LANGUAGE"
                    or metrics.get("actual_model") != "LFM2.5-350M-QAD-Q4_0.gguf"):
                raise ValueError("RUN13T_NATIVE_METRICS_RED")
            if row["native_pid"] in pids:
                raise ValueError("RUN13T_PID_REUSE_RED")
            pids.add(row["native_pid"])
            output = row["final_output"]
            fidelity = audit_source_facts(linked, output)
            expected_fidelity = fidelity["result"] == "FACTS_EXACT"
            if (row.get("score") != j.score(case, output, True)
                    or row.get("exact_copy") is not (output == answer)
                    or row.get("source_facts_verified") is not expected_fidelity
                    or row.get("fidelity_reason") != fidelity["reason"]
                    or row.get("wrong_claims") != t.explicit_wrong_claims(case, output)):
                raise ValueError("RUN13T_SCORE_OR_FIDELITY_RED")
            pair.append(row)
            rows.append(row)
        for key in ("source_event_id", "query_event_id", "context_plan_packet_id",
                    "source_sha256", "answer_sha256", "prompt_sha256",
                    "model_sha256", "model_revision"):
            if pair[0][key] != pair[1][key]:
                raise ValueError("RUN13T_PAIRED_SOURCE_RED:" + key)
        if pair[0]["system_sha256"] == pair[1]["system_sha256"]:
            raise ValueError("RUN13T_SYSTEM_ABLATION_RED")
    totals = {arm: {
        "n": sum(r["arm"] == arm for r in rows),
        "native_final": sum(r["arm"] == arm and r["native_status"] == "FINAL"
                            and r["native_reaped"] for r in rows),
        "exact_copy": sum(r["arm"] == arm and r["exact_copy"] for r in rows),
        "source_facts_verified": sum(r["arm"] == arm and r["source_facts_verified"] for r in rows),
        "wrong_claims": sum(r["wrong_claims"] for r in rows if r["arm"] == arm),
        "numeric_correct": sum(r["score"]["numeric"]["correct"]
                               for r in rows if r["arm"] == arm),
        "faster_correct": sum(r["score"]["faster_correct"]
                              for r in rows if r["arm"] == arm),
        "strict_full": sum(r["score"]["strict_full"]
                           for r in rows if r["arm"] == arm),
        "literal_abstain_dot": sum(r["arm"] == arm and r["final_output"] == "ABSTAIN."
                                  for r in rows),
    } for arm in t.ARMS}
    report = read_json(pilot / "report.json")
    if (report.get("schema") != t.SCHEMA
            or report.get("seed") != t.SEED
            or report.get("fixture_sha256") != t.FIXTURE_SHA256
            or report.get("rows") != 16
            or report.get("totals") != totals
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
        raise ValueError("RUN13T_REPORT_RED")
    return {"status": "RUN13T_ORIGINAL_NATIVE_RAW_REPLAY_VALID",
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