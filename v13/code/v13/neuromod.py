"""WP-N10 / §12.1-12.5, §16.1-16.3, §35, §62-63, §85.10, §101.1: eligibility, typed modulator bus, plasticity gate.

    Δθ_i ∝ e_i × δ_i × M_i × P_i        (§12.4, §35.1)

e_i  eligibility: two-timescale trace per path (§62), grows when the path is active, decays per experience
     event. Fed by the LearningTrace packets the learners already write; detailed traces only selectively.
δ_i  local error: stays the optimizer's own loss inside each worker (not computed here).
M_i  typed modulator vector (§35.2, §101.1): epistemic and instrumental channels kept apart (§12.5),
     weighted per learning kind (§35.3), source credibility per §63; safety is a hard veto, not a channel.
     ModulatorPackets without a path are credit-mapped onto the paths eligible in the same event (§12.2).
P_i  metaplasticity: F7 measured gain (plasticity.py) × Age reopenable plasticity (§95.3), reopened by
     repeated retention failures and novelty (§16.1).

The gate scales only the next explicit shadow-job budget (learning rate, max update norm). It grants no
commit, consolidation, source deletion or native-weight authority. A consolidation tag (§16.3) needs
several distinct confirming events plus F7 stability; a single surprise never tags a path.
All numeric values are BOOT/RESEARCH-BOOT priors from the blueprint, not measured optima.
"""
import hashlib
import json
import math
from .common import dumps
from .contracts import packet
from .plasticity import LR_KEYS

KEY='N10_NEUROMOD';REVISION='n10-neuromod-v1'
FAST_DECAY=.65;SLOW_DECAY=.93;SLOW_MIX=.25  # §62 per experience event
DETAIL_RATE={'normal':.10,'error':.80,'human_feedback':1.}  # §62
SOURCE_WEIGHT={'real_deterministic_outcome':1.,'primary_source':.9,'human_correction':.75,'verified_teacher':.45,
               'internal_crosscheck':.2,'dream':0.}  # §63 M.epistemic
UTILITY_SCALE={'dream':0.}  # dreams never modulate instrumental learning either (fact_write_authority=0)
SAFETY={'permission_violation':1.,'irreversible_action':.9,'rollback_available':-.2}  # §63 M.safety
EPISTEMIC=('evidence_gain','human_correction','world_prediction_error','surprise','novelty','uncertainty',
           'calibration_error','source_quality','retention')
INSTRUMENTAL=('reward_error','action_error','task_success','cost_error','repeated_failure','social','urgency')
CHANNELS=EPISTEMIC+INSTRUMENTAL+('rule_violation',)
CONFIRMING=('evidence_gain','human_correction','retention','task_success')  # surprise/novelty alone never confirm
# §35.3 / §85.10 ModulatorWeights per learning kind. BOOT priors.
KIND_WEIGHTS={
 'knowledge':{'evidence_gain':1.,'source_quality':.9,'human_correction':1.,'retention':.6,'surprise':.4,'calibration_error':.4,'reward_error':.1},
 'control':{'action_error':1.,'task_success':.8,'cost_error':.8,'calibration_error':.8,'repeated_failure':.75,'reward_error':.6,
            'human_correction':.7,'uncertainty':.4,'evidence_gain':.3},
 'language':{'human_correction':1.,'source_quality':.7,'evidence_gain':.5,'social':.4,'task_success':.3,'retention':.4},
 'skill':{'task_success':1.,'action_error':.8,'repeated_failure':.75,'cost_error':.6,'retention':.6,'human_correction':.6},
 'world':{'world_prediction_error':1.,'surprise':.8,'novelty':.5,'evidence_gain':.5,'action_error':.4,'retention':.4},
 'perception':{'world_prediction_error':.7,'human_correction':.7,'surprise':.6,'novelty':.6,'evidence_gain':.6,'calibration_error':.4}}
