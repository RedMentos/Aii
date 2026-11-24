"""WP-AB / §99 mandatory ablations without a language model: eligibility, typed modulators, proceduralization, Age.

Each run drives the *real* modules (Neuromod gate, FastForward lifecycle, AgeControl plasticity) on a synthetic,
open-loop task stream and compares them with the §99 controls on the identical stream:

  Eligibility helps        V13 gate e×M×P   vs  gradient only (factor 1), gradient only at the V13 mean budget,
                                               random mask (Bernoulli at the V13 mean budget), recency only (e = "touched now")
  Typed modulators help    typed M (source weights, kinds, veto)  vs  scalar reward (sum of channels, no source weight),
                                               human-only, outcome-only. Safety veto is kept in all three: it is a hard rule,
                                               not a modulator (§12.5), so only the modulator typing is ablated.
  Proceduralization helps  FastForward OBSERVE→SHADOW→READY + calm check + reopen  vs  full deliberation, static shortcut
  Age helps stability      AgeControl.plasticity (stage, maturity, reopen; BOOT and `stable_reopen` policy)  vs  fixed conservative (.45),
                                               fixed permissive (1.0)

Learners are linear NLMS predictors (dim 4), one per learnable path. The streams contain the regimes the mechanisms
are meant for (clean outcomes, human corrections, dreams with biased labels, unsafe successes, a stale path, drift),
so a win here only shows the code does what its design claims, and where a control is as good or better.
Claim limit: synthetic stream, no language model, no statement about real-model learning quality (§99, §100).
"""
import math
import random
import tempfile
from pathlib import Path

DIM=4;LR0=.5
SEEDS=(13,14,15,16,17)

def _vec(rng):
    v=[rng.gauss(0,1) for _ in range(DIM)];n=math.sqrt(sum(a*a for a in v)) or 1.;return [a/n for a in v]
def _dot(a,b):return sum(x*y for x,y in zip(a,b))
def _nlms(theta,x,y,lr):
    e=y-_dot(theta,x);k=lr*e/(1.+_dot(x,x));return [t+k*xi for t,xi in zip(theta,x)]
def _err(theta,w):return sum((t-a)**2 for t,a in zip(theta,w))/max(1e-9,_dot(w,w))
def _mean(v):return sum(v)/len(v) if v else None
def _sd(v):
    m=_mean(v);return math.sqrt(sum((a-m)**2 for a in v)/(len(v)-1)) if len(v)>1 else 0.

def _store(home):
    from .config import initialize
    from .store import Store
    cfg=initialize(home);return Store(home),cfg

# --- 1+2: eligibility and typed modulators ------------------------------------------------------------------------
LEARN_PATHS=('route','memory_retrieval','world_predictor','c5_action_selection','output_adapter')
ACTIVE_SHARE={'route':.3,'memory_retrieval':.2,'world_predictor':.2,'c5_action_selection':.15,'output_adapter':.15}
STALE_AFTER=.2;PASSIVE_RATE=.3;DREAM_SHARE=.75;HARM_SHARE=.2;NOISE=.1
ELIG_ARMS=('v13','v13_datamix','gradient_only','gradient_only_matched','random_mask','recency_only')
MOD_ARMS=('v13','v13_datamix','scalar_reward','human_only','outcome_only')
ORIGIN={'human_correction':'human','real_deterministic_outcome':'human','dream':'dream','internal_crosscheck':'self'}  # external ground truth counts as non-self
OUTCOME_CH=('task_success','reward_error','action_error','world_prediction_error','cost_error')

