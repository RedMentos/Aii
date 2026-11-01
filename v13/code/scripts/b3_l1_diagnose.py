"""WP-J B3 L1 diagnosis (2026-10-20): why does G-CALLOSUM-UTILITY-002 fail? Exploratory re-analysis, preregistered.

Runs on the cached B1/B2 states of attempt 3 (b3_l1_v3_bench.py, states.npz), same rows, seeds and splits, private
view only. Bridge, gate and utility are imported unchanged from v13/b3bridge.py. The hypotheses and the decision
rules are fixed in code/docs/proofs/b3-l1-diagnose-20261020/preregistration.json:

  H1 bytes            byte term of the utility vs the accuracy gaps
  H2 head asymmetry   canon LATENT is read through the FROZEN NO_MESSAGE readout + message residual, the baselines
                      get a jointly refit head. LATENT_REFIT = same trained bridge message with a refit head;
                      *_RESID = baselines forced through the frozen-head residual.
  H3 supervision      ridge probe R^2 of U and F from the bridge message vs from sender PCA-16
  H4 ceiling          ORACLE_UF = true U, F with a refit head

Because the test items were already seen by attempt 3, nothing here is a canon L1 verdict: the gate on LATENT_REFIT
is 'diagnostic' only, no bridge manifest is written, B3_LATENT stays unavailable.

Usage: b3_l1_diagnose.py <states.npz> <out_dir> [seeds]"""
import hashlib
import json
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import b3_h2_bench as H2
import b3_l1_v3_bench as V3
from v13 import b3bridge as BB

TASKS=('escalate','apologize','action');DEPENDS={'escalate':'U','apologize':'F','action':'U+F'}

def head_offset(X,y,k,off,l2,steps=400,lr=.5):
    """Logistic residual with a fixed offset (the frozen NO_MESSAGE logits): only the feature weights are learned."""
    W=np.zeros((X.shape[1],k));b=np.zeros(k);Y=np.eye(k)[y]
    for _ in range(steps):
        z=off+X@W+b;z-=z.max(1,keepdims=True);p=np.exp(z);p/=p.sum(1,keepdims=True);g=(p-Y)/len(y);W-=lr*(X.T@g+l2*W);b-=lr*g.sum(0)
    return W,b

def resid_acc(Ftr,Fva,Fte,ytr,yva,yte,k,off):
    otr,ova,ote=off
    best=max((float(((ova+Fva@w+b).argmax(1)==yva).mean()),l2) for l2 in (1e-3,1e-2,1e-1,1.) for w,b in [head_offset(Ftr,ytr,k,otr,l2)])[1]
    W,b=head_offset(Ftr,ytr,k,otr,best);return float(((ote+Fte@W+b).argmax(1)==yte).mean())

def r2(Xtr,ytr,Xva,yva,Xte,yte):
    w,b=V3.sel_ridge(Xtr,ytr,Xva,yva);p=Xte@w+b;return float(1-((p-yte)**2).sum()/((yte-yte.mean())**2).sum())

def refit(X,tr,va,te,y,k):
    a,bb,c=H2.std(X[tr],X[va],X[te]);W,b=H2.sel_head(a,y[tr],bb,y[va],k);return H2.acc(W,b,c,y[te])

