"""WP-F / §5.3: reflex layer. Very fast hard reactions below deliberation, kept separate from skills and gain.

Reflexes (BOOT thresholds, logged as ReflexEvent packets):
  imminent_timeout   before the observer stage: remaining deadline < predicted answer time x margin
                     -> shed_observers (no B1/B2 pass, one focal cycle). Prediction from the cerebellar FF model.
  runner_failure     a body failed FAILURES times within WINDOW_S -> circuit_open for COOLDOWN_S; the turn falls back
                     to C3 through the existing Unavailable path (API-failure reflex). One success closes it.
  critical_resource  ResourceGuard CRITICAL (low RAM / heat) -> unload native runners to free memory, then the
                     existing Limits refusal continues (OOM/heat reflex).
A reflex never answers, writes memory or learns weights; it only sheds or blocks load. Outcomes are counted so the
thresholds can later be tuned (`:reflex`).
"""
import time
from .common import dumps
from .contracts import packet

KEY='F_REFLEX';REVISION='f-reflex-v1'
FAILURES=3;WINDOW_S=600.;COOLDOWN_S=120.     # BOOT circuit breaker
TIMEOUT_MARGIN=1.2;TIMEOUT_FLOOR_S=3.         # BOOT imminent-timeout reflex
NEVER_BLOCK={'C3_LANGUAGE'}                    # the last-resort speaker is never circuit-broken

def empty():return {'revision':REVISION,'failures':{},'open':{},'counts':{},'outcomes':{}}

class Reflex:
    def __init__(self,store,clock=time.time):self.s=store;self.clock=clock
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st=empty()
        if st.get('revision')!=REVISION:raise ValueError('Reflex state revision mismatch')
        return st,v
    def _mutate(self,fn):
        for attempt in (0,1):
            st,v=self._load();out=fn(st);dumps(st)
            try:self.s.set_state(KEY,st,expected=v);return out
            except ValueError:
                if attempt:raise
    def _fire(self,event_id,reflex,action,detail):
        self._mutate(lambda st:st['counts'].__setitem__(reflex,st['counts'].get(reflex,0)+1))
        try:
            gen=self.s.generation_id
            self.s.add_packet('ReflexEvent',packet('ReflexEvent','F_REFLEX',event_id or 'none',gen,[],reflex=reflex,action=action,detail=detail))
        except Exception:self.s.log('reflex',event_id,{'reflex':reflex,'action':action})
        return {'reflex':reflex,'action':action,'detail':detail}
    # -- circuit breaker --------------------------------------------------------------------------------
    def circuit_open(self,role):
        if role in NEVER_BLOCK:return False
        until=self._load()[0]['open'].get(role)
        return bool(until and until>self.clock())
    def record_failure(self,role,event_id=None,kind='ERROR'):
        t=self.clock()
        def fn(st):
            xs=[x for x in st['failures'].get(role,[]) if t-x<WINDOW_S]+[t];st['failures'][role]=xs[-16:]
            if len(xs)>=FAILURES and role not in NEVER_BLOCK and not (st['open'].get(role,0)>t):
                st['open'][role]=t+COOLDOWN_S;return True
            return False
        opened=self._mutate(fn)
        return self._fire(event_id,'runner_failure','circuit_open',{'role':role,'kind':kind,'cooldown_s':COOLDOWN_S}) if opened else None
    def record_success(self,role):
        def fn(st):st['failures'].pop(role,None);st['open'].pop(role,None)
        self._mutate(fn)
    # -- imminent timeout -------------------------------------------------------------------------------
    def timeout_check(self,event_id,remaining_s,predicted_answer_s):
        if predicted_answer_s is None:return None
        need=max(TIMEOUT_FLOOR_S,predicted_answer_s*TIMEOUT_MARGIN)
        if remaining_s<need:return self._fire(event_id,'imminent_timeout','shed_observers',{'remaining_s':round(remaining_s,3),'needed_s':round(need,3)})
        return None
    def outcome(self,reflex,status):
        """Did the turn after a reflex still end FINAL? (tuning evidence, not learning)."""
        def fn(st):
            o=st['outcomes'].setdefault(reflex,{'final':0,'other':0});o['final' if status=='FINAL' else 'other']+=1
        self._mutate(fn)
    # -- critical resource ------------------------------------------------------------------------------
    def critical(self,event_id,pool,snapshot):
        try:pool.unload();freed=True
        except Exception:freed=False
        return self._fire(event_id,'critical_resource','unload_runners',{'unloaded':freed,'mem_available_bytes':(snapshot or {}).get('mem_available_bytes'),
                                                                          'battery_temperature_c':(snapshot or {}).get('battery_temperature_c')})
    def report(self):
        st,_=self._load();t=self.clock()
        return {'revision':REVISION,'open_circuits':{r:round(u-t,1) for r,u in st['open'].items() if u>t},'counts':st['counts'],'outcomes':st['outcomes'],
                'recent_failures':{r:len(x) for r,x in st['failures'].items()},'claim_limit':'Reflexes shed or block load only; no answers, memory or learning'}

def controller(runtime):
    r=getattr(runtime,'reflex',None)
    if r is None:r=runtime.reflex=Reflex(runtime.store)
    return r

def operator_command(r,args):
    """:reflex [status|close <Rolle>]"""
    x=controller(r)
    if not args or args==['status']:return dumps(x.report())
    if len(args)==2 and args[0]=='close':x.record_success(args[1]);return dumps(x.report())
    raise ValueError(':reflex [status|close <Rolle>]')
