"""WP-J / B3-H2 + B3-H7 + B3-H8 + B3-H3 L1: learned message subspace and small mobile bridge (numpy only).

B3-H2   Only a small exported message space z[K, r] is aligned, never the private body states:
          sender tokens H[T, d] (frozen body) -> selector (K learned queries, attention over tokens)
          -> shared projector P[d, r] -> z[K, r]  ==> receiver projector Pr[K*r, h] + calibration + gate
          -> additive residual on the receiver's frozen NO_MESSAGE readout.
        Anti-collapse: per-dimension variance hinge + decorrelation on z (VICReg-style) and a slot-overlap
        penalty so the K selector slots read different tokens. Diversity checks: role retention, private-state
        similarity (linear CKA; bodies are frozen, so it can only change through z), fine-vs-gist, old-task
        behaviour (gate closed => logits identical to NO_MESSAGE), message utility.
B3-H7   Bridge stays tiny: parameters and BF16 bytes are reported (`budget`); messages are sent as BF16
        (`to_bf16`), K*r*2 bytes. Age 0: weights + buffers in the KB-to-low-MB class (AGE0_MAX_BYTES).
B3-H8   Training order: bodies frozen, paired experiences, train selector/projector + receiver adapter (`fit`),
        then calibrate the receiver distribution (`calibrate`: mean/sd + OOD threshold), then the L1 gate.
B3-H10  The manifest pins sender/receiver revisions; `load` refuses a mismatch (degrade to the configured channel).
B3-H3   `l1_gate` implements G-CALLOSUM-UTILITY-002 for L1: LATENT must beat NO_MESSAGE, its controls and the
        EXACT/CONTROL/SYMBOLIC baselines on utility per byte, keep role retention, stay in-distribution and
        reload bit-identically. Passing L1 only allows an L2 *shadow* test; it never enables LATENT authority.
"""
import hashlib
import io
import json
import math
import time
from pathlib import Path
import numpy as np

REVISION='b3-bridge-v1'
DIRECTIONS=('B1_TO_B2','B2_TO_B1')
AGE0_MAX_BYTES=2*1024*1024      # B3-H7: KB-to-low-MB class for bridge weights + message buffers
BYTES_NORM=4000.;BYTES_W=.25    # same memory-cost normalizer as callosum.outcome (B3-H9)
OOD_Q=.99                       # calibration: OOD threshold = 99th percentile of fit-set message z-scores

def to_bf16(x):
    """Round float32 to bfloat16 precision (round-to-nearest-even), returned as float32: what a BF16 transfer keeps."""
    a=np.ascontiguousarray(x,dtype=np.float32).view(np.uint32)
    a=((a+0x7FFF+((a>>16)&1))&0xFFFF0000).astype(np.uint32)
    return a.view(np.float32)

def budget(d,K,r,h,classes=0,slots_buffer=None):
    """B3-H7 arithmetic payload (not an RSS guarantee): parameters and BF16 bytes of one directional bridge."""
    params={'selector':K*d,'projector':d*r,'receiver_projector':K*r*h,'gate':1,'readout_residual':h*classes,'input_norm':2*d}
    n=sum(params.values());msg=K*r*2
    buf=(slots_buffer or K)*d*2
    return {'params':params,'param_count':n,'weights_bf16_bytes':2*n,'message_bf16_bytes':msg,'slot_buffer_bf16_bytes':buf,
            'total_bytes':2*n+msg+buf,'age0_ok':2*n+msg+buf<=AGE0_MAX_BYTES,'claim_limit':'arithmetic payload, not RSS'}

def linear_cka(X,Y):
    """Linear CKA between two representations of the same items (1 = same geometry, 0 = unrelated)."""
    X=X-X.mean(0);Y=Y-Y.mean(0)
    hsic=np.linalg.norm(X.T@Y)**2;nx=np.linalg.norm(X.T@X);ny=np.linalg.norm(Y.T@Y)
    return float(hsic/(nx*ny)) if nx>0 and ny>0 else 0.

def _softmax(z,axis):
    z=z-z.max(axis,keepdims=True);e=np.exp(z);return e/e.sum(axis,keepdims=True)

