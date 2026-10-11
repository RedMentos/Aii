"""B3-H2/H7 + B3-H3 L1 retry: learned message subspace bridge vs NO_MESSAGE / EXACT / CONTROL / SYMBOLIC (cloud bench).

Sender = B1 body (LFM2.5-1.2B) per-token final states (llama-server --pooling none); receiver = B2 body (Qwen3.5-0.8B)
mean-pooled state of the receiver's own view. Bodies frozen (B3-H8). The bridge (v13/b3bridge.py) has K learned selector
slots over the sender tokens, a rank-r projector, BF16 transfer, receiver projector + calibration + gate, and adds a gated
residual to the receiver's frozen NO_MESSAGE readout.

Views
  shared  receiver sees the same text as the sender (the first L1 experiment)
  gist    receiver sees a gist view: item names and domain only; numbers, tone and hedging stay with the sender
Tasks (labels by construction)
  max_item, sum_ok   detail tasks with an exact counterpart (numbers)
  tone               worried / relieved / matter-of-fact closing sentence (no short exact counterpart)
  certainty          hedged vs. certain wording of the total (no short exact counterpart)
  topic              receiver role task (gist), used for role retention
Baselines (all with the same supervision and splits)
  NO_MESSAGE   receiver state only
  EXACT        oracle-selected source span re-read by the receiver (numbers for detail tasks, the tone/hedge sentence otherwise)
  CONTROL      sender head confidence + entropy (2 x fp16)
  SYMBOLIC     sender-side readout sends its predicted label word (bounded symbolic)
  LATENT       learned bridge z[K, r] in BF16; controls LATENT_SHUFFLED (messages permuted) and LATENT_RANDOM (same norm)
  L1_MEANPOOL  first experiment's message: mean-pooled sender state, PCA rank 16 (no learned selector)
Usage: b3_h2_bench.py <home> <out_dir> [threads] [seeds]"""
import http.client
import json
import random
import socket
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13 import b3bridge as BB

N=600;K=4;R=8;H_DIM=16;PCA_RECV=48
DOMAINS={'home':['rent','repairs','insurance'],'leisure':['travel','gym','gifts'],'daily':['food','phone','books']}
TONE={0:['Honestly this worries me a lot.','I am anxious about how this adds up.','This keeps me up at night.','I fear we cannot keep this pace.','That number scares me a bit.','I am nervous about next month.'],
      1:['What a relief, that went well.','I am glad it came out fine.','Good, that is a weight off my mind.','Nice, I feel much calmer now.','Great, we handled this nicely.','I am happy with how it turned out.'],
      2:['Noted for the records.','Filed with the other receipts.','Logged in the budget sheet.','Added to the monthly list.','Entered in the ledger.','Recorded as usual.']}
HEDGE={0:['Together that makes {t} euros.','The total is {t} euros.','That comes to exactly {t} euros.','In sum {t} euros.'],
       1:['I think together that makes maybe {t} euros.','Roughly {t} euros, if I counted right.','Probably around {t} euros in total, not sure.','It might come to {t} euros, I guess.']}
TONE_WORD=['worried','relieved','neutral'];CERT_WORD=['certain','hedged'];ITEM_WORD=['first','second','third'];OK_WORD=['wrong','right']

def make(seed=13):
    rnd=random.Random(seed);rows=[]
    for _ in range(N):
        dom=rnd.choice(list(DOMAINS));its=rnd.sample(DOMAINS[dom],3);vals=[rnd.randint(20,900) for _ in its]
        ok=rnd.random()<.5;total=sum(vals)+(0 if ok else rnd.choice([-1,1])*rnd.randint(10,120));tone=rnd.randrange(3);cert=rnd.randrange(2)
        tsent=rnd.choice(TONE[tone]);hsent=rnd.choice(HEDGE[cert]).format(t=total)
        text='This month: '+', '.join(f'{a} {v} euros' for a,v in zip(its,vals))+'. '+hsent+' '+tsent
        gist=f'A note about {dom} costs: '+', '.join(its)+'.'
        rows.append({'text':text,'gist':gist,'sum_ok':int(ok),'max_item':int(np.argmax(vals)),'tone':tone,'certainty':cert,'topic':list(DOMAINS).index(dom),
                     'nums':vals+[total],'num_span':' '.join(str(v) for v in vals+[total]),'tone_span':tsent,'hedge_span':hsent})
    return rows

