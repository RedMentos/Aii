"""WP-AG2 grounded world model: predict the consequence of own actions, then compare with reality.

Every action (tool call, effector, later camera/audio-driven acts) gives a triple
(context, action, predicted outcome) and later the actual outcome. The grounded error is
the M_world signal (Layer 6) and the training target for World-JEPA (§7.2, L4.6) — stronger
than self-assessment. The baseline predictor here is a frequency model per (action kind,
context key); a learned latent predictor plugs in through the same predict()/update()
contract. Modalities register as sources; camera/audio/effectors stay off until STEP8.
Blueprint §7.2: the world model is not a fourth body but state + predictors on A/B/C; §7.2.1 objectives
(forward, inverse, state-align, outcome) map onto predict()/samples(); §7.2.2: every prediction carries
action/state coverage, a self-caused vs external tag and a counterfactual confidence. Prediction ≠ causality:
counterfactual() answers are always tagged SIMULATION and never become fact.
"""
import math
import time
from ..common import dumps
from .base import StateBox,new_id

KEY='G2_GROUNDING';REVISION='g2-grounding-v1'
MODALITIES={'text':True,'tool':True,'screen':False,'camera':False,'audio':False,'effector':False}  # A-plane ports (§4A); off until STEP8
HISTORY=512;MAX_KEYS=1024
STEP8_GATED=frozenset({'screen','camera','audio','effector'})

class FrequencyPredictor:
    """Baseline: most frequent outcome per (kind, context_key); confidence = its share. Not a world model."""
    def __init__(self,table):self.t=table
    def predict(self,kind,ctx):
        h=self.t.get(kind+'|'+ctx) or {}
        n=sum(h.values())
        if not h:return {'outcome':None,'confidence':0.,'coverage':0}
        o=max(h,key=h.get);return {'outcome':o,'confidence':round(h[o]/n,4),'coverage':n}
    def update(self,kind,ctx,outcome):
        k=kind+'|'+ctx;h=self.t.setdefault(k,{});h[outcome]=h.get(outcome,0)+1
        if len(self.t)>MAX_KEYS:self.t.pop(next(iter(self.t)))

def outcome_key(v):
    """Discrete outcome label for comparison: status plus a short value digest."""
    if isinstance(v,dict):return str(v.get('status','?'))+':'+dumps(v.get('result'))[:64]
    return dumps(v)[:80]

class Grounding:
    def __init__(self,store,clock=time.time):
        self.s=store;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'open':{},'closed':[],'table':{},'modalities':dict(MODALITIES),'errors':{}})
    def expect(self,kind,context_key,action,modality='text',predicted=None):
        """Before acting: store the prediction (from a supplied model or the baseline)."""
        st=self.box.load()[0]
        if not st['modalities'].get(modality):raise PermissionError('Modalität aus: '+modality)
        pred=predicted if predicted is not None else FrequencyPredictor(st['table']).predict(kind,context_key)
        aid=new_id('ground')
        def f(st):
            # The modality may have been disabled after the initial prediction read.
            # Recheck against the state used by the optimistic SQLite write.
            if not st['modalities'].get(modality):raise PermissionError('Modalität aus: '+modality)
            st['open'][aid]={'id':aid,'kind':kind,'ctx':context_key,'action':action,'modality':modality,'predicted':pred,'created':self.clock()}
            if len(st['open'])>HISTORY:st['open'].pop(next(iter(st['open'])))
        self.box.mutate(f);return aid,pred
    def observe(self,aid,actual,cause='SELF'):
        """After acting: grounded error = predicted outcome != actual; updates the baseline and per-kind error rate."""
        key=outcome_key(actual)
        def f(st):
            o=st['open'].pop(aid,None)
            if o is None:raise ValueError('Unbekannte Erwartung')
            p=o['predicted'] or {};err=0. if p.get('outcome')==key else 1.
            FrequencyPredictor(st['table']).update(o['kind'],o['ctx'],key)
            e=st['errors'].setdefault(o['kind'],{'n':0,'err':0.});e['n']+=1;e['err']+=err
            if cause not in ('SELF','EXTERNAL','UNKNOWN'):raise ValueError('cause SELF|EXTERNAL|UNKNOWN')
            rec={'id':aid,'kind':o['kind'],'ctx':o['ctx'],'cause':cause,'predicted':p.get('outcome'),'confidence':p.get('confidence'),'actual':key,
                 'grounded_error':err,'latency_s':round(self.clock()-o['created'],3)}
            st['closed']=(st['closed']+[rec])[-HISTORY:];return rec
        rec=self.box.mutate(f);self.s.log('grounded_outcome',None,{'kind':rec['kind'],'grounded_error':rec['grounded_error']})
        return rec
    def counterfactual(self,kind,context_key,coverage_full=20):
        """'What if I did kind here?' without acting. Confidence shrinks with low action coverage (§7.2.2)."""
        if type(coverage_full) not in (int,float):raise ValueError('coverage_full: positive finite number required')
        try:denom=float(coverage_full)
        except OverflowError as exc:raise ValueError('coverage_full: positive finite number required') from exc
        if not math.isfinite(denom) or denom<=0:raise ValueError('coverage_full: positive finite number required')
        p=FrequencyPredictor(self.box.load()[0]['table']).predict(kind,context_key)
        cov=min(1.,p['coverage']/denom)
        return p|{'counterfactual_confidence':round(p['confidence']*cov,4),'coverage_share':round(cov,4),'authority':'SIMULATION_NOT_FACT',
                  'ood':p['coverage']==0}
    def from_tool(self,tx):
        """Adapter for ToolRegistry.on_outcome: tool calls become grounded outcomes."""
        if tx['status'] not in {'EXECUTED','FAILED'}:return None
        aid,_=self.expect('tool:'+tx['tool'],dumps(tx['args'])[:120],{'tool':tx['tool']},'tool',tx.get('predicted'))
        return self.observe(aid,{'status':tx['status'],'result':tx['result']})
    def set_modality(self,name,on):
        if name not in MODALITIES:raise ValueError('Unbekannte Modalität')
        if type(on) is not bool:raise ValueError('Modalität: bool required')
        # This AG2 baseline has no STEP8 sensor/effector approval or device port.
        # A separate, permission-bound STEP8 integration must own activation.
        if on and name in STEP8_GATED:raise PermissionError('STEP8-Modus nicht freigegeben: '+name)
        def f(st):st['modalities'][name]=on
        self.box.mutate(f)
    def samples(self,limit=256):
        """Grounded training pairs for a world predictor (context, action, actual outcome)."""
        return self.box.load()[0]['closed'][-limit:]
    def report(self):
        st=self.box.load()[0]
        return {'revision':REVISION,'modalities':st['modalities'],'open':len(st['open']),'closed':len(st['closed']),
                'error_rate':{k:round(v['err']/v['n'],4) for k,v in st['errors'].items() if v['n']},
                'claim_limit':'Frequency baseline over text/tool outcomes; World-JEPA and sensors (STEP8) plug in later'}