COMPONENT_KIND={'route':'control','wake':'control','halt':'control','control_calibration':'control','memory_retrieval':'knowledge',
                'output_adapter':'language','a3_student':'perception','b1_predictor':'world','b2_predictor':'world',
                'world_predictor':'world','weights':'knowledge',
                'attention_policy':'control','context_policy':'control',
                'jef_offer_utility':'control','jef_topdown_query':'control','jef_broadcast_bridge':'control','fast_forward':'world','c5_action_selection':'control','inquisition_policy':'control','callosum_channel_policy':'control'}  # WP-N5 / WP-N7 control paths
AGE_CAPABILITY={'control':'routing_skill','knowledge':'memory_skill','language':'language','skill':'tool','world':'system','perception':'system'}
ALIASES={'C_WAKE_READOUT':'wake','C_HALT_READOUT':'halt','C2_EXTERNAL_ROUTE_HEAD':'route'}
FLOOR=.25          # BOOT: an explicit human-initiated job always keeps a quarter budget (Age 0 is human-led)
PROVISIONAL=.5     # BOOT: PROVISIONAL modulators count half until FINAL
VETO_BLOCK=.5      # BOOT: decaying veto level at/above which a path may not learn
TAG_CONFIRMATIONS=3;TAG_MIN_EPISTEMIC=.5  # BOOT §16.3, mirrors consolidation.MIN_CONFIRMATIONS
SLEEP_EVENTS=10    # BOOT: one sleep counts as ten events of slow decay; fast traces do not survive sleep
MAX_PATHS=128;MAX_DETAILS=8;BATCH=2000;EPS=1e-4
# WP-T12 §12.2/§12.4 local error δ per path + §16.1/§68 metaplasticity head (BOOT knobs from §68, not measured)
ERROR_CH=('world_prediction_error','action_error','reward_error','calibration_error','cost_error')
DELTA_EMA=.2;R_HAT_RATE=.1;R_HAT0=.5
META={'stability_decay_plasticity':.55,'novelty_reopen':.45,'repeated_failure_reopen':.70,'saturation_suppression':.65,
      'conflict_verify_before_learn':.80}
CONFLICT_MIN=.2   # BOOT (WP-U2): both supporting and contradicting evidence must reach this before a conflict counts
VERIFYING=('human_correction','real_deterministic_outcome','primary_source')  # sources that settle a conflict
META_FEATURES=('stability','novelty','repeated_errors','saturation','error_level','modulator');META_LR=.2;META_MIN_N=8

def clamp(x,lo=0.,hi=1.):
    x=float(x)
    if not math.isfinite(x):raise ValueError('Neuromod: Wert nicht endlich')
    return max(lo,min(hi,x))
def path_of(name):return ALIASES.get(name,name)
def kind_of(path):return COMPONENT_KIND.get(path,'skill')
def oplus(a,b):return 1-(1-a)*(1-b)  # bounded accumulation of independent evidence
def sampled(event_id,path,rate):
    """Deterministic selective sampling (§12.1): restart-stable, no RNG state."""
    if rate>=1:return True
    h=int(hashlib.sha256((str(event_id)+'|'+path).encode()).hexdigest()[:8],16)/0xffffffff
    return h<rate

def empty_path():
    return {'fast':0.,'slow':0.,'seq':0,'activations':0,'epistemic':0.,'instrumental':0.,'veto':0.,'novelty':0.,
            'repeated_errors':0,'confirmations':[],'tag':False,'tag_reason':None,'details':[],'last_event':None,
            'unassigned':0,'stable':False}
def empty():return {'revision':REVISION,'cursor':0,'paths':{},'unassigned_modulators':0,'sleeps':0}
def _sig(z):return 1/(1+math.exp(-max(-30.,min(30.,z))))

def channels_from(p):
    """Typed channels from a ModulatorPacket; legacy 5-field packets map onto the §101.1 channels."""
    ch={k:clamp(v,-1.,1.) for k,v in (p.get('channels') or {}).items() if k in CHANNELS}
    legacy={'evidence_gain':p.get('epistemic_evidence'),'human_correction':p.get('human_correction'),
            'task_success':p.get('task_success'),'cost_error':p.get('resource_cost'),'world_prediction_error':p.get('digital_prediction_error')}
    for k,v in legacy.items():
        if k not in ch and isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v):ch[k]=clamp(v,-1.,1.)
    return ch