class Server:
    def __init__(self,home,model,threads,pooling):
        with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
        self.p=subprocess.Popen([str(home/'bin/llama-server'),'-m',str(model),'--embedding','--pooling',pooling,'--port',str(self.port),'-c','2048','-t',str(threads),'-b','512','-ub','512','--no-warmup','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        end=time.time()+180
        while time.time()<end:
            try:
                c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=2);c.request('GET','/health');r=c.getresponse();r.read()
                if r.status==200:return
            except OSError:pass
            time.sleep(.3)
        raise RuntimeError('llama-server did not start')
    def post(self,path,body):
        c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=600);c.request('POST',path,json.dumps(body),{'Content-Type':'application/json'})
        r=c.getresponse();d=r.read()
        if r.status!=200:raise RuntimeError(d[:300])
        return json.loads(d)
    def close(self):self.p.terminate();self.p.wait(timeout=10)

def pooled(home,model,texts,threads):
    s=Server(home,model,threads,'mean');out=[];t=time.time()
    try:
        for i in range(0,len(texts),16):
            d=s.post('/v1/embeddings',{'input':texts[i:i+16]});out+=[x['embedding'] for x in sorted(d['data'],key=lambda x:x['index'])]
    finally:s.close()
    return np.asarray(out,dtype=np.float32),(time.time()-t)/len(texts)

def tokens(home,model,texts,threads):
    """Per-token final states via --pooling none (/embeddings returns one vector per token)."""
    s=Server(home,model,threads,'none');out=[]
    try:
        for i in range(0,len(texts),8):
            d=s.post('/embeddings',{'content':texts[i:i+8]})
            d=d if isinstance(d,list) else d.get('data',d)
            out+=[np.asarray(x['embedding'],dtype=np.float32) for x in sorted(d,key=lambda x:x['index'])]
    finally:s.close()
    T=max(len(x) for x in out);D=out[0].shape[1];H=np.zeros((len(out),T,D),np.float32);M=np.zeros((len(out),T),np.float32)
    for i,x in enumerate(out):H[i,:len(x)]=x;M[i,:len(x)]=1
    return H,M

def pca(tr,k):
    mu=tr.mean(0);_,_,vt=np.linalg.svd(tr-mu,full_matrices=False);return mu,vt[:k]

def std(tr,*o):
    mu,sd=tr.mean(0),tr.std(0)+1e-6;return [(a-mu)/sd for a in (tr,)+o]

def head(X,y,k,l2=1e-2,steps=400,lr=.5):
    W=np.zeros((X.shape[1],k));b=np.zeros(k);Y=np.eye(k)[y]
    for _ in range(steps):
        z=X@W+b;z-=z.max(1,keepdims=True);p=np.exp(z);p/=p.sum(1,keepdims=True);g=(p-Y)/len(y);W-=lr*(X.T@g+l2*W);b-=lr*g.sum(0)
    return W,b

def acc(W,b,X,y):return float(((X@W+b).argmax(1)==y).mean())

def sel_head(Xtr,ytr,Xva,yva,k):
    best=max((acc(*head(Xtr,ytr,k,l2),Xva,yva),l2) for l2 in (1e-3,1e-2,1e-1,1.))[1];return head(Xtr,ytr,k,best)

def probs(W,b,X):
    z=X@W+b;z-=z.max(1,keepdims=True);p=np.exp(z);return p/p.sum(1,keepdims=True)

