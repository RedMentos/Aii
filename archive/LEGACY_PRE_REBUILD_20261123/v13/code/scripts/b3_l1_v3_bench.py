"""WP-J B3-H3 L1 attempt 3: tasks without a short exact or symbolic form (cloud bench, preregistered).

Attempts 1 (b3_l1_bench.py) and 2 (b3_h2_bench.py) failed G-CALLOSUM-UTILITY-002 on all tasks because every task had a
short exact span (numbers, one tone sentence) or a sender-side label word that carried the same information more cheaply.
This attempt only changes the TASKS, never the gate (v13/b3bridge.l1_gate, unchanged) or the bridge (v13/b3bridge.Bridge,
same K=4, r=8, h=16, 64 B BF16 message):

  * the sender message is a ticket hand-over of 4 sentences; every sentence mixes a graded urgency cue (level 0..4) and a
    graded frustration cue (level 0..4), so the relevant state is distributed over the whole message: the minimal oracle
    EXACT span is the full cue text (all 4 sentences, ~430 B), not one short sentence or number;
  * two tasks depend on receiver-private information the sender never sees (team capacity, client status), so the
    sender cannot compute the label word itself:
      escalate   = sum(urgency) > {low:6, normal:8, high:10}[capacity]
      apologize  = sum(frustration) > {new:9, regular:8, key:6}[client]
  * one task is sender-computable (the honest symbolic case): action = call / fix_quietly / schedule from (U, F);
  * topic is the receiver role task (retention check), as in attempt 2.

Channels (same supervision and splits; per task)
  NO_MESSAGE      receiver state only (pooled B2 state of the receiver's private view)
  EXACT           oracle full cue span re-read by the receiver (PCA 16 of its pooled B2 state, as attempt 2)
  CONTROL         sender head confidence + entropy (2 x fp16)
  SYMBOLIC        sender-side readout sends its predicted task label word
  SYMBOLIC_ATTR   sender-side readouts send urgency and frustration level words (low/mid/high tertiles, trained on the
                  privileged attribute labels; stronger bounded-symbolic baseline)
  SCALAR          (strict add-on, not a canon channel) sender ridge estimates of U and F as 2 x fp16, privileged labels
  LATENT          learned bridge message z[K, r] in BF16; controls LATENT_SHUFFLED, LATENT_RANDOM
  L1_MEANPOOL     attempt-1 message (mean-pooled sender state, PCA 16)

Preregistered verdict (fixed before the run, see code/docs/proofs/b3-l1-v3-20261012/preregistration.json):
  per task and view, l1_gate is evaluated twice, once with SYMBOLIC = label word and once with SYMBOLIC = SYMBOLIC_ATTR;
  L1 PASS for a task requires PASS in both. The SCALAR run is reported as 'strict' and does not change the canon verdict,
  but a strict FAIL is stated as a claim limit. Only the 'private' view is the target experiment; 'shared' (receiver
  also sees the sender text) is a control where NO_MESSAGE should already be strong.

Usage: b3_l1_v3_bench.py <home> <out_dir> [threads] [seeds]
Claim limits: receiver-adapter read only (L1, no backbone injection); synthetic templates and labels; oracle EXACT span;
mean-pooled receiver state; Linux CPU cloud, not Redmi. A PASS only allows an L2 SHADOW experiment; LATENT authority 0."""
import hashlib
import json
import random
import sys
import tempfile
import time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import b3_h2_bench as H2
from v13 import b3bridge as BB

N=600;K=H2.K;R=H2.R;H_DIM=H2.H_DIM;PCA_RECV=H2.PCA_RECV;SEED_DATA=20261012
TOPICS={'billing':['the invoice','the refund','the payment page'],'shipping':['the parcel','the delivery slot','the tracking link'],
        'account':['the login','the password reset','the profile page']}
URG=['It can easily wait until next week.','Whenever you find a moment is fine.','It would be good to sort it out today.',
     'We really need it fixed within the hour.','Everything is blocked, this cannot wait a minute longer.']
URG_ALT=['No rush on this one at all.','Sometime this week would be okay.','Ideally someone looks at it before the evening.',
         'This has to be solved very soon, ideally right away.','It is an emergency and every minute costs us.']
FRU=['Thanks a lot for the friendly help so far.','No big deal, these things happen.','It is getting a little annoying, to be honest.',
     'Honestly, I am quite frustrated by now.','I am absolutely furious about how this was handled.']
FRU_ALT=['I appreciate how patient your team has been.','I am fine with it, just letting you know.','I am slightly irritated that it happened again.',
         'This is really upsetting me more and more.','Frankly this is outrageous and unacceptable.']
CAP={'low':6,'normal':8,'high':10};CLIENT={'new':9,'regular':8,'key':6}
ACTION_WORD=['call','fix_quietly','schedule'];YESNO=['no','yes'];LEVEL=['low','mid','high']

