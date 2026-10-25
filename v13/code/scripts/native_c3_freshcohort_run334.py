#!/usr/bin/env python3
"""Run334 preregistered fresh-cohort three-arm native C3 learning experiment.

New synthetic cohort and diagnostic thresholds; frozen original Run320 cohort,
model/source pins and all negative gates are never modified or promoted.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write, dumps
from native_cache_bench import Server
from native_lfm2_finetune_bench import FFN_LATE, turn, quantize, hit, first_sentence, INVALID
from lora_bench import ANCHORS, PROBES
from native_lfm2_epoch_eval_run320 import validate_receipts, digest, PINNED_SHA
from audit_native_weight_delta_run333 import inspect, assess, deltas, validate_numeric_deltas

SCHEMA = "V13_RUN334_FRESH_C3_THREE_ARM_NATIVE_EPOCH_V1"
COHORT_SHA = "0bcc0fe92de2bd740b4f2b27b47b325c94827c67f32e519360c6e548cb2b94fb"
COHORT_PATH = Path(__file__).resolve().parents[1] / "docs/proofs/continuation-20261025/run334-c3-freshcohort-learning/RUN334_FRESH_COHORT.json"
MASTER_SHA = "5d200c19f13483e66b39d9feb3353032581882f3eb10cc8752f027d4688d6e6f"
HF_REPO = "LiquidAI/LFM2.5-350M"
HF_REVISION = "9e6c6ccf47cd318696e137d381a7ded8fe4df09f"
LLAMA_SHA = "4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe"
GATES = {"STEP2":"UTILITY_FAIL","B3_L1":"FAIL","Body_JEPA":"UNAVAILABLE","jepa_weight":0,"V13":"INCOMPLETE"}
ARMS = {"A_ALL_NO_REPLAY":("all",False),
        "B_ANSWER_NO_REPLAY":("answer",False),
        "C_ANSWER_REPLAY":("answer",True)}
TRAIN = {"lr":1e-5,"epochs":2,"reps":12,"seed":47,"threads":4,"ctx":256,"batch":256,"ubatch":256}
CRITERIA = {"facts_strict_min":4,"paraphrases_strict_min":2,
            "near_miss_leak_strict_max":0.2,"forgotten_baseline_probes_max":0,
            "invalid_outputs_max":0}


def require(cond, message):
    if not cond:
        raise ValueError(message)


def cohort():
    require(digest(COHORT_PATH) == COHORT_SHA, "Run334 frozen fresh cohort SHA drift")
    data = json.loads(COHORT_PATH.read_text())
    require(data.get("schema") == "V13_RUN334_FRESH_SYNTHETIC_C3_COHORT_V1"
            and data.get("seed") == TRAIN["seed"]
            and data.get("authority") == "SYNTHETIC_TEST_ONLY", "Run334 cohort metadata")
    facts, para, near = (data[k] for k in ("facts","paraphrases","near_miss"))
    require((len(facts),len(para),len(near),len(PROBES)) == (8,6,5,12),
            "Run334 frozen cohort denominator")
    require([x["id"] for x in facts] == ["F"+str(i) for i in range(1,9)]
            and [x["id"] for x in para] == ["P"+str(i) for i in range(1,7)]
            and [x["id"] for x in near] == ["N"+str(i) for i in range(1,6)],
            "Run334 cohort order/ID")
    questions = [r["q"] for group in (facts,para,near) for r in group]
    require(len(set(questions)) == len(questions), "Run334 duplicate question")
    for row in facts:
        require(type(row["a"]) is str and row["a"].strip() and
                type(row["keys"]) is list and len(row["keys"]) == 1 and
                row["keys"][0].lower() in row["a"].lower(), "Run334 fact answer/key")
    for row in para:
        require(type(row["keys"]) is list and len(row["keys"]) == 1,
                "Run334 paraphrase key")
    for row in near:
        require(type(row["leak_keys"]) is list and len(row["leak_keys"]) == 1
                and row["leak_keys"][0] not in row["q"].lower(),
                "Run334 near-miss label leakage")
    return data


def verify_sources(master, manifest):
    base = Path(__file__).resolve().parent
    for name in ("lora_bench.py","native_lfm2_finetune_bench.py","native_cache_bench.py"):
        require(digest(base/name) == PINNED_SHA[name], "Run334 frozen source drift: "+name)
    require(digest(master) == MASTER_SHA, "Run334 exact FP32 master SHA")
    source = json.loads(Path(manifest).read_text())
    require(source.get("hf_repo") == HF_REPO and source.get("hf_revision") == HF_REVISION
            and source.get("master_sha256") == MASTER_SHA
            and source.get("llama_source_sha256") == LLAMA_SHA
            and source.get("conversion_outtype") == "f32", "Run334 source/model provenance")
    return cohort()


def make_stream(server, facts, mode, anchors):
    """Exact inference-template history turns; only answers masked for B/C."""
    require(mode in ("all","answer") and len(anchors) in (0,6),
            "Run334 unregistered loss/anchor mode")
    rng = random.Random(TRAIN["seed"])
    chunks = []
    for rep in range(TRAIN["reps"]):
        rows = [(r["q"],r["a"]) for r in facts]
        if anchors:
            rows.append(anchors[rep%len(anchors)])
        rng.shuffle(rows)
        for q,a in rows:
            prompt,answer,sep = turn(server,q,a)
            chunks.append(prompt + ("\x01"+answer+"\x02" if mode=="answer" else answer) + sep)
    return "".join(chunks)


def get_anchors(server):
    out=[]
    for q in ANCHORS:
        try:
            row=server.post("/completion",{"prompt":server.render([{"role":"user","content":q}]),
                                           "n_predict":96,"temperature":0,"cache_prompt":False})
        except urllib.error.HTTPError:
            continue
        if row.get("stop_type") == "eos" and row.get("content","").strip():
            out.append((q,row["content"]))
        if len(out)==6:
            break
    require(len(out)==6, "Run334 six complete frozen baseline anchors unavailable")
    return out


def evaluate(server, model, log, data):
    s=Server(server,model,["--cache-ram","0"],log)
    try:
        def ask(q):
            try:
                return s.post("/completion",{"prompt":s.render([{"role":"user","content":q}]),
                                             "n_predict":32,"temperature":0,"cache_prompt":False})["content"]
            except urllib.error.HTTPError:
                return INVALID
        def row(q,keys,flag):
            answer=ask(q)
            return {"q":q,"a":answer,flag:hit(answer,keys),
                    "strict":hit(first_sentence(answer),keys)}
        facts=[row(x["q"],x["keys"],"ok") for x in data["facts"]]
        para=[row(x["q"],x["keys"],"ok") for x in data["paraphrases"]]
        near=[row(x["q"],x["leak_keys"],"leak") for x in data["near_miss"]]
        probes=[row(x["prompt"],x["expect"],"ok") for x in PROBES]
    finally:
        s.stop()
    invalid=sum(x["a"]==INVALID for group in (facts,para,near,probes) for x in group)
    summary={"facts_strict":sum(x["strict"] for x in facts),
             "paraphrases_strict":sum(x["strict"] for x in para),
             "near_miss_leak_strict":round(sum(x["strict"] for x in near)/len(near),3),
             "probes_ok":sum(x["ok"] for x in probes),
             "invalid_outputs":invalid,
             "facts_n":len(facts),"paraphrases_n":len(para),
             "near_miss_n":len(near),"probes_n":len(probes)}
    return {"facts":facts,"paraphrases":para,"near_miss":near,"probes":probes,
            "invalid_outputs":invalid,"summary":summary}


def select(base, epochs):
    require(len(base["probes"])==12 and len(epochs)==2,"Run334 baseline/epoch denominator")
    rows=[]
    for i,row in enumerate(epochs,1):
        require((len(row["facts"]),len(row["paraphrases"]),len(row["near_miss"]),
                 len(row["probes"]))==(8,6,5,12),"Run334 epoch cohort denominator")
        s=row["summary"]
        forgotten=[x["q"] for x,y in zip(base["probes"],row["probes"]) if x["ok"] and not y["ok"]]
        measured={"epoch":i,"facts_strict":s["facts_strict"],
                  "paraphrases_strict":s["paraphrases_strict"],
                  "near_miss_leak_strict":s["near_miss_leak_strict"],
                  "forgotten_baseline_probes":len(forgotten),
                  "forgotten_questions":forgotten,"invalid_outputs":row["invalid_outputs"]}
        measured["diagnostic_pass"]=bool(
            measured["facts_strict"]>=CRITERIA["facts_strict_min"]
            and measured["paraphrases_strict"]>=CRITERIA["paraphrases_strict_min"]
            and measured["near_miss_leak_strict"]<=CRITERIA["near_miss_leak_strict_max"]
            and measured["forgotten_baseline_probes"]<=CRITERIA["forgotten_baseline_probes_max"]
            and measured["invalid_outputs"]==0)
        rows.append(measured)
    selected=next((r["epoch"] for r in rows if r["diagnostic_pass"]),None)
    return {"criteria":dict(CRITERIA),"rows":rows,"selected_epoch":selected,
            "selection":"CANDIDATE_ONLY_NO_ACTIVATION" if selected else "NONE",
            "AG6_promoted":False,"Body_JEPA_promoted":False}


def tensor_audit(master,epoch1,epoch2):
    """Run333 strict structural/numerical primitives, new receipt-bound files."""
    mreader,m,mraw,mmode=inspect(master,master=True)
    r1,e1,raw1,mode1=inspect(epoch1,master=False)
    r2,e2,raw2,mode2=inspect(epoch2,master=False)
    changes=assess(m,e1,e2)
    metrics={"baseline_to_epoch1":deltas(mraw,raw1),
             "epoch1_to_epoch2":deltas(raw1,raw2)}
    validate_numeric_deltas(metrics)
    assert mreader is not None and r1 is not None and r2 is not None
    return {"changes":changes,"metrics":metrics,
            "metadata_modes":[mmode,mode1,mode2],
            "selected_sha256":{name:[m[name]["sha256"],e1[name]["sha256"],e2[name]["sha256"]]
                               for name in sorted(m) if name in
                               ("blk.12.ffn_down.weight","blk.13.ffn_down.weight",
                                "blk.14.ffn_down.weight","blk.15.ffn_down.weight")}}


def run(tool_dir,server,master,manifest,out):
    tool_dir,server,master,manifest,out=map(Path,(tool_dir,server,master,manifest,out))
    if out.exists():
        raise FileExistsError("Run334 output already exists")
    for p in (server,master,manifest,tool_dir/"native-answer-epoch-checkpoint-run319",
              tool_dir/"llama-quantize"):
        require(p.is_file() and not p.is_symlink(),"Run334 regular pinned source/binary required")
    data=verify_sources(master,manifest)
    out.mkdir(parents=True)
    report={"schema":SCHEMA,"status":"INCOMPLETE","evidence_level":"LINUX_NATIVE_PENDING",
            "cohort_sha256":COHORT_SHA,"master_sha256":MASTER_SHA,
            "hf_repo":HF_REPO,"hf_revision":HF_REVISION,
            "model_license":"LFM Open License v1.0",
            "train":dict(TRAIN),"criteria":dict(CRITERIA),
            "gates":dict(GATES),"weights_published":False,
            "model_activated":False,"arms":{},
            "claim_limit":"New synthetic C3 cohort only; no AG6, Body-JEPA, Redmi or V13 promotion"}
    report_path=out/"RUN334_REPORT.json"
    def save():
        atomic_write(report_path,(dumps(report)+"\n").encode())
    save()
    try:
        s=Server(server,master,["--cache-ram","0"],out/"template.log")
        try:
            anchors=get_anchors(s)
            streams={name:make_stream(s,data["facts"],mode,anchors if replay else [])
                     for name,(mode,replay) in ARMS.items()}
        finally:
            s.stop()
        report["anchors_count"]=len(anchors)
        report["anchor_prompt_sha256"]=hashlib.sha256(
            json.dumps([q for q,_ in anchors],sort_keys=True).encode()).hexdigest()
        for name,stream in streams.items():
            (out/(name+".train.txt")).write_text(stream)
        baseline_q4=out/"baseline-q4.gguf"
        quantize(tool_dir,master,baseline_q4,FFN_LATE)
        report["baseline_q4_sha256"]=digest(baseline_q4)
        baseline=evaluate(server,baseline_q4,out/"eval-baseline.log",data)
        report["baseline"]=baseline
        report["status"]="BASELINE_EVALUATED"
        save()
        for name,(mode,replay) in ARMS.items():
            arm_dir=out/name
            arm_dir.mkdir()
            trained=arm_dir/"trained-f32.gguf"
            stream=out/(name+".train.txt")
            row={"loss_mode":mode,"replay":replay,"train_stream_sha256":digest(stream),
                 "status":"INCOMPLETE","native_training_executed":False,
                 "checkpoint_receipts":[],"epochs":[],"weights_published":False}
            report["arms"][name]=row
            save()
            env=dict(os.environ,V13_TRAIN_TENSORS=",".join(FFN_LATE),
                     V13_EPOCH_CHECKPOINTS="1",V13_LOSS_MODE=mode,V13_KL_WEIGHT="0")
            cmd=[str(tool_dir/"native-answer-epoch-checkpoint-run319"),
                 "-m",str(master),"-f",str(stream),"-o",str(trained),
                 "-c","256","-b","256","-ub","256","--epochs","2",
                 "-lr","1e-5","-t","4","-s","47"]
            start=time.monotonic()
            try:
                p=subprocess.run(cmd,env=env,capture_output=True,text=True,
                                 errors="replace",timeout=1000)
                stdout,stderr,rc=p.stdout,p.stderr,p.returncode
            except subprocess.TimeoutExpired as exc:
                stdout=(exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout,bytes) else (exc.stdout or "")
                stderr=(exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr,bytes) else (exc.stderr or "")
                rc=124
            (arm_dir/"train.stdout.log").write_text(stdout)
            (arm_dir/"train.stderr.log").write_text(stderr)
            row.update({"train_exit":rc,"train_wall_s":round(time.monotonic()-start,2),
                        "train_stdout_sha256":digest(arm_dir/"train.stdout.log"),
                        "train_stderr_sha256":digest(arm_dir/"train.stderr.log")})
            row["status"]="TRAIN_FAILED" if rc else "TRAIN_FINISHED"
            save()
            if rc:
                raise ValueError("Run334 native optimizer failed: "+name)
            receipts=validate_receipts(stdout,trained,epochs=2)
            row["checkpoint_receipts"]=receipts
            row["native_training_executed"]=True
            row["final_master_sha256"]=digest(trained)
            require(row["final_master_sha256"]==receipts[-1]["sha256"],
                    "Run334 final epoch SHA mismatch")
            row["status"]="CHECKPOINTS_VERIFIED"
            save()
            candidates=[]
            for epoch in (1,2):
                source=Path(str(trained)+".epoch"+str(epoch)+".gguf")
                require(digest(source)==receipts[epoch-1]["sha256"],
                        "Run334 epoch SHA changed")
                q4=arm_dir/("epoch"+str(epoch)+"-q4.gguf")
                quantize(tool_dir,source,q4,FFN_LATE)
                evaluated=evaluate(server,q4,arm_dir/("eval-epoch"+str(epoch)+".log"),data)
                candidates.append(evaluated)
                row["epochs"].append({"epoch":epoch,"source_sha256":digest(source),
                                      "q4_sha256":digest(q4),"evaluation":evaluated})
                row["status"]="EPOCH_"+str(epoch)+"_EVALUATED"
                save()
            row["selection_report"]=select(baseline,candidates)
            row["tensor_audit"]=tensor_audit(master,
                Path(str(trained)+".epoch1.gguf"),Path(str(trained)+".epoch2.gguf"))
            row["status"]="COMPLETE_NATIVE_DIAGNOSTIC"
            save()
        report["status"]="COMPLETE_NATIVE_THREE_ARM_DIAGNOSTIC"
        report["evidence_level"]="LINUX_NATIVE_C3_FRESH_COHORT_TRAIN_EVAL"
        save()
        return report
    except BaseException as exc:
        report["status"]="FAIL_CLOSED"
        report["error"]={"type":type(exc).__name__,"message":str(exc)[:350]}
        save()
        return report


def main():
    ap=argparse.ArgumentParser()
    for name in ("tool-dir","server","master","source-manifest","out-dir"):
        ap.add_argument("--"+name,required=True)
    args=ap.parse_args()
    result=run(args.tool_dir,args.server,args.master,args.source_manifest,args.out_dir)
    print(dumps({"status":result["status"],
                 "arms":{k:v.get("selection_report",{}).get("selection")
                         for k,v in result.get("arms",{}).items()}}))
    raise SystemExit(0 if result["status"]=="COMPLETE_NATIVE_THREE_ARM_DIAGNOSTIC" else 2)


if __name__=="__main__":
    main()
