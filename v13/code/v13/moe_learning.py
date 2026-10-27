"""WP-BP3 / Z10: the §91 MoE update order as persisted, enforced state (STEP6C: router frozen, active expert deltas).

Canon §91: sparse routing does not protect the shared parts in front of the router (Z10a: 3/3 fresh fact sets, forgetting
starts before the router, expert updates forget 7-18x less in layers 8-9). The update order is therefore

   A  router + shared trunk frozen; small predictor/projector/delta only
   B  active-expert delta in SHADOW with route monitor and old-task retention      (Z10b measured this)
   C  selected router adaptation in SHADOW; only with missed-routing evidence
   D  selected shared update; rare; only with a proven pre-router bottleneck

This module keeps that order as state and refuses jobs that break it. It decides and records; it never loads or trains
weights (the cloud script ``z10b_expert_delta.py`` and later the phone trainer produce the measured report).

- ``check_job(groups)``  a training job names the groups it moves (expert_delta|predictor|projector|router|shared|base).
                        router/shared/base are refused before their phase is allowed; router never moves with anything else.
- ``record_delta``       a measured expert-delta report becomes DELTA_SHADOW_OK or DELTA_REJECTED. Needs: it learned, old-task
                        loss within the cap, the B3-H6 router gate PASS against the receiver-native calibration, and an exact
                        rollback (delta off gives the old-task loss back).
- ``commit``             §91: a hit expert only creates eligibility; a commit needs error + typed modulator + permission +
                        retention. A committed delta stays a reversible L4 delta (``rollback`` always possible).
Mode ``moe_expert_delta`` off|shadow|active (default shadow): shadow records and judges, active additionally lets ``commit``
reach COMMITTED. Without an installed sparse-MoE body nothing can be recorded (the BOOT bodies are dense; see bodies.py).
Claim limit: evidence level is whatever the report says (Z10b: Linux cloud CPU fp32, not llama.cpp, not Redmi).
"""
import importlib.util
from pathlib import Path
from .agi.base import StateBox
from .common import uid

KEY='WP_BP3_MOE_LEARNING';REVISION='v13-moe-learning-v1'
GROUPS=('predictor','projector','expert_delta','router','shared','base')
PHASE_OF={'predictor':'A','projector':'A','expert_delta':'B','router':'C','shared':'D','base':'D'}
MODES=('off','shadow','active')
MAX_OLD_TASK_DELTA=.2        # BOOT nats; B3 old-task cap for a delta (Z10a experts arm forgot .33-.43 when trained in full)
MIN_LEARNED=.2               # new-task loss must end at or below this share of its start
ROLLBACK_TOL=1e-6            # |loss with delta removed - loss before| in nats

_MON=[]
def monitor():
    """The NumPy monitor of the N11 candidate (scripts/moe_router_monitor.py), loaded once by path."""
    if not _MON:
        p=Path(__file__).resolve().parents[1]/'scripts'/'moe_router_monitor.py'
        spec=importlib.util.spec_from_file_location('v13_moe_router_monitor',p);m=importlib.util.module_from_spec(spec)
        import sys;sys.modules.setdefault('v13_moe_router_monitor',m);spec.loader.exec_module(m);_MON.append(m)
    return _MON[0]

def select_experts(hit_counts,k):
    """Active experts of one layer: the k with the most router top-k hits on the new data (ties: lower index first)."""
    order=sorted(range(len(hit_counts)),key=lambda e:(-hit_counts[e],e))
    return sorted(order[:max(0,int(k))])