def source_of(p,ch):
    s=p.get('source_class')
    if s in SOURCE_WEIGHT:return s
    if ch.get('human_correction',0)>0:return 'human_correction'
    if str(p.get('producer_component','')).startswith('F4_WORLD'):return 'real_deterministic_outcome'
    return 'internal_crosscheck'
def veto_of(p,ch):
    v=max(SAFETY['permission_violation'] if p.get('safety_veto') else 0.,SAFETY['irreversible_action'] if p.get('irreversible') else 0.,abs(ch.get('rule_violation',0.)))
    if v>0 and p.get('rollback_available'):v+=SAFETY['rollback_available']
    return clamp(v)

def score(kind,ch,source,finality):
    """(epistemic, instrumental) worthiness in [0,1] of one packet for one learning kind (§12.5 kept apart)."""
    w=KIND_WEIGHTS[kind];f=1. if finality=='FINAL' else PROVISIONAL
    epi=max([w.get(c,0.)*abs(ch[c]) for c in EPISTEMIC if c in ch]+[0.])*SOURCE_WEIGHT[source]*f
    ins=max([w.get(c,0.)*abs(ch[c]) for c in INSTRUMENTAL if c in ch]+[0.])*UTILITY_SCALE.get(source,1.)*f
    return clamp(epi),clamp(ins)

