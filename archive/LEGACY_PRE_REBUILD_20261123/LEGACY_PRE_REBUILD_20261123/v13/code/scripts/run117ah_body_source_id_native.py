#!/usr/bin/env python3
"""Run117AH pinned native B1/B2 source-ID quote diagnostic, seed1069.

Five serial Body calls per row: prior B2 baseline and ID, current B1
baseline and ID, current B2 salient baseline. Exports full persisted packet
bytes and SourceRefs for independent audit. No native C3 or live output.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

from scripts.run111_c3_b2_context_native import _prepare_home
from scripts.run113b_b1b2_c3_native import _config, _pin_models, _reaped, MODELS
from scripts.run117u_seed1061_native_three_arm import _observe, _body_messages
from v13.b1b2_source_id_quote_candidate import select, KIND
from v13.common import atomic_write, dumps
from v13.runtime import Runtime
from v13.store import audit_closed

SEED=1069
FIXTURE_SHA="cff778da793fbab2d456143b5d8290176b1097cc0e4d867eabbd9fbc2e05f67a"
IDS=("Auric","Beryl","Cobalt","Daphne","Elder","Fable")
CONFIG=_config()|{
    "seed":SEED,"temperature":0.0,"threads":2,
    "learning_mode":"RECORD_ONLY","observer_mode":"off",
    "answer_tokens":64,"observer_tokens":256,
    "observer_seconds":120,"deadline_seconds":180,
    "history_turns":0,"memory_top_k":0,
    "body_residency_mb":0,"teacher_enabled":False,
    "offer_quote_context_chars":200,"b2_quote_select":"pointer",
    "b2_state_slots":2,"b2_context_chars":1500,
    "b2_offer_body_state":False,
}
SCHEMA="v13.run117ah.body_source_id_native_seed1069.v1"
COMPLETE="NATIVE_COMPLETE_BODY_ID_DIAGNOSTIC"
RED="STRUCTURAL_RED"


def fixture(path):
    data=Path(path).read_bytes()
    if sha256(data).hexdigest()!=FIXTURE_SHA:
        raise ValueError("RUN117AH_FIXTURE_SHA_RED")
    value=json.loads(data)
    if (value["schema"]!="v13.run117ah.body_source_id_seed1069.v1"
            or value["seed"]!=SEED
            or value["roles"]!=["B1_DETAIL","B2_GIST"]
            or [r["id"] for r in value["rows"]]!=list(IDS)):
        raise ValueError("RUN117AH_FIXTURE_SHAPE_RED")
    return value["rows"]


def _raw_packet(runtime,packet_id):
    row=runtime.store.one(
        "SELECT kind,payload FROM packets WHERE id=?",(packet_id,))
    if row is None:
        raise ValueError("RUN117AH_PERSISTED_PACKET_MISSING_RED")
    raw=row["payload"]
    return {"kind":row["kind"],"raw":raw,
            "sha256":sha256(raw.encode()).hexdigest()}


def _baseline(runtime,event,role,phase,entry,report,save,*,salient=False):
    item=_observe(runtime,event,role,phase,entry,report,save,
                  salient=salient)
    if item["status"]=="RECORDED":
        item["packet_evidence"]=_raw_packet(runtime,item["packet_id"])
        item["query_evidence"]=_raw_packet(runtime,item["query_packet_id"])
        if (item["packet_evidence"]["kind"]!="OfferPacket"
                or item["query_evidence"]["kind"]!="QueryPacket"):
            item["status"]=RED
    save()
    return item


def _id_native(runtime,event,role,phase,entry,report,save):
    item={"role":role,"phase":phase,"status":"INCOMPLETE",
          "source_ref":event["source_ref"],"native_final":False,
          "process_reaped":False,"model_id_correct":False}
    entry["id_selections"].append(item)
    save()
    before=len(runtime.pool.release_history)
    def generate(messages):
        data=json.loads(messages[1]["content"])
        ids=[c["span_id"] for c in data["candidates"]]
        if (len(ids)!=2 or len(set(ids))!=2
                or data["role"]!=role or data["source_role"]!=
                "UNTRUSTED_EXACT_USER"):
            raise ValueError("RUN117AH_MODEL_PROMPT_SHAPE_RED")
        schema={"type":"object","additionalProperties":False,
                "required":["span_id"],"properties":{
                    "span_id":{"type":"string","enum":ids+["NONE"]}}}
        runner=runtime.pool.get(role)
        report["native_body_calls"]+=1
        save()
        output="".join(runner.generate(
            messages,runtime.cancel_event,time.monotonic()+120,
            64,schema,seed=SEED))
        metrics=dict(runner.last_metrics)
        item["raw_output"]=output
        item["native_metrics"]=metrics
        item["native_final"]=metrics.get("status")=="FINAL"
        return {"raw":output,"metrics":metrics}
    try:
        result=select(runtime,event,role,generate,
                      operator_opt_in=True,callback_opt_in=True)
        item["component_status"]=result["status"]
        item["model_id_correct"]=result.get(
            "selection_correct_shadow") is True
        if result.get("packet_id"):
            item["packet_id"]=result["packet_id"]
            item["packet_evidence"]=_raw_packet(
                runtime,result["packet_id"])
            if item["packet_evidence"]["kind"]!=KIND:
                raise ValueError("RUN117AH_SELECTION_PACKET_KIND_RED")
        item["status"]="RECORDED" if (
            item["native_final"] and result["status"] in (
                "SHADOW_SOURCE_ID_SELECTED",
                "SHADOW_WRONG_SOURCE_ID_RECORDED",
                "SHADOW_ABSTAIN_RECORDED")
            and item.get("packet_id")
            and item.get("native_metrics",{}).get("actual_model")==
            MODELS[role][0]) else RED
    except Exception as exc:
        item["status"]=RED
        item["error_type"]=type(exc).__name__
        item["error"]=str(exc)[:240]
    finally:
        runtime.pool.unload()
        item["process_reaped"]=_reaped(
            runtime.pool.release_history[before:])
        if not item["process_reaped"]:
            item["status"]=RED
        save()
    return item


def _run_row(row,work,report,save,installed):
    home=work/row["id"]
    _prepare_home(home,installed,CONFIG)
    runtime=Runtime(home)
    entry={"id":row["id"],"status":"INCOMPLETE",
           "offers":[],"id_selections":[],
           "baseline_quote_ready":False,
           "closed_store_ok":False,"no_live_output":False}
    report["rows"].append(entry)
    save()
    try:
        prior=runtime.store.event(runtime.session,row["prior"])
        entry["prior_source_ref"]=prior["source_ref"]
        entry["prior_source_text"]=runtime.store.read_source(
            prior["source_ref"])
        b2_prior=_baseline(runtime,prior,"B2_GIST","prior",
                           entry,report,save)
        id_prior=_id_native(runtime,prior,"B2_GIST","prior",
                            entry,report,save)
        current=runtime.store.event(runtime.session,row["current"])
        entry["current_source_ref"]=current["source_ref"]
        entry["current_source_text"]=runtime.store.read_source(
            current["source_ref"])
        b1=_baseline(runtime,current,"B1_DETAIL","current",
                     entry,report,save)
        id_current=_id_native(runtime,current,"B1_DETAIL","current",
                              entry,report,save)
        b2_current=_baseline(runtime,current,"B2_GIST","current",
                             entry,report,save,salient=True)
        if all(x["status"]=="RECORDED" for x in
               (b2_prior,b1,b2_current)):
            ids={"B1_DETAIL":b1["packet_id"],
                 "B2_GIST":b2_current["packet_id"]}
            messages,error=_body_messages(runtime,current,ids,row)
            entry["baseline_quote_ready"]=messages is not None
            entry["baseline_quote_error"]=error
            if messages is not None:
                entry["baseline_prompt_sha256"]=sha256(
                    dumps(messages).encode()).hexdigest()
        else:
            entry["baseline_quote_error"]="BASELINE_OFFER_STRUCTURAL_RED"
        entry["id_pair_correct"]=all(x["model_id_correct"]
                                      for x in (id_prior,id_current))
        entry["status"]=("RECORDED" if all(x["status"]=="RECORDED"
            for x in (b2_prior,b1,b2_current,id_prior,id_current))
            else RED)
    except Exception as exc:
        entry["status"]=RED
        entry["error_type"]=type(exc).__name__
        entry["error"]=str(exc)[:240]
    finally:
        try:
            entry["no_live_output"]=(
                runtime.store.one(
                    "SELECT COUNT(*) AS n FROM actions")["n"]==0
                and runtime.store.one(
                    "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"]==0)
        except Exception:
            entry["no_live_output"]=False
        runtime.close()
        try:
            entry["closed_store_ok"]=bool(audit_closed(home)["ok"])
        except Exception:
            entry["closed_store_ok"]=False
        if not entry["no_live_output"] or not entry["closed_store_ok"]:
            entry["status"]=RED
        save()


def _summarize(report):
    report["baseline_quote_ready_count"]=sum(
        bool(r.get("baseline_quote_ready")) for r in report["rows"])
    report["model_id_pair_correct_count"]=sum(
        bool(r.get("id_pair_correct")) for r in report["rows"])
    report["model_id_by_role_correct"]={
        role:sum(bool(x.get("model_id_correct")) for row in report["rows"]
                 for x in row.get("id_selections",[]) if x["role"]==role)
        for role in ("B1_DETAIL","B2_GIST")}
    if (len(report["rows"])!=6 or report["native_body_calls"]!=30
            or report["native_c3_calls"]!=0
            or report["native_jef_calls"]!=0
            or report["native_c2_calls"]!=0):
        return RED
    for row in report["rows"]:
        if (row["status"]!="RECORDED"
                or len(row["offers"])!=3
                or len(row["id_selections"])!=2
                or not row["closed_store_ok"]
                or not row["no_live_output"]):
            return RED
        for item in row["offers"]+row["id_selections"]:
            if (item["status"]!="RECORDED"
                    or item["process_reaped"] is not True
                    or item["native_metrics"]["status"]!="FINAL"
                    or item["packet_evidence"]["sha256"]!=sha256(
                        item["packet_evidence"]["raw"].encode()).hexdigest()):
                return RED
    return COMPLETE


def run(fixture_path,installed,work,out):
    rows=fixture(fixture_path)
    installed,work,out=Path(installed).resolve(),Path(work),Path(out)
    if work.exists() or out.exists():
        raise FileExistsError("RUN117AH_FRESH_WORK_OUT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    report={"schema":SCHEMA,"seed":SEED,"fixture_sha256":FIXTURE_SHA,
            "status":"INCOMPLETE","native_body_calls":0,
            "native_c3_calls":0,"native_jef_calls":0,"native_c2_calls":0,
            "rows":[],"age0":"RECORD_ONLY",
            "step2_exit":"EVIDENCE_NOT_PASSING","b3":"NO_PROMOTION",
            "body_jepa":"UNAVAILABLE","jepa_weight":0,
            "redmi_measured":False,"whole_system_complete":False,
            "output_committed":False,"tool_dispatches":0,
            "learning_authority":0,"delivery_authority":0}
    def save():
        atomic_write(out/"report.json",dumps(report))
    save()
    try:
        _pin_models(installed)
        for row in rows:
            _run_row(row,work,report,save,installed)
        report["status"]=_summarize(report)
    except Exception as exc:
        report["status"]=RED
        report["error_type"]=type(exc).__name__
        report["error"]=str(exc)[:240]
    save()
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fixture",type=Path,required=True)
    p.add_argument("--installed",type=Path,required=True)
    p.add_argument("--work",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    r=run(a.fixture,a.installed,a.work,a.out)
    print(dumps({"status":r["status"],
                 "native_body_calls":r["native_body_calls"],
                 "baseline_quote_ready_count":r.get("baseline_quote_ready_count"),
                 "model_id_pair_correct_count":r.get(
                     "model_id_pair_correct_count")}))
    return 0 if r["status"]==COMPLETE else 2


if __name__=="__main__":
    raise SystemExit(main())