class MoELearning:
    def __init__(self,store,mode='shadow'):
        if mode not in MODES:raise ValueError('moe_expert_delta: off|shadow|active')
        self.mode=mode
        self.box=StateBox(store,KEY,REVISION,lambda:{'deltas':{},'evidence':{},'log':[]})
    # -- evidence and phases ------------------------------------------------------------------------
    def evidence(self):
        st=self.box.load()[0];ev=dict(st['evidence'])
        ok=[d for d in st['deltas'].values() if d['status'] in ('DELTA_SHADOW_OK','COMMITTED')]
        ev['route_monitor_active']=ev.get('route_monitor_active',False) or bool(st['deltas'])
        ev['phase_a_retention_ok']=bool(ev.get('phase_a_retention_ok'))
        ev['retention_ok']=bool(ev.get('retention_ok')) or bool(ok)
        return ev
    def set_evidence(self,**kw):
        """Evidence from other parts (phase A retention from a predictor/projector run, missed-routing proof, an
        ``interference_report`` verdict of PRE_ROUTER_BOTTLENECK). Only known keys."""
        known={'phase_a_retention_ok','route_monitor_active','retention_ok','missed_routing','pre_router_bottleneck'}
        bad=set(kw)-known
        if bad:raise ValueError('unknown evidence '+','.join(sorted(bad)))
        self.box.mutate(lambda st:st['evidence'].update(kw))
    def phase(self,p):return monitor().phase_allowed(p,self.evidence())
    def check_job(self,groups):
        """(allowed, reasons). Refuses a job that moves a group before its phase, and the router together with anything."""
        groups=list(groups);why=[]
        for g in groups:
            if g not in GROUPS:why.append('unknown group '+str(g))
        if why:return False,why
        if 'router' in groups and len(set(groups))>1:why.append('router never moves jointly with another group (B3-H8)')
        for g in sorted(set(groups)):
            p=PHASE_OF[g]
            if p=='A':continue
            if self.mode=='off':why.append(g+': mode off')
            ph=self.phase(p)
            if not ph['allowed']:why.append('%s needs phase %s: %s'%(g,p,', '.join(ph['missing'])))
            elif p!='B':why.append(g+': phase %s is SHADOW only, never an active update'%p)
        return not why,why
    # -- deltas -------------------------------------------------------------------------------------
    def record_delta(self,report,calibration):
        """report keys: window, arm, rank, k, delta_params, new_task_loss_start/_end, old_task_loss_delta,
        rollback_removed_delta, router (aggregate dict: router_kl, topk_flip_rate, router_input_norm_shift,
        residual_norm_shift), body (model id + revision). Returns the stored record."""
        m=monitor();why=[]
        if self.mode=='off':raise PermissionError('moe_expert_delta is off')
        for key in ('window','new_task_loss_start','new_task_loss_end','old_task_loss_delta','rollback_removed_delta','router','body'):
            if report.get(key) is None:why.append('missing '+key)
        gate={'verdict':'NOT_RUN','reasons':[]}
        if not why:
            if report['new_task_loss_end']>MIN_LEARNED*report['new_task_loss_start']:why.append('did not learn the new data')
            if abs(report['rollback_removed_delta'])>ROLLBACK_TOL:why.append('rollback not exact')
            gate=m.router_stability_gate(report['router'],calibration,old_task_loss_delta=report['old_task_loss_delta'],
                                         max_old_task_loss_delta=MAX_OLD_TASK_DELTA)
            if gate['verdict']!='PASS':why+=['router/retention gate: '+r for r in gate['reasons']]
        rec={'id':uid('moed'),'status':'DELTA_REJECTED' if why else 'DELTA_SHADOW_OK','why':why,'gate':gate['verdict'],
             'arm':report.get('arm'),'window':report.get('window'),'rank':report.get('rank'),'k':report.get('k'),
             'delta_params':report.get('delta_params'),'body':report.get('body'),'old_task_loss_delta':report.get('old_task_loss_delta'),
             'evidence_level':report.get('evidence_level','unspecified')}
        def f(st):
            st['deltas'][rec['id']]=rec;st['log'].append({'event':'record','id':rec['id'],'status':rec['status']});del st['log'][:-200]
        self.box.mutate(f);return rec
    def commit(self,delta_id,*,eligible,error,modulator,permission):
        """§91 weight commit for a SHADOW_OK delta. In shadow mode a passing request is reported as WOULD_COMMIT only."""
        d=self.box.load()[0]['deltas'].get(delta_id)
        if d is None:raise KeyError(delta_id)
        retention_ok=d['status'] in ('DELTA_SHADOW_OK','COMMITTED')
        ok=monitor().expert_commit_allowed(eligible,error,modulator,permission,retention_ok)
        if not ok['commit']:return {'commit':False,'status':d['status'],'missing':ok['missing']}
        if self.mode!='active':return {'commit':False,'status':d['status'],'missing':[],'would_commit':True,'mode':self.mode}
        def f(st):
            st['deltas'][delta_id]['status']='COMMITTED';st['log'].append({'event':'commit','id':delta_id})
        self.box.mutate(f);return {'commit':True,'status':'COMMITTED','missing':[]}
    def rollback(self,delta_id):
        """Always allowed: a delta is a reversible L4 change (adapter off / removed)."""
        def f(st):
            d=st['deltas'].get(delta_id)
            if d is None:raise KeyError(delta_id)
            d['status']='ROLLED_BACK';st['log'].append({'event':'rollback','id':delta_id})
        self.box.mutate(f)
    def report(self):
        st=self.box.load()[0]
        return {'mode':self.mode,'evidence':self.evidence(),'phases':{p:self.phase(p)['allowed'] for p in monitor().PHASES},
                'deltas':{k:{x:v[x] for x in ('status','arm','window','gate','old_task_loss_delta')} for k,v in st['deltas'].items()}}