class Neuromod:
    def __init__(self,store,age=None):
        self.s=store;self.age=age
    # -- state ------------------------------------------------------------------------------------------
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st=empty()
        if st.get('revision')!=REVISION:raise ValueError('Neuromod state revision mismatch')
        return st,v
    def _mutate(self,fn):
        for attempt in (0,1):
            st,v=self._load();out=fn(st);dumps(st)
            try:self.s.set_state(KEY,st,expected=v);return out
            except ValueError:
                if attempt:raise
    def _seq(self,created=None):
        if created is None:row=self.s.one('SELECT COALESCE(MAX(rowid),0) AS n FROM events')
        else:row=self.s.one('SELECT COALESCE(MAX(rowid),0) AS n FROM events WHERE created<=?',(created,))
        return int(row['n'])
    @staticmethod
    def _advance(p,seq):
        """Lazy per-event decay up to `seq` (traces, modulator traces and veto share the slow clock)."""
        n=max(0,seq-p['seq'])
        if n:
            p['fast']*=FAST_DECAY**n;p['slow']*=SLOW_DECAY**n;d=SLOW_DECAY**n
            for k in ('epistemic','instrumental','veto','novelty','error_level'):
                if k in p:p[k]*=d
            p['seq']=seq
        return p
    def _path(self,st,name,seq):
        paths=st['paths'];p=paths.get(name)
        if p is None:
            if len(paths)>=MAX_PATHS:
                drop=min((k for k in paths if not paths[k]['tag']),key=lambda k:paths[k]['fast']+paths[k]['slow']+paths[k]['veto'],default=None)
                if drop is None:raise ValueError('Neuromod: zu viele markierte Pfade')
                paths.pop(drop)
            p=paths[name]=empty_path()|{'seq':seq}
        return self._advance(p,seq)
    # -- intake (packets are the single source of truth) -------------------------------------------------
    def _trace(self,st,pk,seq):
        p=self._path(st,path_of(pk['path_id']),seq);a=clamp(pk['activity'])
        p['fast']=min(1.,p['fast']+a);p['slow']=min(1.,p['slow']+a*(1-SLOW_DECAY));p['activations']+=1;p['last_event']=pk['event_id']
        if p.get('meta_snapshot') is None:p['meta_snapshot']=self.meta_features(p)  # WP-T12: features before the update, labelled by the next retention result
        auth=str(pk.get('authority',''));cls='human_feedback' if ('HUMAN' in auth or 'OPERATOR' in auth) else ('error' if pk.get('error') else 'normal')
        if 'HUMAN' in auth or 'OPERATOR' in auth:
            # An explicit human/operator label is itself the modulator (§63 M.epistemic.human_correction).
            epi,_=score(kind_of(path_of(pk['path_id'])),{'human_correction':1.},'human_correction','FINAL')
            p['epistemic']=oplus(p['epistemic'],epi*a)
        if sampled(pk['event_id'],pk['path_id'],DETAIL_RATE[cls]):
            d={'event_id':pk['event_id'],'activity':a,'authority':auth,'class':cls,'refs':[r.get('source_id') for r in pk.get('provenance',[]) if isinstance(r,dict)][:4]}
            if isinstance(pk.get('detail'),dict):d['detail']=pk['detail']
            p['details']=(p['details']+[d])[-MAX_DETAILS:]
    def _credit(self,st,pk):
        """§12.2 credit_map: explicit path, else the paths that were eligible in the same event."""
        if pk.get('path_id'):return {path_of(pk['path_id']):1.}
        rows=self.s.rows("SELECT payload FROM packets WHERE kind='LearningTrace' AND event_id=?",(pk['event_id'],))
        share={}
        for r in rows:
            t=json.loads(r['payload']);share[path_of(t['path_id'])]=max(share.get(path_of(t['path_id']),0.),clamp(t['activity']))
        return share
    def _modulator(self,st,pk,seq):
        ch=channels_from(pk);source=source_of(pk,ch);fin=pk.get('finality','FINAL');veto=veto_of(pk,ch)
        credit=self._credit(st,pk)
        if not credit:st['unassigned_modulators']+=1;return
        for name,share in credit.items():
            p=self._path(st,name,seq);epi,ins=score(kind_of(name),ch,source,fin)
            p['epistemic']=oplus(p['epistemic'],epi*share);p['instrumental']=oplus(p['instrumental'],ins*share)
            p['veto']=max(p['veto'],veto);p['novelty']=max(p['novelty'],abs(ch.get('novelty',0.)))
            # WP-U2 §68 META.conflict_verify_before_learn: supporting vs. contradicting evidence on the same path.
            sw=SOURCE_WEIGHT[source]*share*(1. if fin=='FINAL' else PROVISIONAL)
            pos=max([ch[c] for c in CONFIRMING if ch.get(c,0)>0]+[0.])*sw;neg=max([-ch[c] for c in CONFIRMING if ch.get(c,0)<0]+[max(0.,ch.get('repeated_failure',0.))]+[0.])*sw
            if fin=='FINAL' and source in VERIFYING and (pos or neg):p['support'],p['contra']=(pos,0.) if pos>=neg else (0.,neg)  # verified: the conflict is settled
            else:p['support']=oplus(p.get('support',0.),pos);p['contra']=oplus(p.get('contra',0.),neg)
            if veto>0:p['tag']=False;p['tag_reason']='VETO';p['confirmations']=[]
            confirmed=fin=='FINAL' and veto==0 and SOURCE_WEIGHT[source]>=TAG_MIN_EPISTEMIC and any(ch.get(c,0)>0 for c in CONFIRMING)
            if confirmed and pk['event_id'] not in p['confirmations']:p['confirmations']=(p['confirmations']+[pk['event_id']])[-16:]
            if name not in LR_KEYS and fin=='FINAL' and veto==0 and ch.get('retention',0)>0:p['stable']=True;p['repeated_errors']=max(0,p['repeated_errors']-1)  # non-F7 paths: measured retention gate
            if ch.get('retention',0)<0 or ch.get('repeated_failure',0)>0:p['stable']=False;p['repeated_errors']+=1;p['tag']=False;p['tag_reason']='RETENTION_FAILURE'
            # WP-T12 §12.2: mapped local error. Unsigned prediction errors feed error_level; a task outcome gives a signed
            # reward-prediction error δ = r - r̂ against the path's own expected outcome (per sample, not per path).
            err=[abs(ch[c]) for c in ERROR_CH if c in ch]
            if err:p['error_level']=round((1-DELTA_EMA)*p.get('error_level',0.)+DELTA_EMA*max(err)*share,6)
            if 'task_success' in ch and veto==0:
                r=max(0.,ch['task_success']);rh=p.get('r_hat',R_HAT0);d=round((r-rh)*share,6)
                p['delta']={'event_id':pk['event_id'],'value':d,'r_hat':round(rh,6)};p['r_hat']=round(rh+R_HAT_RATE*(r-rh),6)
    def _plasticity_state(self,st,pk,seq):
        p=self._path(st,path_of(pk['component']),seq);p['stable']=bool(pk['consolidation_ready'])
        self._meta_learn(st,p,bool(pk['retention_pass']))  # WP-T12 learned metaplasticity head: did the last update hold?
        if pk['retention_pass']:p['repeated_errors']=max(0,p['repeated_errors']-1)
        else:p['repeated_errors']+=1;p['tag']=False;p['tag_reason']='RETENTION_FAILURE';p['confirmations']=[]
    # -- WP-T12 metaplasticity (§16.1, §68) ---------------------------------------------------------------
    @staticmethod
    def meta_features(p):
        rate=min(1.,p['activations']/max(1.,p['seq'] or 1.)) if p.get('seq') else 0.
        return {'stability':1. if p['stable'] and p['tag'] else (.5 if p['stable'] else min(1.,len(p['confirmations'])/TAG_CONFIRMATIONS)*.5),
                'novelty':clamp(p['novelty']),'repeated_errors':min(1.,p['repeated_errors']/3),
                'saturation':clamp(rate*(1-p.get('error_level',0.))),'error_level':clamp(p.get('error_level',0.)),'modulator':oplus(p['epistemic'],p['instrumental'])}
    @staticmethod
    def meta_rule(f):
        """§16.1/§68 BOOT rule: stable mature paths lower plasticity, novelty and repeated failures reopen it, saturation suppresses."""
        p=(1-META['stability_decay_plasticity']*f['stability'])+META['novelty_reopen']*f['novelty']+META['repeated_failure_reopen']*f['repeated_errors']
        return round(clamp(p*(1-META['saturation_suppression']*f['saturation'])),6)
    def _meta_learn(self,st,p,label):
        h=st.setdefault('meta_head',{'w':[0.]*len(META_FEATURES),'b':0.,'n':0,'pos':0})
        snap=p.get('meta_snapshot')
        if snap is None:return
        x=[snap[k] for k in META_FEATURES];z=_sig(sum(a*b for a,b in zip(h['w'],x))+h['b']);g=float(label)-z
        h['w']=[round(a+META_LR*g*b,6) for a,b in zip(h['w'],x)];h['b']=round(h['b']+META_LR*g,6);h['n']+=1;h['pos']+=int(label);p['meta_snapshot']=None
    def meta_predict(self,st,f):
        h=st.get('meta_head')
        if not h or h['n']<META_MIN_N:return None
        return round(_sig(sum(a*f[k] for a,k in zip(h['w'],META_FEATURES))+h['b']),6)
    def _meta_compare(self,name,p,st,features,rule,proposal):
        """One live plasticity proposal per unchanged path/head, never a retention outcome.

        The logistic head predicts retention, so its probability is not comparable to the rule's
        plasticity. Compare the rule with the actual adjusted plasticity proposal on the same features.
        Mark before observing: interruption can conservatively omit evidence, but cannot count an
        unchanged decision again after restart. Diagnostic reports do not call this hook.
        """
        fingerprint=hashlib.sha256(dumps({'event':p.get('last_event'),'n':st['meta_head']['n'],
            'features':features,'rule':rule,'proposal':proposal}).encode()).hexdigest()
        def mark(current):
            path=current['paths'].get(name)
            if path is None or path.get('meta_comparison')==fingerprint:return False
            if current.get('meta_head',{}).get('n')!=st['meta_head']['n'] or path.get('last_event')!=p.get('last_event'):
                return False  # A concurrent new trace/retention result makes this comparison stale.
            path['meta_comparison']=fingerprint;return True
        if self._mutate(mark):
            from .authority import observe
            observe(self.s,'neuromod_meta',rule,proposal)
    def meta_mode(self):return (self._load()[0].get('meta_mode') or 'SHADOW')
    def set_meta_mode(self,mode,authority='SYSTEM'):
        if mode not in {'SHADOW','ACTIVE'}:raise ValueError('SHADOW|ACTIVE')
        if mode=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0)')
        def f(st):st['meta_mode']=mode;return mode
        return self._mutate(f)
    def local_mode(self):return self._load()[0].get('local_mode') or 'SHADOW'
    def set_local_mode(self,mode,authority='SYSTEM'):
        if mode not in {'SHADOW','ACTIVE'}:raise ValueError('SHADOW|ACTIVE')
        if mode=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0)')
        def f(st):st['local_mode']=mode;return mode
        out=self._mutate(f);self.s.log('neuromod_local_mode',None,{'mode':mode,'authority':authority});return out
    def step_scale(self,component):
        """WP-U6 §12.7: factor for a head's own step size. SHADOW (default) -> 1.0, the head learns as before;
        ACTIVE -> the plasticity gate factor of its path (eligibility x modulator x Age/meta/homeostasis; veto/conflict -> 0)."""
        if self.local_mode()!='ACTIVE':return 1.
        return self.gate(component)['factor']
    def local_update(self,component,delta=None):
        """§12.4 Δθ_i ∝ e_i × δ_i × M_i × P_i. delta: the sample's own signed error in [-1, 1]; default the path's last
        mapped reward-prediction error. Returns the signed scale (negative = do not imitate this sample)."""
        g=self.gate(component);d=g['delta']['value'] if delta is None and g.get('delta') else (0. if delta is None else clamp(delta,-1.,1.))
        if g['veto'] or g['conflict']['verify_first']:return {'scale':0.,'delta':d,'gate':g}
        p=g['age_plasticity']*(g['meta']['p_applied'] if g['meta']['mode']=='ACTIVE' else 1.)
        return {'scale':round(g['eligibility']*d*g['modulator']['combined']*p,6),'delta':d,'gate':g}
    @staticmethod
    def _retag(p):
        """§16.3: tag only after distinct confirmations + measured stability (F7 or retention gate), never with veto or open retention errors."""
        if p['veto']>=VETO_BLOCK or p['repeated_errors']>0:p['tag']=False;return
        if len(p['confirmations'])>=TAG_CONFIRMATIONS and p['stable'] and not p['tag']:p['tag']=True;p['tag_reason']='CONFIRMED_STABLE'
    def _sync(self,st):
        rows=self.s.rows("SELECT rowid AS seq_id,kind,payload,created FROM packets WHERE rowid>? AND kind IN ('LearningTrace','ModulatorPacket','PlasticityState') ORDER BY rowid LIMIT ?",(st['cursor'],BATCH))
        for r in rows:
            pk=json.loads(r['payload']);seq=self._seq(r['created'])
            try:{'LearningTrace':self._trace,'ModulatorPacket':self._modulator,'PlasticityState':self._plasticity_state}[r['kind']](st,pk,seq)
            except (KeyError,TypeError,ValueError) as exc:self.s.log('neuromod_packet_skipped',pk.get('event_id'),{'kind':r['kind'],'error':type(exc).__name__})
            st['cursor']=r['seq_id']
        for p in st['paths'].values():self._retag(p)
        return len(rows)
    def sync(self):
        n=1;total=0
        while n:n=self._mutate(self._sync);total+=n
        return total
    # -- emit (for producers without their own packet code, e.g. AG6) ------------------------------------
    def touch(self,path,event_id,activity=1.,authority='SYSTEM',error=False,detail=None,refs=None):
        extra={'error':True} if error else {}
        if detail is not None:extra['detail']=detail
        return self.s.add_packet('LearningTrace',packet('LearningTrace','N10_NEUROMOD',event_id,self.s.generation_id,refs or [],
                                 path_id=path,activity=clamp(activity),eligibility=SLOW_DECAY,authority=authority,**extra))
    def signal(self,event_id,path=None,source_class='internal_crosscheck',finality='FINAL',safety_veto=False,irreversible=False,rollback_available=False,refs=None,**channels):
        if source_class not in SOURCE_WEIGHT:raise ValueError('Unbekannte Quellenklasse: '+str(source_class))
        ch={k:clamp(v,-1.,1.) for k,v in channels.items() if k in CHANNELS}
        if len(ch)!=len(channels):raise ValueError('Unbekannter Modulator-Kanal')
        extra=({'path_id':path} if path else {})|({'irreversible':True} if irreversible else {})|({'rollback_available':True} if rollback_available else {})
        return self.s.add_packet('ModulatorPacket',packet('ModulatorPacket','N10_NEUROMOD',event_id,self.s.generation_id,refs or [],
            epistemic_evidence=max(0.,ch.get('evidence_gain',0.)),human_correction=max(0.,ch.get('human_correction',0.)),
            task_success=max(0.,ch.get('task_success',0.)),resource_cost=max(0.,ch.get('cost_error',0.)),safety_veto=bool(safety_veto),
            channels=ch,source_class=source_class,finality=finality,**extra))
    # -- gate -------------------------------------------------------------------------------------------
    def _age_p(self,kind,p):
        if self.age is None:return 1.
        try:return clamp(self.age.plasticity(AGE_CAPABILITY[kind],novel_domain=p['novelty']>=.5,repeated_errors=p['repeated_errors']))
        except Exception:return 1.
    def gate(self,component,observe=True):
        """Plasticity gate for the next shadow job of `component`: factor in [0,1] scales LR and update norm."""
        self.sync();st,_=self._load();name=path_of(component);seq=self._seq()
        p=self._advance(json.loads(dumps(st['paths'].get(name) or empty_path()|{'seq':seq})),seq)
        e=clamp((1-SLOW_MIX)*p['fast']+SLOW_MIX*p['slow']);m=oplus(p['epistemic'],p['instrumental'])
        kind=kind_of(name);age_p=self._age_p(kind,p);veto=p['veto']>=VETO_BLOCK
        conflict=self.conflict(p);verify=conflict>=META['conflict_verify_before_learn']
        try:
            from .homeostasis import path_gain
            hg,hmode=path_gain(self.s,name)
        except Exception:hg,hmode=1.,'SHADOW'
        mf=self.meta_features(p);rule=self.meta_rule(mf);learned=self.meta_predict(st,mf);mode=st.get('meta_mode') or 'SHADOW'
        p_applied=round(clamp(rule*(.5+learned) if learned is not None else rule),6)
        if observe and learned is not None and name in st['paths'] and not veto and not verify:
            self._meta_compare(name,p,st,mf,rule,p_applied)
        meta_mult=p_applied if mode=='ACTIVE' else 1.
        factor=0. if veto or verify else round(clamp(age_p*meta_mult*(hg if hmode=='ACTIVE' else 1.)*(FLOOR+(1-FLOOR)*e*m),EPS,1.),6)
        return {'revision':REVISION,'path_id':name,'kind':kind,'factor':factor,'eligibility':round(e,6),
                'modulator':{'epistemic':round(p['epistemic'],6),'instrumental':round(p['instrumental'],6),'combined':round(m,6)},
                'age_plasticity':round(age_p,6),'repeated_errors':p['repeated_errors'],'veto':veto,'veto_level':round(p['veto'],6),
                'consolidation_tag':p['tag'],'native_parameter_authority':0,
                'delta':p.get('delta'),'error_level':round(p.get('error_level',0.),6),'r_hat':p.get('r_hat'),
                'meta':{'mode':mode,'features':mf,'rule_p':rule,'learned_p_help':learned,'p_applied':p_applied},
                'conflict':{'level':conflict,'verify_first':verify,'support':round(p.get('support',0.),6),'contra':round(p.get('contra',0.),6)},
                'homeostasis':{'gain':round(hg,6),'mode':hmode}}
    @staticmethod
    def conflict(p):
        """Share of the weaker side when both supporting and contradicting evidence are substantial; else 0."""
        s,c=p.get('support',0.),p.get('contra',0.)
        return round(min(s,c)/max(s,c),6) if min(s,c)>=CONFLICT_MIN else 0.
    def clear_veto(self,component):
        def f(st):
            p=st['paths'].get(path_of(component))
            if not p:raise ValueError('Unbekannter Pfad')
            p['veto']=0.;return True
        out=self._mutate(f);self.s.log('neuromod_veto_cleared',None,{'path':path_of(component)});return out
    # -- sleep (§16.3 eligibility is short-lived) --------------------------------------------------------
    def sleep(self):
        self.sync()
        def f(st):
            seq=self._seq();pruned=0
            for name in list(st['paths']):
                p=self._advance(st['paths'][name],seq);p['fast']=0.;d=SLOW_DECAY**SLEEP_EVENTS
                for k in ('slow','epistemic','instrumental','veto','novelty'):p[k]*=d
                for k in ('support','contra'):
                    if k in p:p[k]*=d
                self._retag(p)
                if not p['tag'] and p['repeated_errors']==0 and max(p['slow'],p['epistemic'],p['instrumental'],p['veto'])<EPS:st['paths'].pop(name);pruned+=1
            st['sleeps']+=1
            return {'paths':len(st['paths']),'pruned':pruned,'tagged':sorted(k for k,p in st['paths'].items() if p['tag'])}
        return self._mutate(f)
    def tags(self):self.sync();return {k:p['tag_reason'] for k,p in self._load()[0]['paths'].items() if p['tag']}
    def report(self,component=None):
        self.sync();st,_=self._load();names=[path_of(component)] if component else sorted(st['paths'])
        return {'revision':REVISION,'paths':{n:self.gate(n,observe=False) for n in names},'unassigned_modulators':st['unassigned_modulators'],'sleeps':st['sleeps'],
                'claim_limit':'Scales explicit shadow-job budgets only; local error δ stays in each worker; no commit, consolidation or native-weight authority'}

