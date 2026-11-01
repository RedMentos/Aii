"""WP-N2 rest / §10, §10.1, §24.17, G5: learned deliberation space, world-error trigger, halt only after a stable trajectory.

World-error trigger (§10)    a recent own world-prediction error (WP-F fast-forward surprise, WP-N9 MIXED self/world
                              attribution, F4 digital latent error) opens Inquisition as WORLD_PREDICTION_ERROR.
Learned deliberation space    per (trigger set, Inquisition mode) the informativeness of the step: a verdict that changed
                              the focal state (CONTESTED, UNSUPPORTED, VIOLATION, SOURCE_LOSS, SUPPORTED, PREFERRED) counts
                              1, NO_TARGET/CONSISTENT/PROPOSED 0; ratings add human value. Only when the Age right for
                              deliberation modes exists *and* `:delib active` is set, the mode order is re-ranked by that
                              value (HYPOTHESIS stays first, the step count is unchanged). SHADOW logs the proposal.
Halt after stable trajectory  the learned halt readout may only steer once the scaffold trajectories for that trigger
                              pattern are stable (same final decision in >= STABLE_SHARE of the last WINDOW runs and a
                              narrow cycle count), so a halt head never shapes an unsettled trajectory (§10.1, G5).
"""
import json
from .common import dumps
from .neuromod import step

KEY='N2_DELIBERATION';REVISION='n2-deliberation-v1';PATH='inquisition_policy'
INFORMATIVE={'CONTESTED','UNSUPPORTED','VIOLATION','SOURCE_LOSS','SUPPORTED','PREFERRED','SOURCE_CHECKED','ALTERNATIVE_PROPOSED'}
WINDOW=10;STABLE_SHARE=.8;CYCLE_SPREAD=1;MIN_N=3;RATE=.2   # BOOT
WORLD_ERROR=.5                                              # BOOT
RECENT_S=900.

def tkey(trigger):return '+'.join(sorted(trigger)) or 'NONE'
def empty():return {'revision':REVISION,'mode':'SHADOW','modes':{},'traj':{},'turns':[]}