class Bridge:
    """One directional bridge. Inference is numpy only (phone); `fit` trains with Adam and manual gradients."""
    def __init__(self,d,K=4,r=8,h=16,classes=2,seed=0,direction='B1_TO_B2',aux=0,recv_cond=0):
        g=np.random.default_rng(seed);self.direction=direction
        self.d,self.K,self.r,self.h,self.classes,self.aux,self.recv_cond=d,K,r,h,classes,aux,recv_cond
        self.p={'Q':g.normal(0,1/math.sqrt(d),(K,d)),'P':g.normal(0,1/math.sqrt(d),(d,r)),'Pr':g.normal(0,1/math.sqrt(K*r),(K*r,h)),
                'gamma':np.array([0.]),'Wu':np.zeros((h,classes))}
        if aux:self.p['Wa']=np.zeros((h,aux))   # training-only auxiliary readout (sender-side attribute targets), never used in receive
        # recv_cond = receiver state dim: gated re-weighting of the receiver's own state while a message is open, so receiver-private
        # facts can be rescaled to the message (e.g. U > threshold[capacity]); gate closed => frozen NO_MESSAGE readout, unchanged
        if recv_cond:self.p['Wx']=np.zeros((recv_cond,classes))
        self.in_mu=np.zeros(d);self.in_sd=np.ones(d)
        self.head=None          # frozen receiver NO_MESSAGE readout (Wr, b) over the receiver's own state
        self.cal=None           # receiver calibration {mu, sd, ood_tau}
        self.manifest={}
    # -- forward --------------------------------------------------------------------------------------------
    def _norm(self,H):return (H-self.in_mu)/self.in_sd
    def encode(self,H,mask,cache=False):
        """Sender side: H[B,T,d] token states + mask[B,T] -> z[B,K,r]. Private states never leave the sender."""
        Hn=self._norm(H)*mask[...,None];sc=1/math.sqrt(self.d)
        S=np.einsum('btd,kd->btk',Hn,self.p['Q'])*sc;S=np.where(mask[...,None]>0,S,-1e30)
        A=_softmax(S,1)*mask[...,None];Sl=np.einsum('btk,btd->bkd',A,Hn);Z=Sl@self.p['P']
        return (Z,{'Hn':Hn,'A':A,'Sl':Sl,'sc':sc}) if cache else Z
    def gate(self):return float(1/(1+math.exp(-self.p['gamma'][0])))
    def ood(self,Z):
        """Receiver OOD score per item: mean |z-score| of the message under the fit-set calibration."""
        if self.cal is None:return np.zeros(len(Z))
        m=Z.reshape(len(Z),-1);return np.abs((m-self.cal['mu'])/self.cal['sd']).mean(1)
    def receive(self,Z,Xr,gate_open=True):
        """Receiver side: frozen NO_MESSAGE readout + gated message residual. Gate closes per item when OOD."""
        Wr,b=self.head;base=Xr@Wr+b
        if not gate_open:return base
        m=Z.reshape(len(Z),-1);U=m@self.p['Pr'];g=self.gate()
        if self.cal is not None:g=g*(self.ood(Z)<=self.cal['ood_tau'])[:,None]
        out=base+(g*U)@self.p['Wu']
        return out+g*(Xr@self.p['Wx']) if 'Wx' in self.p else out
    def logits(self,H,mask,Xr,bf16=True,gate_open=True):
        Z=self.encode(H,mask);Z=to_bf16(Z) if bf16 else Z
        return self.receive(Z,Xr,gate_open)
    # -- training (B3-H8 step 4) ----------------------------------------------------------------------------
    def loss_and_grads(self,H,mask,Xr,y,lam_var=.1,lam_cov=.05,lam_slot=.1,l2=1e-3,aux=None,lam_aux=1.):
        B=len(y);Z,c=self.encode(H,mask,cache=True);m=Z.reshape(B,-1);D=m.shape[1]
        U=m@self.p['Pr'];g=self.gate();Wr,b=self.head
        Rx=Xr@self.p['Wx'] if 'Wx' in self.p else 0.
        L=Xr@Wr+b+(g*U)@self.p['Wu']
        if 'Wx' in self.p:L=L+g*Rx
        P=_softmax(L,1);Y=np.eye(self.classes)[y]
        ce=-float(np.log(P[np.arange(B),y]+1e-12).mean())
        dL=(P-Y)/B;gr={}
        gr['Wu']=(g*U).T@dL+l2*self.p['Wu'];dU=g*dL@self.p['Wu'].T
        gr['gamma']=np.array([float((dL@self.p['Wu'].T*U).sum())*g*(1-g)])
        if 'Wx' in self.p:gr['gamma']+=float((dL*Rx).sum())*g*(1-g);gr['Wx']=g*Xr.T@dL+l2*self.p['Wx']
        la=0.
        if aux is not None and 'Wa' in self.p:
            # auxiliary targets (same supervision the SYMBOLIC_ATTR/SCALAR baselines get): pull those directions into U
            E=U@self.p['Wa']-aux;la=.5*float((E**2).sum())/B;dE=lam_aux*E/B
            gr['Wa']=U.T@dE+l2*self.p['Wa'];dU=dU+dE@self.p['Wa'].T
        elif 'Wa' in self.p:gr['Wa']=np.zeros_like(self.p['Wa'])
        gr['Pr']=m.T@dU+l2*self.p['Pr'];dm=dU@self.p['Pr'].T
        # anti-collapse on the message space: variance hinge + decorrelation
        mc=m-m.mean(0);var=(mc**2).mean(0);std=np.sqrt(var+1e-4);lv=float(np.maximum(0,1-std).mean())
        dm+=lam_var*(-(std<1).astype(float)/D)*mc/(B*std)
        C=mc.T@mc/max(1,B-1);off=C-np.diag(np.diag(C));lc=float((off**2).sum()/D)
        dmc=2*mc@(2*off/D)/max(1,B-1);dm+=lam_cov*(dmc-dmc.mean(0))
        dZ=dm.reshape(Z.shape)
        gr['P']=np.einsum('bkd,bkr->dr',c['Sl'],dZ)+l2*self.p['P'];dSl=dZ@self.p['P'].T
        A=c['A'];dA=np.einsum('bkd,btd->btk',dSl,c['Hn'])
        # selector slot-overlap penalty: different slots should read different tokens
        K=self.K;ls=0.
        if K>1:
            tot=A.sum(2,keepdims=True);ls=float(((A*(tot-A)).sum()/(K*(K-1)*B)))
            dA+=lam_slot*2*(tot-A)/(K*(K-1)*B)
        dS=A*(dA-(A*dA).sum(1,keepdims=True))
        gr['Q']=np.einsum('btk,btd->kd',dS,c['Hn'])*c['sc']+l2*self.p['Q']
        loss=ce+lam_var*lv+lam_cov*lc+lam_slot*ls+lam_aux*la+.5*l2*sum(float((self.p[k]**2).sum()) for k in ('Wu','Pr','P','Q','Wa','Wx') if k in self.p)
        return loss,gr,{'ce':ce,'var_hinge':lv,'decorrelation':lc,'slot_overlap':ls}|({'aux_mse':la} if aux is not None else {})
    def fit_head(self,Xr,y,l2=1e-2,steps=400,lr=.5):
        """Frozen receiver NO_MESSAGE readout (the 'old task'); the bridge only adds a gated residual on top."""
        W=np.zeros((Xr.shape[1],self.classes));b=np.zeros(self.classes);Y=np.eye(self.classes)[y]
        for _ in range(steps):
            p=_softmax(Xr@W+b,1);gg=(p-Y)/len(y);W-=lr*(Xr.T@gg+l2*W);b-=lr*gg.sum(0)
        self.head=(W,b);return self
    def fit(self,H,mask,Xr,y,epochs=60,batch=64,lr=3e-3,seed=0,aux=None,**kw):
        """B3-H8 step 4: bodies frozen; trains selector, projector, receiver projector, gate and residual readout.
        aux[N, A]: optional standardized sender-side attribute targets (bridge built with aux=A); training signal only."""
        if self.head is None:raise ValueError('fit_head first (frozen NO_MESSAGE readout)')
        flat=H[mask>0];self.in_mu=flat.mean(0);self.in_sd=flat.std(0)+1e-6
        rng=np.random.default_rng(seed);mom={k:np.zeros_like(v) for k,v in self.p.items()};vel={k:np.zeros_like(v) for k,v in self.p.items()};t=0;hist=[]
        for ep in range(epochs):
            idx=rng.permutation(len(y));parts=[]
            for i in range(0,len(y),batch):
                j=idx[i:i+batch]
                if len(j)<2:continue
                loss,gr,part=self.loss_and_grads(H[j],mask[j],Xr[j],y[j],aux=None if aux is None else aux[j],**kw);t+=1;parts.append(part)
                for k in self.p:
                    mom[k]=.9*mom[k]+.1*gr[k];vel[k]=.999*vel[k]+.001*gr[k]**2
                    self.p[k]-=lr*(mom[k]/(1-.9**t))/(np.sqrt(vel[k]/(1-.999**t))+1e-8)
            hist.append({k:round(float(np.mean([p[k] for p in parts])),4) for k in parts[0]})
        self.manifest['train']={'epochs':epochs,'lr':lr,'batch':batch,'samples':int(len(y)),'last':hist[-1],'first':hist[0]}  # samples: B3-H8 step 3 evidence
        return hist
    # -- calibration (B3-H8 step 5) -------------------------------------------------------------------------
    def calibrate(self,H,mask,q=OOD_Q):
        Z=to_bf16(self.encode(H,mask));m=Z.reshape(len(Z),-1)
        self.cal={'mu':m.mean(0),'sd':m.std(0)+1e-6,'ood_tau':0.}
        self.cal['ood_tau']=float(np.quantile(self.ood(Z),q));return self.cal
    # -- persistence (B3-H10) -------------------------------------------------------------------------------
    def _arrays(self):
        a={f'p_{k}':v for k,v in self.p.items()}|{'in_mu':self.in_mu,'in_sd':self.in_sd}
        if self.head is not None:a|={'head_W':self.head[0],'head_b':self.head[1]}
        if self.cal is not None:a|={'cal_mu':self.cal['mu'],'cal_sd':self.cal['sd'],'cal_tau':np.array([self.cal['ood_tau']])}
        return a
    def digest(self):
        h=hashlib.sha256()
        for k,v in sorted(self._arrays().items()):h.update(k.encode());h.update(np.ascontiguousarray(v,dtype=np.float64).tobytes())
        return h.hexdigest()
    def save(self,path,sender_revision,receiver_revision,extra=None):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        buf=io.BytesIO();np.savez(buf,**self._arrays());path.with_suffix('.npz').write_bytes(buf.getvalue())
        # fresh fields win over self.manifest (it may hold an earlier save's revisions, e.g. a reload check)
        man=self.manifest|{'revision':REVISION,'direction':self.direction,'d':self.d,'K':self.K,'r':self.r,'h':self.h,'classes':self.classes,'aux':self.aux,'recv_cond':self.recv_cond,
             'sender_revision':sender_revision,'receiver_revision':receiver_revision,'sha256':self.digest(),'calibrated':self.cal is not None,
             'budget':budget(self.d,self.K,self.r,self.h,self.classes),'created_wall_time':time.time()}|(extra or {})
        path.with_suffix('.json').write_text(json.dumps(man,indent=1,default=float));self.manifest=man;return man
    @classmethod
    def load(cls,path,sender_revision=None,receiver_revision=None):
        path=Path(path);man=json.loads(path.with_suffix('.json').read_text())
        if man.get('revision')!=REVISION:raise ValueError('bridge revision mismatch')
        for k,v in (('sender_revision',sender_revision),('receiver_revision',receiver_revision)):
            if v is not None and man.get(k)!=v:raise ValueError(f'B3-H10: {k} changed ({man.get(k)} -> {v}); bridge invalid, use configured channel')
        b=cls(man['d'],man['K'],man['r'],man['h'],man['classes'],direction=man['direction'],aux=man.get('aux',0),recv_cond=man.get('recv_cond',0))
        with np.load(path.with_suffix('.npz')) as a:
            for k in b.p:b.p[k]=a[f'p_{k}']
            b.in_mu,b.in_sd=a['in_mu'],a['in_sd']
            if 'head_W' in a:b.head=(a['head_W'],a['head_b'])
            if 'cal_mu' in a:b.cal={'mu':a['cal_mu'],'sd':a['cal_sd'],'ood_tau':float(a['cal_tau'][0])}
        if b.digest()!=man['sha256']:raise ValueError('bridge weights do not match manifest sha256')
        b.manifest=man;return b