def run_task(task,rows,recv,send_pool,Hs,Ms,exact_feat,exact_bytes,seeds,lat):
    y=np.array([r[task] for r in rows]);k=int(y.max())+1;words={'max_item':ITEM_WORD,'sum_ok':OK_WORD,'tone':TONE_WORD,'certainty':CERT_WORD}[task]
    per={};extra={'ood_rate':[],'role_drop':[],'reload_identical':[],'diversity':[],'train':[]};topic=np.array([r['topic'] for r in rows])
    for seed in range(seeds):
        g=np.random.default_rng(seed);idx=g.permutation(len(rows));n=len(idx);tr,va,te=idx[:n*3//5],idx[n*3//5:n*4//5],idx[n*4//5:]
        mu,V=pca(recv[tr],PCA_RECV);Xr=(recv-mu)@V.T;Xr_tr,Xr_va,Xr_te=std(Xr[tr],Xr[va],Xr[te]);Xr_all=std(Xr[tr],Xr)[1]
        Wn,bn=sel_head(Xr_tr,y[tr],Xr_va,y[va],k);per.setdefault('NO_MESSAGE',[]).append(acc(Wn,bn,Xr_te,y[te]))
        # sender-side readout (bounded SYMBOLIC label word, CONTROL confidence)
        smu,SV=pca(send_pool[tr],PCA_RECV);Xs=(send_pool-smu)@SV.T;Xs_tr,Xs_va,Xs_all=std(Xs[tr],Xs[va],Xs);Ws,bs=sel_head(Xs_tr,y[tr],Xs_va,y[va],k)
        P=probs(Ws,bs,Xs_all);sym=np.eye(k)[P.argmax(1)];ent=-(P*np.log(P+1e-12)).sum(1);ctl=np.c_[P.max(1),ent].astype(np.float16).astype(float)
        ex=exact_feat
        for name,F in (('EXACT',ex),('SYMBOLIC',sym),('CONTROL',ctl)):
            X=np.c_[Xr_all,F];a,bb,c=std(X[tr],X[va],X[te]);W,b=sel_head(a,y[tr],bb,y[va],k);per.setdefault(name,[]).append(acc(W,b,c,y[te]))
        z=(send_pool-smu)@SV[:16].T;X=np.c_[Xr_all,BB.to_bf16(z)];a,bb,c=std(X[tr],X[va],X[te]);W,b=sel_head(a,y[tr],bb,y[va],k);per.setdefault('L1_MEANPOOL',[]).append(acc(W,b,c,y[te]))
        # learned bridge (B3-H2): fit on tr, select epochs on va, test on te
        br=BB.Bridge(Hs.shape[2],K=K,r=R,h=H_DIM,classes=k,seed=seed,direction='B1_TO_B2');br.head=(Wn,bn)
        best=None
        for ep_block in range(6):
            br.fit(Hs[tr],Ms[tr],Xr_tr,y[tr],epochs=10,batch=64,lr=3e-3,seed=seed*100+ep_block) if ep_block==0 else _cont(br,Hs[tr],Ms[tr],Xr_tr,y[tr],seed*100+ep_block)
            va_acc=float((br.logits(Hs[va],Ms[va],Xr_va).argmax(1)==y[va]).mean())
            if best is None or va_acc>best[0]:best=(va_acc,{kk:v.copy() for kk,v in br.p.items()},br.in_mu.copy(),br.in_sd.copy(),(ep_block+1)*10)
        br.p,br.in_mu,br.in_sd=best[1],best[2],best[3];extra['train'].append({'epochs':best[4],'val_acc':round(best[0],4),'last':br.manifest['train']['last']})
        br.calibrate(Hs[tr],Ms[tr])
        t0=time.perf_counter();L=br.logits(Hs[te],Ms[te],Xr_te);lat.append((time.perf_counter()-t0)/len(te))
        per.setdefault('LATENT',[]).append(float((L.argmax(1)==y[te]).mean()))
        Z=BB.to_bf16(br.encode(Hs[te],Ms[te]))
        per.setdefault('LATENT_SHUFFLED',[]).append(float((br.receive(Z[g.permutation(len(Z))],Xr_te).argmax(1)==y[te]).mean()))
        rz=g.normal(size=Z.shape);rz*=np.linalg.norm(Z.reshape(len(Z),-1),axis=1)[:,None,None]/np.linalg.norm(rz.reshape(len(rz),-1),axis=1)[:,None,None]
        br_nocal=br.cal;br.cal=None;per.setdefault('LATENT_RANDOM',[]).append(float((br.receive(rz,Xr_te).argmax(1)==y[te]).mean()));br.cal=br_nocal
        extra['ood_rate'].append(float((br.ood(Z)>br.cal['ood_tau']).mean()))
        # role retention: receiver topic readout from its state vs. its message-conditioned state
        U=lambda idx_:br.gate()*(BB.to_bf16(br.encode(Hs[idx_],Ms[idx_])).reshape(len(idx_),-1)@br.p['Pr'])
        Wt,bt=sel_head(Xr_tr,topic[tr],Xr_va,topic[va],3);a0=acc(Wt,bt,Xr_te,topic[te])
        Ctr,Cva,Cte=std(np.c_[Xr_tr,U(tr)],np.c_[Xr_va,U(va)],np.c_[Xr_te,U(te)]);Wc,bc=sel_head(Ctr,topic[tr],Cva,topic[va],3)
        extra['role_drop'].append(a0-acc(Wc,bc,Cte,topic[te]))
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            br.save(Path(t)/'x','s','r');b2=BB.Bridge.load(Path(t)/'x','s','r');extra['reload_identical'].append(bool(np.array_equal(b2.logits(Hs[te],Ms[te],Xr_te),L)))
        if seed==0:
            extra['diversity'].append(BB.diversity_report(br,Hs[te],Ms[te],send_pool[te],recv[te],Xr_te))
            extra['bridge']=br
    bytes_={'NO_MESSAGE':0,'EXACT':exact_bytes,'SYMBOLIC':float(np.mean([len(w) for w in words])),'CONTROL':4,'LATENT':K*R*2,'L1_MEANPOOL':32}
    acc_={c:v for c,v in per.items() if c!='L1_MEANPOOL'}
    gate=BB.l1_gate({'acc':acc_,'bytes':bytes_,'role_drop':float(np.mean(extra['role_drop'])),'ood_rate':float(np.mean(extra['ood_rate'])),'reload_identical':all(extra['reload_identical'])})
    res={'chance':round(float(np.bincount(y).max()/len(y)),3),'acc':{c:{'mean':round(float(np.mean(v)),4),'sd':round(float(np.std(v)),4)} for c,v in per.items()},'bytes':bytes_,
         'paired_LATENT_minus_NO_MESSAGE':BB.paired(per['LATENT'],per['NO_MESSAGE']),'paired_LATENT_minus_L1_MEANPOOL':BB.paired(per['LATENT'],per['L1_MEANPOOL']),
         'role_drop':round(float(np.mean(extra['role_drop'])),4),'ood_rate':round(float(np.mean(extra['ood_rate'])),4),'reload_identical':all(extra['reload_identical']),
         'diversity_seed0':extra['diversity'][0],'train':extra['train'],'l1_gate':gate}
    return res,extra['bridge']

def _cont(br,H,M,X,y,seed):
    """Continue training (keeps Adam-free warm weights; a fresh optimizer per 10-epoch block)."""
    mu,sd=br.in_mu.copy(),br.in_sd.copy();br.fit(H,M,X,y,epochs=10,batch=64,lr=3e-3,seed=seed);br.in_mu,br.in_sd=mu,sd

def main(home,out,threads=4,seeds=5):
    home=Path(home);out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=make()
    b1=next((home/'models/body').glob('*.gguf'));b2=next((home/'models/gist').glob('*.gguf'));cache=out/'states.npz';t=time.time()
    if cache.exists():
        c=np.load(cache);d={k:c[k] for k in c.files}
    else:
        Hs,Ms=tokens(home,b1,[r['text'] for r in rows],threads)
        sp,_=pooled(home,b1,[r['text'] for r in rows],threads)
        rs,lat_full=pooled(home,b2,[r['text'] for r in rows],threads);rg,lat_gist=pooled(home,b2,[r['gist'] for r in rows],threads)
        spans={k:pooled(home,b2,[r[k] for r in rows],threads) for k in ('tone_span','hedge_span')}
        d={'Hs':Hs.astype(np.float16),'Ms':Ms,'send_pool':sp,'recv_shared':rs,'recv_gist':rg,'tone_span':spans['tone_span'][0],'hedge_span':spans['hedge_span'][0],
           'lat':np.array([lat_full,lat_gist,spans['tone_span'][1],spans['hedge_span'][1]])}
        np.savez_compressed(cache,**d)
    Hs=d['Hs'].astype(np.float32);Ms=d['Ms'];emb_s=time.time()-t
    nums=np.array([r['nums'] for r in rows],dtype=float);ex_num=np.c_[nums,nums[:,3]-nums[:,:3].sum(1),np.abs(nums[:,3]-nums[:,:3].sum(1))==0,np.argmax(nums[:,:3],1)[:,None]==np.arange(3)]
    num_bytes=float(np.mean([len(r['num_span']) for r in rows]))
    def spanpca(S):
        mu,V=pca(S,R*2);return (S-mu)@V.T
    exact={'max_item':(ex_num,num_bytes),'sum_ok':(ex_num,num_bytes),'tone':(spanpca(d['tone_span']),float(np.mean([len(r['tone_span']) for r in rows]))),
           'certainty':(spanpca(d['hedge_span']),float(np.mean([len(r['hedge_span']) for r in rows])))}
    rep={'kind':'B3_H2_LEARNED_SELECTOR_L1','sender':b1.name,'receiver':b2.name,'n':N,'K':K,'r':R,'h':H_DIM,'seeds':seeds,'states_seconds':round(emb_s,1),
         'sender_dim':int(Hs.shape[2]),'max_tokens':int(Hs.shape[1]),'receiver_dim':int(d['recv_shared'].shape[1]),
         'budget_b3_h7':BB.budget(int(Hs.shape[2]),K,R,H_DIM,3),'receiver_prefill_s_per_item':{'full_text':round(float(d['lat'][0]),5),'gist':round(float(d['lat'][1]),5),'tone_span':round(float(d['lat'][2]),5),'hedge_span':round(float(d['lat'][3]),5)},
         'views':{},'claim_limit':'L1 receiver-adapter read only (no backbone injection); synthetic labels; EXACT spans oracle-selected; mean-pooled receiver state; CPU cloud, not Redmi'}
    lat=[];saved=False
    for view,recv in (('shared',d['recv_shared']),('gist',d['recv_gist'])):
        rep['views'][view]={}
        for task in ('max_item','sum_ok','tone','certainty'):
            ef,eb=exact[task];r_,br=run_task(task,rows,recv.astype(np.float64),d['send_pool'].astype(np.float64),Hs,Ms,ef,eb,seeds,lat)
            rep['views'][view][task]=r_;print(view,task,json.dumps({c:v['mean'] for c,v in r_['acc'].items()}),r_['l1_gate']['verdict'],flush=True)
            if view=='gist' and task=='tone':br.save(out/'bridge_gist_tone_B1_TO_B2','bench:'+b1.name,'bench:'+b2.name,{'l1_gate':r_['l1_gate'],'task':'gist/tone'});saved=True
    rep['bridge_latency_us_per_item']=round(1e6*float(np.mean(lat)),1)
    passes=[f'{v}/{t}' for v,ts in rep['views'].items() for t,x in ts.items() if x['l1_gate']['verdict']=='PASS']
    rep['summary']={'l1_pass':passes,'verdict':'PASS on '+', '.join(passes) if passes else 'FAIL on all tasks','saved_example_bridge':saved}
    (out/'report.json').write_text(json.dumps(rep,indent=1,default=float));print(json.dumps(rep['summary']))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 4,int(sys.argv[4]) if len(sys.argv)>4 else 5)
