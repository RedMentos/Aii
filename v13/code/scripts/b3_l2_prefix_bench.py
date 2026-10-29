"""WP-Z4b B3 L2 prefix SHADOW for private/action only (cloud bench, preregistered).

B3 L1 attempt 4 (bench-results/b3-l1-v4-20261021) passed the canon L1 gate only on private/action. Per B3-H8 step 7 the
next allowed experiment is the L2 prefix SHADOW test (blueprint "L2 - Calibrated continuous input-prefix conditioning"):

  selected sender states -> frozen attempt-4 aux bridge (same seeds and splits) -> message z[K=4, r=8] (BF16, 64 B)
  -> alignment into the receiver's native input-embedding space -> receiver distribution calibration
  -> K=4 continuous prefix slots -> receiver native input path (llama.cpp batch.embd, Qwen3.5-0.8B Q4_0, frozen)
  -> receiver final per-token states, mean over the receiver's OWN private-view tokens (prefix positions excluded)
  -> the same readout as NO_MESSAGE in L1 (PCA 48 of the pooled state, standardized, softmax head, l2 on select split).

The message never reaches the readout directly: any gain must pass through the frozen receiver backbone.

Alignment variants (both preregistered; PCA_ALIGN decides the verdict, EXACT_ALIGN is reported as exploratory)
  PCA_ALIGN    geometry-preserving: per-slot standardized message dims -> the top r principal directions of the native
               input-token embeddings (scaled by their native spread), no task labels.
  EXACT_ALIGN  low-rank ridge from the flat message (32 dims) to the receiver's own token-embedding mean of each of the
               4 cue sentences (what the receiver would read natively), no task labels.
  Calibration (both): prefix = native mean + c * deviation, c sets the mean deviation norm on the fit split equal to the
  native token deviation norm (B3-H4 packet: norm ratio, mean shift, variance ratio, geometry error).

Controls/baselines (required by the blueprint): PREFIX_OFF (= NO_MESSAGE), PREFIX_SHUFFLED (another test item's prefix),
PREFIX_RANDOM (Gaussian with native per-dim spread, deviation norm matched per item and slot), and the native text
baselines read through the same input path and readout: EXACT (oracle cue span), SYMBOLIC (sender-predicted label word),
SYMBOLIC_ATTR (sender-predicted urgency/frustration level words). Text baselines enter as their own token embeddings in
the prefix slot position, so every channel is pooled over the same private-view tokens.

Gate: v13/b3bridge.l2_gate (beats prefix off/shuffled/random, utility beats EXACT/SYMBOLIC/SYMBOLIC_ATTR, role retention
drop <= 0.01, norm ratio in [0.8, 1.25], bit-identical rerun). PASS only allows an L3 tiny-residual SHADOW test.

Usage: b3_l2_prefix_bench.py <work_dir> <states.npz> <model.gguf> <runner_binary> <backend_dir> <out_dir> [threads] [seeds]
Claim limits: synthetic templates (the ones used to design the aux fix); single task; frozen bodies; Linux CPU cloud, not
Redmi; LATENT authority 0; runtime unchanged."""
import hashlib
import json
import re
import struct
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import b3_h2_bench as H2
import b3_l1_v3_bench as V3
import b3_l1_v4_bench as V4
from v13 import b3bridge as BB

TASK='action';K=V4.K;R=V4.R;PCA_RECV=H2.PCA_RECV;VARIANTS=('PCA_ALIGN','EXACT_ALIGN');PRIMARY='PCA_ALIGN'
SYM_TEXT='Suggested action: {}.';ATTR_TEXT='Urgency {}, frustration {}.';RIDGE_L2=(1e-2,1e-1,1.,10.,100.)

class Runner:
    """b3_prefix_embd wrapper: prefix vectors + text -> L2-normalized mean final state over the text tokens."""
    def __init__(self,binary,model,backend_dir,work,threads):
        self.bin,self.model,self.work,self.threads=str(binary),str(model),Path(work),threads;self.env={'GGML_BACKEND_DIR':str(backend_dir)};self.calls=0
    def _env(self):
        import os;e=dict(os.environ);e.update(self.env);return e
    def tokenize(self,texts):
        u=sorted(set(texts));inp=''.join(t.replace('\n','\\n')+'\n' for t in u)
        out=subprocess.run([self.bin,self.model,'--tokenize'],input=inp,capture_output=True,text=True,check=True,env=self._env()).stdout.splitlines()
        m={t:[int(x) for x in o.split()] for t,o in zip(u,out)};return [m[t] for t in texts]
    def run(self,items):
        self.calls+=1;j=self.work/f'job{self.calls}.bin';o=self.work/f'out{self.calls}.bin';d=1024
        with open(j,'wb') as f:
            f.write(struct.pack('<II',len(items),d))
            for pre,t in items:
                pre=np.asarray(pre,np.float32).reshape(-1,d);b=t.encode()
                f.write(struct.pack('<I',len(pre)));f.write(pre.tobytes());f.write(struct.pack('<I',len(b)));f.write(b)
        subprocess.run([self.bin,self.model,str(j),str(o),str(self.threads)],check=True,env=self._env(),stderr=subprocess.DEVNULL)
        a=o.read_bytes();n,dd=struct.unpack('<II',a[:8]);X=np.frombuffer(a[8:],dtype=np.uint8).reshape(n,4+4*dd)
        X=X[:,4:].copy().view(np.float32);j.unlink();o.unlink()
        return X/np.linalg.norm(X,axis=1,keepdims=True)