# -- B3-H2 diversity checks ---------------------------------------------------------------------------------
def diversity_report(bridge,H,mask,Xs_private,Xr_private,Xr_head,y_role=None,role_head=None):
    """Role retention, private-state similarity, old-task behaviour, message geometry (B3-H2 required checks)."""
    Z=to_bf16(bridge.encode(H,mask));m=Z.reshape(len(Z),-1)
    closed=bridge.receive(Z,Xr_head,gate_open=False);W,b=bridge.head
    out={'cka_private_sender_receiver':round(linear_cka(Xs_private,Xr_private),4),'cka_message_receiver':round(linear_cka(m,Xr_private),4),
         'cka_message_sender':round(linear_cka(m,Xs_private),4),'old_task_identical_when_gate_closed':bool(np.array_equal(closed,Xr_head@W+b)),
         'message_dim_std_min':round(float(m.std(0).min()),4),'message_effective_rank':round(float(_eff_rank(m)),2),'gate':round(bridge.gate(),4),
         'selector_slot_overlap':round(float(_slot_overlap(bridge,H,mask)),4)}
    if y_role is not None and role_head is not None:
        Wr,br=role_head;out['role_task_acc']=round(float(((Xr_private@Wr+br).argmax(1)==y_role).mean()),4)
    return out

