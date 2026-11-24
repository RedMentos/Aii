#!/usr/bin/env python3
"""Independent Run70 native raw reparse, never a STEP2/age/utility promoter."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import jef_c3_source_reasoning_fixture_743 as f

EXPECTED_MODEL="LFM2.5-350M-QAD-Q4_0.gguf"


def verify(report):
    if type(report) is not dict:
        raise ValueError("REPORT_TYPE_RED")
    rows=f.fixtures()
    if (report.get("schema")!="v13.run70.c3_source_reasoning_native.v1"
            or report.get("seed")!=f.SEED
            or report.get("table_sha256")!=f.TABLE_SHA256
            or report.get("model_sha256_required")!=f.MODEL_SHA256
            or report.get("runner_sha256_required")!=f.RUNNER_SHA256
            or report.get("model_sha256_observed")!=f.MODEL_SHA256
            or report.get("runner_sha256_observed")!=f.RUNNER_SHA256
            or report.get("native_call_count")!=12
            or report.get("closed_store_ok") is not True
            or report.get("no_live_output") is not True
            or report.get("source_only_oracle_hidden") is not True
            or report.get("delivery_authority")!=0
            or report.get("tool_dispatches")!=0
            or report.get("learning_authority")!=0
            or report.get("tty_approved") is not False
            or report.get("output_committed") is not False
            or report.get("age0")!="RECORD_ONLY"
            or report.get("step2")!="UTILITY_FAIL"
            or report.get("b3")!="NO_PROMOTION"
            or report.get("jepa_weight")!=0
            or report.get("redmi_measured") is not False
            or report.get("whole_system_complete") is not False):
        raise ValueError("RUN70_REPORT_BOUNDARY_RED")
    cases=report.get("cases")
    if type(cases) is not list or len(cases)!=6:
        raise ValueError("RUN70_CASE_COUNT_RED")
    scores={arm:0 for arm in f.ARMS}
    for row,case in zip(rows,cases):
        if (type(case) is not dict or case.get("index")!=row["index"]
                or case.get("expected")!=row["expected"]
                or case.get("project_sha256")!=f.sha(row["project"].encode())
                or case.get("source_sha256")!={k:f.sha(row[k].encode("utf-8"))
                     for k in ("current","policy_source","sheet_source")}):
            raise ValueError("RUN70_CASE_BINDING_RED")
        arms=case.get("arms")
        order=f.ARMS if row["index"]%2==0 else f.ARMS[::-1]
        if type(arms) is not list or len(arms)!=2 or tuple(x.get("arm") for x in arms)!=order:
            raise ValueError("RUN70_ARM_ORDER_RED")
        for item in arms:
            arm=item["arm"]
            output=item.get("output")
            if (type(output) is not str
                    or not 0<len(output.encode("utf-8"))<=1024
                    or item.get("output_bytes")!=len(output.encode("utf-8"))
                    or item.get("output_sha256")!=f.sha(output.encode("utf-8"))
                    or item.get("parsed_action")!=f.run68.decode_schema(output)
                    or item.get("strict")!=f.score(output,row["expected"])
                    or item.get("typed_answer_visible") is not (arm=="TYPED_SCHEMA")
                    or type(item.get("input_sha256")) is not str
                    or len(item["input_sha256"])!=64
                    or item.get("native_final") is not True
                    or item.get("process_reaped") is not True
                    or item.get("actual_model")!=EXPECTED_MODEL
                    or item.get("status")!="RECORDED"):
                raise ValueError("RUN70_NATIVE_ARM_RED")
            scores[arm]+=item["strict"]
        if arms[0]["input_sha256"]==arms[1]["input_sha256"]:
            raise ValueError("RUN70_NO_ARM_DIFFERENCE_RED")
    if report.get("strict")!=scores:
        raise ValueError("RUN70_SCORE_REPARSE_RED")
    status=("SOURCE_REASONING_SMALL_SYNTHETIC_PASS"
            if scores["SOURCE_SCHEMA"]>=4 and scores["TYPED_SCHEMA"]>=4
            else "SOURCE_REASONING_DIAGNOSTIC_RED")
    if report.get("status")!=status:
        raise ValueError("RUN70_STATUS_REPARSE_RED")
    return {"status":"INDEPENDENT_RUN70_NATIVE_REPARSE_PASS",
            "registered_result":status,"strict":scores,
            "native_calls":12,"claim_limit":"SIX_SYNTHETIC_SOURCE_TASKS_ONLY"}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("report",type=Path)
    args=p.parse_args()
    data=json.loads(args.report.read_text(encoding="utf-8"))
    print(json.dumps(verify(data),sort_keys=True))


if __name__=="__main__":
    main()
