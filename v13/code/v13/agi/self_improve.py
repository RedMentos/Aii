"""WP-AG8 self-improvement: an outer loop outside the live system, always behind the human.

V13 (or the user) proposes a change to knobs (config.KNOBS) or learning rules (sleep policy).
The change is evaluated in a sandbox: the caller's evaluator runs the AG12 suite with the
candidate settings on a copy, never on the live runtime. The regression shield compares
candidate vs base on every axis; only a change that regresses nothing and improves
something becomes a PENDING request. Applying it is a human act (approve + apply).
Never proposable: hard rules, Age caps/stages, learning_mode, latents, output channel.
WP-HX1: kind 'harness' edits allow-listed text/rule data around frozen weights (agi/harness.py); the
approved settings go to HarnessLibrary.apply(), which keeps the rollback point. Safety/moral texts never.
Structural changes (new body, architecture) are recorded only and need the Age right
structural_modification (Age 5), the structural unlock and the user — they are never
executed here. Generation manifests keep the rollback point.
"""
import copy
import time
from .base import StateBox,age_allows

KEY='G8_SELF_IMPROVEMENT';REVISION='g8-self-improve-v1'
KINDS=('knob','learning_rule','harness','structural')
FORBIDDEN={'system_stage','user_stage_cap','learning_mode','latents_enabled','channel','teacher_enabled','schema_version','seed','route_override'}
MIN_GAIN=.01  # BOOT: smallest improvement worth a human's attention
AXES=('overall','seen','unseen')

class SelfImprovement:
    def __init__(self,store,cfg,age=None,clock=time.time):
        self.s=store;self.cfg=cfg;self.age=age;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'proposals':{},'seq':0})
    def _candidate(self,kind,diff):
        if kind=='knob':
            from ..config import KNOBS,validate
            bad=[k for k in diff if k in FORBIDDEN or k not in KNOBS]
            if bad:raise PermissionError('Nicht vorschlagbar: '+', '.join(sorted(bad)))
            cand=copy.deepcopy(self.cfg)|diff;validate(cand);return cand
        if kind=='learning_rule':
            from ..sleep import default_policy,validate_policy,LOCKED
            if set(diff)&set(LOCKED):raise PermissionError('Gesperrte Lernregel')
            base=self.s.state('SLEEP_POLICY',None)[0] or default_policy()
            cand=copy.deepcopy(base)|diff;validate_policy(cand);return cand
        if kind=='harness':
            from .harness import candidate
            return candidate(diff)
        return None
    def propose(self,kind,diff,rationale='',origin='SELF'):
        if kind not in KINDS:raise ValueError('kind '+'|'.join(KINDS))
        if origin!='USER' and not age_allows(self.age,'propose_config_changes',origin):raise PermissionError('Eigene Vorschläge erst ab Age-Recht propose_config_changes')
        if kind=='structural' and not (self.age and self.age.allowed('structural_modification')):
            status='RECORDED_LOCKED'  # recorded for the human, never evaluated or executed
        else:status='PROPOSED';self._candidate(kind,diff)
        def f(st):
            st['seq']+=1;pid=f'imp_{st["seq"]}'
            st['proposals'][pid]={'id':pid,'kind':kind,'diff':diff,'rationale':str(rationale)[:500],'origin':origin,'status':status,
                                  'created':self.clock(),'base_generation':self.s.generation_id,'shield':None,'request_id':None}
            return pid
        return self.box.mutate(f)
    def evaluate(self,pid,evaluator):
        """evaluator(settings_or_None) -> AG12 summary; None = base. Runs both, applies the regression shield."""
        p=self.get(pid)
        if p['status']!='PROPOSED':raise ValueError('Nur PROPOSED wird geprüft')
        cand=self._candidate(p['kind'],p['diff'])
        base=evaluator(None);new=evaluator(cand)
        delta=float(self.cfg.get('retention_max_delta',.02));axes={}
        for a in AXES:
            b,c=base.get(a),new.get(a)
            axes[a]={'base':b,'candidate':c,'delta':None if b is None or c is None else round(c-b,4)}
        regress=[a for a,v in axes.items() if v['delta'] is not None and v['delta']<-delta]
        bf,cf=(base.get('forgetting') or {}).get('rate'),(new.get('forgetting') or {}).get('rate')
        if bf is not None and cf is not None and cf>bf+delta:regress.append('forgetting')
        gain=max([v['delta'] for v in axes.values() if v['delta'] is not None],default=0.)
        ok=not regress and gain>=MIN_GAIN
        def f(st):
            q=st['proposals'][pid];q['shield']={'axes':axes,'regressions':regress,'gain':gain,'passed':ok}
            if ok:
                q['request_id']=self.s.request('SELF_IMPROVEMENT',{'proposal':pid,'kind':q['kind'],'diff':q['diff'],'shield':q['shield']})
                q['status']='PENDING_USER'
            else:q['status']='SHIELD_FAIL'
            return dict(q)
        return self.box.mutate(f)
    def approve(self,pid):
        """Human only. Returns the new settings; the caller persists them (config.save_config / sleep set_policy / HarnessLibrary.apply)."""
        def f(st):
            q=st['proposals'][pid]
            if q['status']!='PENDING_USER':raise ValueError('Freigabe nur für PENDING_USER')
            if q['base_generation']!=self.s.generation_id:raise ValueError('Generation hat sich geändert; neu prüfen')
            q['status']='APPROVED';q['approved']=self.clock()
            if q['request_id']:
                with self.s.tx() as c:c.execute("UPDATE requests SET status='APPROVED' WHERE id=?",(q['request_id'],))
            return dict(q)
        q=self.box.mutate(f);return {'proposal':q,'settings':self._candidate(q['kind'],q['diff'])}
    def reject(self,pid):
        def f(st):st['proposals'][pid]['status']='REJECTED'
        self.box.mutate(f)
    def get(self,pid):
        p=self.box.load()[0]['proposals'].get(pid)
        if p is None:raise KeyError(pid)
        return p
    def report(self):
        ps=list(self.box.load()[0]['proposals'].values())
        return {'revision':REVISION,'proposals':[{k:p[k] for k in ('id','kind','status','origin')} for p in ps[-16:]],
                'self_proposals_allowed':age_allows(self.age,'propose_config_changes','SELF'),
                'claim_limit':'Knob/learning-rule/harness proposals with sandbox shield and human approval; structural changes recorded only'}