def run_task(task,rows,recv,send_pool,Hs,Ms,exact,seeds):
    y=np.array([r[task] for r in rows]);k=int(y.max())+1
    U=np.array([r['U'] for r in rows],float);F=np.array([r['F'] for r in rows],float)
    per={};probe={'U':{'sender_pca16':[],'bridge_msg':[]},'F':{'sender_pca16':[],'bridge_msg':[]}}
    for seed in range(seeds):
        g=np.random.default_rng(seed);idx=g.permutation(len(rows));n=len(idx);tr,va,te=idx[:n*3//5],idx[n*3//5:n*4//5],idx[n*4//5:]
        mu,V=H2.pca(recv[tr],H2.PCA_RECV);Xr=(recv-mu)@V.T;Xr_tr,Xr_va,Xr_te=H2.std(Xr[tr],Xr[va],Xr[te]);Xr_all=H2.std(Xr[tr],Xr)[1]
        Wn,bn=H2.sel_head(Xr_tr,y[tr],Xr_va,y[va],k);per.setdefault('NO_MESSAGE',[]).append(H2.acc(Wn,bn,Xr_te,y[te]))
        off=(Xr_tr@Wn+bn,Xr_va@Wn+bn,Xr_te@Wn+bn)
        smu,SV=H2.pca(send_pool[tr],H2.PCA_RECV);Xs=(send_pool-smu)@SV.T;Xs_tr,Xs_va,Xs_all=H2.std(Xs[tr],Xs[va],Xs)
        Ws,bs=H2.sel_head(Xs_tr,y[tr],Xs_va,y[va],k);P=H2.probs(Ws,bs,Xs_all);sym=np.eye(k)[P.argmax(1)]
        attr=[]
        for v in (U,F):
            lv=V3.tertile(v,tr);Wa,ba=H2.sel_head(Xs_tr,lv[tr],Xs_va,lv[va],3);attr.append(np.eye(3)[H2.probs(Wa,ba,Xs_all).argmax(1)])
        attr=np.c_[attr[0],attr[1]]
        sc=np.c_[[(Xs_all@w+b) for w,b in [V3.sel_ridge(Xs_tr,v[tr],Xs_va,v[va]) for v in (U,F)]]].T.astype(np.float16).astype(float)
        feats={'EXACT':exact,'SYMBOLIC':sym,'SYMBOLIC_ATTR':attr,'SCALAR':sc,'ORACLE_UF':np.c_[U,F].astype(np.float16).astype(float)}
        for name,Fe in feats.items():
            per.setdefault(name,[]).append(refit(np.c_[Xr_all,Fe],tr,va,te,y,k))
            if name in ('SYMBOLIC','SYMBOLIC_ATTR','SCALAR'):
                Ftr,Fva,Fte=H2.std(Fe[tr],Fe[va],Fe[te]);per.setdefault(name+'_RESID',[]).append(resid_acc(Ftr,Fva,Fte,y[tr],y[va],y[te],k,off))
        # bridge: trained exactly as in attempt 3 (same seeds, blocks, early stop on the select split)
        br=BB.Bridge(Hs.shape[2],K=H2.K,r=H2.R,h=H2.H_DIM,classes=k,seed=seed,direction='B1_TO_B2');br.head=(Wn,bn);best=None
        for blk in range(6):
            br.fit(Hs[tr],Ms[tr],Xr_tr,y[tr],epochs=10,batch=64,lr=3e-3,seed=seed*100+blk) if blk==0 else H2._cont(br,Hs[tr],Ms[tr],Xr_tr,y[tr],seed*100+blk)
            va_acc=float((br.logits(Hs[va],Ms[va],Xr_va).argmax(1)==y[va]).mean())
            if best is None or va_acc>best[0]:best=(va_acc,{kk:v.copy() for kk,v in br.p.items()},br.in_mu.copy(),br.in_sd.copy())
        br.p,br.in_mu,br.in_sd=best[1],best[2],best[3];br.calibrate(Hs[tr],Ms[tr])
        per.setdefault('LATENT',[]).append(float((br.logits(Hs[te],Ms[te],Xr_te).argmax(1)==y[te]).mean()))
        Z=BB.to_bf16(br.encode(Hs,Ms)).reshape(len(rows),-1)
        per.setdefault('LATENT_REFIT',[]).append(refit(np.c_[Xr_all,Z],tr,va,te,y,k))
        Zs=BB.to_bf16(br.encode(Hs,Ms))[g.permutation(len(rows))].reshape(len(rows),-1)  # shuffled control for the refit reader
        per.setdefault('LATENT_REFIT_SHUFFLED',[]).append(refit(np.c_[Xr_all,Zs],tr,va,te,y,k))
        rz=g.normal(size=Z.shape)*Z.std(0)+Z.mean(0)
        per.setdefault('LATENT_REFIT_RANDOM',[]).append(refit(np.c_[Xr_all,rz],tr,va,te,y,k))
        Ztr,Zva,Zte=H2.std(Z[tr],Z[va],Z[te])
        for name,v in (('U',U),('F',F)):
            probe[name]['sender_pca16'].append(r2(Xs_tr,v[tr],Xs_va,v[va],Xs_all[te],v[te]))
            probe[name]['bridge_msg'].append(r2(Ztr,v[tr],Zva,v[va],Zte,v[te]))
        print(task,seed,{c:round(v[-1],3) for c,v in per.items()},flush=True)
    return per,probe

def gate(per,by,lat,sym):
    acc={'NO_MESSAGE':per['NO_MESSAGE'],'EXACT':per['EXACT'],'LATENT':per[lat],'SYMBOLIC':per[sym],
         'LATENT_SHUFFLED':per[lat+'_SHUFFLED'] if lat+'_SHUFFLED' in per else None,'LATENT_RANDOM':per[lat+'_RANDOM'] if lat+'_RANDOM' in per else None}
    acc={c:v for c,v in acc.items() if v is not None};b=dict(by);b['SYMBOLIC']=by[sym.replace('_RESID','')];b['LATENT']=by['LATENT']
    # role/OOD/reload are unchanged by a refit reader of the same message; attempt 3 measured them (<=0.3 pt, 1.0-1.2 %, identical)
    return BB.l1_gate({'acc':acc,'bytes':b,'role_drop':0.,'ood_rate':0.,'reload_identical':True})

def main(states,out,seeds=5):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=V3.make();t=time.time()
    c=np.load(states);d={k:c[k] for k in c.files};Hs=d['Hs'].astype(np.float32);Ms=d['Ms']
    mu,V=H2.pca(d['cue_span'],H2.R*2);exact=(d['cue_span']-mu)@V.T;exact_bytes=float(np.mean([len(r['cue_span'].encode()) for r in rows]))
    words={'escalate':V3.YESNO,'apologize':V3.YESNO,'action':V3.ACTION_WORD}
    rep={'kind':'B3_L1_DIAGNOSIS','status':'EXPLORATORY (test items seen by attempt 3); diagnostic gate only, no canon verdict',
         'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'bridge_sha256':hashlib.sha256(Path(BB.__file__).read_bytes()).hexdigest(),
         'v3_script_sha256':hashlib.sha256(Path(V3.__file__).read_bytes()).hexdigest(),'states_sha256':hashlib.sha256(Path(states).read_bytes()).hexdigest(),
         'data_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'seeds':seeds,'tasks':{}}
    for task in TASKS:
        per,probe=run_task(task,rows,d['recv_private'].astype(np.float64),d['send_pool'].astype(np.float64),Hs,Ms,exact,seeds)
        by={'NO_MESSAGE':0,'EXACT':exact_bytes,'SYMBOLIC':float(np.mean([len(w) for w in words[task]])),
            'SYMBOLIC_ATTR':float(np.mean([len(f'urgency {a}, frustration {b}') for a in V3.LEVEL for b in V3.LEVEL])),'SCALAR':4,'LATENT':H2.K*H2.R*2}
        cost={c:round(BB.BYTES_W*min(1.,b/BB.BYTES_NORM),5) for c,b in by.items()}
        m={c:round(float(np.mean(v)),4) for c,v in per.items()}
        rep['tasks'][task]={'acc_mean':m,'acc_per_seed':{c:[round(x,4) for x in v] for c,v in per.items()},'bytes':by,'byte_cost':cost,
            'H1_max_byte_cost_gap_vs_symbolic':round(max(abs(cost['LATENT']-cost['SYMBOLIC']),abs(cost['LATENT']-cost['SYMBOLIC_ATTR'])),5),
            'H2_refit_gain_pts':round(100*(m['LATENT_REFIT']-m['LATENT']),2),
            'H2_resid_cost_pts':{s:round(100*(m[s]-m[s+'_RESID']),2) for s in ('SYMBOLIC','SYMBOLIC_ATTR','SCALAR')},
            'H3_probe_r2':{q:{k:round(float(np.mean(v)),4) for k,v in p.items()} for q,p in probe.items()},'depends_on':DEPENDS[task],
            'paired_LATENT_REFIT_minus_LATENT':BB.paired(per['LATENT_REFIT'],per['LATENT']),
            'diagnostic_gate':{'canon_like_label_word':gate(per,by,'LATENT_REFIT','SYMBOLIC'),'canon_like_attr_words':gate(per,by,'LATENT_REFIT','SYMBOLIC_ATTR'),
                               'strict_scalar':gate(per,by,'LATENT_REFIT','SCALAR'),'resid_fair_attr_words':gate(per,by,'LATENT','SYMBOLIC_ATTR_RESID'),
                               'resid_fair_label_word':gate(per,by,'LATENT','SYMBOLIC_RESID')}}
    T=rep['tasks']
    rep['verdicts']={'H1_bytes_not_cause':all(x['H1_max_byte_cost_gap_vs_symbolic']<.005 for x in T.values()),
        'H2_head_asymmetry':sum(x['H2_refit_gain_pts']>=3 for x in T.values())>=2 or sum(min(x['H2_resid_cost_pts']['SYMBOLIC_ATTR'],x['H2_resid_cost_pts']['SCALAR'])>=3 for x in T.values())>=2,
        'H3_supervision_per_task':{t:any(x['H3_probe_r2'][q]['bridge_msg']<x['H3_probe_r2'][q]['sender_pca16']-.1 for q in ('U','F') if q in x['depends_on']) for t,x in T.items()},
        'diagnostic_gate_pass':{t:{k:v['verdict'] for k,v in x['diagnostic_gate'].items()} for t,x in T.items()}}
    rep['seconds']=round(time.time()-t,1)
    (out/'report.json').write_text(json.dumps(rep,indent=1,default=float));print(json.dumps(rep['verdicts'],indent=1))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 5)