def credit_stream(seed,T=600):
    """Open-loop events: (path, x, y, true w, touch, signal kwargs). Labels never depend on the learner."""
    rng=random.Random(seed);w={p:_vec(rng) for p in LEARN_PATHS};w2=_vec(rng)
    bias={p:_vec(rng) for p in LEARN_PATHS};harm=_vec(rng);out=[]
    for t in range(T):
        share={p:s for p,s in ACTIVE_SHARE.items() if p!='output_adapter' or t<STALE_AFTER*T}
        r=rng.random()*sum(share.values());p=None
        for p,s in share.items():
            r-=s
            if r<=0:break
        if p=='route' and t>=T//2:w['route']=w2  # real drift: the route target changes once
        x=[rng.gauss(0,1) for _ in range(DIM)];true=w[p];y=_dot(true,x)+rng.gauss(0,NOISE)
        sig={'source_class':'real_deterministic_outcome','task_success':1.}
        if p in ('memory_retrieval','output_adapter'):sig={'source_class':'human_correction','human_correction':1.}
        elif p=='world_predictor':
            if rng.random()<DREAM_SHARE:y=_dot(bias[p],x);sig={'source_class':'dream','surprise':.8,'novelty':.5}
            else:sig={'source_class':'real_deterministic_outcome','world_prediction_error':.6}
        elif p=='c5_action_selection' and rng.random()<HARM_SHARE:
            y=_dot(harm,x);sig={'source_class':'real_deterministic_outcome','task_success':1.,'safety_veto':True}  # it "worked", but was unsafe
        out.append({'t':t,'path':p,'x':x,'y':y,'w':list(true),'touch':True,'signal':sig})
        if t>=STALE_AFTER*T and rng.random()<PASSIVE_RATE:  # stale path: only self-generated, slowly biased labels arrive
            x=[rng.gauss(0,1) for _ in range(DIM)]
            out.append({'t':t,'path':'output_adapter','x':x,'y':_dot(bias['output_adapter'],x),'w':list(w['output_adapter']),'touch':False,
                        'signal':{'source_class':'internal_crosscheck','evidence_gain':.3,'path':'output_adapter'}})
    return out

def record_gates(stream,store):
    """Feed the stream through the real Neuromod (touch + signal per event) and record the gate per update."""
    from .neuromod import Neuromod
    n=Neuromod(store);sess=store.new_session();rows=[];last=None;eid=None
    for ev in stream:
        if ev['t']!=last:eid=store.event(sess,'ab'+str(ev['t']))['event_id'];last=ev['t']
        if ev['touch']:n.touch(ev['path'],eid)
        n.signal(eid,**ev['signal']);g=n.gate(ev['path'])
        rows.append(ev|{'gate':{k:g[k] for k in ('factor','eligibility','veto')}|{'m':g['modulator']['combined']}})
    return rows

def _oplus(a,b):return 1-(1-a)*(1-b)

def _control_m(rows,kind):
    """Per-row modulator for a control arm, accumulated and decayed like the V13 bus (oplus, SLOW_DECAY per event)."""
    from .neuromod import SLOW_DECAY,clamp
    m={};seen={};out=[]
    for r in rows:
        p=r['path'];s=r['signal'];ch={k:v for k,v in s.items() if k not in ('source_class','safety_veto','path')}
        if kind=='scalar_reward':v=clamp(sum(ch.values()))
        elif kind=='human_only':v=clamp(ch.get('human_correction',0.))
        else:v=clamp(max([ch.get(c,0.) for c in OUTCOME_CH]+[0.]))
        if p in seen:m[p]*=SLOW_DECAY**(r['t']-seen[p])
        seen[p]=r['t'];m[p]=_oplus(m.get(p,0.),v);out.append(m[p])
    return out

def factors(rows,arm,rng):
    from .neuromod import FLOOR
    v13=[r['gate']['factor'] for r in rows];q=_mean(v13)
    if arm=='v13':return v13
    if arm=='v13_datamix':  # full V13 composition: gate + v4 data-mix quotas (guards.enforce_data_mix) on the training rows
        from .guards import enforce_data_mix
        keep=set(map(id,enforce_data_mix(rows,lambda r:ORIGIN[r['signal']['source_class']])))
        return [f if id(r) in keep else 0. for r,f in zip(rows,v13)]
    if arm=='gradient_only':return [1.]*len(rows)
    if arm=='gradient_only_matched':return [q]*len(rows)
    if arm=='random_mask':return [1. if rng.random()<q else 0. for _ in rows]
    if arm=='recency_only':return [0. if r['gate']['veto'] else FLOOR+(1-FLOOR)*float(r['touch'])*r['gate']['m'] for r in rows]
    m=_control_m(rows,arm)
    return [0. if r['gate']['veto'] else FLOOR+(1-FLOOR)*r['gate']['eligibility']*mi for r,mi in zip(rows,m)]