def step(n,path):
    """Head-side WP-U6 helper: 1.0 without a neuromod controller or on any error (never blocks a head)."""
    if n is None:return 1.
    try:return float(n.step_scale(path))
    except Exception:return 1.

def controller(runtime):
    """Runtime-scoped instance (like age.controller); uses the live Age envelope when present."""
    n=getattr(runtime,'neuromod',None)
    if n is None:
        age=None
        try:
            from .age import controller as age_controller
            age=age_controller(runtime)
        except Exception:age=None
        n=runtime.neuromod=Neuromod(runtime.store,age)
    return n

def operator_command(r,args):
    """:neuromod [status|path <name>|sleep|clear-veto <name>]"""
    n=controller(r)
    if not args or args==['status']:return dumps(n.report())
    if args[0]=='path' and len(args)==2:return dumps(n.report(args[1]))
    if args[0]=='sleep' and len(args)==1:return dumps(n.sleep())
    if args[0]=='clear-veto' and len(args)==2:return dumps({'cleared':n.clear_veto(args[1])})
    if args[0]=='local' and len(args)==2 and args[1] in ('shadow','active'):return dumps({'local_mode':n.set_local_mode(args[1].upper(),'EXPLICIT_HUMAN' if args[1]=='active' else 'SYSTEM')})
    if args[0]=='meta' and len(args)==2 and args[1] in ('shadow','active'):return dumps({'meta_mode':n.set_meta_mode(args[1].upper(),'EXPLICIT_HUMAN' if args[1]=='active' else 'SYSTEM')})
    raise ValueError(':neuromod [status|path <Name>|sleep|clear-veto <Name>|meta shadow|meta active|local shadow|local active]')
