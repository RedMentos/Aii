"""WP-J B3 L1, EXPLORATORY check of the fix candidate from the 2026-10-20 diagnosis (not a canon verdict).

Diagnosis: the 64 B bridge message already carries U/F (probe R^2 0.88-0.94; decoded with a privileged U/F probe it
matches SCALAR), but the bridge is trained only on the task label, while SYMBOLIC_ATTR/SCALAR get privileged U/F labels.
Fix candidate: Bridge(aux=2).fit(..., aux=standardized [U, F]) - the same supervision the baselines get, used as a
training-only signal; the receiver path and the 64 B message are unchanged.

Same cached states, seeds and splits as attempt 3; the test items were seen before, so this can only motivate a fresh
preregistered attempt 4 on new data. l1_gate is evaluated with SYMBOLIC = label word and = attribute words (both must
PASS, as preregistered for attempt 3); no bridge manifest is written, B3_LATENT stays unavailable.
Usage: b3_l1_aux_explore.py <states.npz> <diagnose_report.json> <out_dir> [seeds]"""
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

def run_task(task,rows,recv,Hs,Ms,seeds):
    y=np.array([r[task] for r in rows]);k=int(y.max())+1;T=np.c_[[r['U'] for r in rows],[r['F'] for r in rows]].astype(float);per={};ood=[]
    for seed in range(seeds):
        g=np.random.default_rng(seed);idx=g.permutation(len(rows));n=len(idx);tr,va,te=idx[:n*3//5],idx[n*3//5:n*4//5],idx[n*4//5:]
        mu,V=H2.pca(recv[tr],H2.PCA_RECV);Xr=(recv-mu)@V.T;Xr_tr,Xr_va,Xr_te=H2.std(Xr[tr],Xr[va],Xr[te])
        Wn,bn=H2.sel_head(Xr_tr,y[tr],Xr_va,y[va],k)
        A=(T-T[tr].mean(0))/T[tr].std(0)
        br=BB.Bridge(Hs.shape[2],K=H2.K,r=H2.R,h=H2.H_DIM,classes=k,seed=seed,direction='B1_TO_B2',aux=2);br.head=(Wn,bn);best=None
        for blk in range(6):
            if blk==0:br.fit(Hs[tr],Ms[tr],Xr_tr,y[tr],epochs=10,batch=64,lr=3e-3,seed=seed*100+blk,aux=A[tr])
            else:
                m_,s_=br.in_mu.copy(),br.in_sd.copy();br.fit(Hs[tr],Ms[tr],Xr_tr,y[tr],epochs=10,batch=64,lr=3e-3,seed=seed*100+blk,aux=A[tr]);br.in_mu,br.in_sd=m_,s_
            va_acc=float((br.logits(Hs[va],Ms[va],Xr_va).argmax(1)==y[va]).mean())
            if best is None or va_acc>best[0]:best=(va_acc,{kk:v.copy() for kk,v in br.p.items()},br.in_mu.copy(),br.in_sd.copy())
        br.p,br.in_mu,br.in_sd=best[1],best[2],best[3];br.calibrate(Hs[tr],Ms[tr])
        per.setdefault('LATENT_AUX',[]).append(float((br.logits(Hs[te],Ms[te],Xr_te).argmax(1)==y[te]).mean()))
        Z=BB.to_bf16(br.encode(Hs[te],Ms[te]))
        per.setdefault('LATENT_AUX_SHUFFLED',[]).append(float((br.receive(Z[g.permutation(len(Z))],Xr_te).argmax(1)==y[te]).mean()))
        rz=g.normal(size=Z.shape);rz*=np.linalg.norm(Z.reshape(len(Z),-1),axis=1)[:,None,None]/np.linalg.norm(rz.reshape(len(rz),-1),axis=1)[:,None,None]
        cal=br.cal;br.cal=None;per.setdefault('LATENT_AUX_RANDOM',[]).append(float((br.receive(rz,Xr_te).argmax(1)==y[te]).mean()));br.cal=cal
        ood.append(float((br.ood(Z)>br.cal['ood_tau']).mean()))
        print(task,seed,{c:round(v[-1],3) for c,v in per.items()},flush=True)
    return per,ood

def main(states,diag,out,seeds=5):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=V3.make();t=time.time();dg=json.loads(Path(diag).read_text())
    c=np.load(states);d={k:c[k] for k in c.files};Hs=d['Hs'].astype(np.float32);Ms=d['Ms']
    rep={'kind':'B3_L1_AUX_EXPLORE','status':'EXPLORATORY (seen test items); motivates attempt 4 only, no canon verdict',
         'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'bridge_sha256':hashlib.sha256(Path(BB.__file__).read_bytes()).hexdigest(),'tasks':{}}
    for task in D.TASKS:
        per,ood=run_task(task,rows,d['recv_private'].astype(np.float64),Hs,Ms,seeds);base=dg['tasks'][task]
        acc={c:base['acc_per_seed'][c] for c in ('NO_MESSAGE','EXACT')}|{'LATENT':per['LATENT_AUX'],'LATENT_SHUFFLED':per['LATENT_AUX_SHUFFLED'],'LATENT_RANDOM':per['LATENT_AUX_RANDOM']}
        gates={}
        for name,sym in (('label_word','SYMBOLIC'),('attr_words','SYMBOLIC_ATTR'),('strict_scalar','SCALAR')):
            by=dict(base['bytes']);by['SYMBOLIC']=base['bytes'][sym]
            gates[name]=BB.l1_gate({'acc':acc|{'SYMBOLIC':base['acc_per_seed'][sym]},'bytes':by,'role_drop':0.,'ood_rate':float(np.mean(ood)),'reload_identical':True})
        rep['tasks'][task]={'acc_mean':{c:round(float(np.mean(v)),4) for c,v in per.items()}|{c:base['acc_mean'][c] for c in ('NO_MESSAGE','EXACT','SYMBOLIC','SYMBOLIC_ATTR','SCALAR','LATENT')},
                            'acc_per_seed':{c:[round(x,4) for x in v] for c,v in per.items()},'ood_rate':round(float(np.mean(ood)),4),
                            'paired_LATENT_AUX_minus_LATENT':BB.paired(per['LATENT_AUX'],base['acc_per_seed']['LATENT']),
                            'gates':gates,'exploratory_verdict':'PASS' if gates['label_word']['verdict']==gates['attr_words']['verdict']=='PASS' else 'FAIL',
                            'note':'role retention not re-measured here (receiver path unchanged); reload identity covered by tests/test_b3bridge'}
    rep['seconds']=round(time.time()-t,1)
    (out/'aux_explore.json').write_text(json.dumps(rep,indent=1,default=float))
    print(json.dumps({t:{'acc':x['acc_mean'],'verdict':x['exploratory_verdict'],'strict':x['gates']['strict_scalar']['verdict']} for t,x in rep['tasks'].items()},indent=1))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]) if len(sys.argv)>4 else 5)