def run_credit(rows,arm,seed):
    rng=random.Random(seed*7+len(arm));f=factors(rows,arm,rng);theta={p:[0.]*DIM for p in LEARN_PATHS};T=rows[-1]['t']+1
    tail={p:[] for p in LEARN_PATHS};drift=[];w_now={}
    for r,fi in zip(rows,f):
        p=r['path'];theta[p]=_nlms(theta[p],r['x'],r['y'],LR0*fi);w_now[p]=r['w']
        if r['t']>=.75*T:tail[p].append(_err(theta[p],r['w']))
        if p=='route' and T//2<=r['t']<T//2+60:drift.append(_err(theta[p],r['w']))
    final={p:round(_err(theta[p],w_now[p]),4) for p in LEARN_PATHS}
    return {'final':final,'tail':{p:round(_mean(v),4) for p,v in tail.items() if v},'route_after_drift':round(_mean(drift),4),
            'mean_final':round(_mean(list(final.values())),4),'budget':round(_mean(f),4)}

# --- 1b: delayed reward (second eligibility timescale, §62) --------------------------------------------------------
# Paths are touched in short bursts with long quiet gaps; the outcome of each touch arrives 3..40 events later.
# 70 % of samples carry the true label and are confirmed (task_success), 30 % carry a biased label and get an
# unconfirmed outcome. The learner updates a sample when its outcome arrives, scaled by the arm's factor then.
DELAY_PATHS=('route','wake','halt','c5_action_selection');DELAY_MIN=3;DELAY_MAX=40;GOOD_SHARE=.7;BURST=5;GAP=(20,60);OUTCOME_FLIP=.1
DELAY_ARMS=('v13','v13_delta','fast_only','slow_only','recency_only','gradient_only','gradient_only_matched','random_mask','oracle')

def delayed_stream(seed,T=800):
    rng=random.Random(seed);w={p:_vec(rng) for p in DELAY_PATHS};bias={p:_vec(rng) for p in DELAY_PATHS}
    nxt={p:rng.randrange(GAP[1]) for p in DELAY_PATHS};left={p:0 for p in DELAY_PATHS};events=[]
    for t in range(T):
        for p in DELAY_PATHS:
            if left[p]==0 and t>=nxt[p]:left[p]=BURST
        act=[p for p in DELAY_PATHS if left[p]>0];p=rng.choice(act) if act else None;touch=None
        if p:
            left[p]-=1
            if left[p]==0:nxt[p]=t+rng.randint(*GAP)
            x=[rng.gauss(0,1) for _ in range(DIM)];good=rng.random()<GOOD_SHARE
            y=_dot(w[p],x)+rng.gauss(0,NOISE) if good else _dot(bias[p],x)
            touch={'path':p,'x':x,'y':y,'good':good,'confirmed':good!=(rng.random()<OUTCOME_FLIP),'due':t+rng.randint(DELAY_MIN,DELAY_MAX)}  # outcome report is 10 % wrong
        events.append({'t':t,'touch':touch})
    return {'events':events,'w':w}

def record_delayed(stream,store,slow_mix=None):
    """Real Neuromod: touch at sample time, typed outcome signal when it arrives, gate read right after the signal."""
    from . import neuromod as nm
    old=nm.SLOW_MIX
    if slow_mix is not None:nm.SLOW_MIX=slow_mix
    try:
        n=nm.Neuromod(store);sess=store.new_session();pending=[];rows=[]
        for ev in stream['events']:
            eid=store.event(sess,'dl'+str(ev['t']))['event_id'];tp=ev['touch']
            if tp:n.touch(tp['path'],eid);pending.append(tp)
            for s in [s for s in pending if s['due']==ev['t']]:
                pending.remove(s);n.signal(eid,path=s['path'],source_class='real_deterministic_outcome',task_success=1. if s['confirmed'] else 0.)
                lu=n.local_update(s['path']);g=lu['gate']  # WP-T12: signed per-sample δ = r - r̂
                rows.append(s|{'t':ev['t'],'factor':g['factor'],'m':g['modulator']['combined'],'touched_now':bool(tp and tp['path']==s['path']),'local':lu['scale'],'delta':lu['delta']})
        return rows
    finally:nm.SLOW_MIX=old

