"""Adaptive reasoning effort and selective body-wake policy (G5B, §10.2, §59, §61).

``reasoning_effort`` in [0,1] budgets real per-turn compute, not answer length:
body wake ``none|detail|gist|both``, B re-entry, focal coalition slots, observer
time and verify requests. Gains and bands are the blueprint's BOOT values (§59),
not learned or Redmi-measured. Hard deadline, resource guard, observer switch and
Age permissions always bind; a user override is honoured only inside them.

Claim limits: no separate verifier, tool or long-context restore runner exists
yet. ``verify``/``focal_cycles``/``tool_steps`` are recorded budgets; the only
executed extra cycle is the existing B1 re-entry.
"""
import json
import re
from .common import dumps
from .contracts import packet
from . import resource_modes as rmodes

MODES=('disabled','low','adaptive','high','max','detail','gist')
FIXED={'disabled':0.,'low':.15,'high':.70,'max':.95,'detail':.70,'gist':.70}
# WP-Z6e §24.22 'A only' / 'B only': user-forced single body (B1 detail or B2 gist) at the 'high' budget; limits still bind
ONE_BODY_MODES=('detail','gist')
WAKES=('none','detail','gist','both')
BOOT={'default':.25,'conflict_gain':.60,'uncertainty_gain':.55,'novelty_gain':.40,'salience_gain':.35,
      'escalate_uncertainty':.45,'escalate_conflict':.40,'escalate_floor':.50,'verify_risk':.65,
      'one_body_need':.35,'min_body_seconds':2.,'max_cycles_age0':3}
# Age (§17.5) bounds *autonomous* escalation via age.budgets()['autonomous_effort_max'].
# BOOT mapping to effort ceilings: Age-0 'low' keeps the proven scaffold-driven
# B1/B2 wake (STEP2) but blocks autonomous DEEP_FOCAL. A user-forced mode is not
# autonomous; it is still bound by Age rights (deliberation, tools, focal depth).
AUTONOMOUS_CEILING={'disabled':.19,'low':.79,'adaptive':.79,'high':.95,'max':1.}
RESOURCE_MODE=rmodes.LEGACY_MODE  # §97.2: one table (PRESSURE = ORANGE, CRITICAL = RED)
BANDS=((.2,'DIRECT_C_NATIVE'),(.5,'C_NATIVE_ONE_BODY'),(.8,'FOCAL_TARGETED'),(1.01,'DEEP_FOCAL'))
STATE_KEY='REASONING_EFFORT_MODE'
DETAIL=re.compile(r'code|python|berechn|calculate|budget|mathe|debug|fehler|exakt|genau|zahl|\d\s*[+*/=-]\s*\d|wie viel|wann|wer ',re.I)
GIST=re.compile(r'zusammenfass|summary|summari|überblick|plan|kontext|strategie|warum|erklär',re.I)
CONFLICT=re.compile(r'vergleich|compare|abwäg|trade.?off|widerspr|aber |oder |stimmt das|wirklich',re.I)
SALIENT=re.compile(r'dringend|wichtig|achtung|sofort|gefahr|sicher\?|beweis|gründlich|schritt für schritt|think hard|ausführlich',re.I)
WORD=re.compile(r'\w{4,}',re.U)

def clip(x):return max(0.,min(1.,float(x)))
def band(effort):return next(name for limit,name in BANDS if effort<limit)
def roles(wake):return {'none':[],'detail':['B1_DETAIL'],'gist':['B2_GIST'],'both':['B1_DETAIL','B2_GIST']}[wake]
def cap_wake(wake,ceiling,prefer='detail'):
    """Largest subset of ``wake`` that fits a ceiling (both > one body > none); ``one`` = any single body."""
    if ceiling=='both' or wake=='none':return wake
    if ceiling=='none':return 'none'
    if ceiling=='one':return prefer if wake=='both' else wake
    if wake=='both':return ceiling
    return wake if wake==ceiling else 'none'