def _eff_rank(m):
    s=np.linalg.svd(m-m.mean(0),compute_uv=False);p=s/s.sum() if s.sum()>0 else s
    return math.exp(-float((p[p>0]*np.log(p[p>0])).sum())) if s.sum()>0 else 0.

def _slot_overlap(bridge,H,mask):
    _,c=bridge.encode(H,mask,cache=True);A=c['A'];K=bridge.K
    if K<2:return 0.
    tot=A.sum(2,keepdims=True);return (A*(tot-A)).sum()/(K*(K-1)*len(A))

# -- B3-H3 L1 gate (G-CALLOSUM-UTILITY-002) -----------------------------------------------------------------
def utility(acc,base_acc,nbytes):
    """Utility of a channel: accuracy gain over NO_MESSAGE minus the callosum memory cost of the bytes sent."""
    return acc-base_acc-BYTES_W*min(1.,nbytes/BYTES_NORM)

def paired(a,b):
    d=np.asarray(a)-np.asarray(b);se=float(d.std(ddof=1)/math.sqrt(len(d))) if len(d)>1 else float('inf')
    return {'mean':round(float(d.mean()),4),'se':round(se,4),'wins':int((d>0).sum()),'n':len(d),'significant':bool(d.mean()-2*se>0)}

def l1_gate(task,role_drop=.01,ood_max=.05):
    """task: {'acc': {channel: [per-seed acc]}, 'bytes': {channel: bytes}, 'role_drop': float, 'ood_rate': float,
    'reload_identical': bool}. Channels: NO_MESSAGE, EXACT, CONTROL, SYMBOLIC, LATENT, LATENT_SHUFFLED, LATENT_RANDOM
    (missing baselines are skipped and reported). Returns criteria + verdict PASS/FAIL. PASS only permits L2 SHADOW."""
    acc,by=task['acc'],task['bytes'];base=np.asarray(acc['NO_MESSAGE'])
    u={c:[utility(a,b0,by.get(c,0)) for a,b0 in zip(acc[c],base)] for c in acc}
    crit={'beats_no_message':paired(acc['LATENT'],acc['NO_MESSAGE'])}
    for ctl in ('LATENT_SHUFFLED','LATENT_RANDOM'):
        if ctl in acc:crit['beats_'+ctl.lower()]=paired(acc['LATENT'],acc[ctl])
    for bl in ('EXACT','CONTROL','SYMBOLIC'):
        if bl in acc:crit['utility_beats_'+bl.lower()]=paired(u['LATENT'],u[bl])
    crit['role_retention']={'drop':round(task.get('role_drop',0.),4),'significant':task.get('role_drop',0.)<=role_drop}
    crit['receiver_ood']={'rate':round(task.get('ood_rate',0.),4),'significant':task.get('ood_rate',0.)<=ood_max}
    crit['restart_reproducibility']={'significant':bool(task.get('reload_identical',False))}
    ok=all(v['significant'] for v in crit.values())
    return {'gate':'G-CALLOSUM-UTILITY-002','level':'L1','verdict':'PASS' if ok else 'FAIL','criteria':crit,
            'utility_mean':{c:round(float(np.mean(v)),4) for c,v in u.items()},'missing_baselines':[c for c in ('EXACT','CONTROL','SYMBOLIC') if c not in acc],
            'consequence':'L2 prefix SHADOW test allowed; LATENT authority stays 0' if ok else 'B3_LATENT stays unavailable; SOURCE_EXACT/CONTROL/SYMBOLIC only'}

