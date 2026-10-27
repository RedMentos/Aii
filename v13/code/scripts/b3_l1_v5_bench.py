"""WP-J B3-H3 L1 attempt 5: escalate/apologize with a receiver-conditioned bridge on FRESH data (cloud, preregistered).

Attempt 4 (bench-results/b3-l1-v4-20261021) passed L1 only on private/action. escalate and apologize need a
receiver-private fact (team capacity / client status) combined with the sender quantity (escalate = U > thr[capacity],
apologize = F > thr[client]); action is sender-computable. The bridge reads as an additive residual on the FROZEN
NO_MESSAGE readout, whose capacity/client weights were fit without U/F and are therefore attenuated; a sharp message
term cannot rescale them, so the per-capacity threshold blurs. All baselines get a jointly refit readout. Diagnosis:
bench-results/b3-l1-escapo-diagnose-20261021 (exploratory, attempt-4 states).

Compared with attempt 4 (b3_l1_v4_bench.py) only two things change:
  * data: new seed SEED_DATA=20261105 (same templates, tasks and rule thresholds, 600 fresh rows; new B1/B2 states);
    rows whose sender text also occurs in attempt 3 or 4 are counted and reported;
  * LATENT = aux bridge (attempt-4 recipe) built with Bridge(recv_cond=receiver dim): a gated re-weighting of the
    receiver's own state while the message gate is open (gate closed => frozen NO_MESSAGE readout, unchanged), trained
    end to end, then `refit_readout`: the open-gate readout is refit jointly over [receiver state, gated message
    projection] on the fit split with L2 picked on the select split - the same readout every baseline channel gets.
    The message, selector and projectors are not touched by the refit. References (not gate inputs): LATENT_AUX
    (attempt-4 aux bridge) and LATENT_RC_E2E (the same recv_cond bridge before the readout refit).

Unchanged: gate (v13/b3bridge.l1_gate), bridge message (K=4, r=8, h=16, 64 B BF16), all baselines/controls, splits
(60/20/20, seeds 0..4), role retention, OOD, reload identity, both views, canon rule (label word AND attribute words).

Usage: b3_l1_v5_bench.py <home> <out_dir> [threads] [seeds]
Claim limits: receiver-adapter read only (L1, no backbone injection); synthetic templates (same as attempts 3/4);
oracle EXACT span; mean-pooled receiver state; Linux CPU cloud, not Redmi. A PASS only allows an L2 SHADOW experiment;
LATENT authority 0."""
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import b3_h2_bench as H2
import b3_l1_v3_bench as V3
import b3_l1_v4_bench as V4
from v13 import b3bridge as BB

SEED_DATA=20261105;K=H2.K;R=H2.R;H_DIM=H2.H_DIM;PCA_RECV=H2.PCA_RECV;AUX=('U','F')

def train_bridge(Hs,Ms,Xr_tr,Xr_va,y,tr,va,k,head,seed,aux,recv_cond=0):
    """Attempt-4 recipe (6 blocks x 10 epochs, best block on the select split, aux in every block) + optional recv_cond."""
    br=BB.Bridge(Hs.shape[2],K=K,r=R,h=H_DIM,classes=k,seed=seed,direction='B1_TO_B2',aux=aux.shape[1],recv_cond=recv_cond);br.head=head;best=None
    for blk in range(6):
        mu,sd=br.in_mu.copy(),br.in_sd.copy()
        br.fit(Hs[tr],Ms[tr],Xr_tr,y[tr],epochs=10,batch=64,lr=3e-3,seed=seed*100+blk,aux=aux[tr])
        if blk:br.in_mu,br.in_sd=mu,sd
        va_acc=float((br.logits(Hs[va],Ms[va],Xr_va).argmax(1)==y[va]).mean())
        if best is None or va_acc>best[0]:best=(va_acc,{kk:v.copy() for kk,v in br.p.items()},br.in_mu.copy(),br.in_sd.copy(),(blk+1)*10)
    br.p,br.in_mu,br.in_sd=best[1],best[2],best[3];br.calibrate(Hs[tr],Ms[tr])
    return br,{'epochs':best[4],'val_acc':round(best[0],4),'last':br.manifest['train']['last']}

