"""B3-H4 receiver calibration packet, B3-H5 hard receiver gate, B3-H9 latent utility (WP-N20).

B3-H4 [MUST]: every candidate latent message carries or references measured receiver-compatibility
metadata. ``compute`` builds the full packet from what was measured at the receiver's target tap:

  native      (n, d) receiver states at ``target_tap_id`` on calibration inputs (no message)
  message     (m, d) message vectors already mapped into that receiver space (receiver projector output)

  native_norm_mean / native_norm_std   row L2 norms of ``native``
  message_norm                         mean row norm of ``message``; norm_ratio = message_norm / native_norm_mean
  mean_shift                           |mean(message) - mean(native)| / native_norm_mean
  variance_ratio                       total variance(message) / total variance(native)
  geometry_error                       total-variation distance between the receiver's variance shares on its own
                                       principal axes and the message's variance shares on those axes (+ the part
                                       outside them); 0 = same spread, 1 = disjoint. A message that lives in
                                       directions the receiver barely uses scores high even at matching norm
  calibration_confidence               BOOT heuristic: sample sufficiency x (1 - geometry_error)
  router_kl / expert_flip_rate / residual_norm_shift / receiver_loss_delta / attention_shift
                                       only when measured (receiver runs with/without the message); None otherwise
  manifold_distance                    never filled: not implemented and validated (the canon makes it optional)

``valid_until_revision`` is the receiver revision; a calibration from another receiver/sender revision is
invalid (``validity``).

B3-H5 [LOCKED] ``gate``: calibration missing or invalid -> LATENT OFF; receiver revision changed -> OFF;
OOD or router-drift gate fails -> OFF with a fallback channel; utility after cost <= fallback utility ->
LATENT authority must not increase. Router thresholds are ``[TUNE after calibration]`` in the canon: for
a sparse-MoE receiver without calibrated thresholds the router gate cannot pass.

B3-H9 [MUST] ``latent_utility``: task_gain + uncertainty_reduction + source_recovery_gain - latency_cost
- memory_cost - router_drift_penalty - retention_penalty. ``latent_preferred``: LATENT only after it wins
against every simpler baseline over a sufficient validation window (paired, mean - 2 SE > 0, n >= window).

Status: mechanism with fixture tests. No receiver tap pair (B1 -> B2 states at a real target tap) exists in
the project data yet, so no real packet has been computed; LATENT stays unavailable (WP-J).
"""
import hashlib
import math
import numpy as np

REVISION='b3-receiver-calibration-v1'
REQUIRED=('body_pair_id','sender_revision','receiver_revision','injection_level','target_tap_id',
          'native_norm_mean','native_norm_std','message_norm','norm_ratio','mean_shift','variance_ratio',
          'geometry_error','calibration_confidence','router_kl','expert_flip_rate','residual_norm_shift',
          'downstream_utility','latency_cost','memory_cost','sample_count','calibration_dataset_id','valid_until_revision')
OPTIONAL=('manifold_distance','attention_shift','receiver_loss_delta')
KINDS=('dense','moe')
MIN_SAMPLES=64                # BOOT: below this the statistics are not a calibration
GEOMETRY_MAX=.5;NORM_RATIO_BAND=(.5,2.);MEAN_SHIFT_MAX=1.;VARIANCE_BAND=(.25,4.)  # BOOT compatibility bands
PENALTY_W={'router_drift':1.,'retention':1.}  # BOOT weights of the B3-H9 penalties
WINDOW=20                     # BOOT validation window (paired episodes)

def _a(x):
    a=np.asarray(x,dtype=np.float64)
    if a.ndim!=2 or not len(a):raise ValueError('expected a non-empty (n, d) array')
    if not np.isfinite(a).all():raise ValueError('non-finite values')
    return a

def geometry(native,message):
    """Total-variation distance between how the receiver spreads its variance over its own principal axes and
    how the message spreads its variance over the same axes (+ one bucket for message variance outside them).
    Direction-aware: a message with matching norm and spectrum but on the receiver's quiet axes scores high."""
    cn=native-native.mean(0);cm=message-message.mean(0)
    _,s,vt=np.linalg.svd(cn,full_matrices=False);keep=s>1e-12*max(s.max(),1e-300) if len(s) else s>0
    s,vt=s[keep],vt[keep]
    tn=float((s**2).sum());tm=float((cm**2).sum())
    if tn<=0 or tm<=0:return 1.
    p=np.append(s**2/tn,0.);proj=((cm@vt.T)**2).sum(0)/tm;q=np.append(proj,max(0.,1.-proj.sum()))
    return float(min(1.,.5*np.abs(p-q).sum()))