def run_delayed(rows,arm,w,seed,v13_mean=None):
    from .neuromod import FLOOR
    rng=random.Random(seed*11+len(arm));theta={p:[0.]*DIM for p in DELAY_PATHS};used=[];bad_w=[];good_w=[]
    for r in rows:
        if arm in ('v13','fast_only','slow_only'):f=r['factor']
        elif arm=='v13_delta':f=r['factor']*(1. if r['delta']>0 else 0.)  # §12.4 sign of the sample's own δ: imitate only confirmed-better-than-expected samples
        elif arm=='recency_only':f=FLOOR+(1-FLOOR)*float(r['touched_now'])*r['m']
        elif arm=='gradient_only':f=1.
        elif arm=='gradient_only_matched':f=v13_mean
        elif arm=='random_mask':f=1. if rng.random()<v13_mean else 0.
        else:f=1. if r['good'] else 0.
        theta[r['path']]=_nlms(theta[r['path']],r['x'],r['y'],LR0*f);used.append(f);(good_w if r['good'] else bad_w).append(f)
    final={p:round(_err(theta[p],w[p]),4) for p in DELAY_PATHS}
    return {'final':final,'mean_final':round(_mean(list(final.values())),4),'budget':round(_mean(used),4),
            'good_vs_bad_factor':round(_mean(good_w)/_mean(bad_w),4) if bad_w and _mean(bad_w)>0 else None}

def delayed_ablation(base,seeds=SEEDS):
    out={a:[] for a in DELAY_ARMS}
    for s in seeds:
        st=delayed_stream(s);rec={}
        for key,mix in (('v13',None),('fast_only',0.),('slow_only',1.)):
            store,_=_store(Path(base)/('delay-'+key+'-'+str(s)))
            try:rec[key]=record_delayed(st,store,mix)
            finally:store.close()
        q=_mean([r['factor'] for r in rec['v13']])
        for a in DELAY_ARMS:out[a].append(run_delayed(rec.get(a,rec['v13']),a,st['w'],s,q))
    summ={a:{'mean_final':round(_mean([r['mean_final'] for r in v]),4),'sd':round(_sd([r['mean_final'] for r in v]),4),'budget':round(_mean([r['budget'] for r in v]),4),
             'good_vs_bad_factor':(round(_mean([r['good_vs_bad_factor'] for r in v]),4) if all(r['good_vs_bad_factor'] is not None for r in v) else None)} for a,v in out.items()}
    wins={a:sum(x['mean_final']<y['mean_final'] for x,y in zip(out['v13'],v)) for a,v in out.items() if a!='v13'}
    dwins={a:sum(x['mean_final']<y['mean_final'] for x,y in zip(out['v13_delta'],v)) for a,v in out.items() if a!='v13_delta'}
    return {'summary':summ,'v13_wins_of_n':wins,'v13_delta_wins_of_n':dwins,'n':len(seeds),'raw':out}

# --- 3: proceduralization -----------------------------------------------------------------------------------------
PATTERNS={'A':'none','B':'detail','C':'gist'};SALIENT_WAKE='both';WAKES=('none','detail','gist','both')
COST_DELIB=3.;COST_PROC=1.;DELIB_OK=.98;SALIENT=.1