def signals(text,route='simple',route_info=None,memories=(),prior_goals=(),open_questions=0):
    """Cheap pre-wake state features; every value in [0,1] with its reason."""
    info=route_info or {};words=set(w.lower() for w in WORD.findall(text));seen=set()
    for goal in prior_goals:seen|=set(w.lower() for w in WORD.findall(goal))
    new=words-seen;novelty=clip(len(new)/12)*(1. if words else 0.)
    best=max([m.get('retrieval_score') or 0. for m in memories],default=0.)
    if best:novelty*=1-clip(best)*.6
    source=info.get('source','BOOT_SCAFFOLD')
    if source=='APPROVED_SOURCE_BOUND_PROCEDURE':novelty*=.3
    if source=='APPROVED_EXTERNAL_HEAD':uncertainty=clip(1-(info.get('decision') or {}).get('margin',0.)*4)*.5
    elif source in {'APPROVED_SOURCE_BOUND_PROCEDURE','OPERATOR_ROUTE_OVERRIDE'}:uncertainty=.1
    else:uncertainty=.2+(.15 if info.get('control_unavailable') or info.get('native_control_rejected') else 0.)
    uncertainty+=min(.45,.15*open_questions)+(.15 if len(text)>800 else 0.)
    conflict=(.5 if route=='both' or CONFLICT.search(text) else 0.)+(.3 if any(m.get('scope') for m in memories) and route!='simple' else 0.)
    proposals=(info.get('scaffold'),route)
    if info.get('source')=='NATIVE_C2_ADVISORY' and proposals[0]!=proposals[1]:conflict+=.3
    salience=clip(.5*len(SALIENT.findall(text))+.1*max(0,text.count('?')-1))
    risk=clip((.7 if DETAIL.search(text) or route=='detail' else .2)+(.1 if open_questions else 0.))
    detail_need=clip((.6 if route in {'detail','both'} else 0.)+(.4 if DETAIL.search(text) else 0.))
    gist_need=clip((.6 if route in {'gist','both'} else 0.)+(.3 if GIST.search(text) else 0.)+(.3 if len(text)>600 else 0.))
    return {k:round(clip(v),4) for k,v in dict(novelty=novelty,uncertainty=uncertainty,conflict=conflict,salience=salience,
            epistemic_risk=risk,detail_need=detail_need,gist_need=gist_need).items()}|{'route_hint':route,'route_source':source}

def adaptive_effort(sig,p=BOOT):
    e=p['default']+p['conflict_gain']*sig['conflict']+p['uncertainty_gain']*sig['uncertainty']+p['novelty_gain']*sig['novelty']+p['salience_gain']*sig['salience']
    # The BOOT baseline already sits inside the one-body band; signals only add.
    e-=p['default']*(1-max(sig['conflict'],sig['uncertainty'],sig['novelty'],sig['salience'],sig['detail_need'],sig['gist_need']))
    if sig['uncertainty']>p['escalate_uncertainty'] or sig['conflict']>p['escalate_conflict']:e=max(e,p['escalate_floor'])
    return round(clip(e),4)

def plan_for(effort,sig,p=BOOT):
    """Map effort to concrete compute budgets (§10.2 boot bands)."""
    b=band(effort);one='detail' if sig['detail_need']>=sig['gist_need'] else 'gist';need=max(sig['detail_need'],sig['gist_need'])
    if b=='DIRECT_C_NATIVE':wake,reentry,cycles,slots,scale='none',0,0,1,0.
    elif b=='C_NATIVE_ONE_BODY':wake,reentry,cycles,slots,scale=(one if need>=p['one_body_need'] or sig['uncertainty']>p['escalate_uncertainty'] else 'none'),0,1,2,.6
    elif b=='FOCAL_TARGETED':
        both=min(sig['detail_need'],sig['gist_need'])>=p['one_body_need'] or sig['conflict']>p['escalate_conflict']
        wake='both' if both else one;reentry=1 if wake=='both' and (sig['conflict']>p['escalate_conflict'] or sig['uncertainty']>p['escalate_uncertainty']) else 0;cycles,slots,scale=2,3,.85
    else:wake,reentry,cycles,slots,scale='both',2,p['max_cycles_age0'],4,1.  # WP-T1: up to 2 goal-directed re-entries, focal stops on a stable trajectory
    return {'effort':effort,'band':b,'wake':wake,'one_body':one,'max_reentry':reentry,'focal_cycles':cycles,'focal_slots':slots,'observer_scale':scale,
            'verify':bool(b!='DIRECT_C_NATIVE' and (sig['epistemic_risk']>p['verify_risk'] and effort>=.5 or b=='DEEP_FOCAL')),'tool_steps':1 if b=='DEEP_FOCAL' else 0}

