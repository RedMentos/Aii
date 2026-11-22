"""B3-H3 L1 — receiver-adapter-only latent read (first latent experiment, cloud bench, no backbone injection).

Sender = B1 body (LFM2.5-1.2B) mean-pooled final state; receiver = B2 body (Qwen3.5-0.8B) mean-pooled final state.
A small receiver-side readout (logistic regression) predicts a detail label the receiver needs. Channels compared
(B3-H3 required comparisons and controls):
  NO_MESSAGE  receiver state only
  EXACT       receiver state + typed exact numbers from the source (SOURCE_EXACT channel as features)
  SYMBOLIC    receiver state + the receiver's own embedding of a short sender-side hypothesis string
  L1          receiver state + PCA-projected sender state (rank R), the B3 message z
  L1_SHUFFLED sender message shuffled across items (control)
  L1_RANDOM   random vector with the same norm per item (control)
Tasks (synthetic, labels by construction): sum_ok (is the stated total correct?), max_item (which of 3 items is most
expensive?), topic (gist control: which domain?). Fit / select / test partitions, 5 seeds; report test accuracy.
Usage: b3_l1_bench.py <home> <out.json> [threads]"""
import http.client
import json
import random
import socket
import subprocess
import sys
import time
from pathlib import Path
import numpy as np

N=480;R=16;SEEDS=10;PCA_RECEIVER=48
ITEMS=['rent','food','travel','books','repairs','insurance','phone','gym','gifts','tools']
DOMAINS={'home':['rent','repairs','insurance'],'leisure':['travel','gym','gifts'],'daily':['food','phone','books']}

def make(seed=13):
    rnd=random.Random(seed);rows=[]
    for i in range(N):
        dom=rnd.choice(list(DOMAINS));its=rnd.sample(DOMAINS[dom],3);vals=[rnd.randint(20,900) for _ in its]
        ok=rnd.random()<.5;total=sum(vals)+(0 if ok else rnd.choice([-1,1])*rnd.randint(10,120))
        text='This month: '+', '.join(f'{a} {v} euros' for a,v in zip(its,vals))+f'. Together that makes {total} euros.'
        hyp=f'largest item {its[int(np.argmax(vals))]}; stated total {total}'
        rows.append({'text':text,'sum_ok':int(ok),'max_item':int(np.argmax(vals)),'topic':list(DOMAINS).index(dom),'nums':vals+[total],'hyp':hyp})
    return rows

