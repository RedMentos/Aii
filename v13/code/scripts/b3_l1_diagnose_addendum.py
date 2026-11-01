"""WP-J B3 L1 diagnosis, POST-HOC addendum (2026-10-20, not preregistered; written after b3_l1_diagnose.py showed that
the bridge message carries U/F almost as well as sender PCA-16 but still loses in task accuracy).

Question: is the gap the CONTENT of the 64 B message or the RECEIVER READOUT that has to find the U/F direction in a
32-dim message from a few hundred binary labels, while SCALAR gets that direction from privileged U/F regression labels?

  LATENT_PROBE  = ridge U, F read out of the SAME bridge message Z (privileged labels, exactly like SCALAR) -> 2 x fp16
                  -> refit head. If LATENT_PROBE ~ SCALAR, the message content is sufficient and the gap is readout.
  learning curve: fit split subsampled to 50 % and 100 % for LATENT, LATENT_REFIT, SCALAR, SYMBOLIC_ATTR.

Same states, seeds and splits as attempt 3. Diagnostic only, no canon verdict, no bridge manifest.
Usage: b3_l1_diagnose_addendum.py <states.npz> <out_dir> [seeds]"""
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
import b3_l1_diagnose as D
from v13 import b3bridge as BB

FRACS=(.5,1.)

def train_bridge(Hs,Ms,Xr_tr,Xr_va,y,tr,va,k,Wn,bn,seed):
    br=BB.Bridge(Hs.shape[2],K=H2.K,r=H2.R,h=H2.H_DIM,classes=k,seed=seed,direction='B1_TO_B2');br.head=(Wn,bn);best=None
    for blk in range(6):
        br.fit(Hs[tr],Ms[tr],Xr_tr,y[tr],epochs=10,batch=64,lr=3e-3,seed=seed*100+blk) if blk==0 else H2._cont(br,Hs[tr],Ms[tr],Xr_tr,y[tr],seed*100+blk)
        va_acc=float((br.logits(Hs[va],Ms[va],Xr_va).argmax(1)==y[va]).mean())
        if best is None or va_acc>best[0]:best=(va_acc,{kk:v.copy() for kk,v in br.p.items()},br.in_mu.copy(),br.in_sd.copy())
    br.p,br.in_mu,br.in_sd=best[1],best[2],best[3];return br

def run_task(task,rows,recv,send_pool,Hs,Ms,seeds):
    y=np.array([r[task] for r in rows]);k=int(y.max())+1
    U=np.array([r['U'] for r in rows],float);F=np.array([r['F'] for r in rows],float);out={}
    for frac in FRACS:
        per={}
        for seed in range(seeds):
            g=np.random.default_rng(seed);idx=g.permutation(len(rows));n=len(idx);tr,va,te=idx[:n*3//5],idx[n*3//5:n*4//5],idx[n*4//5:]
            tr=tr[:int(round(len(tr)*frac))]
            mu,V=H2.pca(recv[tr],H2.PCA_RECV);Xr=(recv-mu)@V.T;Xr_tr,Xr_va,Xr_te=H2.std(Xr[tr],Xr[va],Xr[te]);Xr_all=H2.std(Xr[tr],Xr)[1]
            Wn,bn=H2.sel_head(Xr_tr,y[tr],Xr_va,y[va],k);per.setdefault('NO_MESSAGE',[]).append(H2.acc(Wn,bn,Xr_te,y[te]))
            smu,SV=H2.pca(send_pool[tr],H2.PCA_RECV);Xs=(send_pool-smu)@SV.T;Xs_tr,Xs_va,Xs_all=H2.std(Xs[tr],Xs[va],Xs)
            attr=[]
            for v in (U,F):
                lv=V3.tertile(v,tr);Wa,ba=H2.sel_head(Xs_tr,lv[tr],Xs_va,lv[va],3);attr.append(np.eye(3)[H2.probs(Wa,ba,Xs_all).argmax(1)])
            sc=np.c_[[(Xs_all@w+b) for w,b in [V3.sel_ridge(Xs_tr,v[tr],Xs_va,v[va]) for v in (U,F)]]].T.astype(np.float16).astype(float)
            per.setdefault('SYMBOLIC_ATTR',[]).append(D.refit(np.c_[Xr_all,attr[0],attr[1]],tr,va,te,y,k))
            per.setdefault('SCALAR',[]).append(D.refit(np.c_[Xr_all,sc],tr,va,te,y,k))
            br=train_bridge(Hs,Ms,Xr_tr,Xr_va,y,tr,va,k,Wn,bn,seed)
            per.setdefault('LATENT',[]).append(float((br.logits(Hs[te],Ms[te],Xr_te).argmax(1)==y[te]).mean()))
            Z=BB.to_bf16(br.encode(Hs,Ms)).reshape(len(rows),-1);per.setdefault('LATENT_REFIT',[]).append(D.refit(np.c_[Xr_all,Z],tr,va,te,y,k))
            Ztr,Zva,Zall=H2.std(Z[tr],Z[va],Z)
            pz=np.c_[[(Zall@w+b) for w,b in [V3.sel_ridge(Ztr,v[tr],Zva,v[va]) for v in (U,F)]]].T.astype(np.float16).astype(float)
            per.setdefault('LATENT_PROBE',[]).append(D.refit(np.c_[Xr_all,pz],tr,va,te,y,k))
            print(task,frac,seed,{c:round(v[-1],3) for c,v in per.items()},flush=True)
        out[str(frac)]={'n_fit':int(round(360*frac)),'acc_mean':{c:round(float(np.mean(v)),4) for c,v in per.items()},
                        'acc_per_seed':{c:[round(x,4) for x in v] for c,v in per.items()},
                        'paired_LATENT_PROBE_minus_SCALAR':BB.paired(per['LATENT_PROBE'],per['SCALAR']),
                        'paired_LATENT_PROBE_minus_LATENT':BB.paired(per['LATENT_PROBE'],per['LATENT'])}
    return out

def main(states,out,seeds=5):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=V3.make();t=time.time()
    c=np.load(states);d={k:c[k] for k in c.files};Hs=d['Hs'].astype(np.float32);Ms=d['Ms']
    rep={'kind':'B3_L1_DIAGNOSIS_ADDENDUM','status':'POST-HOC, not preregistered; diagnostic only',
         'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'bridge_sha256':hashlib.sha256(Path(BB.__file__).read_bytes()).hexdigest(),
         'seeds':seeds,'tasks':{}}
    for task in D.TASKS:
        rep['tasks'][task]=run_task(task,rows,d['recv_private'].astype(np.float64),d['send_pool'].astype(np.float64),Hs,Ms,seeds)
    rep['seconds']=round(time.time()-t,1)
    (out/'addendum.json').write_text(json.dumps(rep,indent=1,default=float))
    print(json.dumps({t:{f:x['acc_mean'] for f,x in v.items()} for t,v in rep['tasks'].items()},indent=1))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 5)
