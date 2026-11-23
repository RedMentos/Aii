"""EXPLORATORY (post hoc, not preregistered) follow-up to gist_readout_native_bench.py: is the hybrid win only a
group-count effect? Hybrid ends with fewer, larger groups than fixed size 8 (13.6 vs 15.3 per document). This re-runs
fixed grouping at sizes 9 and 10 (group counts at or below hybrid) on the same documents and taps.
Usage: python3 scripts/gist_readout_posthoc_size.py --server ... --model ... --out DIR"""
import argparse,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gist_readout_native_bench as B
from v13 import gist_readout as R

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--server');ap.add_argument('--model');ap.add_argument('--out');a=ap.parse_args()
    srv=B.Server(a.server,a.model,4);arms={('hybrid',8):[],('fixed',8):[],('fixed',9):[],('fixed',10):[]};groups={k:[] for k in arms}
    try:
        for d in B.documents():
            text=d['text'];ref={'source_id':'x','sha256':'0'*64,'char_start':0,'char_end':len(text),'modality':'text'}
            ids,pieces,V=srv.tap(text);spans=R.token_spans(text,pieces);mu=V.mean(0);qv=[srv.tap(q[1])[2].mean(0) for q in d['queries']]
            for (m,size) in arms:
                raw=R.group(text,ref,spans,V,size,m);groups[(m,size)].append(len(raw))
                arms[(m,size)]+=[B.overlaps(B.best(raw,v,mu,True),q[3],q[4]) for q,v in zip(d['queries'],qv)]
    finally:srv.close()
    rep={'kind':'GIST_READOUT_POSTHOC_SIZE','status':'EXPLORATORY_NOT_PREREGISTERED',
         'arms':{'%s_%d'%k:{'recall_raw':round(float(np.mean(v)),4),'mean_groups':round(float(np.mean(groups[k])),2)} for k,v in arms.items()},
         'hybrid8_vs_fixed':{'fixed_%d'%s:B.paired_ci(arms[('hybrid',8)],arms[('fixed',s)]) for s in (8,9,10)}}
    Path(a.out).mkdir(parents=True,exist_ok=True);(Path(a.out)/'posthoc-size.json').write_text(json.dumps(rep,indent=1));print(json.dumps(rep,indent=1))

if __name__=='__main__':main()