def embed(home,model,texts,threads):
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    p=subprocess.Popen([str(home/'bin/llama-server'),'-m',str(model),'--embedding','--pooling','mean','--port',str(port),'-c','512','-t',str(threads),'-b','512','-ub','512','--no-warmup','--no-webui'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        end=time.time()+120
        while time.time()<end:
            try:
                c=http.client.HTTPConnection('127.0.0.1',port,timeout=2);c.request('GET','/health');r=c.getresponse();r.read()
                if r.status==200:break
            except OSError:pass
            time.sleep(.3)
        out=[]
        for i in range(0,len(texts),16):
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=300)
            c.request('POST','/v1/embeddings',json.dumps({'input':texts[i:i+16]}),{'Content-Type':'application/json'})
            d=json.loads(c.getresponse().read());out+=[x['embedding'] for x in sorted(d['data'],key=lambda x:x['index'])]
        return np.asarray(out,dtype=np.float64)
    finally:p.terminate();p.wait(timeout=10)

def pca(train,k):
    mu=train.mean(0);u,s,vt=np.linalg.svd(train-mu,full_matrices=False);return mu,vt[:k]

def fit(X,y,k,l2=1e-2,steps=400,lr=.5):
    W=np.zeros((X.shape[1],k));b=np.zeros(k);Y=np.eye(k)[y]
    for _ in range(steps):
        z=X@W+b;z-=z.max(1,keepdims=True);p=np.exp(z);p/=p.sum(1,keepdims=True)
        g=(p-Y)/len(y);W-=lr*(X.T@g+l2*W);b-=lr*g.sum(0)
    return W,b

def acc(W,b,X,y):return float(((X@W+b).argmax(1)==y).mean())

def standardize(tr,*others):
    mu,sd=tr.mean(0),tr.std(0)+1e-6;return [(a-mu)/sd for a in (tr,)+others]

def run(rows,recv,send,hyp_recv):
    res={}
    for task in ('sum_ok','max_item','topic'):
        y=np.array([r[task] for r in rows]);k=int(y.max())+1;per={}
        for seed in range(SEEDS):
            rnd=np.random.default_rng(seed);idx=rnd.permutation(len(rows));tr,va,te=idx[:len(idx)*3//5],idx[len(idx)*3//5:len(idx)*4//5],idx[len(idx)*4//5:]
            mu,V=pca(recv[tr],PCA_RECEIVER);base=(recv-mu)@V.T
            smu,SV=pca(send[tr],R);z=(send-smu)@SV.T
            hmu,HV=pca(hyp_recv[tr],R);h=(hyp_recv-hmu)@HV.T
            nums=np.array([r['nums'] for r in rows],dtype=float);ex=np.c_[nums,nums[:,3]-nums[:,:3].sum(1),np.abs(nums[:,3]-nums[:,:3].sum(1))==0,np.argmax(nums[:,:3],1)[:,None]==np.arange(3)]
            shuf=z[rnd.permutation(len(z))];rand=rnd.normal(size=z.shape);rand*=np.linalg.norm(z,axis=1,keepdims=True)/np.linalg.norm(rand,axis=1,keepdims=True)
            feats={'NO_MESSAGE':base,'EXACT':np.c_[base,ex],'SYMBOLIC':np.c_[base,h],'L1':np.c_[base,z],'L1_SHUFFLED':np.c_[base,shuf],'L1_RANDOM':np.c_[base,rand]}
            for name,X in feats.items():
                Xtr,Xva,Xte=standardize(X[tr],X[va],X[te])
                best=max((acc(*fit(Xtr,y[tr],k,l2),Xva,y[va]),l2) for l2 in (1e-3,1e-2,1e-1,1.))[1]  # select l2 on the middle partition
                W,b=fit(Xtr,y[tr],k,best);per.setdefault(name,[]).append(acc(W,b,Xte,y[te]))
        d=np.array(per['L1'])-np.array(per['NO_MESSAGE']);ds=np.array(per['L1'])-np.array(per['L1_SHUFFLED'])
        res[task]={n:{'mean':round(float(np.mean(v)),3),'sd':round(float(np.std(v)),3)} for n,v in per.items()}|{'chance':round(float(np.bincount(y).max()/len(y)),3),
                   'paired_L1_minus_NO_MESSAGE':{'mean':round(float(d.mean()),3),'se':round(float(d.std(ddof=1)/np.sqrt(len(d))),3),'wins':int((d>0).sum()),'ties':int((d==0).sum()),'n':len(d)},
                   'paired_L1_minus_SHUFFLED':{'mean':round(float(ds.mean()),3),'se':round(float(ds.std(ddof=1)/np.sqrt(len(ds))),3),'wins':int((ds>0).sum()),'n':len(ds)}}
    return res

def main(home,out,threads=4):
    home=Path(home);rows=make();texts=[r['text'] for r in rows]
    b1=next((home/'models/body').glob('*.gguf'));b2=next((home/'models/gist').glob('*.gguf'))
    cache=Path(out).with_suffix('.npz') if len(sys.argv)<5 else Path(sys.argv[4]);t=time.time()
    if cache.exists():c=np.load(cache);send,recv,hyp=c['send'],c['recv'],c['hyp']
    else:
        send=embed(home,b1,texts,threads);recv=embed(home,b2,texts,threads);hyp=embed(home,b2,[r['hyp'] for r in rows],threads)
        np.savez_compressed(cache,send=send.astype(np.float32),recv=recv.astype(np.float32),hyp=hyp.astype(np.float32))
    send,recv,hyp=(a.astype(np.float64) for a in (send,recv,hyp));emb_s=time.time()-t
    rep={'kind':'B3_L1_RECEIVER_ADAPTER_READ','sender':b1.name,'receiver':b2.name,'n':N,'rank':R,'seeds':SEEDS,'embedding_seconds':round(emb_s,1),
         'sender_dim':int(send.shape[1]),'receiver_dim':int(recv.shape[1]),'results':run(rows,recv,send,hyp),
         'claim_limit':'Receiver-side readout only (L1); no backbone injection; synthetic labels; SYMBOLIC uses an oracle-built hypothesis string'}
    Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(rep,indent=1))
    print(json.dumps(rep['results'],indent=1))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 4)