def token_embd(model):
    import gguf
    t=next(x for x in gguf.GGUFReader(str(model)).tensors if x.name=='token_embd.weight')
    return gguf.quants.dequantize(t.data,t.tensor_type).astype(np.float32)

def native_stats(E,tok_lists):
    """Receiver native input statistics from the token embeddings of the fit-split receiver inputs."""
    T=E[np.concatenate(tok_lists)];mu=T.mean(0);D=T-mu;C=D.T@D/len(D);w,V=np.linalg.eigh(C);o=np.argsort(w)[::-1]
    return {'mu':mu,'U':V[:,o[:R]].T,'sig':np.sqrt(np.maximum(w[o[:R]],0)),'dev_norm':float(np.linalg.norm(D,axis=1).mean()),
            'norm_mean':float(np.linalg.norm(T,axis=1).mean()),'norm_std':float(np.linalg.norm(T,axis=1).std()),'dim_std':D.std(0),
            'dim_var_mean':float(D.var(0).mean()),'n_tokens':len(T),'top_r_var_share':float(w[o[:R]].sum()/w.sum())}

def calibrate(P,ns,tr):
    """Re-centre on the native mean and scale so the fit-split mean deviation norm matches the native token deviation
    norm (B3-H4: mean shift 0, norm ratio ~1)."""
    D=P-P[tr].mean(0);c=ns['dev_norm']/float(np.linalg.norm(D[tr],axis=2).mean());return ns['mu']+c*D,c

def packet(P,ns,tr,geom):
    n=np.linalg.norm(P[tr],axis=2);D=P[tr].reshape(-1,P.shape[2])-ns['mu']
    return {'native_norm_mean':round(ns['norm_mean'],5),'native_norm_std':round(ns['norm_std'],5),'message_norm':round(float(n.mean()),5),
            'norm_ratio':round(float(n.mean()/ns['norm_mean']),4),'mean_shift':round(float(np.linalg.norm(D.mean(0))/ns['dev_norm']),4),
            'variance_ratio':round(float(D.var(0).mean()/ns['dim_var_mean']),4),'geometry_error':geom,'injection_level':'L2','target_tap_id':'qwen35.inp_embd.prefix.v1',
            'native_tokens':ns['n_tokens'],'top_r_native_var_share':round(ns['top_r_var_share'],4)}

def pca_align(Z,ns,tr):
    m,s=Z[tr].mean(0),Z[tr].std(0)+1e-6;Zh=(Z-m)/s;P,c=calibrate(ns['mu']+Zh@(ns['sig'][:,None]*ns['U']),ns,tr)
    # geometry error: relative distortion of pairwise slot distances (orthonormal map + per-dim scale -> only the scale)
    A=Zh[tr].reshape(-1,R)[:200];B=(P[tr]-ns['mu']).reshape(-1,P.shape[2])[:200]@ns['U'].T/ns['sig']
    da=np.linalg.norm(A[:,None]-A[None],axis=2);db=np.linalg.norm(B[:,None]-B[None],axis=2)/c
    return P,{'scale':round(c,4),'geometry_error':round(float(np.abs(da-db).mean()/da.mean()),6)}

def exact_align(Z,Y,tr,va):
    """Ridge from the flat standardized message to the 4 cue-sentence embedding means (fit split; l2 by select MSE)."""
    X=Z.reshape(len(Z),-1);m,s=X[tr].mean(0),X[tr].std(0)+1e-6;X=(X-m)/s;Yf=Y.reshape(len(Y),-1);yb=Yf[tr].mean(0)
    best=None
    for l2 in RIDGE_L2:
        W=np.linalg.solve(X[tr].T@X[tr]+l2*np.eye(X.shape[1]),X[tr].T@(Yf[tr]-yb));e=float(((X[va]@W+yb-Yf[va])**2).mean())
        if best is None or e<best[0]:best=(e,l2,W)
    P=(X@best[2]+yb).reshape(Y.shape);r2=1-best[0]/float(((Yf[va]-yb)**2).mean())
    return P,{'ridge_l2':best[1],'select_r2':round(r2,4)}

