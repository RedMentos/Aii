#!/usr/bin/env python3
"""Summarize an existing STEP2 real-weight ablation without promoting any gate.

This intentionally uses only recorded evidence. It does not rerun inference and it does
not infer semantic correctness from lexical number coverage.
"""
import argparse, json, statistics
from pathlib import Path

SINGLES={"b1_only","b2_only"}
BOTH={"both_none","both_exact","both_control"}

def count_true(d): return sum(bool(v) for v in (d or {}).values())

def task_score(row):
    """Use only task-specific assertions recorded by the real-weight runner.

    Unlike expected-number presence, these assertions bind a value/decision to its
    subject. They remain deterministic benchmark evidence, not a semantic judge.
    """
    a=row.get("task_assertions") or {}
    if not isinstance(a,dict) or not a:return None
    vals=[bool(v) for v in a.values()]
    return {"passed":sum(vals),"total":len(vals),"fraction":sum(vals)/len(vals) if vals else None}

def analyze(p):
    rows=p.get("rows",[]); fixtures={f["id"]:f for f in p.get("fixtures",[]) if "id" in f}
    out={
      "proof_kind":"STEP2_ABLATION_ANALYSIS", "analysis_version":1,
      "source_proof_kind":p.get("proof_kind"), "source_status":p.get("status"),
      "uses_real_weights":bool(p.get("uses_real_weights")), "phone_measured":bool(p.get("phone_measured")),
      "gate_promotion":False, "complementarity_proven":False, "fixtures":[],
      "claim_limits":[
        "Lexical expected-number coverage is diagnostic only; it is not semantic correctness.",
        "Task assertions are deterministic fixture-specific checks, not an LLM semantic judge or general reasoning proof.",
        "A positive signal on one fixture does not prove general B1/B2 complementarity.",
        "Linux process RSS does not prove target-phone sustained RSS or thermal safety."
      ]}
    peak=[]; lats=[]; signals=[]
    for fid,fixture in fixtures.items():
        rs=[r for r in rows if r.get("fixture")==fid and r.get("status")=="CHECKS_PASS"]
        vals=[]
        for r in rs:
            cov=count_true((r.get("lexical_number_coverage") or {}).get("final"))
            m=r.get("measurements") or {}; lat=m.get("turn_s"); rss=m.get("sampled_native_peak_rss_bytes")
            vals.append({"variant":r.get("variant"),"expected_number_hits":cov,"task_score":task_score(r),"turn_s":lat,"sampled_native_peak_rss_bytes":rss})
            if isinstance(lat,(int,float)):lats.append(lat)
            if isinstance(rss,(int,float)):peak.append(rss)
        single=max((v["expected_number_hits"] for v in vals if v["variant"] in SINGLES),default=0)
        both=max((v["expected_number_hits"] for v in vals if v["variant"] in BOTH),default=0)
        positive=both>single
        task_singles=[v["task_score"]["fraction"] for v in vals if v["variant"] in SINGLES and v.get("task_score") and v["task_score"]["fraction"] is not None]
        task_both=[v["task_score"]["fraction"] for v in vals if v["variant"] in BOTH and v.get("task_score") and v["task_score"]["fraction"] is not None]
        best_task_single=max(task_singles,default=None);best_task_both=max(task_both,default=None)
        task_positive=best_task_single is not None and best_task_both is not None and best_task_both>best_task_single
        if positive:signals.append(fid)
        out["fixtures"].append({"id":fid,"expected_numbers":fixture.get("expected_numbers",[]),"variants":vals,"best_single_hits":single,"best_both_hits":both,"diagnostic_positive_combination_signal":positive,"best_single_task_fraction":best_task_single,"best_both_task_fraction":best_task_both,"task_bound_positive_combination_signal":task_positive})
    out["measurements"]={
      "max_sampled_native_peak_rss_bytes":max(peak) if peak else None,
      "median_turn_s":statistics.median(lats) if lats else None,
      "max_turn_s":max(lats) if lats else None,
      "diagnostic_positive_signal_fixtures":signals,
      "diagnostic_positive_signal_count":len(signals),
      "fixture_count":len(fixtures)
    }
    out["status"]="DIAGNOSTIC_SIGNAL_ONLY" if signals else "NO_DIAGNOSTIC_COMPLEMENTARITY_SIGNAL"
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("proof");ap.add_argument("--out",required=True);a=ap.parse_args()
    p=json.loads(Path(a.proof).read_text());o=analyze(p);Path(a.out).write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":o["status"],"signals":o["measurements"]["diagnostic_positive_signal_fixtures"],"gate_promotion":False}))
if __name__=="__main__":main()