L2_NORM_BAND=(.8,1.25)          # B3-H4: prefix norm / native input-token norm must stay in this band

def l2_gate(task,role_drop=.01,norm_band=L2_NORM_BAND):
    """B3 L2 prefix SHADOW gate (WP-Z4b, preregistered). task: {'acc': {channel: [per-seed acc]}, 'bytes', 'role_drop',
    'norm_ratio', 'reproducible'}. Channels are receiver-backbone reads of the same readout: PREFIX (calibrated latent
    prefix), PREFIX_OFF (= NO_MESSAGE), PREFIX_SHUFFLED, PREFIX_RANDOM (norm-matched), and the native text baselines
    EXACT, SYMBOLIC (label word), SYMBOLIC_ATTR. PASS only permits an L3 tiny-residual SHADOW test."""
    acc,by=task['acc'],task['bytes'];base=np.asarray(acc['PREFIX_OFF'])
    u={c:[utility(a,b0,by.get(c,0)) for a,b0 in zip(acc[c],base)] for c in acc}
    crit={'beats_prefix_off':paired(acc['PREFIX'],acc['PREFIX_OFF'])}
    for ctl in ('PREFIX_SHUFFLED','PREFIX_RANDOM'):crit['beats_'+ctl.lower()]=paired(acc['PREFIX'],acc[ctl])
    for bl in ('EXACT','SYMBOLIC','SYMBOLIC_ATTR'):
        if bl in acc:crit['utility_beats_'+bl.lower()]=paired(u['PREFIX'],u[bl])
    crit['role_retention']={'drop':round(task.get('role_drop',0.),4),'significant':task.get('role_drop',0.)<=role_drop}
    nr=task.get('norm_ratio');crit['receiver_calibration']={'norm_ratio':nr,'band':list(norm_band),'significant':nr is not None and norm_band[0]<=nr<=norm_band[1]}
    crit['restart_reproducibility']={'significant':bool(task.get('reproducible',False))}
    ok=all(v['significant'] for v in crit.values())
    return {'gate':'G-CALLOSUM-UTILITY-002','level':'L2','verdict':'PASS' if ok else 'FAIL','criteria':crit,
            'utility_mean':{c:round(float(np.mean(v)),4) for c,v in u.items()},'missing_baselines':[c for c in ('EXACT','SYMBOLIC','SYMBOLIC_ATTR') if c not in acc],
            'consequence':'L3 tiny-residual SHADOW test allowed; LATENT authority stays 0' if ok else 'B3_LATENT stays at L1_shadow; L3 stays locked'}

