#!/usr/bin/env python3
"""Run70 pinned C3 native source-only decision vs typed-answer schema control.

Small disjoint synthetic diagnostic; never user-visible, tool or learning.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import os
import time

from v13.common import atomic_write, dumps, file_hash
from v13.config import initialize, save_config
from v13.store import audit_closed
from v13.jef_c3_typed_envelope_candidate import build_jef_c3_typed_envelope
from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts import jef_c3_source_reasoning_fixture_743 as f
from scripts.run63_jef_c3_native import RUN_CONFIG
from scripts import p2x_disjoint_receiver_trainset as p2x

REPORT_SCHEMA="v13.run70.c3_source_reasoning_native.v1"
C3_FILE="LFM2.5-350M-QAD-Q4_0.gguf"


def _save(path,obj):
    atomic_write(path,dumps(obj))


def _record(runtime,key,value):
    e=runtime.store.event(runtime.session,"Record: "+key)
    mid=runtime.memory.feedback(e["event_id"],"fact",value,
                                permission="record",key=key,scope="session")
    runtime.memory.candidate(mid,runtime.session)
    return mid


def run(home,out):
    home,out=Path(home),Path(out)
    if out.exists():
        raise FileExistsError("RUN70_OUTPUT_EXISTS")
    rows=f.fixtures()
    original=p2x.fixtures()
    p2x.validate(original)
    if {r["project"] for r in rows}&{r["id"] for r in original}:
        raise ValueError("RUN70_P2X_OVERLAP_RED")
    if any(p2x.decide_sources(r["current"],[r["policy_source"],r["sheet_source"]])
           !=r["expected"] for r in rows):
        raise ValueError("RUN70_SOURCE_ORACLE_RED")
    out.mkdir(parents=True)
    report_path=out/"report.json"
    report={
        "schema":REPORT_SCHEMA,"evidence_kind":"LINUX_NATIVE_C3_SOURCE_REASONING_SMALL_SYNTHETIC_SHADOW",
        "preregistered":True,"seed":f.SEED,"max_tokens":32,
        "table_sha256":f.TABLE_SHA256,"model_sha256_required":f.MODEL_SHA256,
        "runner_sha256_required":f.RUNNER_SHA256,
        "status":"INCOMPLETE","cases":[],
        "age0":"RECORD_ONLY","step2":"UTILITY_FAIL","b3":"NO_PROMOTION",
        "body_jepa":"UNAVAILABLE","world_jepa":"SHADOW","jepa_weight":0,
        "redmi_measured":False,"whole_system_complete":False,
        "delivery_authority":0,"tool_dispatches":0,"learning_authority":0,
        "tty_approved":False,"output_committed":False,
        "source_only_oracle_hidden":True,
    }
    _save(report_path,report)
    runtime=None
    try:
        initialize(home)
        save_config(home,RUN_CONFIG|{"seed":f.SEED,"temperature":0.0,"answer_tokens":32})
        runtime=cli.Runtime(home)
        model_sha=file_hash(runtime.models.path_for("C3_LANGUAGE"))
        runner_path=Path(os.environ.get("V13_LLAMA_SERVER",str(home/"bin/llama-server")))
        runner_sha=file_hash(runner_path)
        report["model_sha256_observed"]=model_sha
        report["runner_sha256_observed"]=runner_sha
        if model_sha!=f.MODEL_SHA256 or runner_sha!=f.RUNNER_SHA256:
            raise ValueError("RUN70_NATIVE_PINS_RED")
        for row in rows:
            project,domain=row["project"],row["domain"]
            ids=[
                _record(runtime,f"Project {project} archived {domain} policy",row["policy_source"]),
                _record(runtime,f"Project {project} latest {domain} option sheet",row["sheet_source"]),
            ]
            event=runtime.store.event(runtime.session,row["current"])
            envelope=build_jef_c3_typed_envelope(
                runtime.memory,runtime.session,event["event_id"],
                event["source_ref"],ids,operator_opt_in=True)
            if (envelope.get("status")!="JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL"
                    or envelope.get("typed_jef_action")!=row["expected"]
                    or envelope.get("source_rechecked") is not True):
                raise ValueError("RUN70_SOURCE_ENVELOPE_RED")
            case={"index":row["index"],"project_sha256":f.sha(project.encode()),
                  "expected":row["expected"],
                  "source_sha256":{k:f.sha(row[k].encode("utf-8"))
                    for k in ("current","policy_source","sheet_source")},
                  "arms":[]}
            report["cases"].append(case)
            _save(report_path,report)
            order=f.ARMS if row["index"]%2==0 else f.ARMS[::-1]
            for arm in order:
                msgs=f.model_messages(envelope,arm)
                item={"arm":arm,"input_sha256":f.sha(dumps(msgs).encode("utf-8")),
                      "typed_answer_visible":arm=="TYPED_SCHEMA",
                      "native_final":False,"process_reaped":False,
                      "strict":0,"status":"INCOMPLETE"}
                case["arms"].append(item)
                _save(report_path,report)
                previous=len(runtime.pool.release_history)
                try:
                    runner=runtime.pool.get("C3_LANGUAGE")
                    output="".join(runner.generate(
                        msgs,runtime.cancel_event,time.monotonic()+90,
                        32,f.SCHEMA,seed=f.SEED))
                    metrics=dict(runner.last_metrics)
                    item["output"]=output
                    item["output_sha256"]=f.sha(output.encode("utf-8"))
                    item["parsed_action"]=f.run68.decode_schema(output)
                    item["output_bytes"]=len(output.encode("utf-8"))
                    item["native_final"]=metrics.get("status")=="FINAL"
                    item["actual_model"]=metrics.get("actual_model")
                    item["strict"]=f.score(output,row["expected"])
                except Exception as exc:
                    item["error_type"]=type(exc).__name__
                finally:
                    try:
                        runtime.pool.unload()
                    except Exception as exc:
                        item["release_error_type"]=type(exc).__name__
                    releases=runtime.pool.release_history[previous:]
                    item["process_reaped"]=(bool(releases)
                        and any(x.get("before") is not None for x in releases)
                        and all(x.get("process_reaped") is True for x in releases))
                    item["status"]=("RECORDED" if item["native_final"]
                        and item["actual_model"]==C3_FILE and item["process_reaped"]
                        and 0<item.get("output_bytes",0)<=1024
                        else "STRUCTURAL_RED")
                    _save(report_path,report)
                if item["status"]!="RECORDED":
                    raise RuntimeError("RUN70_NATIVE_ROW_RED")
        report["no_live_output"]=(
            runtime.store.one("SELECT COUNT(*) AS n FROM messages WHERE role='assistant' AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"]==0
            and runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"]==0)
    except Exception as exc:
        report["error_type"]=type(exc).__name__
        report["status"]="STRUCTURAL_RED"
    finally:
        if runtime is not None:
            try:
                runtime.close()
            except Exception as exc:
                report["close_error_type"]=type(exc).__name__
                report["status"]="STRUCTURAL_RED"
        try:
            report["closed_store_ok"]=bool(audit_closed(home)["ok"])
        except Exception:
            report["closed_store_ok"]=False
        items=[a for c in report["cases"] for a in c["arms"]]
        report["native_call_count"]=len(items)
        report["strict"]={arm:sum(x["strict"] for x in items if x["arm"]==arm)
                          for arm in f.ARMS}
        structural=(len(report["cases"])==6 and len(items)==12
                    and all(x["status"]=="RECORDED" for x in items)
                    and report.get("no_live_output") is True
                    and report["closed_store_ok"]
                    and report["status"]!="STRUCTURAL_RED")
        if structural:
            report["status"]=("SOURCE_REASONING_SMALL_SYNTHETIC_PASS"
                if report["strict"]["SOURCE_SCHEMA"]>=4
                and report["strict"]["TYPED_SCHEMA"]>=4
                else "SOURCE_REASONING_DIAGNOSTIC_RED")
        else:
            report["status"]="STRUCTURAL_RED"
        _save(report_path,report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    r=run(args.home,args.out)
    print(dumps({"status":r["status"],"strict":r["strict"],
                 "native_call_count":r["native_call_count"]}))
    raise SystemExit(0 if r["status"] in (
        "SOURCE_REASONING_SMALL_SYNTHETIC_PASS",
        "SOURCE_REASONING_DIAGNOSTIC_RED") else 1)


if __name__=="__main__":
    main()
