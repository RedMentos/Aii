#!/usr/bin/env python3
"""Run607: independent POSTHOC geometry audit of frozen Run606 real native states.

No model call, bridge activation, learning or gate promotion. This is NOT a
prospectively registered hypothesis test: Run606 results were seen beforehand.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

import numpy as np

APP = Path(__file__).resolve().parents[1]
COHORT = APP / "docs/proofs/continuation-20261026/run606-cross-body-latent-shadow/RUN606_COHORT.json"
COHORT_BLOB = "c0c2a2f74ab8a487563df2449d5faad79fab738f"
STATES_SHA = "368efacc04860ca6407aa9296f188a8aa6c3d7760ff44b2724231079b89a62c0"
RUN606_HEAD = "de20b8611027c0aa3cd27ee4bc5436e3b86b259f"
B1_SHA = "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1"
B2_SHA = "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"
SEED = 20261026
PERMUTATIONS = 1000
GATES = {"STEP2":"UTILITY_FAIL","B3_L1":"FAIL","Body_JEPA":"UNAVAILABLE",
         "jepa_weight":0,"Redmi":"UNMEASURED","V13":"INCOMPLETE"}
REQUIRED = {"RUN606_HEAD.txt","RUN606_NATIVE_REPORT.json","RUN606_STATES.npz",
            "RUN606_NATIVE_EXIT.txt","RUN606_AUDIT_EXIT.txt","RUN606_PRIVACY_EXIT.txt"}


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()


def blob_sha(path):
    b=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\\0"+b).hexdigest()


def verify_closed_raw(folder):
    """Check every entry in the original SHA-closed manifest; refuse traversal/duplicates."""
    folder=Path(folder)
    manifest=folder/"RUN606_SHA256SUMS.txt"
    entries={}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest,sep,name=line.partition("  ")
        if not sep or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("malformed SHA manifest")
        if not name.startswith("./") or Path(name).name!=name[2:] or name in entries:
            raise ValueError("unsafe or repeated SHA manifest member")
        entries[name]=digest
    if not REQUIRED.issubset({x[2:] for x in entries}):
        raise ValueError("incomplete SHA manifest")
    for name,expected in entries.items():
        if sha256(folder/name)!=expected:
            raise ValueError("raw artifact hash mismatch: "+name)
    if sha256(folder/"RUN606_STATES.npz")!=STATES_SHA:
        raise ValueError("frozen native states SHA mismatch")
    if (folder/"RUN606_HEAD.txt").read_text().strip()!=RUN606_HEAD:
        raise ValueError("Run606 head mismatch")
    for suffix in ("NATIVE","AUDIT","PRIVACY"):
        if (folder/("RUN606_"+suffix+"_EXIT.txt")).read_text().strip()!="0":
            raise ValueError("original "+suffix+" exit not zero")
    return len(entries)


def load_verified(folder):
    folder=Path(folder)
    members=verify_closed_raw(folder)
    if blob_sha(COHORT)!=COHORT_BLOB:
        raise ValueError("frozen cohort blob mismatch")
    cohort=json.loads(COHORT.read_text(encoding="utf-8"))
    if cohort.get("schema")!="V13_RUN606_COHORT_V1" or cohort.get("seed")!=SEED:
        raise ValueError("cohort schema/seed mismatch")
    rows=cohort["prompts"]
    if len(rows)!=40 or len({r["id"] for r in rows})!=40:
        raise ValueError("cohort rows mismatch")
    report=json.loads((folder/"RUN606_NATIVE_REPORT.json").read_text(encoding="utf-8"))
    if (report.get("schema")!="V13_RUN606_CROSS_BODY_NATIVE_SHADOW_V1"
            or report.get("status")!="NO_EXPLORATORY_SIGNAL"
            or report.get("gates")!=GATES
            or report.get("states_sha256")!=STATES_SHA
            or report.get("cohort_blob")!=COHORT_BLOB
            or report.get("no_weight_updates") is not True
            or report.get("can_latent_inject") is not False
            or report.get("b3_promoted") is not False
            or report.get("redmi_measured") is not False):
        raise ValueError("Run606 report status/authority mismatch")
    for role,expected,dim in (("B1_DETAIL",B1_SHA,2048),("B2_GIST",B2_SHA,1024)):
        model=report["models"][role]
        receipts=report["receipts"][role]
        if model["sha256"]!=expected or model["dimension"]!=dim or len(receipts)!=40:
            raise ValueError("native model or receipt mismatch")
        for row,receipt in zip(rows,receipts):
            if (receipt["id"]!=row["id"] or receipt["dimension"]!=dim
                    or receipt["prompt_sha256"]!=hashlib.sha256(row["text"].encode()).hexdigest()
                    or not 1<=receipt["token_count"]<=64):
                raise ValueError("source-bound receipt mismatch")
    with np.load(folder/"RUN606_STATES.npz",allow_pickle=False) as npz:
        if set(npz.files)!={"x_b1","y_b2","prompt_ids","train_idx","test_idx"}:
            raise ValueError("unexpected native state fields")
        x=npz["x_b1"].astype(np.float64);y=npz["y_b2"].astype(np.float64)
        ids=npz["prompt_ids"].tolist()
        train=npz["train_idx"].tolist();test=npz["test_idx"].tolist()
    expected_train=[i for i,r in enumerate(rows) if r["topic"] in cohort["train_topics"]]
    expected_test=[i for i,r in enumerate(rows) if r["topic"] in cohort["test_topics"]]
    if (x.shape!=(40,2048) or y.shape!=(40,1024)
            or ids!=[r["id"] for r in rows] or train!=expected_train
            or test!=expected_test or len(train)!=30 or len(test)!=10
            or set(cohort["train_topics"])&set(cohort["test_topics"])
            or not np.isfinite(x).all() or not np.isfinite(y).all()):
        raise ValueError("native states, source order or heldout split mismatch")
    return x,y,train,test,rows,report,members


def normalize(a):
    a=np.asarray(a,dtype=np.float64)
    if a.ndim!=2 or not np.isfinite(a).all():
        raise ValueError("invalid latent matrix")
    n=np.linalg.norm(a,axis=1,keepdims=True)
    if np.any(n<=1e-12):raise ValueError("zero latent row")
    return a/n


def pearson(a,b):
    a=np.asarray(a,dtype=np.float64).ravel()
    b=np.asarray(b,dtype=np.float64).ravel()
    if len(a)!=len(b) or len(a)<3 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("invalid correlation inputs")
    a=a-a.mean();b=b-b.mean()
    denom=np.linalg.norm(a)*np.linalg.norm(b)
    if denom<=1e-12:raise ValueError("degenerate correlation")
    return float(np.dot(a,b)/denom)


def design(rows,report,test):
    topics=[rows[i]["topic"] for i in test]
    lengths={}
    for role in ("B1_DETAIL","B2_GIST"):
        lengths[role]=np.array([report["receipts"][role][i]["token_count"] for i in test],dtype=float)
    u,v=np.triu_indices(len(test),1)
    same=np.array([topics[i]==topics[j] for i,j in zip(u,v)],dtype=float)
    l1=lengths["B1_DETAIL"];l2=lengths["B2_GIST"]
    conf=np.column_stack((np.ones(len(u)),same,np.abs(l1[u]-l1[v]),
                          np.abs(l2[u]-l2[v]),l1[u]+l1[v],l2[u]+l2[v]))
    return u,v,same,conf


def analyze(x,y,train,test,rows,report,seed=SEED,permutations=PERMUTATIONS):
    if permutations<1 or len(test)<5 or len(set(test))!=len(test):
        raise ValueError("invalid posthoc audit split")
    # Training-only mean prevents the heldout representations from defining their own origin.
    x=normalize(x);y=normalize(y)
    xv=normalize(x[test]-x[train].mean(axis=0))
    yv=normalize(y[test]-y[train].mean(axis=0))
    a=xv@xv.T;b=yv@yv.T
    u,v,same,conf=design(rows,report,test)
    av=a[u,v];bv=b[u,v]
    ar=av-conf@np.linalg.lstsq(conf,av,rcond=None)[0]
    def stats(bmat):
        bb=bmat[u,v]
        br=bb-conf@np.linalg.lstsq(conf,bb,rcond=None)[0]
        return (pearson(av,bb),pearson(ar,br),pearson(av[same==1],bb[same==1]))
    observed=stats(b)
    nearest_a=np.argmax(a-np.eye(len(test))*10,axis=1)
    nearest_b=np.argmax(b-np.eye(len(test))*10,axis=1)
    agreement=float(np.mean(nearest_a==nearest_b))
    rng=np.random.default_rng(seed)
    null=np.empty((permutations,3))
    for k in range(permutations):
        p=rng.permutation(len(test))
        null[k]=stats(b[np.ix_(p,p)])
    names=("pearson_rsa","token_topic_partial_rsa","within_topic_rsa")
    metrics={}
    for i,name in enumerate(names):
        vnull=null[:,i]
        metrics[name]={"observed":observed[i],"null_mean":float(vnull.mean()),
                       "null_p95":float(np.percentile(vnull,95)),
                       "exploratory_permutation_p":float((1+np.count_nonzero(vnull>=observed[i]))/(permutations+1))}
    return {"metrics":metrics,"nearest_neighbor_agreement":agreement,
            "within_topic_pairs":int(np.count_nonzero(same)),
            "cross_topic_pairs":int(np.count_nonzero(1-same)),
            "heldout_n":len(test),"permutations":permutations,"seed":seed,
            "claim_limit":"Posthoc shared native geometry, NOT direct mapping, semantic utility, B3 L1/L2 or JEPA"}


def atomic_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",dir=path.parent,encoding="utf-8",delete=False) as f:
        tmp=Path(f.name)
        json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False)
        f.write("\\n");f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def run(folder,out):
    result={"schema":"V13_RUN607_POSTHOC_NATIVE_GEOMETRY_V1","status":"ERROR",
            "evidence_level":"OFFLINE_POSTHOC_REANALYSIS_OF_LINUX_NATIVE",
            "prospective":False,"input_run":40399494903,"input_artifact":12688127140,
            "input_states_sha256":STATES_SHA,"gates":dict(GATES),
            "no_weight_updates":True,"can_latent_inject":False,"redmi_measured":False,
            "canonical_architecture_complete":False,"user_full_scope_complete":False}
    try:
        x,y,train,test,rows,report,members=load_verified(folder)
        result.update(analyze(x,y,train,test,rows,report),verified_manifest_entries=members,
                      run606_original_status=report["status"],status="POSTHOC_GEOMETRY_ONLY")
    except BaseException as e:
        result.update(error_type=type(e).__name__,error=str(e)[:250])
        atomic_json(out,result)
        raise
    atomic_json(out,result)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--artifact",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    print(json.dumps(run(args.artifact,args.out),sort_keys=True))


if __name__=="__main__":
    main()