def dataset_id(*arrays):
    h=hashlib.sha256()
    for a in arrays:a=np.ascontiguousarray(a,dtype=np.float64);h.update(str(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()[:16]

def compute(native,message,*,body_pair_id,sender_revision,receiver_revision,target_tap_id,injection_level=1,receiver_kind='dense',
            downstream_utility=None,latency_cost=None,memory_cost=None,router_kl=None,expert_flip_rate=None,residual_norm_shift=None,
            receiver_loss_delta=None,attention_shift=None):
    """The full B3-H4 packet from measured receiver states (see module doc)."""
    if receiver_kind not in KINDS:raise ValueError('receiver_kind: dense|moe')
    if not 1<=int(injection_level)<=4:raise ValueError('injection_level 1..4 (L1..L4)')
    n,m=_a(native),_a(message)
    if n.shape[1]!=m.shape[1]:raise ValueError('native and message must share the receiver dimension')
    nn=np.linalg.norm(n,axis=1);mn=float(np.linalg.norm(m,axis=1).mean());base=float(nn.mean()) or 1e-12
    vn,vm=float(n.var(0).sum()),float(m.var(0).sum())
    geo=geometry(n,m) if len(n)>1 and len(m)>1 else 1.
    samples=min(len(n),len(m))
    r=lambda v:None if v is None else round(float(v),6)
    return {'revision':REVISION,'body_pair_id':body_pair_id,'sender_revision':sender_revision,'receiver_revision':receiver_revision,
            'injection_level':int(injection_level),'target_tap_id':target_tap_id,'receiver_kind':receiver_kind,
            'native_norm_mean':r(base),'native_norm_std':r(nn.std()),'message_norm':r(mn),'norm_ratio':r(mn/base),
            'mean_shift':r(np.linalg.norm(m.mean(0)-n.mean(0))/base),'variance_ratio':r(vm/vn) if vn>0 else None,
            'geometry_error':r(geo),'manifold_distance':None,'calibration_confidence':r(min(1.,samples/MIN_SAMPLES)*(1-geo)),
            'router_kl':r(router_kl),'expert_flip_rate':r(expert_flip_rate),'residual_norm_shift':r(residual_norm_shift),
            'attention_shift':r(attention_shift),'receiver_loss_delta':r(receiver_loss_delta),
            'downstream_utility':r(downstream_utility),'latency_cost':r(latency_cost),'memory_cost':r(memory_cost),
            'sample_count':samples,'calibration_dataset_id':dataset_id(n,m),'valid_until_revision':receiver_revision}

def validity(cal,receiver_revision,sender_revision=None):
    """(ok, reasons). Stale revision, missing field, too few samples, MoE receiver without router metrics."""
    if not cal:return False,['CALIBRATION_MISSING']
    why=[k for k in REQUIRED if k not in cal]
    why=['FIELD_MISSING:'+k for k in why]
    if cal.get('revision')!=REVISION:why.append('PACKET_REVISION')
    if receiver_revision is None or cal.get('valid_until_revision')!=receiver_revision or cal.get('receiver_revision')!=receiver_revision:
        why.append('STALE_RECEIVER_REVISION')
    if sender_revision is not None and cal.get('sender_revision')!=sender_revision:why.append('STALE_SENDER_REVISION')
    if (cal.get('sample_count') or 0)<MIN_SAMPLES:why.append('TOO_FEW_SAMPLES')
    if cal.get('receiver_kind')=='moe' and (cal.get('router_kl') is None or cal.get('expert_flip_rate') is None):why.append('MOE_ROUTER_NOT_MEASURED')
    return not why,why

def compatible(cal):
    """Distribution compatibility of the message with the receiver tap (BOOT bands). Returns failing checks."""
    out=[]
    if cal['geometry_error'] is None or cal['geometry_error']>GEOMETRY_MAX:out.append('GEOMETRY')
    if cal['norm_ratio'] is None or not NORM_RATIO_BAND[0]<=cal['norm_ratio']<=NORM_RATIO_BAND[1]:out.append('NORM_RATIO')
    if cal['mean_shift'] is None or cal['mean_shift']>MEAN_SHIFT_MAX:out.append('MEAN_SHIFT')
    if cal['variance_ratio'] is None or not VARIANCE_BAND[0]<=cal['variance_ratio']<=VARIANCE_BAND[1]:out.append('VARIANCE_RATIO')
    return out

def router_ok(cal,thresholds=None):
    """B3-H6 router gate from the packet. Dense receivers: not applicable (True). MoE: needs calibrated thresholds."""
    if cal.get('receiver_kind')!='moe':return True,[]
    t=thresholds or {}
    need={'router_kl':'B3.max_router_kl','expert_flip_rate':'B3.max_expert_flip_rate','residual_norm_shift':'B3.max_residual_norm_shift'}
    why=[]
    for f,k in need.items():
        if t.get(k) is None:why.append('THRESHOLD_UNCALIBRATED:'+k)
        elif cal.get(f) is None or cal[f]>t[k]:why.append('ROUTER_GATE:'+f)
    return not why,why

def gate(cal,receiver_revision,*,sender_revision=None,ood_ok=None,thresholds=None,latent_utility=None,fallback_utility=None,fallback='SOURCE_EXACT'):
    """B3-H5 hard receiver gate. Returns {'latent': ON|OFF, 'reasons', 'fallback', 'authority_may_increase'}."""
    ok,why=validity(cal,receiver_revision,sender_revision)
    if not ok:
        miss='CALIBRATION_MISSING' if 'CALIBRATION_MISSING' in why else ('RECEIVER_REVISION_CHANGED' if 'STALE_RECEIVER_REVISION' in why else 'CALIBRATION_INVALID')
        return {'latent':'OFF','reasons':[miss]+[w for w in why if w!=miss],'fallback':fallback,'authority_may_increase':False}
    why=[]
    if ood_ok is not True:why.append('OOD_GATE' if ood_ok is False else 'OOD_NOT_MEASURED')
    rok,rwhy=router_ok(cal,thresholds);why+=rwhy
    why+=['COMPATIBILITY:'+c for c in compatible(cal)]
    if why:return {'latent':'OFF','reasons':why,'fallback':fallback,'authority_may_increase':False}
    up=latent_utility is not None and fallback_utility is not None and latent_utility>fallback_utility
    return {'latent':'ON','reasons':[] if up else ['UTILITY_NOT_ABOVE_FALLBACK'],'fallback':fallback,'authority_may_increase':up}

def latent_utility(task_gain,uncertainty_reduction,source_recovery_gain,latency_cost,memory_cost,router_drift=0.,retention_drop=0.):
    """B3-H9 for LATENT. router_drift / retention_drop: increase over the baseline at grant time (>= 0 counts)."""
    rp=PENALTY_W['router_drift']*max(0.,router_drift or 0.);tp=PENALTY_W['retention']*max(0.,retention_drop or 0.)
    parts={'task_gain':task_gain,'uncertainty_reduction':uncertainty_reduction,'source_recovery_gain':source_recovery_gain,
           'latency_cost':latency_cost,'memory_cost':memory_cost,'router_drift_penalty':rp,'retention_penalty':tp}
    return task_gain+uncertainty_reduction+source_recovery_gain-latency_cost-memory_cost-rp-tp,parts

def paired_win(a,b):
    d=np.asarray(a,dtype=np.float64)-np.asarray(b,dtype=np.float64)
    if len(d)<2:return {'n':len(d),'mean':float(d.mean()) if len(d) else None,'se':None,'wins':False}
    se=float(d.std(ddof=1)/math.sqrt(len(d)));return {'n':len(d),'mean':round(float(d.mean()),4),'se':round(se,4),'wins':bool(d.mean()-2*se>0)}

def latent_preferred(history,window=WINDOW):
    """history: {channel: [utility per paired episode]} incl. LATENT and the simpler baselines (NO_MESSAGE,
    SOURCE_EXACT, CONTROL, SYMBOLIC as measured). LATENT may become preferred only when it wins against every
    present baseline over the last ``window`` paired episodes. No global latent_first flag exists."""
    lat=list(history.get('LATENT') or [])
    base=[c for c in ('NO_MESSAGE','SOURCE_EXACT','CONTROL','SYMBOLIC') if history.get(c)]
    if len(lat)<window or 'NO_MESSAGE' not in base:return {'preferred':False,'reason':'VALIDATION_WINDOW_TOO_SHORT' if len(lat)<window else 'NO_MESSAGE_BASELINE_MISSING','n':len(lat)}
    res={}
    for c in base:
        n=min(window,len(lat),len(history[c]));res[c]=paired_win(lat[-n:],history[c][-n:])
        if res[c]['n']<window:return {'preferred':False,'reason':'VALIDATION_WINDOW_TOO_SHORT','n':res[c]['n'],'against':res}
    return {'preferred':all(x['wins'] for x in res.values()),'reason':None if all(x['wins'] for x in res.values()) else 'DOES_NOT_BEAT_ALL_BASELINES','n':window,'against':res}