def proc_stream(seed,N=600):
    rng=random.Random(seed);out=[]
    for t in range(N):
        k=rng.choice(sorted(PATTERNS));sal=rng.random()<SALIENT
        want=SALIENT_WAKE if sal else ('detail' if k=='A' and t>=N//2 else PATTERNS[k])
        out.append({'t':t,'key':k+('|novel' if sal else ''),'salient':sal,'want':want,'delib_ok':rng.random()<DELIB_OK,'alt':rng.choice([w for w in WAKES if w!=want])})
    return out

def run_proc(stream,arm,home=None):
    ff=None;static={}
    if arm=='v13':
        from .fastforward import FastForward
        store,_=_store(Path(home));ff=FastForward(store);ff.set_mode('ACTIVE','EXPLICIT_HUMAN')
    cost=0.;wrong=[];after=[];sal=[];applied=0;N=len(stream)
    for ev in stream:
        sig={'novelty':.8} if ev['salient'] else {}
        use=None
        if arm=='v13':
            d=ff.procedural(ev['key'],sig)
            if d['apply']:use=d['wake']
        elif arm=='static_shortcut':
            s=static.get(ev['key'][0])  # a static shortcut keys on the surface pattern only (no salience bucket)
            if s and s['compiled']:use=s['compiled']
        if use is not None:wake=use;cost+=COST_PROC;applied+=1
        else:wake=ev['want'] if ev['delib_ok'] else ev['alt'];cost+=COST_DELIB
        ok=wake==ev['want'];wrong.append(not ok)
        if ev['t']>=N//2:after.append(not ok)
        if ev['salient']:sal.append(not ok)
        if arm=='v13':ff.record_turn(ev['key'],wake,'FINAL' if ok else 'FAILED',COST_PROC if use else COST_DELIB,applied=use is not None,predicted_fast_s=COST_PROC)
        elif arm=='static_shortcut' and use is None:
            s=static.setdefault(ev['key'][0],{'last':None,'run':0,'compiled':None})
            if ok:s['run']=s['run']+1 if s['last']==wake else 1;s['last']=wake
            else:s['run']=0
            if s['run']>=5:s['compiled']=wake
    if ff is not None:ff.s.close()
    return {'cost_per_turn':round(cost/N,4),'error_rate':round(_mean(wrong),4),'error_after_drift':round(_mean(after),4),
            'salient_error':round(_mean(sal),4) if sal else None,'fast_path_share':round(applied/N,4)}

# --- 4: Age plasticity ----------------------------------------------------------------------------------------------
PHASES=((0,400,'learn'),(400,1000,'noisy'),(1000,1500,'shift'));WINDOW=50
FIXED={'fixed_conservative':.45,'fixed_permissive':1.};AGE_ARMS=('age','age_stable','age_noise','age_no_reopen')+tuple(FIXED)

def age_stream(seed):
    rng=random.Random(seed);w=_vec(rng);w2=_vec(rng);out=[]
    for t in range(PHASES[-1][1]):
        phase=next(p for a,b,p in PHASES if a<=t<b);true=w2 if phase=='shift' else w
        x=[rng.gauss(0,1) for _ in range(DIM)];y=_dot(true,x)+rng.gauss(0,NOISE)
        if phase=='noisy':y=_dot(_vec(rng),x)*2 if rng.random()<.1 else _dot(true,x)+rng.gauss(0,1.)
        out.append({'t':t,'phase':phase,'x':x,'y':y,'w':true})
    return out

def run_age(stream,arm,home=None,lr=.3):
    ctl=None
    if arm in ('age','age_stable','age_noise','age_no_reopen'):
        from .age import AgeControl
        store,cfg=_store(Path(home));cfg['user_stage_cap']=5;cfg['age_plasticity_policy']={'age_stable':'stable_reopen','age_noise':'noise_aware'}.get(arm,'boot');ctl=AgeControl(store,cfg,build_ceiling=5)
    theta=[0.]*DIM;errs={p:[] for _,_,p in PHASES};prev_err=None;prev_theta=list(theta);fails=0;novel=True;p_used=[];stages=[]
    win=[]
    for ev in stream:
        if ctl:p=ctl.plasticity('language',novel_domain=novel,repeated_errors=0 if arm=='age_no_reopen' else fails)
        else:p=FIXED[arm]
        p_used.append(p);theta=_nlms(theta,ev['x'],ev['y'],lr*p);e=_err(theta,ev['w']);errs[ev['phase']].append(e);win.append(e)
        if (ev['t']+1)%WINDOW==0:
            err=_mean(win);win=[]
            novel=prev_err is not None and err>2*prev_err and err>.1
            passed=prev_err is None or err<=prev_err*1.1+.02;fails=0 if passed else fails+1
            if ctl:
                drift=math.sqrt(sum((a-b)**2 for a,b in zip(theta,prev_theta)))/max(1e-9,math.sqrt(_dot(theta,theta)))
                comp=max(0.,1-err)
                ctl.record('language',{'experience':ev['t']+1,'competence':comp,'stability':max(0.,1-drift),'retention':comp,'calibration':.8,
                                       'memory_health':.97,'safe_self_control':.999,'regression_pass':passed},evidence_id='ab-'+str(ev['t']))
                stages.append(ctl.state()[0]['capabilities']['language']['stage'])
            prev_err=err;prev_theta=list(theta)
    if ctl:ctl.s.close()
    return {'phase_error':{p:round(_mean(v),4) for p,v in errs.items() if v},'final_error':round(_err(theta,stream[-1]['w']),4),
            'mean_plasticity':{p:round(_mean(v),4) for p,v in ((p,[p_used[i] for i,ev in enumerate(stream) if ev['phase']==p]) for _,_,p in PHASES) if v},
            'max_stage':max(stages) if stages else None}

# --- driver -----------------------------------------------------------------------------------------------------------
def _agg(runs,path):
    vals=[]
    for r in runs:
        v=r
        for k in path:v=v[k]
        vals.append(v)
    return {'mean':round(_mean(vals),4),'sd':round(_sd(vals),4)}

def _summ(per_seed,keys):
    out={}
    for arm,runs in per_seed.items():out[arm]={'.'.join(k):_agg(runs,k) for k in keys}
    return out

def run_all(seeds=SEEDS,T=600,N=600,workdir=None):
    base=Path(workdir or tempfile.mkdtemp(prefix='ab99-'));credit={a:[] for a in dict.fromkeys(ELIG_ARMS+MOD_ARMS)}
    proc={a:[] for a in ('v13','full_deliberation','static_shortcut')};agep={a:[] for a in AGE_ARMS}
    for s in seeds:
        store,_=_store(base/('credit-'+str(s)));rows=record_gates(credit_stream(s,T),store);store.close()
        for a in credit:credit[a].append(run_credit(rows,a,s))
        ps=proc_stream(s,N)
        for a in proc:proc[a].append(run_proc(ps,a,base/('proc-'+a+'-'+str(s))))
        st=age_stream(s)
        for a in agep:agep[a].append(run_age(st,a,base/('age-'+a+'-'+str(s))))
    ck=[('mean_final',),('route_after_drift',),('budget',)]+[('final',p) for p in LEARN_PATHS]
    return {'kind':'ABLATION_99','seeds':list(seeds),'claim_limit':'synthetic open-loop streams, linear NLMS learners, no language model',
            'eligibility':{'arms':list(ELIG_ARMS),'summary':{a:v for a,v in _summ(credit,ck).items() if a in ELIG_ARMS}},
            'modulators':{'arms':list(MOD_ARMS),'summary':{a:v for a,v in _summ(credit,ck).items() if a in MOD_ARMS}},
            'proceduralization':{'summary':_summ(proc,[('cost_per_turn',),('error_rate',),('error_after_drift',),('salient_error',),('fast_path_share',)])},
            'age':{'summary':_summ(agep,[('phase_error','learn'),('phase_error','noisy'),('phase_error','shift'),('final_error',)]+[('mean_plasticity',p) for _,_,p in PHASES]),
                   'max_stage':{a:[r['max_stage'] for r in v] for a,v in agep.items()}},
            'raw':{'credit':credit,'proceduralization':proc,'age':agep}}