def run_task(task,rows,recv,send_pool,Hs,Ms,exact_feat,exact_bytes,seeds,lat):
    y=np.array([r[task] for r in rows]);k=int(y.max())+1;words={'escalate':V3.YESNO,'apologize':V3.YESNO,'action':V3.ACTION_WORD}[task]
    U=np.array([r['U'] for r in rows],float);F=np.array([r['F'] for r in rows],float);topic=np.array([r['topic'] for r in rows]);T=np.c_[U,F]
    per={};extra={'ood_rate':[],'role_drop':[],'reload_identical':[],'diversity':[],'train':[],'train_aux':[]}
    for seed in range(seeds):
        g=np.random.default_rng(seed);idx=g.permutation(len(rows));n=len(idx);tr,va,te=idx[:n*3//5],idx[n*3//5:n*4//5],idx[n*4//5:]
        mu,V=H2.pca(recv[tr],PCA_RECV);Xr=(recv-mu)@V.T;Xr_tr,Xr_va,Xr_te=H2.std(Xr[tr],Xr[va],Xr[te]);Xr_all=H2.std(Xr[tr],Xr)[1]
        Wn,bn=H2.sel_head(Xr_tr,y[tr],Xr_va,y[va],k);per.setdefault('NO_MESSAGE',[]).append(H2.acc(Wn,bn,Xr_te,y[te]))
        smu,SV=H2.pca(send_pool[tr],PCA_RECV);Xs=(send_pool-smu)@SV.T;Xs_tr,Xs_va,Xs_all=H2.std(Xs[tr],Xs[va],Xs)
        Ws,bs=H2.sel_head(Xs_tr,y[tr],Xs_va,y[va],k);P=H2.probs(Ws,bs,Xs_all)
        sym=np.eye(k)[P.argmax(1)];ent=-(P*np.log(P+1e-12)).sum(1);ctl=np.c_[P.max(1),ent].astype(np.float16).astype(float)
        attr=[]
        for v in (U,F):
            lv=V3.tertile(v,tr);Wa,ba=H2.sel_head(Xs_tr,lv[tr],Xs_va,lv[va],3);attr.append(np.eye(3)[H2.probs(Wa,ba,Xs_all).argmax(1)])
        attr=np.c_[attr[0],attr[1]]
        sc=np.c_[[(Xs_all@w+b) for w,b in [V3.sel_ridge(Xs_tr,v[tr],Xs_va,v[va]) for v in (U,F)]]].T.astype(np.float16).astype(float)
        for name,Fe in (('EXACT',exact_feat),('SYMBOLIC',sym),('SYMBOLIC_ATTR',attr),('SCALAR',sc),('CONTROL',ctl)):
            X=np.c_[Xr_all,Fe];a,bb,c=H2.std(X[tr],X[va],X[te]);W,b=H2.sel_head(a,y[tr],bb,y[va],k);per.setdefault(name,[]).append(H2.acc(W,b,c,y[te]))
        z=(send_pool-smu)@SV[:16].T;X=np.c_[Xr_all,BB.to_bf16(z)];a,bb,c=H2.std(X[tr],X[va],X[te]);W,b=H2.sel_head(a,y[tr],bb,y[va],k)
        per.setdefault('L1_MEANPOOL',[]).append(H2.acc(W,b,c,y[te]))
        A=(T-T[tr].mean(0))/T[tr].std(0)
        b0,info0=train_bridge(Hs,Ms,Xr_tr,Xr_va,y,tr,va,k,(Wn,bn),seed,A)
        per.setdefault('LATENT_AUX',[]).append(float((b0.logits(Hs[te],Ms[te],Xr_te).argmax(1)==y[te]).mean()));extra['train_aux'].append(info0)
        br,info=train_bridge(Hs,Ms,Xr_tr,Xr_va,y,tr,va,k,(Wn,bn),seed,A,recv_cond=Xr.shape[1])
        per.setdefault('LATENT_RC_E2E',[]).append(float((br.logits(Hs[te],Ms[te],Xr_te).argmax(1)==y[te]).mean()))
        info['readout_l2']=br.refit_readout(Hs[tr],Ms[tr],Xr_tr,y[tr],Xr_va,Hs[va],Ms[va],y[va]);extra['train'].append(info)
        t0=time.perf_counter();L=br.logits(Hs[te],Ms[te],Xr_te);lat.append((time.perf_counter()-t0)/len(te))
        per.setdefault('LATENT',[]).append(float((L.argmax(1)==y[te]).mean()))
        Z=BB.to_bf16(br.encode(Hs[te],Ms[te]))
        per.setdefault('LATENT_SHUFFLED',[]).append(float((br.receive(Z[g.permutation(len(Z))],Xr_te).argmax(1)==y[te]).mean()))
        rz=g.normal(size=Z.shape);rz*=np.linalg.norm(Z.reshape(len(Z),-1),axis=1)[:,None,None]/np.linalg.norm(rz.reshape(len(rz),-1),axis=1)[:,None,None]
        cal=br.cal;br.cal=None;per.setdefault('LATENT_RANDOM',[]).append(float((br.receive(rz,Xr_te).argmax(1)==y[te]).mean()));br.cal=cal
        extra['ood_rate'].append(float((br.ood(Z)>br.cal['ood_tau']).mean()))
        Uf=lambda ii:br.gate()*(BB.to_bf16(br.encode(Hs[ii],Ms[ii])).reshape(len(ii),-1)@br.p['Pr'])
        Wt,bt=H2.sel_head(Xr_tr,topic[tr],Xr_va,topic[va],3);a0=H2.acc(Wt,bt,Xr_te,topic[te])
        Ctr,Cva,Cte=H2.std(np.c_[Xr_tr,Uf(tr)],np.c_[Xr_va,Uf(va)],np.c_[Xr_te,Uf(te)]);Wc,bc=H2.sel_head(Ctr,topic[tr],Cva,topic[va],3)
        extra['role_drop'].append(a0-H2.acc(Wc,bc,Cte,topic[te]))
        with tempfile.TemporaryDirectory() as t:
            br.save(Path(t)/'x','s','r');b2=BB.Bridge.load(Path(t)/'x','s','r');extra['reload_identical'].append(bool(np.array_equal(b2.logits(Hs[te],Ms[te],Xr_te),L)))
        if seed==0:
            extra['diversity'].append(BB.diversity_report(br,Hs[te],Ms[te],send_pool[te],recv[te],Xr_te));extra['bridge']=br
        print(task,seed,{c:round(v[-1],3) for c,v in per.items()},flush=True)
    bytes_={'NO_MESSAGE':0,'EXACT':exact_bytes,'SYMBOLIC':float(np.mean([len(w) for w in words])),
            'SYMBOLIC_ATTR':float(np.mean([len(f'urgency {a}, frustration {b}') for a in V3.LEVEL for b in V3.LEVEL])),'SCALAR':4,'CONTROL':4,'LATENT':K*R*2,'L1_MEANPOOL':32}
    gates={'label_word':V3.gate_with(per,bytes_,extra,'SYMBOLIC'),'attr_words':V3.gate_with(per,bytes_,extra,'SYMBOLIC_ATTR'),'strict_scalar':V3.gate_with(per,bytes_,extra,'SCALAR')}
    canon='PASS' if gates['label_word']['verdict']==gates['attr_words']['verdict']=='PASS' else 'FAIL'
    res={'chance':round(float(np.bincount(y).max()/len(y)),3),'acc':{c:{'mean':round(float(np.mean(v)),4),'sd':round(float(np.std(v)),4),'per_seed':[round(x,4) for x in v]} for c,v in per.items()},
         'bytes':bytes_,'paired_LATENT_minus_NO_MESSAGE':BB.paired(per['LATENT'],per['NO_MESSAGE']),'paired_LATENT_minus_EXACT_acc':BB.paired(per['LATENT'],per['EXACT']),
         'paired_LATENT_minus_LATENT_AUX':BB.paired(per['LATENT'],per['LATENT_AUX']),'paired_LATENT_minus_LATENT_RC_E2E':BB.paired(per['LATENT'],per['LATENT_RC_E2E']),'paired_LATENT_minus_SCALAR_acc':BB.paired(per['LATENT'],per['SCALAR']),
         'role_drop':round(float(np.mean(extra['role_drop'])),4),'role_drop_per_seed':[round(x,4) for x in extra['role_drop']],'ood_rate':round(float(np.mean(extra['ood_rate'])),4),
         'reload_identical':all(extra['reload_identical']),'diversity_seed0':extra['diversity'][0],'train':extra['train'],'train_aux':extra['train_aux'],
         'l1_gates':gates,'canon_verdict':canon,'strict_verdict':gates['strict_scalar']['verdict']}
    return res,extra['bridge']

def overlap(rows):
    o3={r['text'] for r in V3.make()};o4={r['text'] for r in V3.make(V4.SEED_DATA)}
    return {'same_sender_text_as_attempt3':sum(r['text'] in o3 for r in rows),'same_sender_text_as_attempt4':sum(r['text'] in o4 for r in rows),'n':len(rows)}

def main(home,out,threads=4,seeds=5):
    home=Path(home);out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=V3.make(SEED_DATA)
    b1=next((home/'models/body').glob('*.gguf'));b2=next((home/'models/gist').glob('*.gguf'));cache=out/'states.npz';t=time.time()
    data_sha=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    if cache.exists():
        c=np.load(cache);d={k:c[k] for k in c.files}
    else:
        Hs,Ms=H2.tokens(home,b1,[r['text'] for r in rows],threads)
        sp,_=H2.pooled(home,b1,[r['text'] for r in rows],threads)
        rp,lat_p=H2.pooled(home,b2,[r['private'] for r in rows],threads);rs,lat_s=H2.pooled(home,b2,[r['shared'] for r in rows],threads)
        cs,lat_c=H2.pooled(home,b2,[r['cue_span'] for r in rows],threads)
        d={'Hs':Hs.astype(np.float16),'Ms':Ms,'send_pool':sp,'recv_private':rp,'recv_shared':rs,'cue_span':cs,'lat':np.array([lat_p,lat_s,lat_c])}
        np.savez_compressed(cache,**d)
    Hs=d['Hs'].astype(np.float32);Ms=d['Ms'];emb_s=time.time()-t
    mu,V=H2.pca(d['cue_span'],R*2);exact=(d['cue_span']-mu)@V.T;exact_bytes=float(np.mean([len(r['cue_span'].encode()) for r in rows]))
    ys={t:np.array([r[t] for r in rows]) for t in ('escalate','apologize','action','topic')}
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    rep={'kind':'B3_L1_V5_RECV_COND_BRIDGE_FRESH_DATA','script_sha256':sha(__file__),'v3_helpers_sha256':sha(V3.__file__),'v4_helpers_sha256':sha(V4.__file__),
         'bridge_sha256':sha(BB.__file__),'h2_helpers_sha256':sha(H2.__file__),'model_sha256':{'sender':sha(b1),'receiver':sha(b2)},
         'data_seed':SEED_DATA,'data_sha256':data_sha,'overlap':overlap(rows),'sender':b1.name,'receiver':b2.name,'n':len(rows),'K':K,'r':R,'h':H_DIM,
         'aux_targets':list(AUX),'recv_cond':'receiver PCA dim (gated re-weighting of the receiver state)','seeds':seeds,'states_seconds':round(emb_s,1),'sender_dim':int(Hs.shape[2]),'max_tokens':int(Hs.shape[1]),'receiver_dim':int(d['recv_private'].shape[1]),
         'label_balance':{t:np.bincount(v).tolist() for t,v in ys.items()},'exact_bytes_mean':round(exact_bytes,1),
         'budget_b3_h7':BB.budget(int(Hs.shape[2]),K,R,H_DIM,3),
         'receiver_prefill_s_per_item':{'private':round(float(d['lat'][0]),5),'shared':round(float(d['lat'][1]),5),'exact_cue_span':round(float(d['lat'][2]),5)},
         'views':{},'claim_limit':'L1 receiver-adapter read only (no backbone injection); synthetic templates (same as attempts 3/4); EXACT span oracle-selected; mean-pooled receiver state; Linux CPU cloud, not Redmi; LATENT authority stays 0'}
    lat=[]
    for view,key in (('private','recv_private'),('shared','recv_shared')):
        rep['views'][view]={}
        for task in ('escalate','apologize','action'):
            r_,br=run_task(task,rows,d[key].astype(np.float64),d['send_pool'].astype(np.float64),Hs,Ms,exact,exact_bytes,seeds,lat)
            rep['views'][view][task]=r_
            print(view,task,json.dumps({c:v['mean'] for c,v in r_['acc'].items()}),'canon',r_['canon_verdict'],'strict',r_['strict_verdict'],flush=True)
            if view=='private' and r_['canon_verdict']=='PASS':
                br.save(out/f'bridge_private_{task}_B1_TO_B2','bench:'+b1.name,'bench:'+b2.name,{'l1_gate':r_['l1_gates']['attr_words'],'task':f'private/{task}'})
    rep['bridge_latency_us_per_item']=round(1e6*float(np.mean(lat)),1)
    passes=[f'{v}/{t}' for v,ts in rep['views'].items() for t,x in ts.items() if x['canon_verdict']=='PASS']
    strict=[f'{v}/{t}' for v,ts in rep['views'].items() for t,x in ts.items() if x['strict_verdict']=='PASS']
    target=[p for p in passes if p.startswith('private/')]
    rep['summary']={'canon_l1_pass':passes,'strict_scalar_pass':strict,
                    'verdict':('L1 PASS (private view) on '+', '.join(target)) if target else 'L1 FAIL on all target tasks (private view)',
                    'consequence':'L2 prefix SHADOW experiment allowed for the passing task(s); LATENT authority stays 0; runtime unchanged' if target else 'B3_LATENT stays unavailable; L2 stays locked'}
    rep['seconds']=round(time.time()-t,1)
    (out/'report.json').write_text(json.dumps(rep,indent=1,default=float));print(json.dumps(rep['summary']))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 4,int(sys.argv[4]) if len(sys.argv)>4 else 5)
