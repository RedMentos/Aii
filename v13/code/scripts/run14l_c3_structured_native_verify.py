"""Run14L independent offline replay of original 16 native C3 source/score receipts.

The replay checks the raw files, not just the collector's report. A software
test with forged native receipts does not establish native execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts import run13j_c3_jef_native as j
from scripts import run13j_c3_jef_native_verify as jverify
from scripts import run13k_c3_copy_native as k
from scripts import run13l_c3_system_native as l
from scripts import run14l_c3_structured_native as pilot
from v13.agi.c3_source_fidelity_shadow_run13m import audit_source_facts
from v13.agi.c3_structured_source_shadow_run14k import (
    audit_slots, prompt_for as structured_prompt,
)
from v13.agi.jef_c3_shadow_prompt_run13i import PREFIX


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("RUN14L_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def read_json(path):
    def reject(_):
        raise ValueError("RUN14L_NONFINITE_JSON")
    data = json.loads(Path(path).read_text(encoding="utf-8"),
                      parse_constant=reject, object_pairs_hook=_unique)
    if type(data) is not dict:
        raise ValueError("RUN14L_JSON_OBJECT_RED")
    return data


def linked_answer(answer):
    return {
        "reason": "VERIFIED_JEF_TO_C3_SHADOW_CANDIDATE",
        "status": "SHADOW_NO_AUTHORITY", "delivery_authority": 0,
        "context_authority": 0, "native_calls": 0, "weight_updates": False,
        "answer": answer, "answer_sha256": sha(answer),
        "candidate_prompt": PREFIX + answer,
        "prompt_sha256": sha(PREFIX + answer),
    }


def expected_score(linked, case, arm, output):
    if arm == "COPY_BASELINE":
        fidelity = audit_source_facts(linked, output)
        return {
            "full_source_faithful": fidelity["result"] == "FACTS_EXACT",
            "fidelity_reason": fidelity["reason"],
            "exact_copy": output == linked["answer"],
            "structured_slots_exact": False,
            "copy_task_score": j.score(case, output, True),
        }
    if arm == "STRUCTURED_JSON":
        slots = audit_slots(linked, output)
        exact = slots["result"] == "SLOTS_EXACT"
        return {
            "full_source_faithful": exact,
            "fidelity_reason": slots["reason"],
            "exact_copy": False,
            "structured_slots_exact": exact,
            "copy_task_score": None,
        }
    raise ValueError("RUN14L_UNKNOWN_ARM")


def verify(folder, fixture):
    cases = pilot.load_fixture(fixture)
    folder = Path(folder)
    expected_files = {f"{i:02d}_{arm}.json" for i in range(8)
                      for arm in pilot.ARMS}
    actual_files = {p.name for p in (folder / "raw").glob("*.json")}
    if actual_files != expected_files:
        raise ValueError("RUN14L_RAW_COVERAGE_RED")
    rows, pids = [], set()
    for i, case in enumerate(cases):
        answer = jverify.expected_answer(case)
        linked = linked_answer(answer)
        pair = []
        for arm in pilot.ARMS:
            row = read_json(folder / "raw" / f"{i:02d}_{arm}.json")
            if arm == "COPY_BASELINE":
                system, user = l.SYSTEM_COPY, k.COPY_PREFIX + answer + k.COPY_SUFFIX
            else:
                system, user = structured_prompt(linked)
            if (row.get("schema") != pilot.SCHEMA
                    or type(row.get("seed")) is not int or row["seed"] != pilot.SEED
                    or type(row.get("index")) is not int or row["index"] != i
                    or row.get("project") != case["project"] or row.get("arm") != arm
                    or row.get("source_sha256") != sha(j.frozen.prompt(case))
                    or row.get("answer_sha256") != sha(answer)
                    or row.get("prompt_sha256") != sha(user)
                    or row.get("system_sha256") != sha(system)
                    or row.get("model_sha256") != pilot.MODEL_SHA
                    or row.get("model_revision") != pilot.MODEL_REVISION
                    or any(type(row.get(name)) is not str or not row[name]
                           for name in ("source_event_id", "query_event_id",
                                        "context_plan_packet_id"))
                    or row.get("learning_mode") != "RECORD_ONLY"
                    or type(row.get("jepa_weight")) is not int
                    or row["jepa_weight"] != 0
                    or row.get("step2_status") != "UTILITY_FAIL"
                    or row.get("b3_status") != "NO_PROMOTION"
                    or row.get("body_jepa_status") != "UNAVAILABLE"
                    or row.get("redmi_measured") is not False
                    or row.get("whole_system_complete") is not False):
                raise ValueError("RUN14L_SOURCE_MODEL_OR_GATE_RED")
            metrics = row.get("native_metrics")
            release = row.get("native_release")
            output = row.get("final_output")
            pid = row.get("native_pid")
            if (row.get("native_role") != "C3_LANGUAGE"
                    or type(row.get("native_calls")) is not int
                    or row["native_calls"] != 1
                    or row.get("native_status") != "FINAL"
                    or row.get("native_reaped") is not True
                    or type(release) is not dict
                    or release.get("process_reaped") is not True
                    or type(metrics) is not dict
                    or metrics.get("status") != "FINAL"
                    or metrics.get("role") != "C3_LANGUAGE"
                    or metrics.get("actual_model") != "LFM2.5-350M-QAD-Q4_0.gguf"
                    or type(pid) is not int or pid <= 0 or pid in pids
                    or type(output) is not str
                    or row.get("native_output_sha256") != sha(output)
                    or type(row.get("native_output_bytes")) is not int
                    or row["native_output_bytes"] != len(output.encode("utf-8"))):
                raise ValueError("RUN14L_NATIVE_PROOF_RED")
            pids.add(pid)
            if row.get("score") != expected_score(linked, case, arm, output):
                raise ValueError("RUN14L_SCORE_REPLAY_RED")
            rows.append(row)
            pair.append(row)
        for key in ("source_event_id", "query_event_id",
                    "context_plan_packet_id", "source_sha256",
                    "answer_sha256", "model_sha256", "model_revision"):
            if pair[0][key] != pair[1][key]:
                raise ValueError("RUN14L_PAIRED_SOURCE_RED")
    totals = {arm: {
        "n": sum(r["arm"] == arm for r in rows),
        "native_final": sum(r["arm"] == arm and r["native_status"] == "FINAL"
                            and r["native_reaped"] for r in rows),
        "full_source_faithful": sum(r["arm"] == arm
                                    and r["score"]["full_source_faithful"] for r in rows),
        "exact_copy": sum(r["arm"] == arm and r["score"]["exact_copy"] for r in rows),
        "structured_slots_exact": sum(r["arm"] == arm
                                       and r["score"]["structured_slots_exact"] for r in rows),
        "copy_strict_full": sum(r["arm"] == arm
                                and r["score"]["copy_task_score"] is not None
                                and r["score"]["copy_task_score"]["strict_full"]
                                for r in rows),
    } for arm in pilot.ARMS}
    a = totals["COPY_BASELINE"]["full_source_faithful"]
    b = totals["STRUCTURED_JSON"]["full_source_faithful"]
    status = ("BOUNDED_PROTOCOL_FIDELITY_SIGNAL_NOT_UTILITY_GATE"
              if b >= a + 2 else "FIDELITY_HURT"
              if b < a else "NO_BOUNDED_FIDELITY_SIGNAL")
    report = read_json(folder / "report.json")
    if (report.get("schema") != pilot.SCHEMA
            or report.get("seed") != pilot.SEED
            or report.get("fixture_sha256") != pilot.FIXTURE_SHA256
            or report.get("rows") != 16 or report.get("totals") != totals
            or report.get("status") != status
            or report.get("all_native_final_and_reaped") is not True
            or report.get("learning_mode") != "RECORD_ONLY"
            or report.get("step2_status") != "UTILITY_FAIL"
            or report.get("b3_status") != "NO_PROMOTION"
            or report.get("body_jepa_status") != "UNAVAILABLE"
            or type(report.get("jepa_weight")) is not int
            or report["jepa_weight"] != 0
            or report.get("redmi_measured") is not False
            or report.get("utility_gate_promoted") is not False
            or report.get("semantic_quality_proven") is not False
            or report.get("production_activation") is not False
            or report.get("whole_system_complete") is not False):
        raise ValueError("RUN14L_REPORT_REPLAY_RED")
    return {"status": "ORIGINAL_NATIVE_RAW_REPLAY_VALID",
            "rows": len(rows), "distinct_native_pids": len(pids),
            "totals": totals, "protocol_diagnostic": status,
            "utility_gate_promoted": False, "redmi_measured": False,
            "whole_system_complete": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", required=True, type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.pilot, args.fixture), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
