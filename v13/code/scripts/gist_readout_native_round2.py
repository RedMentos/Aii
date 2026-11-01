"""WP-G2 round 2 (preregistered after round 1, 2026-10-20): does boundary grouping beat fixed grouping when both have
exactly the same number of groups per document?

Round 1 (`gist_readout_native_bench.py`) was SUPPORTED, but an exploratory post-hoc check showed that fixed size 9
(about the hybrid group count) closed half the gap (+.05, CI [-.03,.13]). Round 2 removes the count confound.

Same body, runner, tap, fact bank and query protocol as round 1; new documents (data seed 20261021), 160 documents x
4 queries = 640 queries. For every mode m in text/native/hybrid the control `fixed_matched_m` cuts the same document
into exactly as many groups as m produced, as equal-length native-token runs (pure fixed, no legality rule).

PREREG (fixed before the run, pushed first):
  primary = recall@1 raw groups, centered cosine (as round 1)
  H1      = hybrid - fixed_matched_hybrid >= .03 and paired bootstrap 95 % CI lower bound > 0
  verdict = SUPPORTED if H1, else FAIL
  default = 'hybrid' stays the readout default only if SUPPORTED; otherwise the best of text/native whose own matched
            difference has CI lower bound > 0, else 'fixed'
  secondary (no gate): text and native vs their own matched control, fitted-12 recall, answer split rates.
Claim limit as round 1.
Usage: --prereg OUT_DIR | --server ... --model ... --out OUT_DIR
"""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gist_readout_native_bench as B
from v13 import gist_readout as R

DOCS=160;DATA_SEED=20261021
PREREG={'schema':'GIST_READOUT_NATIVE_ROUND2_PREREG_V1','round1':'bench-results/gist-readout-native-20261020/result.json','docs':DOCS,'data_seed':DATA_SEED,
        'queries_per_doc':B.QUERIES_PER_DOC,'size':B.SIZE,'slots':B.SLOTS,'bootstrap':B.BOOT,'hybrid_weight':R.HYBRID_WEIGHT,
        'control':'fixed_matched_m: equal-length native-token runs, same group count as mode m per document',
        'primary':'recall@1 raw groups, centered cosine','H1':'hybrid - fixed_matched_hybrid >= .03 and CI low > 0','verdict':'SUPPORTED if H1 else FAIL',
        'default_rule':'hybrid if SUPPORTED; else best of text/native with matched CI low > 0; else fixed'}

def matched(V,spans,k):
    n=len(spans);edges=np.linspace(0,n,k+1).round().astype(int);out=[]
    for a,b in zip(edges[:-1],edges[1:]):
        if b>a:out.append({'tokens':(a,b),'char':(spans[a][0],spans[b-1][1]),'units':b-a,'vector':V[a:b].mean(0),'boundary':1.,'shift':None,'scale':1})
    return out

def run(a):
    B.DOCS=DOCS;B.DATA_SEED=DATA_SEED;docs=B.documents();srv=B.Server(a.server,a.model,a.threads);started=time.monotonic()
    arms=['fixed']+list(R.MODES[1:])+['fixed_matched_'+m for m in R.MODES[1:]];rows={x:{'raw':[],'fit':[],'split':[],'groups':[]} for x in arms}
    try:
        for d in docs:
            text=d['text'];ref={'source_id':'r2-%d'%d['doc'],'sha256':'0'*64,'char_start':0,'char_end':len(text),'modality':'text'}
            ids,pieces,V=srv.tap(text);spans=R.token_spans(text,pieces);mu=V.mean(0);qv=[srv.tap(q[1])[2].mean(0) for q in d['queries']]
            groups={}
            for m in R.MODES:groups[m]=R.group(text,ref,spans,V,B.SIZE,m)
            for m in R.MODES[1:]:groups['fixed_matched_'+m]=matched(V,spans,len(groups[m]))
            for x in arms:
                raw=groups[x];fit=R.fit([dict(g,source_ref=dict(ref,char_start=g['char'][0],char_end=g['char'][1])) for g in raw],B.SLOTS)
                cover=sorted((g['char'] for g in raw));assert cover[0][0]==0 and cover[-1][1]==len(text) and all(p[1]==q[0] for p,q in zip(cover,cover[1:]))
                rows[x]['groups'].append(len(raw))
                for q,v in zip(d['queries'],qv):
                    rows[x]['raw'].append(B.overlaps(B.best(raw,v,mu,True),q[3],q[4]));rows[x]['fit'].append(B.overlaps(B.best(fit,v,mu,True),q[3],q[4]))
                    rows[x]['split'].append(sum(B.overlaps(g,q[3],q[4]) for g in raw)>1)
    finally:srv.close()
    summary={x:{'recall_raw':round(float(np.mean(rows[x]['raw'])),4),'recall_fit12':round(float(np.mean(rows[x]['fit'])),4),
                'answer_split_rate':round(float(np.mean(rows[x]['split'])),4),'mean_groups':round(float(np.mean(rows[x]['groups'])),2)} for x in arms}
    vs={m:B.paired_ci(rows[m]['raw'],rows['fixed_matched_'+m]['raw']) for m in R.MODES[1:]}
    h1=vs['hybrid'];ok=h1['diff']>=.03 and h1['ci95'][0]>0;verdict='SUPPORTED' if ok else 'FAIL'
    if ok:default='hybrid'
    else:
        c=[m for m in ('text','native') if vs[m]['ci95'][0]>0];default=max(c,key=lambda m:vs[m]['diff']) if c else 'fixed'
    rep={'kind':'GIST_READOUT_NATIVE_ROUND2','prereg':PREREG,'script_sha256':B.sha(__file__),'module_sha256':B.sha(R.__file__),'facts_sha256':B.sha(B.FACTS),
         'queries':len(rows['fixed']['raw']),'summary':summary,'vs_matched_fixed':vs,'H1':h1|{'pass':ok},'verdict':verdict,'default_mode':default,
         'duration_s':round(time.monotonic()-started,1),'claim_limit':'One body (Qwen3.5-0.8B Q4_0), English synthetic facts, Linux CPU; retrieval proxy, not answer utility, not Redmi'}
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'result-round2.json').write_text(json.dumps(rep,indent=1))
    print(json.dumps({k:rep[k] for k in ('summary','vs_matched_fixed','verdict','default_mode')},indent=1))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prereg');ap.add_argument('--server');ap.add_argument('--model');ap.add_argument('--out');ap.add_argument('--threads',type=int,default=4);a=ap.parse_args()
    if a.prereg:
        out=Path(a.prereg);out.mkdir(parents=True,exist_ok=True)
        (out/'prereg-round2.json').write_text(json.dumps(dict(PREREG,script_sha256=B.sha(__file__),module_sha256=B.sha(R.__file__)),indent=1));return
    run(a)

if __name__=='__main__':main()
