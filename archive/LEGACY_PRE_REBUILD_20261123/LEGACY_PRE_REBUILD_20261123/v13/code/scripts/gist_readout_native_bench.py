"""WP-G2 / G1B native bench: does grouping B2's native token states at boundaries give better gist slots than fixed
grouping? (thread "Nächste Pakete Abdeckung", 2026-10-20)

Body: the pinned B2 Qwen3.5-0.8B Q4_0 (specs/models.json `gist`), llama-server b10964 `--embedding --pooling none`,
final RMSNorm states = the runtime tap `qwen35.result_norm.final.v1`. Native tokenizer unchanged.
Data: specs/gist-readout-bench.json (64 invented English facts). Each document = 8 facts drawn and ordered by a seeded
RNG; 4 queries per document ask for 4 of its facts by paraphrase. A query is embedded alone by the same body (mean of
its token states). Every document is consumed once by `v13.gist_readout.consume` per mode at size 8 tokens.

Arms (same tap per document): fixed | text | native | hybrid | random (same group count and the same legal cut
positions as hybrid, 5 seeds averaged).
Retrieval: cosine between the query vector and each group vector after subtracting the document's mean token state
from both (anisotropy correction, fixed before the run). A query is correct when the best group overlaps the
answer span.

PREREG (fixed before the first run, pushed first):
  primary  = recall@1 on raw groups (before slot fitting), centered cosine
  H1       = hybrid - fixed >= .05 and paired-bootstrap 95 % CI lower bound > 0
  H2       = hybrid - random >= .05 and CI lower bound > 0
  verdict  = SUPPORTED if H1 and H2, PARTIAL if exactly one, FAIL otherwise
  default  = DEFAULT_MODE stays 'hybrid' only if SUPPORTED; otherwise the arm among text/native/hybrid with the best
             primary whose CI vs fixed is above 0, else 'fixed'
  secondary (reported, no gate): recall@1 after fitting to 12 slots, uncentered recall, answer split rate (answer span
             cut across groups), group counts, AUC of the native shift at sentence ends (after / before the period).
Claim limit: one body, one language, synthetic facts, Linux CPU; a retrieval proxy for gist-slot quality, not
answer utility, not Redmi.

Usage: python3 scripts/gist_readout_native_bench.py --prereg OUT_DIR
       python3 scripts/gist_readout_native_bench.py --server .../llama-server --model .../Qwen3.5-0.8B-Q4_0.gguf --out OUT_DIR
"""
import argparse
import hashlib
import json
import os
import random
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import numpy as np
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from v13 import gist_readout as R

FACTS=APP/'specs/gist-readout-bench.json'
DOCS=40;FACTS_PER_DOC=8;QUERIES_PER_DOC=4;SIZE=8;SLOTS=12;RANDOM_SEEDS=(13,21,34,55,89);BOOT=2000;DATA_SEED=20261020
ARMS=('fixed','text','native','hybrid','random')
PREREG={'schema':'GIST_READOUT_NATIVE_PREREG_V1','body':'gist Qwen3.5-0.8B Q4_0 rev 8fea620810c4afa23dd6443f999a48574c1611a3','runner':'llama.cpp b10964 --embedding --pooling none',
        'tap':'qwen35.result_norm.final.v1','docs':DOCS,'facts_per_doc':FACTS_PER_DOC,'queries_per_doc':QUERIES_PER_DOC,'size':SIZE,'slots':SLOTS,
        'data_seed':DATA_SEED,'random_seeds':list(RANDOM_SEEDS),'bootstrap':BOOT,'hybrid_weight':R.HYBRID_WEIGHT,'arms':list(ARMS),
        'primary':'recall@1 raw groups, centered cosine, correct = best group overlaps answer span',
        'H1':'hybrid-fixed >= .05 and paired bootstrap 95% CI low > 0','H2':'hybrid-random >= .05 and CI low > 0',
        'verdict':'SUPPORTED if H1 and H2; PARTIAL if one; FAIL otherwise',
        'default_rule':"hybrid if SUPPORTED; else best of text/native/hybrid with CI vs fixed > 0; else fixed",
        'secondary':['recall@1 fitted 12 slots','uncentered recall@1','answer split rate','group counts','native shift AUC at sentence ends']}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def documents():
    facts=json.loads(FACTS.read_text())['facts'];rng=random.Random(DATA_SEED);out=[]
    for d in range(DOCS):
        pick=rng.sample(range(len(facts)),FACTS_PER_DOC);text='';spans=[]
        for k in pick:
            s,q,a=facts[k]
            if text:text+=' '
            start=len(text);text+=s;i=s.index(a);spans.append((k,q,a,start+i,start+i+len(a)))
        out.append({'doc':d,'text':text,'queries':[spans[j] for j in sorted(rng.sample(range(FACTS_PER_DOC),QUERIES_PER_DOC))]})
    return out