def make(seed=SEED_DATA):
    rnd=random.Random(seed);rows=[]
    for _ in range(N):
        top=rnd.choice(list(TOPICS));objs=[rnd.choice(TOPICS[top]) for _ in range(4)]
        u=[rnd.randrange(5) for _ in range(4)];f=[rnd.randrange(5) for _ in range(4)];sents=[]
        for o,ui,fi in zip(objs,u,f):
            us=rnd.choice((URG,URG_ALT))[ui];fs=rnd.choice((FRU,FRU_ALT))[fi]
            sents.append(f'About {o}: '+(us+' '+fs if rnd.random()<.5 else fs+' '+us))
        U,F=sum(u),sum(f);cap=rnd.choice(list(CAP));cli=rnd.choice(list(CLIENT))
        action=0 if (U>=8 and F>=8) else 1 if U>=8 else 2
        text='Hand-over note. '+' '.join(sents)
        private=f'Ticket area: {top}. Our team capacity today is {cap}. The client is a {cli} client.'
        rows.append({'text':text,'private':private,'shared':text+' '+private,'cue_span':' '.join(sents),
                     'escalate':int(U>CAP[cap]),'apologize':int(F>CLIENT[cli]),'action':action,'topic':list(TOPICS).index(top),
                     'U':U,'F':F,'cap':cap,'client':cli})
    return rows

def tertile(v,tr):
    a,b=np.quantile(v[tr],[1/3,2/3]);return np.digitize(v,[a,b])

def ridge(X,y,l2):
    A=X.T@X+l2*np.eye(X.shape[1]);return np.linalg.solve(A,X.T@(y-y.mean())),y.mean()

def sel_ridge(Xtr,ytr,Xva,yva):
    best=min((float(np.mean((Xva@w+b-yva)**2)),l2) for l2 in (1e-1,1.,10.,100.) for w,b in [ridge(Xtr,ytr,l2)])[1];return ridge(Xtr,ytr,best)

def gate_with(per,bytes_,extra,sym):
    acc={c:v for c,v in per.items() if c in ('NO_MESSAGE','EXACT','CONTROL','LATENT','LATENT_SHUFFLED','LATENT_RANDOM')}
    acc['SYMBOLIC']=per[sym];by=dict(bytes_);by['SYMBOLIC']=bytes_[sym]
    return BB.l1_gate({'acc':acc,'bytes':by,'role_drop':float(np.mean(extra['role_drop'])),'ood_rate':float(np.mean(extra['ood_rate'])),
                       'reload_identical':all(extra['reload_identical'])})

