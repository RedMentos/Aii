"""B3 L1: why do escalate/apologize fail while action passes? Exploratory diagnosis on the attempt-4 states (cloud).

Attempt 4 (bench-results/b3-l1-v4-20261021) passed L1 only on private/action. escalate and apologize differ from action in
one structural way: their label needs a RECEIVER-PRIVATE fact (team capacity / client status) combined with the sender
quantity (escalate = U > thr[capacity], apologize = F > thr[client]); action is sender-computable.

The bridge reads as an additive residual on the FROZEN NO_MESSAGE readout. That readout was fit without U/F, so its
capacity/client weights are attenuated (U/F act as noise). With a sharp message term a*U the needed receiver term is
a*thr[capacity]; a frozen, attenuated receiver term cannot be rescaled, so the per-capacity threshold blurs. Every
baseline (EXACT, SYMBOLIC, SYMBOLIC_ATTR, SCALAR) gets a jointly refit readout over [receiver state, feature] instead.

Hypotheses (checked here, exploratory: the test items were already used by attempt 4):
  D1 frozen-head cost   ORACLE U/F through the frozen residual vs a jointly refit readout; cost >= 3 points on
                        escalate and apologize and < 1.5 on action => the frozen residual is the structural cause.
  D2 receiver fact      capacity/client decodable from the receiver state (3-way accuracy); if low, no channel can help.
  D3 fix candidate      Bridge(recv_cond=dim): gated re-weighting of the receiver's own state while the message is open
                        (gate closed => frozen NO_MESSAGE readout, unchanged). LATENT_RC vs LATENT (attempt-4 recipe).
  D4 error locus        share of LATENT errors with |quantity - threshold| <= 1 (near-threshold precision vs fact blur).

Usage: b3_l1_escapo_diagnose.py <attempt4_states.npz> <out_dir> [seeds]
Claim limit: exploratory, seen test items; not a canon L1 verdict. Linux CPU cloud."""
import json
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import b3_h2_bench as H2
import b3_l1_v3_bench as V3
import b3_l1_diagnose as DG
from v13 import b3bridge as BB

SEED_DATA=20261021;K=H2.K;R=H2.R;H_DIM=H2.H_DIM;PCA_RECV=H2.PCA_RECV
PRIV={'escalate':('cap',V3.CAP,'U'),'apologize':('client',V3.CLIENT,'F'),'action':(None,None,'U+F')}

def train_bridge(Hs,Ms,Xr_tr,Xr_va,y,tr,va,k,head,seed,aux,recv_cond=0):
    """Attempt-4 recipe (6 blocks x 10 epochs, best block on select, aux every block); recv_cond optional."""
    br=BB.Bridge(Hs.shape[2],K=K,r=R,h=H_DIM,classes=k,seed=seed,direction='B1_TO_B2',aux=aux.shape[1],recv_cond=recv_cond);br.head=head;best=None
    for blk in range(6):
        mu,sd=br.in_mu.copy(),br.in_sd.copy()
        br.fit(Hs[tr],Ms[tr],Xr_tr,y[tr],epochs=10,batch=64,lr=3e-3,seed=seed*100+blk,aux=aux[tr])
        if blk:br.in_mu,br.in_sd=mu,sd
        va_acc=float((br.logits(Hs[va],Ms[va],Xr_va).argmax(1)==y[va]).mean())
        if best is None or va_acc>best[0]:best=(va_acc,{kk:v.copy() for kk,v in br.p.items()},br.in_mu.copy(),br.in_sd.copy())
    br.p,br.in_mu,br.in_sd=best[1],best[2],best[3];br.calibrate(Hs[tr],Ms[tr]);return br

