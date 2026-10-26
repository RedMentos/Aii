#!/usr/bin/env python3
"""Run608: prospectively frozen native B1→B2 paraphrase proxy, SHADOW only.

No bridge activation, receiver injection, weight updates or gate promotion.
The cohort, protocol and pre-inference amendment were committed first.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time

import numpy as np

from v13.common import APP, atomic_write, dumps
from v13.config import DEFAULTS
from v13.runners import TAP_SPECS
from scripts import run606_cross_body_latent_shadow as R606

PROOF=APP/"docs/proofs/continuation-20261026/run608-cross-body-paraphrase"
COHORT=PROOF/"RUN608_COHORT.json"
COHORT_BLOB="f452bdf80bb8d8a784c1909c98e310041d3157aa"
SEED=20261026
ALPHA=1.0
CONTROLS=200
TRAIN_TOPICS=("transport","cooking","astronomy","gardening","finance","sports")
TEST_TOPICS=("music","weather")
GATES=dict(R606.GATES)


def load_cohort(path=COHORT):
    if R606.git_blob_sha(path)!=COHORT_BLOB:
        raise ValueError("Run608 frozen cohort SHA mismatch")
    d=json.loads(Path(path).read_text(encoding="utf-8"))
    rows=d.get("prompts",[])
    if (d.get("schema")!="V13_RUN608_PARAPHRASE_COHORT_V1"
            or d.get("seed")!=SEED or tuple(d.get("train_topics",[]))!=TRAIN_TOPICS
            or tuple(d.get("test_topics",[]))!=TEST_TOPICS
            or len(rows)!=80 or len({r.get("id") for r in rows})!=80
            or len({r.get("text") for r in rows})!=80):
        raise ValueError("Run608 cohort schema/size/seed mismatch")
    facts={}
    for row in rows:
        if (row.get("topic") not in TRAIN_TOPICS+TEST_TOPICS
                or row.get("variant") not in ("A","B")
                or not isinstance(row.get("text"),str) or not row["text"].strip()
                or row.get("fact_id")!=row["id"].rsplit("-",1)[0]):
            raise ValueError("Run608 malformed fact/variant")
        facts.setdefault(row["fact_id"],[]).append(row)
    if (len(facts)!=40 or any(len(v)!=2 or {r["variant"] for r in v}!={"A","B"}
                              or len({r["topic"] for r in v})!=1 for v in facts.values())
            or any(sum(r["topic"]==topic for r in rows)!=10 for topic in TRAIN_TOPICS+TEST_TOPICS)):
        raise ValueError("Run608 paired facts or topic split mismatch")
    return d


def lexical_top1(rows,test,opposite):
    tokens=lambda s:set(re.findall(r"[a-z0-9]+",s.lower()))
    sets=[tokens(rows[i]["text"]) for i in test]
    correct=0
    for i,source in enumerate(sets):
        similarities=[]
        for j,target in enumerate(sets):
            if i==j:similarities.append(float("-inf"));continue
            union=len(source|target)
            similarities.append(len(source&target)/union if union else 0.)
        correct+=int(int(np.argmax(similarities))==opposite[i])
    return correct/len(test)


def normalize(x):
    return R606.normalize(x)


def evaluate(x,y,train,test,rows,seed=SEED,controls=CONTROLS):
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y,dtype=np.float64)
    train=np.asarray(train,dtype=int);test=np.asarray(test,dtype=int)
    if (x.shape!=(80,2048) or y.shape!=(80,1024)
            or len(train)!=60 or len(test)!=20 or len(set(train))!=60
            or len(set(test))!=20 or set(train)&set(test)
            or not np.array_equal(train,np.array([i for i,r in enumerate(rows) if r["topic"] in TRAIN_TOPICS]))
            or not np.array_equal(test,np.array([i for i,r in enumerate(rows) if r["topic"] in TEST_TOPICS]))
            or controls<1):
        raise ValueError("Run608 state dimensions or frozen split mismatch")
    x=normalize(x);y=normalize(y)
    xm=x[train].mean(0);ym=y[train].mean(0)
    xt=normalize(x[train]-xm);xv=normalize(x[test]-xm)
    yt=normalize(y[train]-ym);yv=normalize(y[test]-ym)
    cross=xv@xt.T
    ridge=np.linalg.solve(xt@xt.T+ALPHA*np.eye(len(train)),np.eye(len(train)))
    ids={rows[idx]["id"]:i for i,idx in enumerate(test)}
    opposite=[]
    for idx in test:
        r=rows[idx]
        other=r["fact_id"]+"-"+("B" if r["variant"]=="A" else "A")
        if other not in ids:raise ValueError("heldout opposite paraphrase missing")
        opposite.append(ids[other])
    opposite=np.asarray(opposite,dtype=int)
    if np.any(opposite==np.arange(len(test))):
        raise ValueError("opposite maps to same prompt")
    def score(targets):
        pred=normalize(cross@ridge@targets)
        sim=pred@yv.T
        exact=float(np.mean(np.argmax(sim,axis=1)==np.arange(len(test))))
        cross_sim=sim.copy()
        np.fill_diagonal(cross_sim,float("-inf"))
        para=float(np.mean(np.argmax(cross_sim,axis=1)==opposite))
        matched=float(np.mean(sim[np.arange(len(test)),opposite]))
        return exact,para,matched
    observed=score(yt)
    rng=np.random.default_rng(seed)
    null=np.asarray([score(yt[rng.permutation(len(train))]) for _ in range(controls)])
    p_exact=(1+int(np.count_nonzero(null[:,0]>=observed[0])))/(controls+1)
    p_para=(1+int(np.count_nonzero(null[:,1]>=observed[1])))/(controls+1)
    lexical=lexical_top1(rows,test,opposite)
    signal=bool(observed[1]>=.25 and p_para<=.05 and observed[1]-lexical>=.10)
    # Secondary representational similarity; permute whole B2 heldout rows,
    # not the dependent 190 pairwise entries.
    u,v=np.triu_indices(len(test),1)
    aa=(xv@xv.T)[u,v];bbmat=yv@yv.T
    def corr(a,b):
        a=a-a.mean();b=b-b.mean()
        den=np.linalg.norm(a)*np.linalg.norm(b)
        if den<=1e-12:raise ValueError("degenerate geometry")
        return float(a@b/den)
    rsa=corr(aa,bbmat[u,v])
    rsa_null=np.asarray([corr(aa,bbmat[np.ix_(p,p)][u,v])
                         for p in (rng.permutation(len(test)) for _ in range(controls))])
    nn_a=np.argmax(xv@xv.T-np.eye(len(test))*10,axis=1)
    nn_b=np.argmax(bbmat-np.eye(len(test))*10,axis=1)
    return {"observed":{"exact_top1":observed[0],"opposite_paraphrase_top1":observed[1],
                         "opposite_matched_cosine":observed[2]},
            "lexical_jaccard_opposite_top1":lexical,
            "opposite_advantage_over_lexical":observed[1]-lexical,
            "shuffled":{"n":controls,"mean_exact_top1":float(null[:,0].mean()),
                        "mean_opposite_top1":float(null[:,1].mean()),
                        "p95_opposite_top1":float(np.percentile(null[:,1],95))},
            "empirical_p_exact":p_exact,"empirical_p_opposite":p_para,
            "rsa":{"pearson":rsa,"empirical_p":float((1+np.count_nonzero(rsa_null>=rsa))/(controls+1)),
                   "null_mean":float(rsa_null.mean())},
            "nearest_neighbor_agreement":float(np.mean(nn_a==nn_b)),
            "paraphrase_proxy_signal":signal,"chance_opposite":1/19,
            "chance_exact":1/20,"train_n":len(train),"heldout_n":len(test),
            "alpha":ALPHA,"seed":seed,
            "claim":"Independent synthetic paraphrase source retrieval proxy, no B3/JEPA/receiver utility"}


def run(home,out,states_path):
    home,out,states_path=Path(home),Path(out),Path(states_path)
    out.parent.mkdir(parents=True,exist_ok=True);states_path.parent.mkdir(parents=True,exist_ok=True)
    report={"schema":"V13_RUN608_NATIVE_PARAPHRASE_PROXY_V1","status":"INCOMPLETE",
            "evidence_level":"LINUX_NATIVE_PAIRED_READONLY","gates":dict(GATES),
            "cohort_blob":COHORT_BLOB,"seed":SEED,"no_weight_updates":True,
            "can_latent_inject":False,"b3_promoted":False,"redmi_measured":False,
            "canonical_architecture_complete":False,"user_full_scope_complete":False}
    def save():atomic_write(out,(dumps(report)+"\\n").encode())
    save()
    try:
        cohort=load_cohort();rows=cohort["prompts"]
        specs=json.loads((APP/"specs/models.json").read_text())
        if specs["runner"]["linux_binaries"]["linux-x86_64"]["sha256"]!=R606.ARCHIVE_SHA:
            raise ValueError("pinned native runner archive mismatch")
        server=home/"bin/llama-server"
        if not server.is_file():raise ValueError("native server missing")
        report["runner_sha256"]=R606.file_sha(server)
        arrays=[];receipts={}
        with tempfile.TemporaryDirectory(prefix="v13-run608-") as td:
            for role,key,sha,dim in (("B1_DETAIL","body",R606.B1_SHA,2048),
                                      ("B2_GIST","gist",R606.B2_SHA,1024)):
                spec=specs["models"][key]
                model=home/"models"/key/spec["main_file"]
                if R606.file_sha(model)!=sha or spec["files"][0]["sha256"]!=sha:
                    raise ValueError("pinned "+role+" model hash mismatch")
                if TAP_SPECS[key][1]!=dim:raise ValueError("native tap dimension changed")
                values,rc=R606.capture(model,server,role,key,rows,Path(td)/key)
                arrays.append(values);receipts[role]=rc
                report.setdefault("models",{})[role]={"model_id":spec["model_id"],
                    "revision":spec["revision"],"sha256":sha,"tap_id":TAP_SPECS[key][0],
                    "dimension":dim,"rows":len(values)}
                report.setdefault("receipts",{})[role]=rc
                save()
        train=[i for i,r in enumerate(rows) if r["topic"] in TRAIN_TOPICS]
        test=[i for i,r in enumerate(rows) if r["topic"] in TEST_TOPICS]
        metrics=evaluate(arrays[0],arrays[1],train,test,rows)
        with tempfile.NamedTemporaryFile(dir=states_path.parent,suffix=".npz",delete=False) as f:
            tmp=Path(f.name)
            np.savez_compressed(f,x_b1=arrays[0],y_b2=arrays[1],
                prompt_ids=np.array([r["id"] for r in rows]),
                train_idx=np.array(train),test_idx=np.array(test))
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,states_path)
        report.update(metrics=metrics,states_sha256=R606.file_sha(states_path),
                      states_bytes=states_path.stat().st_size,
                      status="PARAPHRASE_PROXY_SIGNAL" if metrics["paraphrase_proxy_signal"]
                             else "NO_PARAPHRASE_PROXY_SIGNAL")
        save()
        return report
    except BaseException as e:
        report.update(status="ERROR",error_type=type(e).__name__,error=str(e)[:300])
        save()
        raise


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--home",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--states",required=True)
    args=p.parse_args()
    result=run(args.home,args.out,args.states)
    print(dumps({"status":result["status"],"metrics":result["metrics"],
                 "states_sha256":result["states_sha256"]}))


if __name__=="__main__":
    main()
