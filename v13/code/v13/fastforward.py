"""WP-F / §7.1, §85.6, §75, §6.3-6.5, §24.3-24.4, G4: Fast-Forward (cerebellar) predictor + proceduralization.

Fast-Forward is not a body (§7.1, §85.6): a tiny feed-forward model on the current turn state predicts the immediate
outcome of an own action (answer time, success, answer length) and corrects itself after every outcome with a
normalized delta rule (the cerebellar error-correction picture). Its predictions feed the imminent-timeout reflex,
the turn metadata and a world-prediction-error modulator (WP-N10 path `fast_forward`).

Proceduralization (§75, §85.6 G-PROCEDURALIZATION-004): turns are grouped by a coarse state pattern. When the
deliberative route for a pattern succeeds repeatedly with the same wake decision (SKILL.compile_after_successes),
it compiles into a procedural policy, which then runs SHADOW for SKILL.shadow_cycles turns (agreement with what the
full route did, no failure). It becomes READY only if latency drops by prediction, accuracy is non-inferior and it
never failed. Only in ACTIVE (explicit human switch) may a READY policy set the wake decision, and only on calm turns
(automatic authority is a ceiling: it may skip body passes, never add authority). Failure reopens it to the full
route (SKILL.reopen_on_failure); a surprising outcome or a salient/novel turn bypasses it (§24.4 de-automatization).
Numbers are §75 BOOT values or marked BOOT.
"""
import math
import re
from .common import dumps
from .neuromod import step

KEY='F_FAST_FORWARD';REVISION='f-fast-forward-v1';PATH='fast_forward'
SKILL={'compile_after_successes':5,'shadow_cycles':10,'automatic_authority':.20,'reopen_on_surprise':.85,'reopen_on_failure':1.}  # §75 BOOT
FEATURES=('bias','input_len','r_simple','r_detail','r_gist','r_both','w_none','w_detail','w_gist','w_both','memory','effort','novelty','conflict')
TARGETS=('log_duration','success','log_chars')
LR=.3                         # BOOT NLMS step
REPLAY_MAX=256                # WP-S7 outcome buffer for sleep consolidation
AGREE_MIN=.9;CONSISTENT=.8;CALM={'novelty':.5,'conflict':.3,'uncertainty':.45,'salience':.65}  # BOOT
DIGITS=re.compile(r'\d')

def clip(x,lo=0.,hi=1.):return min(hi,max(lo,float(x)))
def empty():return {'revision':REVISION,'mode':'SHADOW','w':{t:[0.]*len(FEATURES) for t in TARGETS},'n':0,'abs_err':{t:0. for t in TARGETS},'procs':{}}

def features(text,route,wake,memories=(),effort=.5,sig=None):
    sig=sig or {}
    return [1.,clip(math.log1p(len(text or ''))/8),*(float(route==r) for r in ('simple','detail','gist','both')),
            *(float(wake==w) for w in ('none','detail','gist','both')),float(bool(memories)),clip(effort),clip(sig.get('novelty',0.)),clip(sig.get('conflict',0.))]

def pattern(text,route,sig,memories=()):
    """Coarse state pattern; deliberately few buckets so a habit can form."""
    sig=sig or {}
    parts=[route,sig.get('route_source','BOOT_SCAFFOLD'),'long' if len(text or '')>400 else 'short','num' if DIGITS.search(text or '') else 'nonum',
           'mem' if memories else 'nomem','novel' if sig.get('novelty',0)>=.5 else 'familiar']
    return '|'.join(parts)