class Deliberation:
    def __init__(self,store,neuromod=None):self.s=store;self.n=neuromod
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st=empty()
        if st.get('revision')!=REVISION:raise ValueError('Deliberation state revision mismatch')
        return st,v
    def _mutate(self,fn):
        for attempt in (0,1):
            st,v=self._load();out=fn(st);dumps(st)
            try:self.s.set_state(KEY,st,expected=v);return out
            except ValueError:
                if attempt:raise
    def set_mode(self,mode,authority='SYSTEM'):
        if mode not in {'SHADOW','ACTIVE'}:raise ValueError('SHADOW|ACTIVE')
        if mode=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0)')
        def fn(st):st['mode']=mode;return mode
        return self._mutate(fn)
    # -- world-error trigger --------------------------------------------------------------------------
    def world_error(self,session=None,now=None):
        """Recent own world-prediction error in this session (any source)."""
        import time
        t=now or time.time()
        rows=self.s.rows("SELECT p.kind,p.payload,p.created FROM packets p JOIN events e ON e.id=p.event_id WHERE p.kind IN ('ModulatorPacket','SelfWorldAttribution') AND (? IS NULL OR e.session_id=?) ORDER BY p.rowid DESC LIMIT 12",(session,session))
        for r in rows:
            if t-r['created']>RECENT_S:continue
            p=json.loads(r['payload'])
            if r['kind']=='SelfWorldAttribution' and p['attribution']=='MIXED':return True
            if r['kind']=='ModulatorPacket':
                ch=p.get('channels') or {}
                if ch.get('world_prediction_error',0)>=WORLD_ERROR or (p.get('digital_prediction_error') or 0)>=WORLD_ERROR:return True
        return False
    # -- learned mode order ---------------------------------------------------------------------------
    def order(self,modes,trigger,deliberation_allowed):
        """Re-rank Inquisition modes by learned value; HYPOTHESIS first, same length. Returns (modes, proposal, applied)."""
        st,_=self._load();k=tkey(trigger)
        val=lambda m:(st['modes'].get(k+'|'+m) or {'n':0,'v':.5})
        known=[m for m in modes if val(m)['n']>=MIN_N]
        head,rest=(['HYPOTHESIS'],list(modes[1:])) if modes and modes[0]=='HYPOTHESIS' else ([],list(modes))
        proposal=head+sorted(rest,key=lambda m:-val(m)['v']) if known else list(modes)
        applied=st['mode']=='ACTIVE' and deliberation_allowed and bool(known)
        if known:
            from .authority import observe
            observe(self.s,'deliberation',list(modes),proposal)
        return (proposal if applied else list(modes)),proposal,applied
    # -- stability gate for the halt readout ----------------------------------------------------------
    def halt_allowed(self,trigger):
        st,_=self._load();xs=st['traj'].get(tkey(trigger),[])[-WINDOW:]
        if len(xs)<WINDOW:return False
        decs=[x['decision'] for x in xs];top=max(set(decs),key=decs.count);cyc=[x['cycles'] for x in xs]
        return decs.count(top)/len(decs)>=STABLE_SHARE and max(cyc)-min(cyc)<=CYCLE_SPREAD
    # -- learning -------------------------------------------------------------------------------------
    def record(self,event_id,trigger,decision,cycles,steps,proposal=None,applied=False):
        k=tkey(trigger);sc=step(self.n,PATH)  # WP-U6 §12.7
        def fn(st):
            xs=st['traj'].setdefault(k,[]);xs.append({'decision':decision,'cycles':cycles});st['traj'][k]=xs[-WINDOW*3:]
            for s in steps:
                q=st['modes'].setdefault(k+'|'+s['mode'],{'n':0,'v':.5});q['n']+=1;q['v']+=sc*RATE*((1. if s['verdict'] in INFORMATIVE else 0.)-q['v'])
            st['turns']=(st['turns']+[{'event_id':event_id,'trigger':k,'modes':[s['mode'] for s in steps]}])[-64:]
            return k
        self._mutate(fn)
        if self.n is not None and steps:
            try:self.n.touch(PATH,event_id,activity=min(1.,len(steps)/4),detail={'trigger':k,'applied':applied,'proposal':proposal})
            except Exception:pass
    def outcome(self,event_id,utility):
        """Human value of a turn's deliberation: nudges every mode used in it."""
        u=max(0.,min(1.,float(utility)));sc=step(self.n,PATH)
        def fn(st):
            t=next((x for x in st['turns'] if x['event_id']==event_id),None)
            if not t:return 0
            for m in set(t['modes']):
                q=st['modes'].setdefault(t['trigger']+'|'+m,{'n':0,'v':.5});q['n']+=1;q['v']+=sc*RATE*(u-q['v'])
            return len(set(t['modes']))
        n=self._mutate(fn)
        if n and self.n is not None:
            try:self.n.signal(event_id,path=PATH,source_class='human_correction',task_success=u)
            except Exception:pass
        return {'updated_modes':n}
    def report(self):
        st,_=self._load()
        return {'revision':REVISION,'mode':st['mode'],'mode_values':{k:{'n':q['n'],'value':round(q['v'],3)} for k,q in st['modes'].items()},
                'trajectory_stability':{k:{'n':len(x),'halt_allowed':self.halt_allowed(k.split('+') if k!='NONE' else [])} for k,x in st['traj'].items()}}

def controller(runtime):
    d=getattr(runtime,'deliberation',None)
    if d is None:
        n=None
        try:
            from .neuromod import controller as nc
            n=nc(runtime)
        except Exception:n=None
        d=runtime.deliberation=Deliberation(runtime.store,n)
    return d

def on_rating(store,event_id,score):return Deliberation(store).outcome(event_id,(score-1)/9)

def operator_command(r,args):
    """:delib [status|shadow|active]"""
    d=controller(r)
    if not args or args==['status']:return dumps(d.report())
    if args==['shadow']:return dumps({'mode':d.set_mode('SHADOW')})
    if args==['active']:return dumps({'mode':d.set_mode('ACTIVE','EXPLICIT_HUMAN')})
    raise ValueError(':delib [status|shadow|active]')