# -- :doctor (B3-H11) ---------------------------------------------------------------------------------------
def bridge_dir(home):return Path(home)/'b3'

def doctor_fields(home,direction,receiver_revision=None):
    """Fields for verification.b3_doctor from a trained bridge manifest (if any). LATENT authority is never granted."""
    p=bridge_dir(home)/f'{direction}.json'
    if not p.exists():return {'bridge':None}
    try:man=json.loads(p.read_text())
    except Exception as exc:return {'bridge':{'error':type(exc).__name__}}
    gate=man.get('l1_gate') or {};stale=receiver_revision is not None and man.get('receiver_revision') not in (None,receiver_revision)
    level='L1_PASSED_L2_SHADOW_ALLOWED' if gate.get('verdict')=='PASS' and not stale else 'unavailable'
    return {'latent_level':level,'calibration':'calibrated' if man.get('calibrated') else None,'message_rank':man.get('r'),'slot_budget':man.get('K'),
            'bridge':{'sha256':man.get('sha256'),'param_count':(man.get('budget') or {}).get('param_count'),'weights_bf16_bytes':(man.get('budget') or {}).get('weights_bf16_bytes'),
                      'message_bf16_bytes':(man.get('budget') or {}).get('message_bf16_bytes'),'l1_verdict':gate.get('verdict'),'stale_receiver_revision':stale,
                      'last_calibration':man.get('created_wall_time')},
            'latent_read_authority':0,'latent_learn_authority':0}

