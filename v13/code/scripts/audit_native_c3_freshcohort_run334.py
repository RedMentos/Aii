#!/usr/bin/env python3
"""Run334 independent read-only report/raw-score/receipt audit.

Does not re-execute native optimizer or re-open deleted GGUF. The native
tensor-byte audits are separate receipt-bound diagnostics in the original run.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from native_c3_freshcohort_run334 import (
    SCHEMA as RUN_SCHEMA, COHORT_SHA, MASTER_SHA, GATES, ARMS, TRAIN,
    CRITERIA, cohort, select, hit, first_sentence, INVALID, PROBES,
)

SCHEMA="V13_RUN334_INDEPENDENT_RAW_SCORE_AUDIT_V1"


def require(cond,message):
    if not cond:
        raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()


def valid_sha(value):
    return isinstance(value,str) and len(value)==64 and all(c in "0123456789abcdef" for c in value)


def recompute(row,data):
    groups=(("facts",data["facts"],"keys","ok"),
            ("paraphrases",data["paraphrases"],"keys","ok"),
            ("near_miss",data["near_miss"],"leak_keys","leak"),
            ("probes",PROBES,"expect","ok"))
    require([len(row.get(name,[])) for name,_,_,_ in groups]==[8,6,5,12],
            "Run334 raw score denominator")
    scores={}
    invalid=0
    for name,items,key_name,flag in groups:
        scores[name]=[]
        for observed,expected in zip(row[name],items):
            q=expected.get("q",expected.get("prompt"))
            require(observed.get("q")==q and type(observed.get("a")) is str,
                    "Run334 raw score order/question")
            ans=observed["a"]
            ok=hit(ans,expected[key_name])
            strict=hit(first_sentence(ans),expected[key_name])
            require(observed.get(flag)==ok and observed.get("strict")==strict,
                    "Run334 raw score label drift")
            invalid+=ans==INVALID
            scores[name].append((ok,strict))
    s=row.get("summary",{})
    expected={
        "facts_strict":sum(x[1] for x in scores["facts"]),
        "paraphrases_strict":sum(x[1] for x in scores["paraphrases"]),
        "near_miss_leak_strict":round(sum(x[1] for x in scores["near_miss"])/5,3),
        "probes_ok":sum(x[0] for x in scores["probes"]),
        "invalid_outputs":invalid,
        "facts_n":8,"paraphrases_n":6,"near_miss_n":5,"probes_n":12,
    }
    require(s==expected and row.get("invalid_outputs")==invalid,
            "Run334 raw summary mismatch")
    return expected


def audit(report,root):
    data=cohort()
    require(report.get("schema")==RUN_SCHEMA
            and report.get("status")=="COMPLETE_NATIVE_THREE_ARM_DIAGNOSTIC"
            and report.get("evidence_level")=="LINUX_NATIVE_C3_FRESH_COHORT_TRAIN_EVAL",
            "Run334 native run incomplete")
    require(report.get("cohort_sha256")==COHORT_SHA
            and report.get("master_sha256")==MASTER_SHA
            and report.get("train")==TRAIN and report.get("criteria")==CRITERIA,
            "Run334 source/cohort/train/threshold drift")
    require(report.get("gates")==GATES
            and report.get("weights_published") is False
            and report.get("model_activated") is False,
            "Run334 original negative gates or activation changed")
    require(report.get("anchors_count")==6, "Run334 frozen anchor count")
    require(set(report.get("arms",{}))==set(ARMS), "Run334 fixed three arms")
    require(valid_sha(report.get("baseline_q4_sha256")), "Run334 baseline quant SHA")
    base=report.get("baseline",{})
    recompute(base,data)
    details={}
    for name,(mode,replay) in ARMS.items():
        arm=report["arms"][name]
        require(arm.get("loss_mode")==mode and arm.get("replay") is replay
                and arm.get("status")=="COMPLETE_NATIVE_DIAGNOSTIC"
                and arm.get("native_training_executed") is True
                and arm.get("train_exit")==0 and arm.get("weights_published") is False
                and arm.get("weights_retained") is False,
                "Run334 arm mode/native execution/weight publication")
        stream=Path(root)/(name+".train.txt")
        require(stream.is_file() and not stream.is_symlink()
                and digest(stream)==arm.get("train_stream_sha256"),
                "Run334 raw train stream missing or hash mismatch")
        for kind in ("stdout","stderr"):
            path=Path(root)/name/("train."+kind+".log")
            require(path.is_file() and not path.is_symlink()
                    and digest(path)==arm.get("train_"+kind+"_sha256"),
                    "Run334 raw train log missing or hash mismatch")
        receipts=arm.get("checkpoint_receipts")
        epochs=arm.get("epochs")
        require(isinstance(receipts,list) and len(receipts)==2
                and isinstance(epochs,list) and len(epochs)==2,
                "Run334 two exact epoch receipts")
        for i,(receipt,epoch) in enumerate(zip(receipts,epochs),1):
            require(receipt.get("epoch")==i and epoch.get("epoch")==i
                    and valid_sha(receipt.get("sha256"))
                    and receipt.get("sha256")==epoch.get("source_sha256")
                    and valid_sha(epoch.get("q4_sha256")),
                    "Run334 epoch/source/quant receipt mismatch")
            recompute(epoch.get("evaluation",{}),data)
        require(arm.get("final_master_sha256")==receipts[-1]["sha256"],
                "Run334 final master checkpoint receipt mismatch")
        expected_selection=select(base,[x["evaluation"] for x in epochs])
        require(arm.get("selection_report")==expected_selection,
                "Run334 selection or heldout threshold drift")
        tensor=arm.get("tensor_audit",{})
        changes=tensor.get("changes",{})
        require(changes.get("unchanged_nonselected")==144
                and changes.get("changed_epoch1") and changes.get("changed_epoch2"),
                "Run334 tensor audit selected-only/nonzero change")
        modes=tensor.get("metadata_modes")
        require(modes==["EXPLICIT_F32","OMITTED_EPOCH_ONLY","OMITTED_EPOCH_ONLY"],
                "Run334 unexpected GGUF metadata mode")
        metrics=tensor.get("metrics",{})
        for stage in ("baseline_to_epoch1","epoch1_to_epoch2"):
            rows=metrics.get(stage,{})
            require(len(rows)==4 and
                    any(v.get("changed_elements",0)>0 and v.get("l2",0)>0
                        for v in rows.values())
                    and all(math.isfinite(v.get("l2",float("nan")))
                            and math.isfinite(v.get("max_abs",float("nan")))
                            for v in rows.values()),
                    "Run334 numerical tensor delta invalid")
        details[name]={"selection":expected_selection["selection"],
                       "selected_epoch":expected_selection["selected_epoch"],
                       "epoch1":expected_selection["rows"][0],
                       "epoch2":expected_selection["rows"][1],
                       "unchanged_nonselected":144}
    return {"schema":SCHEMA,"status":"PASS_SOURCE_ONLY_REPORT_AUDIT_NOT_NATIVE_REEXECUTION",
            "cohort_sha256":COHORT_SHA,"master_sha256":MASTER_SHA,
            "arms":details,"gates":GATES,
            "model_activated":False,"weights_published":False,
            "claim_limit":"Raw report consistency and train-stream hashes only; native GGUF evidence remains in original Run334 execution"}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--report",type=Path,required=True)
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    try:
        result=audit(json.loads(args.report.read_text()),args.root)
    except (ValueError,OSError,TypeError,KeyError,AssertionError) as exc:
        result={"schema":SCHEMA,"status":"FAIL_CLOSED",
                "error":type(exc).__name__+": "+str(exc)[:350],
                "model_activated":False,"weights_published":False,"gates":GATES}
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if result["status"]=="PASS_SOURCE_ONLY_REPORT_AUDIT_NOT_NATIVE_REEXECUTION" else 2)


if __name__=="__main__":
    main()