def age_limits(control,resource_state='NORMAL'):
    """Read Age rights/budgets from v13.age (WP-C); this module invents none."""
    mode=rmodes.as_mode(resource_state);b=control.budgets('system',mode)
    return {'stage':control.ceiling('system'),'autonomous_effort_max':b['autonomous_effort_max'],'focal_depth':int(b['focal_depth']),
            'deliberation':control.may('deliberation_modes',resource_mode=mode),'tools':control.may('simple_tool_choice',resource_mode=mode),
            'long_loops':control.may('long_loops',resource_mode=mode),'resource_mode':mode}  # WP-T2: each right at its capability's ceiling
AGE0={'stage':0,'autonomous_effort_max':'low','focal_depth':1,'deliberation':False,'tools':False,'long_loops':False,'resource_mode':'UNKNOWN'}

def constrain(plan,*,direct=False,observers=True,resource_state='NORMAL',resource_mode=None,observer_window_s=None,cfg=None,age=None,p=BOOT):
    """Hard limits that no mode, override or learned readout may exceed."""
    plan=dict(plan);cfg=cfg or {};age=age or AGE0;why=[];ceiling='both'
    if direct:plan.update(effort=0.,band='DIRECT_C_NATIVE');ceiling='none';why.append('EXACT_OR_FIXED_OUTPUT')
    if not observers:ceiling='none';why.append('OBSERVERS_OFF')
    rmode=rmodes.as_mode(resource_mode or resource_state);rpol=rmodes.POLICY[rmode]  # §97.2 resource modes
    if rmode!='GREEN':why.append('RESOURCE_'+rmode)
    if rpol['max_observer_bodies']==0:ceiling='none'
    elif rpol['max_observer_bodies']==1 and ceiling=='both':ceiling='one';why.append('RESOURCE_ONE_BODY')
    if rpol['focal_cycles_max'] is not None and plan['focal_cycles']>rpol['focal_cycles_max']:plan['focal_cycles']=rpol['focal_cycles_max'];why.append('RESOURCE_FOCAL_DEPTH')
    if rpol['observer_depth']<1:plan['observer_scale']=round(plan['observer_scale']*rpol['observer_depth'],4)
    if observer_window_s is not None and ceiling!='none':
        fits=int(observer_window_s//max(p['min_body_seconds'],1e-9))
        if fits<1:ceiling='none';why.append('DEADLINE_NO_BODY')
        elif fits<2 and plan['wake']=='both':ceiling='one';why.append('DEADLINE_ONE_BODY')
    if plan['max_reentry']>cfg.get('max_reentry',1):plan['max_reentry']=cfg.get('max_reentry',1);why.append('CFG_MAX_REENTRY')
    if plan['focal_slots']>cfg.get('focal_slots',8):plan['focal_slots']=cfg['focal_slots'];why.append('CFG_FOCAL_SLOTS')
    depth=min(age['focal_depth'],p['max_cycles_age0']) if age['stage']==0 else age['focal_depth']
    if plan['focal_cycles']>depth:plan['focal_cycles']=depth;why.append('AGE_FOCAL_DEPTH')
    if plan['tool_steps'] and not age['tools']:plan['tool_steps']=0;why.append('AGE_NO_TOOLS')
    if plan['verify'] and not age['deliberation']:plan['verify']=False;why.append('AGE_NO_DELIBERATION_MODES')
    capped=cap_wake(plan['wake'],ceiling,plan.get('one_body','detail'))
    if capped!=plan['wake']:plan['wake']=capped
    if plan['wake']!='both':plan['max_reentry']=0
    if ceiling=='none':plan.update(verify=False,observer_scale=0.)
    plan['wake_ceiling']=ceiling;plan['constraints']=why;plan['age_stage']=age['stage'];return plan

def decide(mode,sig,**limits):
    if mode not in MODES:raise ValueError('effort mode: '+'|'.join(MODES))
    effort=adaptive_effort(sig) if mode=='adaptive' else FIXED[mode];requested=effort;age=limits.get('age') or AGE0
    if mode=='adaptive' and effort>AUTONOMOUS_CEILING[age['autonomous_effort_max']]:effort=AUTONOMOUS_CEILING[age['autonomous_effort_max']]
    plan=plan_for(effort,sig)
    if mode in ONE_BODY_MODES:plan.update(wake=mode,one_body=mode,max_reentry=0)
    plan=constrain(plan,**limits);plan['mode']=mode;plan['requested_effort']=requested
    if effort<requested:plan['constraints'].insert(0,'AGE_AUTONOMOUS_EFFORT_MAX_'+age['autonomous_effort_max'].upper())
    plan['learned_wake_allowed']=mode=='adaptive';return plan

def resolve_wake(plan,learned=None):
    """A learned wake readout may choose only inside the effort ceiling.

    A user-forced mode keeps its own wake decision; the ceiling always binds.
    """
    if learned is None or not plan['learned_wake_allowed']:return plan['wake'],'EFFORT_POLICY'
    if learned not in WAKES:raise ValueError('wake action')
    # The hard resource/deadline ceiling is not the effort budget. A low
    # adaptive turn can have resource headroom for two bodies while its
    # DIRECT_C_NATIVE / C_NATIVE_ONE_BODY band forbids that compute.
    effort_ceiling={'DIRECT_C_NATIVE':'none','C_NATIVE_ONE_BODY':'one',
                    'FOCAL_TARGETED':'both','DEEP_FOCAL':'both'}.get(plan['band'])
    if effort_ceiling is None:raise ValueError('unknown effort band')
    prefer=plan.get('one_body','detail')
    within_effort=cap_wake(learned,effort_ceiling,prefer)
    capped=cap_wake(within_effort,plan['wake_ceiling'],prefer)
    return capped,'LEARNED_WAKE' if capped==learned else 'LEARNED_WAKE_CAPPED'

def get_mode(store):
    value,_=store.state(STATE_KEY,{'mode':'adaptive'});return value.get('mode','adaptive') if value.get('mode') in MODES else 'adaptive'
def set_mode(store,mode):
    if mode not in MODES:raise ValueError('effort mode: '+'|'.join(MODES))
    store.set_state(STATE_KEY,{'mode':mode});return mode

def record(store,e,plan,sig,wake,wake_source):
    """Per-turn telemetry: one EffortDecision packet plus a telemetry row."""
    body={k:plan[k] for k in ['band','max_reentry','focal_cycles','focal_slots','observer_scale','verify','tool_steps','wake_ceiling','requested_effort','age_stage']}
    p=packet('EffortDecision','C4_FOCAL',e['event_id'],e['brain_generation_id'],[e['source_ref']],mode=plan['mode'],effort=float(plan['effort']),
             wake=wake,wake_source=wake_source,plan=body,signals=sig,constraints=list(plan['constraints']),parameter_status='BOOT_HEURISTIC_NOT_LEARNED')
    store.add_packet('EffortDecision',p)
    store.log('reasoning_effort',e['event_id'],{'mode':plan['mode'],'effort':plan['effort'],'band':plan['band'],'wake':wake,'wake_source':wake_source,'constraints':plan['constraints']})
    return p

def summary(store,limit=200):
    """§24.22/24.23 runtime counters over recent turns (no quality claim)."""
    rows=store.rows("SELECT payload FROM packets WHERE kind='EffortDecision' ORDER BY rowid DESC LIMIT ?",(limit,))
    items=[json.loads(r['payload']) for r in rows];n=len(items)
    bands={};wakes={}
    for x in items:bands[x['plan']['band']]=bands.get(x['plan']['band'],0)+1;wakes[x['wake']]=wakes.get(x['wake'],0)+1
    return {'mode':get_mode(store),'turns':n,'bands':bands,'wakes':wakes,
            'body_wake_rate':round(sum(len(roles(x['wake'])) for x in items)/n,4) if n else None,
            'mean_effort':round(sum(x['effort'] for x in items)/n,4) if n else None,
            'constrained_turns':sum(1 for x in items if x['constraints']),'parameters':BOOT,'status':'BOOT_HEURISTIC_NOT_LEARNED'}

def compare(cases,cost={'detail':1.,'gist':1.,'reentry':.5,'verify':.25}):
    """Offline policy check over labelled signal cases (§24.23 shape).

    ``cases`` are dicts with ``signals`` and ``need`` (a WAKES label). Quality is
    only "needed bodies woken"; this is a scaffold self-check, not model quality.
    """
    out={}
    for mode in ('low','high','max','adaptive'):
        miss=over=0;spent=0.;hard=easy=0
        for c in cases:
            plan=decide(mode,c['signals']);need=set(roles(c['need']));got=set(roles(plan['wake']))
            spent+=sum(cost['detail' if r=='B1_DETAIL' else 'gist'] for r in got)+cost['reentry']*plan['max_reentry']+cost['verify']*plan['verify']
            if need:hard+=1;miss+=not need<=got
            else:easy+=1;over+=bool(got)
        out[mode]={'hard_task_underthinking':round(miss/hard,4) if hard else None,'easy_task_overthinking':round(over/easy,4) if easy else None,'mean_cost':round(spent/len(cases),4) if cases else None}
    return out
