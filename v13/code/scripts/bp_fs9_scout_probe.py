"""WP-FS9: hidden-state scout probe before generation vs text-only controls (see PREREG.md in the output dir).
Usage: python scripts/bp_fs9_scout_probe.py OUTDIR in1.json ...   (needs torch+transformers, LFM2.5-350M from HF)"""
import json,os,sys,glob
import numpy as np,torch
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
from v13.agi import selfpredictor as sp,metaeff
from transformers import AutoTokenizer,AutoModelForCausalLM
out=sys.argv[1];rows=[]
for f in sys.argv[2:]:
    for r in json.load(open(f))['rows']:r['seed']=f;rows.append(r)
name='LiquidAI/LFM2.5-350M';tok=AutoTokenizer.from_pretrained(name);m=AutoModelForCausalLM.from_pretrained(name,torch_dtype=torch.float32).eval()
cache=os.path.join(out,'hidden.npz')
if os.path.exists(cache):H=dict(np.load(cache))
else:
    feats={k:[] for k in('mid_mean','mid_last','end_mean','end_last')}
    with torch.no_grad():
        for r in rows:
            ids=tok.apply_chat_template([{'role':'user','content':r['text']}],add_generation_prompt=True,return_tensors='pt',return_dict=True)
            hs=m(**ids,output_hidden_states=True).hidden_states;mid=hs[len(hs)//2][0];end=hs[-1][0]
            feats['mid_mean'].append(mid.mean(0).numpy());feats['mid_last'].append(mid[-1].numpy());feats['end_mean'].append(end.mean(0).numpy());feats['end_last'].append(end[-1].numpy())
    H={k:np.array(v) for k,v in feats.items()};np.savez(cache,**H)
y=np.array([int(not r['pass1']['pass']) for r in rows]);seeds=np.array([r['seed'] for r in rows]);fam=np.array([r['fixture'][:-2] for r in rows])
def auc(sc,yy):return metaeff.auroc2([(float(s),int(l)) for s,l in zip(sc,yy)])
def loso(X,l2):
    p=np.zeros(len(y))
    for s in set(seeds):
        te=seeds==s;mo=sp.fit(X[~te],y[~te],l2=l2,iters=300,lr=.3);p[te]=[sp.predict(mo,x) for x in X[te]]
    return p
def pca(X,k=32):
    Z=X-X.mean(0);u,s,vt=np.linalg.svd(Z,full_matrices=False);return Z@vt[:k].T
T=np.array([sp.input_feats(r['text'],r['nums'])+[int(f=='compare')] for r,f in zip(rows,fam)],float)
res={'n':len(y),'wrong_rate':float(y.mean()),'text_control':{},'fam_only':None,'probes':{},'ref_digit_conf':0.877}
pt=loso(T,1.);res['text_control']={'auroc':auc(pt,y),'by_family':{f:auc(pt[fam==f],y[fam==f]) for f in set(fam)}}
pf=np.array([y[fam==f].mean() for f in fam]);res['fam_only']=auc(pf,y)
rng=np.random.default_rng(0)
for k,X in H.items():
    p=loso(pca(X),10.);a=auc(p,y);bf={f:auc(p[fam==f],y[fam==f]) for f in set(fam)}
    null=[auc(p,rng.permutation(y)) for _ in range(300)];res['probes'][k]={'auroc':a,'by_family':bf,'perm_p':float((np.array(null)>=a).mean())}
best=max(res['probes'],key=lambda k:res['probes'][k]['auroc']);b=res['probes'][best]
ctrl=max(res['text_control']['auroc'],res['fam_only'])
res['best_view']=best;res['verdict']='SCOUT_USEFUL' if b['auroc']>=ctrl+.05 and all(v>.5 for v in b['by_family'].values()) and b['perm_p']<.05 else 'NO_SCOUT_GAIN'
json.dump(res,open(os.path.join(out,'report.json'),'w'),indent=1);print(json.dumps(res,indent=1))