class FastForward:
    def __init__(self,store,neuromod=None):self.s=store;self.n=neuromod
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st=empty()
        if st.get('revision')!=REVISION:raise ValueError('Fast-Forward state revision mismatch')
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
    # -- cerebellar predictor -------------------------------------------------------------------------
    @staticmethod
    def _dot(w,x):return sum(a*b for a,b in zip(w,x))
    def predict(self,x,st=None):
        st=st or self._load()[0];w=st['w']
        if st['n']<3:return {'duration_s':None,'success_p':None,'chars':None,'trained_on':st['n']}
        return {'duration_s':round(math.exp(max(-5.,min(7.,self._dot(w['log_duration'],x)))),3),'success_p':round(clip(self._dot(w['success'],x)),4),
                'chars':int(math.exp(max(0.,min(10.,self._dot(w['log_chars'],x))))),'trained_on':st['n']}
    def learn(self,event_id,x,duration_s,status,chars):
        """Normalized delta rule on the actual outcome; returns the prediction error (surprise in [0,1])."""
        y={'log_duration':math.log(max(.01,duration_s)),'success':1. if status=='FINAL' else 0.,'log_chars':math.log(max(1,chars))}
        norm=1e-6+sum(v*v for v in x);sc=step(self.n,PATH)  # WP-U6 §12.7
        def fn(st):
            before=self.predict(x,st);err={}
            for t in TARGETS:
                e=y[t]-self._dot(st['w'][t],x);err[t]=e
                st['w'][t]=[w+sc*LR*e*xi/norm for w,xi in zip(st['w'][t],x)]
                st['abs_err'][t]+=(abs(e)-st['abs_err'][t])/min(st['n']+1,50)
            st['n']+=1;st['replay']=(st.get('replay',[])+[{'x':[round(v,6) for v in x],'y':y}])[-REPLAY_MAX:]  # WP-S7 offline replay buffer
            return before,err
        before,err=self._mutate(fn)
        surprise=clip(abs(err['log_duration'])/2) if before['duration_s'] is not None else 0.
        if self.n is not None and before['duration_s'] is not None:
            try:self.n.touch(PATH,event_id,activity=1.,error=surprise>=.5);self.n.signal(event_id,path=PATH,source_class='real_deterministic_outcome',world_prediction_error=surprise)
            except Exception:pass
        return {'predicted':before,'surprise':round(surprise,4),'errors':{k:round(v,4) for k,v in err.items()}}
    def consolidate(self,epochs=3,lr=LR/3,holdout=.2,checkpoint=None):
        """WP-S7 sleep: extra low-rate NLMS passes over the stored outcomes. Kept only if the held-out error does not rise."""
        st,source_version=self._load();buf=st.get('replay',[])
        if len(buf)<10:return {'status':'SKIPPED_TOO_FEW','samples':len(buf)}
        k=max(2,int(len(buf)*holdout));train,test=buf[:-k],buf[-k:]
        def err(w):return sum(abs(s['y'][t]-self._dot(w[t],s['x'])) for s in test for t in TARGETS)/len(test)
        w={t:list(v) for t,v in st['w'].items()};before=err(w)
        for _ in range(epochs):
            for s in train:
                if checkpoint:checkpoint()
                norm=1e-6+sum(v*v for v in s['x'])
                for t in TARGETS:
                    e=s['y'][t]-self._dot(w[t],s['x']);w[t]=[a+lr*e*xi/norm for a,xi in zip(w[t],s['x'])]
        after=err(w);kept=after<=before
        if kept:
            # Sleep trained against one exact replay/weight snapshot. Never
            # rebase its weights onto a newer live learning or procedure state:
            # the Store's optimistic version check is the commit boundary.
            st['w']=w
            st['sleep_updates']=st.get('sleep_updates',0)+1
            try:
                self.s.set_state(KEY,st,expected=source_version)
            except ValueError:
                if self._load()[1]!=source_version:
                    return {'status':'SKIPPED_STALE_LIVE_STATE','samples':len(buf),
                            'heldout_error_before':round(before,4),'heldout_error_after':round(after,4)}
                raise
        return {'status':'KEPT' if kept else 'REVERTED','samples':len(buf),'heldout_error_before':round(before,4),'heldout_error_after':round(after,4)}
    # -- proceduralization ----------------------------------------------------------------------------
    def procedural(self,key,sig=None):
        """Should the compiled policy set the wake decision for this turn? Never on salient/novel turns."""
        st,_=self._load();p=st['procs'].get(key);sig=sig or {}
        calm=all(sig.get(k,0.)<v for k,v in CALM.items())
        if not p or p['stage'] not in ('READY',) or not p.get('compiled'):return {'apply':False,'stage':p['stage'] if p else None,'key':key}
        return {'apply':st['mode']=='ACTIVE' and calm,'wake':p['compiled']['wake'],'stage':p['stage'],'key':key,'calm':calm,
                'reason':None if calm else 'salience_reopens_focal'}
    def record_turn(self,key,wake,status,duration_s,surprise=0.,predicted_fast_s=None,applied=False):
        """After a deliberative or procedural turn: lifecycle OBSERVE -> SHADOW -> READY, reopen on failure/surprise."""
        def fn(st):
            p=st['procs'].setdefault(key,{'stage':'OBSERVE','succ':0,'n':0,'decisions':{},'durations':[],'shadow':{'n':0,'agree':0,'fail':0},'compiled':None,'history':[]})
            p['n']+=1;ok=status=='FINAL'
            if not ok and p['stage'] in ('SHADOW','READY') and SKILL['reopen_on_failure']>=1:
                p.update(stage='OBSERVE',succ=0,decisions={},compiled=None,shadow={'n':0,'agree':0,'fail':0});p['history'].append(['REOPEN_FAILURE',p['n']]);return p['stage']
            if applied and surprise>=SKILL['reopen_on_surprise']:
                p.update(stage='SHADOW',shadow={'n':0,'agree':0,'fail':0});p['history'].append(['REOPEN_SURPRISE',p['n']]);return p['stage']
            if p['stage']=='OBSERVE':
                if ok:
                    p['succ']+=1;p['decisions'][wake]=p['decisions'].get(wake,0)+1;p['durations']=(p['durations']+[duration_s])[-20:]
                top=max(p['decisions'].items(),key=lambda kv:kv[1]) if p['decisions'] else (None,0)
                if p['succ']>=SKILL['compile_after_successes'] and top[1]/max(1,sum(p['decisions'].values()))>=CONSISTENT:
                    p['compiled']={'wake':top[0],'compiled_from':p['succ']};p['stage']='SHADOW';p['history'].append(['COMPILED',p['n']])
            elif p['stage']=='SHADOW':
                s=p['shadow'];s['n']+=1;s['agree']+=int(wake==p['compiled']['wake']);s['fail']+=int(not ok)
                if ok:p['durations']=(p['durations']+[duration_s])[-20:]
                if s['n']>=SKILL['shadow_cycles']:
                    delib=sum(p['durations'])/len(p['durations']) if p['durations'] else None
                    # A missing or invalid estimate is NOT evidence of a
                    # faster procedure. This is still predictor-only evidence,
                    # not a measured counterfactual execution speedup.
                    faster=(type(predicted_fast_s) in (int,float)
                            and math.isfinite(predicted_fast_s) and predicted_fast_s>0
                            and delib is not None and math.isfinite(delib)
                            and delib>0 and predicted_fast_s<delib)
                    if s['agree']/s['n']>=AGREE_MIN and s['fail']==0 and faster:
                        p['stage']='READY';p['gate']={'agreement':round(s['agree']/s['n'],3),'failures':0,'latency_ok':faster,'latency_evidence':'PREDICTOR_ESTIMATE_NOT_MEASURED','canonical_gate_pass':False,'G':'G-PROCEDURALIZATION-004'}
                        p['history'].append(['READY',p['n']])
                    else:p['shadow']={'n':0,'agree':0,'fail':0};p['history'].append(['GATE_FAILED',p['n']])
            p['history']=p['history'][-12:];return p['stage']
        return self._mutate(fn)
    def report(self):
        st,_=self._load()
        return {'revision':REVISION,'mode':st['mode'],'trained_on':st['n'],'mean_abs_error':{k:round(v,4) for k,v in st['abs_err'].items()},
                'procedures':{k:{x:p.get(x) for x in ('stage','succ','n','compiled','shadow','gate')} for k,p in st['procs'].items()},
                'claim_limit':'Small feed-forward predictor; procedures may only skip body passes on calm turns'}

def controller(runtime):
    f=getattr(runtime,'fastforward',None)
    if f is None:
        n=None
        try:
            from .neuromod import controller as neuromod_controller
            n=neuromod_controller(runtime)
        except Exception:n=None
        f=runtime.fastforward=FastForward(runtime.store,n)
    return f

def operator_command(r,args):
    """:ff [status|shadow|active]"""
    f=controller(r)
    if not args or args==['status']:return dumps(f.report())
    if args==['shadow']:return dumps({'mode':f.set_mode('SHADOW')})
    if args==['active']:return dumps({'mode':f.set_mode('ACTIVE','EXPLICIT_HUMAN')})
    raise ValueError(':ff [status|shadow|active]')