# -- B3-H12 completion gate (LOCKED) / B3-H13 -------------------------------------------------------------
COMPLETION=('CODE','REAL_SENDER_STATE_PATH','REAL_RECEIVER_EFFECT','RECEIVER_CALIBRATED_BRIDGE','FALLBACK_CHANNELS',
            'OOD_GATE','ROUTER_STABILITY_METRICS','RESTART_PERSISTENCE','INTEGRATION_TESTS','TELEMETRY',
            'NO_MESSAGE_ABLATION','EXACT_ABLATION','SYMBOLIC_CONTROL_ABLATION','REAL_TARGET_RUNNER_MEASUREMENT')
CANON='The callosal bridge must learn a receiver-compatible communication language before it earns the right to perturb a receiver\'s pretrained internal dynamics (B3-H13).'

def completion_gate(home,direction,row,messages=0,app=None):
    """B3-H12: every condition from evidence, never from intent. row: the :doctor row of this direction (callosum +
    doctor_fields). Returns criteria, the allowed intermediate status and B3_LATENT_IMPLEMENTED (all criteria)."""
    app=Path(app or Path(__file__).resolve().parents[1]);man=None;p=bridge_dir(home)/f'{direction}.json'
    if p.exists():
        try:man=json.loads(p.read_text())
        except Exception:man=None
    gate=(man or {}).get('l1_gate') or {};crit=gate.get('criteria') or {};bridge=row.get('bridge') or {}
    stale=bool(bridge.get('stale_receiver_revision'))
    c={'CODE':(app/'v13/b3bridge.py').exists(),
       'REAL_SENDER_STATE_PATH':bool(row.get('native_taps')),
       'REAL_RECEIVER_EFFECT':bool(row.get('receiver_tap_ids')) and bool(row.get('latent_gain')),
       'RECEIVER_CALIBRATED_BRIDGE':bool(man and man.get('calibrated') and man.get('receiver_revision')) and not stale,
       'FALLBACK_CHANNELS':bool(row.get('fallback_channel') or row.get('fallback')) and (row.get('experience_count') or 0)>0,
       'OOD_GATE':'receiver_ood' in crit,
       'ROUTER_STABILITY_METRICS':row.get('router_kl') is not None or row.get('router_collision_metrics') is not None,
       'RESTART_PERSISTENCE':bool((crit.get('restart_reproducibility') or {}).get('significant')),
       'INTEGRATION_TESTS':all((app/'tests'/f).exists() for f in ('test_b3bridge.py','test_callosum.py')),
       'TELEMETRY':messages>0,
       'NO_MESSAGE_ABLATION':'beats_no_message' in crit,
       'EXACT_ABLATION':'utility_beats_exact' in crit,
       'SYMBOLIC_CONTROL_ABLATION':'utility_beats_symbolic' in crit and 'utility_beats_control' in crit,
       'REAL_TARGET_RUNNER_MEASUREMENT':bool(row.get('hardware_proof_id'))}
    implemented=all(c.values())
    if implemented:status='active'
    elif gate.get('verdict')=='PASS' and not stale:status='L1_shadow'
    elif c['CODE']:status='scaffold'
    else:status='unavailable'
    return {'criteria':c,'missing':[k for k in COMPLETION if not c[k]],'status':status,'B3_LATENT_IMPLEMENTED':implemented,
            'latent_authority':0,'canon':CANON}