def readout(S,y,tr,va,te,k):
    """L1 NO_MESSAGE readout: PCA 48 on the fit split, standardized, softmax head (l2 chosen on select)."""
    mu,V=H2.pca(S[tr],PCA_RECV);X=(S-mu)@V.T;m,s=X[tr].mean(0),X[tr].std(0)+1e-6;f=lambda A:((A-mu)@V.T-m)/s
    W,b=H2.sel_head(f(S[tr]),y[tr],f(S[va]),y[va],k);return (lambda A:f(A)@W+b)

def readout_full(S,y,tr,va,te,k):
    """Exploratory (not gate): all 1024 standardized dims."""
    m,s=S[tr].mean(0),S[tr].std(0)+1e-6;f=lambda A:(A-m)/s;W,b=H2.sel_head(f(S[tr]),y[tr],f(S[va]),y[va],k);return (lambda A:f(A)@W+b)

def acc_of(fn,S,y):return float((fn(S).argmax(1)==y).mean())

def sentences(cue):
    p=re.split(r' (?=About )',cue);assert len(p)==4,cue;return p

def main(work,states,model,binary,backend_dir,out,threads=4,seeds=5):
    work=Path(work);out=Path(out);work.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True);t0=time.time()
    rows=V3.make(V4.SEED_DATA);c=np.load(states);d={k:c[k] for k in c.files};Hs=d['Hs'].astype(np.float32);Ms=d['Ms']
    recv=d['recv_private'].astype(np.float64);send_pool=d['send_pool'].astype(np.float64)
    y=np.array([r[TASK] for r in rows]);k=int(y.max())+1;topic=np.array([r['topic'] for r in rows]);n=len(rows)
    U=np.array([r['U'] for r in rows],float);F=np.array([r['F'] for r in rows],float);T=np.c_[U,F]
    run=Runner(binary,model,backend_dir,work,threads);E=token_embd(model)
    priv=[r['private'] for r in rows];tok_shared=run.tokenize([r['shared'] for r in rows])
    sent=[sentences(r['cue_span']) for r in rows];tok_sent=run.tokenize([s for ss in sent for s in ss])
    Ysent=np.array([E[t].mean(0) for t in tok_sent]).reshape(n,4,-1)
    tok_cue=run.tokenize([r['cue_span'] for r in rows])
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    rep={'kind':'B3_L2_PREFIX_SHADOW_PRIVATE_ACTION','task':f'private/{TASK}','script_sha256':sha(__file__),'bridge_sha256':sha(BB.__file__),
         'v4_sha256':sha(V4.__file__),'runner_source_sha256':sha(Path(__file__).parent/'native/b3_prefix_embd.cpp'),'runner_binary_sha256':sha(binary),
         'receiver_sha256':sha(model),'states_sha256':sha(states),'data_seed':V4.SEED_DATA,'n':n,'K':K,'r':R,'seeds':seeds,'primary_variant':PRIMARY,
         'claim_limit':'L2 prefix SHADOW on one synthetic task (private/action); frozen B1/B2; Linux CPU cloud, not Redmi; LATENT authority 0; runtime unchanged'}
    # seed-independent channels: prefix off (runner check vs the L1 cache) and the oracle EXACT span
    S_off=run.run([(np.zeros((0,1024)),t) for t in priv]);rep['runner_check_prefix_off_vs_l1_cache_max_rel_l2']=float(np.max(np.linalg.norm(S_off-recv/np.linalg.norm(recv,axis=1,keepdims=True),axis=1)))
    S_exact=run.run([(E[tc],t) for tc,t in zip(tok_cue,priv)])
    bytes_={'PREFIX':K*R*2,'PREFIX_OFF':0,'PREFIX_SHUFFLED':K*R*2,'PREFIX_RANDOM':K*R*2,'EXACT':float(np.mean([len(r['cue_span'].encode()) for r in rows])),
            'SYMBOLIC':float(np.mean([len(w) for w in V3.ACTION_WORD])),'SYMBOLIC_ATTR':float(np.mean([len(f'urgency {a}, frustration {b}') for a in V3.LEVEL for b in V3.LEVEL]))}
    per={v:{} for v in VARIANTS};expl={v:{} for v in VARIANTS};extra={v:{'role_drop':[],'role_off_head_on_prefix':[],'drift_cos':[],'packet':[],'align':[]} for v in VARIANTS}
    base={};l1=[];l1_ref=json.loads((Path(__file__).resolve().parents[2]/'bench-results/b3-l1-v4-20261021/report.json').read_text())['views']['private'][TASK]['acc']['LATENT']['per_seed']
    reproducible=None;digest0=None
    for seed in range(seeds):
        g=np.random.default_rng(seed);idx=g.permutation(n);tr,va,te=idx[:n*3//5],idx[n*3//5:n*4//5],idx[n*4//5:]
        # attempt-4 L1 pipeline, unchanged (receiver PCA head = frozen NO_MESSAGE head; aux bridge, same seeds)
        mu,V=H2.pca(recv[tr],PCA_RECV);Xr=(recv-mu)@V.T;Xr_tr,Xr_va,Xr_te=H2.std(Xr[tr],Xr[va],Xr[te])
        Wn,bn=H2.sel_head(Xr_tr,y[tr],Xr_va,y[va],k);A=(T-T[tr].mean(0))/T[tr].std(0)
        br,_=V4.train_bridge(Hs,Ms,Xr_tr,Xr_va,y,tr,va,k,(Wn,bn),seed,aux=A)
        l1.append(float((br.logits(Hs[te],Ms[te],Xr_te).argmax(1)==y[te]).mean()))
        if seed==0:digest0=br.digest()
        Z=BB.to_bf16(br.encode(Hs,Ms))
        # sender-side symbolic baselines exactly as attempt 4, sent as text through the receiver input path
        smu,SV=H2.pca(send_pool[tr],PCA_RECV);Xs=(send_pool-smu)@SV.T;Xs_tr,Xs_va,Xs_all=H2.std(Xs[tr],Xs[va],Xs)
        Ws,bs=H2.sel_head(Xs_tr,y[tr],Xs_va,y[va],k);sym=H2.probs(Ws,bs,Xs_all).argmax(1);lv=[]
        for v in (U,F):
            l_=V3.tertile(v,tr);Wa,ba=H2.sel_head(Xs_tr,l_[tr],Xs_va,l_[va],3);lv.append(H2.probs(Wa,ba,Xs_all).argmax(1))
        sym_t=[SYM_TEXT.format(V3.ACTION_WORD[i]) for i in sym];att_t=[ATTR_TEXT.format(V3.LEVEL[a],V3.LEVEL[b]) for a,b in zip(*lv)]
        ts,ta=run.tokenize(sym_t),run.tokenize(att_t)
        S_sym=run.run([(E[t],p) for t,p in zip(ts,priv)]);S_att=run.run([(E[t],p) for t,p in zip(ta,priv)])
        for name,S in (('PREFIX_OFF',S_off),('EXACT',S_exact),('SYMBOLIC',S_sym),('SYMBOLIC_ATTR',S_att)):
            base.setdefault(name,[]).append(acc_of(readout(S,y,tr,va,te,k),S[te],y[te]))
            base.setdefault(name+'__full',[]).append(acc_of(readout_full(S,y,tr,va,te,k),S[te],y[te]))
        ns=native_stats(E,[tok_shared[i] for i in tr])
        fo=readout(S_off,topic,tr,va,te,3);a_off=acc_of(fo,S_off[te],topic[te])
        for var in VARIANTS:
            if var=='PCA_ALIGN':P,al=pca_align(Z,ns,tr);geom=al['geometry_error']
            else:
                P0,al=exact_align(Z,Ysent,tr,va);P,cc=calibrate(P0,ns,tr);al['scale']=round(cc,4);geom=round(1-al['select_r2'],4)
            S=run.run([(P[i],priv[i]) for i in range(n)]);f=readout(S,y,tr,va,te,k)
            per[var].setdefault('PREFIX',[]).append(acc_of(f,S[te],y[te]))
            perm=g.permutation(len(te));S_sh=run.run([(P[te][perm][i],priv[j]) for i,j in enumerate(te)])
            per[var].setdefault('PREFIX_SHUFFLED',[]).append(acc_of(f,S_sh,y[te]))
            Dv=P[te]-ns['mu'];rz=g.normal(size=Dv.shape)*ns['dim_std'];rz*=np.linalg.norm(Dv,axis=2,keepdims=True)/np.linalg.norm(rz,axis=2,keepdims=True)
            S_rd=run.run([(ns['mu']+rz[i],priv[j]) for i,j in enumerate(te)])
            per[var].setdefault('PREFIX_RANDOM',[]).append(acc_of(f,S_rd,y[te]))
            expl[var].setdefault('PREFIX__full',[]).append(acc_of(readout_full(S,y,tr,va,te,k),S[te],y[te]))
            ft=readout(S,topic,tr,va,te,3);extra[var]['role_drop'].append(a_off-acc_of(ft,S[te],topic[te]))
            extra[var]['role_off_head_on_prefix'].append(acc_of(fo,S[te],topic[te]))
            extra[var]['drift_cos'].append(float(np.mean(np.sum(S[te]*S_off[te],1))))
            extra[var]['packet'].append(packet(P,ns,tr,geom));extra[var]['align'].append(al)
            if seed==0 and var==PRIMARY:
                again=run.run([(P[i],priv[i]) for i in te[:8]]);reproducible=bool(np.array_equal(again,S[te[:8]]))
            print(seed,var,{c_:round(v_[-1],3) for c_,v_ in per[var].items()},flush=True)
        print(seed,'base',{c_:round(v_[-1],3) for c_,v_ in base.items()},'L1',round(l1[-1],3),flush=True)
    man=json.loads((Path(__file__).resolve().parents[2]/'bench-results/b3-l1-v4-20261021/bridge_private_action_B1_TO_B2.json').read_text())
    rep['l1_reproduction']={'per_seed':[round(x,4) for x in l1],'attempt4_per_seed':l1_ref,'identical':[round(x,4) for x in l1]==l1_ref,
                            'seed0_bridge_digest':digest0,'artifact_sha256':man.get('sha256'),'artifact_match':digest0==man.get('sha256')}
    st=lambda v:{'mean':round(float(np.mean(v)),4),'sd':round(float(np.std(v)),4),'per_seed':[round(x,4) for x in v]}
    rep['baselines']={c_:st(v_) for c_,v_ in base.items()};rep['L1_adapter_read']=st(l1);rep['bytes']=bytes_;rep['variants']={}
    for var in VARIANTS:
        acc={**{c_:v_ for c_,v_ in per[var].items()},**{c_:base[c_] for c_ in ('PREFIX_OFF','EXACT','SYMBOLIC','SYMBOLIC_ATTR')}}
        nr=float(np.mean([p['norm_ratio'] for p in extra[var]['packet']]))
        gate=BB.l2_gate({'acc':acc,'bytes':bytes_,'role_drop':float(np.mean(extra[var]['role_drop'])),'norm_ratio':round(nr,4),'reproducible':bool(reproducible)})
        rep['variants'][var]={'acc':{c_:st(v_) for c_,v_ in acc.items()},'exploratory_full_readout':{c_:st(v_) for c_,v_ in expl[var].items()},
            'paired_PREFIX_minus_PREFIX_OFF':BB.paired(acc['PREFIX'],acc['PREFIX_OFF']),'paired_PREFIX_minus_L1':BB.paired(acc['PREFIX'],l1),
            'role_drop':round(float(np.mean(extra[var]['role_drop'])),4),'role_drop_per_seed':[round(x,4) for x in extra[var]['role_drop']],
            'topic_acc_prefix_off_head_on_prefixed_states':st(extra[var]['role_off_head_on_prefix']),'drift_cos_prefixed_vs_off':st(extra[var]['drift_cos']),
            'calibration_packet_per_seed':extra[var]['packet'],'alignment_per_seed':extra[var]['align'],'l2_gate':gate,'verdict':gate['verdict']}
        print(var,json.dumps({c_:round(float(np.mean(v_)),4) for c_,v_ in acc.items()}),'gate',gate['verdict'],flush=True)
    rep['reproducible_rerun_8_items']=reproducible
    pv=rep['variants'][PRIMARY]['verdict'];ev=rep['variants']['EXACT_ALIGN']['verdict']
    rep['summary']={'verdict':f'L2 {pv} on private/{TASK} (primary {PRIMARY})','exploratory_EXACT_ALIGN':ev,
                    'consequence':'L3 tiny-residual SHADOW test allowed for private/action; LATENT authority stays 0; runtime unchanged' if pv=='PASS'
                    else 'B3_LATENT stays at L1_shadow for private/action; L3 locked'+('; EXACT_ALIGN passed exploratorily -> confirmatory rerun on fresh data needed' if ev=='PASS' else '')}
    rep['seconds']=round(time.time()-t0,1);rep['runner_calls']=run.calls
    (out/'report.json').write_text(json.dumps(rep,indent=1,default=float));print(json.dumps(rep['summary']))

if __name__=='__main__':
    a=sys.argv[1:];main(*a[:6],int(a[6]) if len(a)>6 else 4,int(a[7]) if len(a)>7 else 5)