class Server:
    def __init__(self,binary,model,threads):
        s=socket.socket();s.bind(('127.0.0.1',0));self.port=s.getsockname()[1];s.close()
        env=dict(os.environ,LD_LIBRARY_PATH=str(Path(binary).parent))
        self.p=subprocess.Popen([str(binary),'-m',str(model),'--embedding','--pooling','none','--port',str(self.port),'-c','2048','-t',str(threads),
                                 '-b','512','-ub','512','--no-warmup','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env)
        for _ in range(240):
            try:
                if json.load(urllib.request.urlopen('http://127.0.0.1:%d/health'%self.port,timeout=2)).get('status')=='ok':return
            except Exception:pass
            if self.p.poll() is not None:raise RuntimeError('llama-server beendet')
            time.sleep(.5)
        raise RuntimeError('llama-server nicht bereit')
    def post(self,path,data):
        req=urllib.request.Request('http://127.0.0.1:%d%s'%(self.port,path),json.dumps(data).encode(),{'Content-Type':'application/json'})
        return json.load(urllib.request.urlopen(req,timeout=600))
    def tap(self,text):
        toks=self.post('/tokenize',{'content':text,'add_special':True,'with_pieces':True})['tokens']
        vec=self.post('/embeddings',{'input':[t['id'] for t in toks],'embd_normalize':-1})[0]['embedding']
        if len(vec)!=len(toks):raise RuntimeError('Tap/Token-Bindung')
        return [t['id'] for t in toks],[t['piece'] for t in toks],np.asarray(vec,dtype=np.float64)
    def close(self):
        self.p.terminate()
        try:self.p.wait(10)
        except subprocess.TimeoutExpired:self.p.kill();self.p.wait()

def random_groups(text,spans,vectors,count,seed):
    """Same legal cut positions as the readout modes, `count` groups, uniformly random cuts."""
    inside=R._exact_inside(text);n=len(spans)
    legal=[i for i in range(n-1) if R.legal(text,spans,i,inside)]
    rng=random.Random(seed);cuts=sorted(rng.sample(legal,min(count-1,len(legal))))+[n-1];out=[];start=0
    for c in cuts:
        out.append({'tokens':(start,c+1),'char':(spans[start][0],spans[c][1]),'vector':vectors[start:c+1].mean(0)});start=c+1
    return out

def best(groups,q,mu,center):
    G=np.stack([g['vector'] for g in groups]);qq=q
    if center:G=G-mu;qq=q-mu
    G=G/np.maximum(np.linalg.norm(G,axis=1,keepdims=True),1e-12);qq=qq/max(np.linalg.norm(qq),1e-12)
    return groups[int(np.argmax(G@qq))]

def overlaps(g,a,b):return g['char'][0]<b and a<g['char'][1]

def auc(scores,labels):
    s=np.asarray(scores);y=np.asarray(labels,dtype=bool)
    if y.all() or not y.any():return None
    order=np.argsort(s,kind='mergesort');rank=np.empty(len(s));rank[order]=np.arange(1,len(s)+1)
    for v in np.unique(s):  # average ties
        m=s==v;rank[m]=rank[m].mean()
    return float((rank[y].sum()-y.sum()*(y.sum()+1)/2)/(y.sum()*(~y).sum()))

def paired_ci(a,b,seed=DATA_SEED):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float);d=a-b;rng=np.random.default_rng(seed)
    boots=np.array([d[rng.integers(0,len(d),len(d))].mean() for _ in range(BOOT)])
    return {'diff':round(float(d.mean()),4),'ci95':[round(float(np.percentile(boots,2.5)),4),round(float(np.percentile(boots,97.5)),4)]}

def run(args):
    docs=documents();srv=Server(args.server,args.model,args.threads);rows={a:{'raw':[],'fit':[],'raw_uncentered':[],'split':[],'groups':[]} for a in ARMS}
    shifts_after=[];labels_after=[];labels_before=[];per_doc=[];started=time.monotonic()
    try:
        for d in docs:
            text=d['text'];ref={'source_id':'bench-%d'%d['doc'],'sha256':hashlib.sha256(text.encode()).hexdigest(),'char_start':0,'char_end':len(text),'modality':'text'}
            ids,pieces,V=srv.tap(text);spans=R.token_spans(text,pieces);mu=V.mean(0);shift=R.native_shift(V)
            for i in range(len(spans)-1):
                e=spans[i][1];shifts_after.append(float(shift[i]))
                labels_after.append(e>0 and text[e-1] in '.!?' and (e==len(text) or text[e].isspace()))
                labels_before.append(e<len(text) and text[e] in '.!?')
            qv=[srv.tap(q[1])[2].mean(0) for q in d['queries']];doc_row={'doc':d['doc'],'native_tokens':len(ids)}
            arm_groups={}
            for m in R.MODES:
                plan,_=R.consume(text,ref,ids,pieces,V,size=SIZE,slots=SLOTS,mode=m)
                raw=R.group(text,ref,spans,V,SIZE,m,shift);arm_groups[m]=(raw,R.fit(raw,SLOTS))
                if not plan['lossless']:raise RuntimeError('nicht verlustfrei')
            for m in R.MODES:
                raw,fit=arm_groups[m];rows[m]['groups'].append(len(raw))
                for q,v in zip(d['queries'],qv):
                    a,b=q[3],q[4]
                    rows[m]['raw'].append(overlaps(best(raw,v,mu,True),a,b));rows[m]['fit'].append(overlaps(best(fit,v,mu,True),a,b))
                    rows[m]['raw_uncentered'].append(overlaps(best(raw,v,mu,False),a,b))
                    rows[m]['split'].append(sum(overlaps(g,a,b) for g in raw)>1)
            n_h=len(arm_groups['hybrid'][0]);rr=[];rf=[];ru=[];rs=[]
            for sd in RANDOM_SEEDS:
                g=random_groups(text,spans,V,n_h,sd+d['doc']*1000);gf=R.fit([dict(x,units=x['tokens'][1]-x['tokens'][0],boundary=1.,shift=None,scale=1,source_ref=dict(ref,char_start=x['char'][0],char_end=x['char'][1])) for x in g],SLOTS)
                rr.append([overlaps(best(g,v,mu,True),q[3],q[4]) for q,v in zip(d['queries'],qv)])
                rf.append([overlaps(best(gf,v,mu,True),q[3],q[4]) for q,v in zip(d['queries'],qv)])
                ru.append([overlaps(best(g,v,mu,False),q[3],q[4]) for q,v in zip(d['queries'],qv)])
                rs.append([sum(overlaps(x,q[3],q[4]) for x in g)>1 for q in d['queries']])
            for key,src in (('raw',rr),('fit',rf),('raw_uncentered',ru),('split',rs)):rows['random'][key]+=list(np.mean(src,axis=0))
            rows['random']['groups'].append(n_h);doc_row['groups']={m:len(arm_groups[m][0]) for m in R.MODES};per_doc.append(doc_row)
    finally:srv.close()
    summary={a:{'recall_raw':round(float(np.mean(rows[a]['raw'])),4),'recall_fit12':round(float(np.mean(rows[a]['fit'])),4),
                'recall_raw_uncentered':round(float(np.mean(rows[a]['raw_uncentered'])),4),'answer_split_rate':round(float(np.mean(rows[a]['split'])),4),
                'mean_groups':round(float(np.mean(rows[a]['groups'])),2)} for a in ARMS}
    h1=paired_ci(rows['hybrid']['raw'],rows['fixed']['raw']);h2=paired_ci(rows['hybrid']['raw'],rows['random']['raw'])
    ok1=h1['diff']>=.05 and h1['ci95'][0]>0;ok2=h2['diff']>=.05 and h2['ci95'][0]>0
    verdict='SUPPORTED' if ok1 and ok2 else 'PARTIAL' if ok1 or ok2 else 'FAIL'
    vs_fixed={m:paired_ci(rows[m]['raw'],rows['fixed']['raw']) for m in ('text','native','hybrid','random')}
    if verdict=='SUPPORTED':default='hybrid'
    else:
        ok=[m for m in ('text','native','hybrid') if vs_fixed[m]['ci95'][0]>0]
        default=max(ok,key=lambda m:summary[m]['recall_raw']) if ok else 'fixed'
    rep={'kind':'GIST_READOUT_NATIVE_BENCH','prereg':PREREG,'prereg_sha256':hashlib.sha256(json.dumps(PREREG,sort_keys=True).encode()).hexdigest(),
         'script_sha256':sha(__file__),'module_sha256':sha(R.__file__),'facts_sha256':sha(FACTS),'model_sha256':sha(args.model) if args.hash_model else 'not_hashed',
         'queries':len(rows['fixed']['raw']),'summary':summary,'H1_hybrid_vs_fixed':h1|{'pass':ok1},'H2_hybrid_vs_random':h2|{'pass':ok2},'vs_fixed':vs_fixed,
         'verdict':verdict,'default_mode':default,
         'native_shift_auc':{'after_sentence_end':auc(shifts_after,labels_after),'before_sentence_end':auc(shifts_after,labels_before)},
         'per_doc':per_doc,'duration_s':round(time.monotonic()-started,1),
         'claim_limit':'One body (Qwen3.5-0.8B Q4_0), English synthetic facts, Linux CPU; retrieval proxy for gist-slot quality, not answer utility, not Redmi'}
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True);(out/'result.json').write_text(json.dumps(rep,indent=1,ensure_ascii=False))
    print(json.dumps({k:rep[k] for k in ('summary','H1_hybrid_vs_fixed','H2_hybrid_vs_random','verdict','default_mode','native_shift_auc')},indent=1))
    return rep

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prereg');ap.add_argument('--server');ap.add_argument('--model');ap.add_argument('--out')
    ap.add_argument('--threads',type=int,default=4);ap.add_argument('--hash-model',action='store_true');a=ap.parse_args()
    if a.prereg:
        out=Path(a.prereg);out.mkdir(parents=True,exist_ok=True);body=dict(PREREG,script_sha256=sha(__file__),module_sha256=sha(R.__file__),facts_sha256=sha(FACTS))
        (out/'prereg.json').write_text(json.dumps(body,indent=1,ensure_ascii=False));print(json.dumps(body,indent=1));return
    if not (a.server and a.model and a.out):ap.error('--server, --model, --out')
    run(a)

if __name__=='__main__':main()