def run_task(task,rows,recv,send_pool,Hs,Ms,exact_feat,exact_bytes,seeds,lat):
    y=np.array([r[task] for r in rows]);k=int(y.max())+1;words={'escalate':YESNO,'apologize':YESNO,'action':ACTION_WORD}[task]
    U=np.array([r['U'] for r in rows],float);F=np.array([r['F'] for r in rows],float);topic=np.array([r['topic'] for r in rows])
    per={};extra={'ood_rate':[],'role_drop':[],'reload_identical':[],'diversity':[],'train':[]}
    for seed in range(seeds):
        g=np.random.default_rng(seed);idx=g.permutation(len(rows));n=len(idx);tr,va,te=idx[:n*3//5],idx[n*3//5:n*4//5],idx[n*4//5:]
        mu,V=H2.pca(recv[tr],PCA_RECV);Xr=(recv-mu)@V.T;Xr_tr,Xr_va,Xr_te=H2.std(Xr[tr],Xr[va],Xr[te]);Xr_all=H2.std(Xr[tr],Xr)[1]
        Wn,bn=H2.sel_head(Xr_tr,y[tr],Xr_va,y[va],k);per.setdefault('NO_MESSAGE',[]).append(H2.acc(Wn,bn,Xr_te,y[te]))
        smu,SV=H2.pca(send_pool[tr],PCA_RECV);Xs=(send_pool-smu)@SV.T;Xs_tr,Xs_va,Xs_all=H2.std(Xs[tr],Xs[va],Xs)
        Ws,bs=H2.sel_head(Xs_tr,y[tr],Xs_va,y[va],k);P=H2.probs(Ws,bs,Xs_all)
        sym=np.eye(k)[P.argmax(1)];ent=-(P*np.log(P+1e-12)).sum(1);ctl=np.c_[P.max(1),ent].astype(np.float16).astype(float)
        attr=[]
        for v in (U,F):
            lv=tertile(v,tr);Wa,ba=H2.sel_head(Xs_tr,lv[tr],Xs_va,lv[va],3);attr.append(np.eye(3)[H2.probs(Wa,ba,Xs_all).argmax(1)])
        attr=np.c_[attr[0],attr[1]]
        sc=np.c_[[(Xs_all@w+b) for w,b in [sel_ridge(Xs_tr,v[tr],Xs_va,v[va]) for v in (U,F)]]].T.astype(np.float16).astype(float)
        for name,Fe in (('EXACT',exact_feat),('SYMBOLIC',sym),('SYMBOLIC_ATTR',attr),('SCALAR',sc),('CONTROL',ctl)):
            X=np.c_[Xr_all,Fe];a,bb,c=H2.std(X[tr],X[va],X[te]);W,b=H2.sel_head(a,y[tr],bb,y[va],k);per.setdefault(name,[]).append(H2.acc(W,b,c,y[te]))
        z=(send_pool-smu)@SV[:16].T;X=np.c_[Xr_all,BB.to_bf16(z)];a,bb,c=H2.std(X[tr],X[va],X[te]);W,b=H2.sel_head(a,y[tr],bb,y[va],k)
        per.setdefault('L1_MEANPOOL',[]).append(H2.acc(W,b,c,y[te]))
        br=BB.Bridge(Hs.shape[2],K=K,r=R,h=H_DIM,classes=k,seed=seed,direction='B1_TO_B2');br.head=(Wn,bn);best=None
        for blk in range(6):
            br.fit(Hs[tr],Ms[tr],Xr_tr,y[tr],epochs=10,batch=64,lr=3e-3,seed=seed*100+blk) if blk==0 else H2._cont(br,Hs[tr],Ms[tr],Xr_tr,y[tr],seed*100+blk)
            va_acc=float((br.logits(Hs[va],Ms[va],Xr_va).argmax(1)==y[va]).mean())
            if best is None or va_acc>best[0]:best=(va_acc,{kk:v.copy() for kk,v in br.p.items()},br.in_mu.copy(),br.in_sd.copy(),(blk+1)*10)
        br.p,br.in_mu,br.in_sd=best[1],best[2],best[3];extra['train'].append({'epochs':best[4],'val_acc':round(best[0],4),'last':br.manifest['train']['last']})
        br.calibrate(Hs[tr],Ms[tr])
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
    bytes_={'NO_MESSAGE':0,'EXACT':exact_bytes,'SYMBOLIC':float(np.mean([len(w) for w in words])),
            'SYMBOLIC_ATTR':float(np.mean([len(f'urgency {a}, frustration {b}') for a in LEVEL for b in LEVEL])),'SCALAR':4,'CONTROL':4,'LATENT':K*R*2,'L1_MEANPOOL':32}
    gates={'label_word':gate_with(per,bytes_,extra,'SYMBOLIC'),'attr_words':gate_with(per,bytes_,extra,'SYMBOLIC_ATTR'),'strict_scalar':gate_with(per,bytes_,extra,'SCALAR')}
    canon='PASS' if gates['label_word']['verdict']==gates['attr_words']['verdict']=='PASS' else 'FAIL'
    res={'chance':round(float(np.bincount(y).max()/len(y)),3),'acc':{c:{'mean':round(float(np.mean(v)),4),'sd':round(float(np.std(v)),4),'per_seed':[round(x,4) for x in v]} for c,v in per.items()},
         'bytes':bytes_,'paired_LATENT_minus_NO_MESSAGE':BB.paired(per['LATENT'],per['NO_MESSAGE']),'paired_LATENT_minus_EXACT_acc':BB.paired(per['LATENT'],per['EXACT']),
         'paired_LATENT_minus_L1_MEANPOOL':BB.paired(per['LATENT'],per['L1_MEANPOOL']),
         'role_drop':round(float(np.mean(extra['role_drop'])),4),'ood_rate':round(float(np.mean(extra['ood_rate'])),4),'reload_identical':all(extra['reload_identical']),
         'diversity_seed0':extra['diversity'][0],'train':extra['train'],'l1_gates':gates,'canon_verdict':canon,'strict_verdict':gates['strict_scalar']['verdict']}
    return res,extra['bridge']

def main(home,out,threads=4,seeds=5):
    home=Path(home);out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=make()
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
    rep={'kind':'B3_L1_V3_NO_SHORT_EXACT_FORM','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'bridge_sha256':hashlib.sha256((Path(BB.__file__)).read_bytes()).hexdigest(),'h2_helpers_sha256':hashlib.sha256(Path(H2.__file__).read_bytes()).hexdigest(),
         'data_seed':SEED_DATA,'data_sha256':data_sha,'sender':b1.name,'receiver':b2.name,'n':N,'K':K,'r':R,'h':H_DIM,'seeds':seeds,'states_seconds':round(emb_s,1),
         'sender_dim':int(Hs.shape[2]),'max_tokens':int(Hs.shape[1]),'receiver_dim':int(d['recv_private'].shape[1]),
         'label_balance':{t:np.bincount(v).tolist() for t,v in ys.items()},'exact_bytes_mean':round(exact_bytes,1),
         'budget_b3_h7':BB.budget(int(Hs.shape[2]),K,R,H_DIM,3),
         'receiver_prefill_s_per_item':{'private':round(float(d['lat'][0]),5),'shared':round(float(d['lat'][1]),5),'exact_cue_span':round(float(d['lat'][2]),5)},
         'views':{},'claim_limit':'L1 receiver-adapter read only (no backbone injection); synthetic templates and labels; EXACT span oracle-selected; mean-pooled receiver state; Linux CPU cloud, not Redmi; LATENT authority stays 0'}
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
    (out/'report.json').write_text(json.dumps(rep,indent=1,default=float));print(json.dumps(rep['summary']))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 4,int(sys.argv[4]) if len(sys.argv)>4 else 5)