def run_task(task,rows,recv,send_pool,Hs,Ms,seeds):
    y=np.array([r[task] for r in rows]);k=int(y.max())+1
    U=np.array([r['U'] for r in rows],float);F=np.array([r['F'] for r in rows],float);T=np.c_[U,F]
    key,thr,dep=PRIV[task]
    if key:
        fact=np.array([list(thr).index(r[key]) for r in rows]);q=U if dep=='U' else F;th=np.array([thr[r[key]] for r in rows],float)
    per={};near={'LATENT':[],'LATENT_RC':[]};fact_acc=[]
    for seed in range(seeds):
        g=np.random.default_rng(seed);idx=g.permutation(len(rows));n=len(idx);tr,va,te=idx[:n*3//5],idx[n*3//5:n*4//5],idx[n*4//5:]
        mu,V=H2.pca(recv[tr],PCA_RECV);Xr=(recv-mu)@V.T;Xr_tr,Xr_va,Xr_te=H2.std(Xr[tr],Xr[va],Xr[te]);Xr_all=H2.std(Xr[tr],Xr)[1]
        Wn,bn=H2.sel_head(Xr_tr,y[tr],Xr_va,y[va],k);per.setdefault('NO_MESSAGE',[]).append(H2.acc(Wn,bn,Xr_te,y[te]))
        off=(Xr_tr@Wn+bn,Xr_va@Wn+bn,Xr_te@Wn+bn)
        if key:
            Wf,bf=H2.sel_head(Xr_tr,fact[tr],Xr_va,fact[va],3);fact_acc.append(H2.acc(Wf,bf,Xr_te,fact[te]))
        smu,SV=H2.pca(send_pool[tr],PCA_RECV);Xs=(send_pool-smu)@SV.T;Xs_tr,Xs_va,Xs_all=H2.std(Xs[tr],Xs[va],Xs)
        sc=np.c_[[(Xs_all@w+b) for w,b in [V3.sel_ridge(Xs_tr,v[tr],Xs_va,v[va]) for v in (U,F)]]].T.astype(np.float16).astype(float)
        attr=[]
        for v in (U,F):
            lv=V3.tertile(v,tr);Wa,ba=H2.sel_head(Xs_tr,lv[tr],Xs_va,lv[va],3);attr.append(np.eye(3)[H2.probs(Wa,ba,Xs_all).argmax(1)])
        attr=np.c_[attr[0],attr[1]]
        for name,Fe in (('ORACLE_UF',T),('SCALAR',sc),('SYMBOLIC_ATTR',attr)):
            per.setdefault(name+'_REFIT',[]).append(DG.refit(np.c_[Xr_all,Fe],tr,va,te,y,k))
            a,bb,c=H2.std(Fe[tr],Fe[va],Fe[te]);per.setdefault(name+'_FROZEN',[]).append(DG.resid_acc(a,bb,c,y[tr],y[va],y[te],k,off))
        if key:per.setdefault('ORACLE_UF_TRUEFACT',[]).append(DG.refit(np.c_[np.eye(3)[fact],T],tr,va,te,y,k))
        A=(T-T[tr].mean(0))/T[tr].std(0)
        for name,rc in (('LATENT',0),('LATENT_RC',Xr.shape[1])):
            br=train_bridge(Hs,Ms,Xr_tr,Xr_va,y,tr,va,k,(Wn,bn),seed,A,rc);L=br.logits(Hs[te],Ms[te],Xr_te);wrong=L.argmax(1)!=y[te]
            per.setdefault(name,[]).append(float(1-wrong.mean()))
            Z=BB.to_bf16(br.encode(Hs[te],Ms[te]));per.setdefault(name+'_SHUFFLED',[]).append(float((br.receive(Z[g.permutation(len(Z))],Xr_te).argmax(1)==y[te]).mean()))
            if key:near[name].append([int(wrong.sum()),int((wrong&(np.abs(q[te]-th[te])<=1)).sum())])
            if name=='LATENT':
                Uf=lambda ii:br.gate()*(BB.to_bf16(br.encode(Hs[ii],Ms[ii])).reshape(len(ii),-1)@br.p['Pr'])
                Ua=np.zeros((len(rows),H_DIM));Ua[idx]=Uf(idx);per.setdefault('LATENT_REFIT',[]).append(DG.refit(np.c_[Xr_all,Ua],tr,va,te,y,k))
        print(task,seed,{c:round(v[-1],3) for c,v in per.items()},flush=True)
    m={c:round(float(np.mean(v)),4) for c,v in per.items()}
    res={'acc':{c:{'mean':m[c],'per_seed':[round(x,4) for x in v]} for c,v in per.items()},
         'D1_frozen_cost_pts':{n:round(100*(m[n+'_REFIT']-m[n+'_FROZEN']),2) for n in ('ORACLE_UF','SCALAR','SYMBOLIC_ATTR')},
         'D3_paired_LATENT_RC_minus_LATENT':BB.paired(per['LATENT_RC'],per['LATENT']),'paired_LATENT_REFIT_minus_LATENT':BB.paired(per['LATENT_REFIT'],per['LATENT'])}
    if key:
        res['D2_fact_from_receiver_acc']=round(float(np.mean(fact_acc)),4)
        res['D4_errors_near_threshold']={n:{'errors':int(sum(a for a,_ in v)),'near_le1':int(sum(b for _,b in v))} for n,v in near.items()}
        res['near_threshold_share_of_test_items']=round(float(np.mean(np.abs(q-th)<=1)),4)
    return res

def main(states,out,seeds=5):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=V3.make(SEED_DATA);t=time.time()
    c=np.load(states);Hs=c['Hs'].astype(np.float32);Ms=c['Ms'];recv=c['recv_private'].astype(np.float64);sp=c['send_pool'].astype(np.float64)
    rep={'kind':'B3_L1_ESCAPO_DIAGNOSE_EXPLORATORY','states':str(Path(states).name),'data_seed':SEED_DATA,'seeds':seeds,'view':'private','tasks':{},
         'claim_limit':'exploratory on attempt-4 test items (already seen); not a canon verdict'}
    for task in ('escalate','apologize','action'):
        rep['tasks'][task]=run_task(task,rows,recv,sp,Hs,Ms,seeds);print(task,json.dumps({k:v for k,v in rep['tasks'][task].items() if k!='acc'}),flush=True)
    rep['seconds']=round(time.time()-t,1);(out/'report.json').write_text(json.dumps(rep,indent=1,default=float))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 5)
