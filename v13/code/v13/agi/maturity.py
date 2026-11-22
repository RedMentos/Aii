"""Age evidence feeder + stage estimate: turns the AG measurements into the metrics age.record() needs.

Until now nothing called AgeControl.record(), so no stage could ever be earned. collect() builds one
evidence record from what the system actually measured:
  experience        human-labelled experiences (feedback rows) + grounded outcomes (AG2)
  competence        AG12 overall score of the last complete run
  retention         Sleep A protected-old retention (fallback: 1 - AG12 forgetting rate)
  calibration       AG9 calibrated 1-ECE (system = worst of the known components)
  stability         share of the last AG12 runs without a drop > retention_max_delta
  memory_health     SQLite quick integrity check (1/0)
  safe_self_control share of own (SELF/SYSTEM) tool calls that were not DENIED
  regression_pass   last Sleep A without regression flag and no AG6 batch in GATE_FAIL
Missing measurements stay None, so the gate fails honestly instead of guessing.
estimate() says which gates block the next stage and how many days the experience part alone needs
at a given rate; it is an estimate, not a promise (BUILD_CEILING and user_stage_cap still bind).
"""
import math
import time
from ..age import GATES,METRICS,PROMOTE_AFTER

FEED_KEY='age_feed'
TURN_FEED_MIN_S=3600  # WP-T2 BOOT: at most one turn-driven evidence record per hour, and only after new experience

def collect(g,store,cfg):
    m={}
    fb=store.one('SELECT COUNT(*) AS n FROM feedback')['n']
    m['experience']=fb+len(g.grounding.samples(10**6))
    runs=[r for r in g.eval.box.load()[0]['runs'] if r['status']=='DONE']
    m['competence']=runs[-1]['summary']['overall'] if runs else None
    last=(store.state('SLEEP_LAST',None)[0] or {}).get('phases',[])
    a=next((p for p in last if p.get('phase')=='SLEEP_A'),{})
    fr=(runs[-1]['summary'].get('forgetting') or {}).get('rate') if runs else None
    m['retention']=a.get('retention_old') if a.get('retention_old') is not None else (None if fr is None else round(1-fr,4))
    cals=[g.metacog.age_metric(c) for c in g.metacog.box.load()[0]['components']]
    cals=[c for c in cals if c is not None];m['calibration']=min(cals) if cals else None
    delta=float(cfg.get('retention_max_delta',.02));ov=[r['summary']['overall'] for r in runs[-6:]]
    m['stability']=round(1-sum(b<a_-delta for a_,b in zip(ov,ov[1:]))/max(1,len(ov)-1),4) if len(ov)>=2 else None
    try:
        with store.mutex:ok=store.db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        m['memory_health']=1. if ok else 0.
    except Exception:m['memory_health']=None
    own=[c for c in g.tools.box.load()[0]['calls'] if c['origin']!='USER']
    m['safe_self_control']=round(sum(c['status']!='DENIED' for c in own)/len(own),4) if own else None
    gate_fail=any(b['status']=='GATE_FAIL' for b in g.weights.box.load()[0]['batches'].values())
    m['regression_pass']=(not a.get('regression_flag',False)) and not gate_fail if (a or runs) else None
    return m

def capability_metrics(g,m):
    """WP-T2 §17.4: evidence per capability from what each one is actually measured by; unmeasured ones get none.
    language/routing_skill: the AG12 run (all current tasks are language answers through C5 routes).
    memory_skill: Sleep A protected-old retention as its competence. tool: share of own executed tool calls that succeeded."""
    out={'language':dict(m),'routing_skill':dict(m)}
    if m.get('retention') is not None:out['memory_skill']=dict(m,competence=m['retention'])
    own=[c for c in g.tools.box.load()[0]['calls'] if c['origin']!='USER' and c['status'] in ('EXECUTED','FAILED')]
    if own:out['tool']=dict(m,competence=round(sum(c['status']=='EXECUTED' for c in own)/len(own),4))
    return out

def feed(g,origin,key,metrics=None):
    """One evidence record for system + each measured capability (ids are distinct, so a repeat key is not double counted)."""
    if g.age is None:return None
    m=collect(g,g.s,g.cfg) if metrics is None else metrics;base='age:'+origin+':'+str(key);out={'metrics':m,'recorded':{}}
    for subject,sm in [('system',m)]+list(capability_metrics(g,m).items()):
        try:r=g.age.record(subject,sm,base+(':'+subject if subject!='system' else ''));out['recorded'][subject]={'stage':r['stage'],'change':r['change'],'proposal':r.get('proposal'),'noise':r.get('noise')}
        except ValueError as exc:out['recorded'][subject]={'skipped':str(exc)[:120]}
    g.s.log('age_evidence',None,{'origin':origin,'key':str(key)[:64],'subjects':sorted(out['recorded'])})
    return out

def turn_feed(g,clock=time.time):
    """Live feed from turns: rate-limited, and only when new human/grounded experience arrived since the last record."""
    st=g.s.state(FEED_KEY,None)[0] or {'last':0.,'experience':-1,'n':0};now=clock()
    if now-float(st.get('last',0.))<TURN_FEED_MIN_S:return None
    m=collect(g,g.s,g.cfg)
    if (m.get('experience') or 0)<=int(st.get('experience',-1)):return None
    out=feed(g,'turn',int(now),m)
    g.s.set_state(FEED_KEY,{'last':now,'experience':m.get('experience') or 0,'n':int(st.get('n',0))+1})
    return out

def estimate(metrics,stage,experience_per_day=(10,30,100)):
    """What blocks stage+1, and days needed for the experience threshold at several daily rates."""
    target=stage+1
    if target>5:return {'target':None,'note':'Age 5 is the top; lifelong windows reopen per capability'}
    blockers={}
    for k in METRICS:
        need=GATES[k][target];have=metrics.get(k)
        if have is None or have<need:blockers[k]={'have':have,'need':need}
    if metrics.get('regression_pass') is not True:blockers['regression_pass']={'have':metrics.get('regression_pass'),'need':True}
    need_exp=GATES['experience'][target];have_exp=metrics.get('experience') or 0
    days={str(r):max(0,math.ceil((need_exp-have_exp)/r)) for r in experience_per_day}
    return {'target':target,'experience':{'have':have_exp,'need':need_exp,'days_at_rate':days},'blockers':blockers,
            'evidence_records_needed':PROMOTE_AFTER,'note':'Days cover only the experience count; quality gates usually dominate'}
