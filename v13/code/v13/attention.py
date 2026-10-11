"""WP-N5 / F1, §4B, §5.1-5.2, A4 (§51.5), L9.1, §60, §48.14: attention requests, thalamic gain, admission.

Three separate signals (§5, §60 "high gain != high truth"; never one confidence scalar):
  salience     S  bottom-up "this matters now"  (SAL.*: novelty, conflict, prediction error, goal violation, interrupt)
  cautiousness C  "look again before acting"    (CAUT.*: source risk, B1/B2 disagreement, world surprise, ...)
  gain         g  coupling strength per region edge (GAIN.*), driven by S and C, relaxes back to its BOOT base
                  per experience event (homeostasis). Gain scales admission and coupling only; it never touches
                  confidence, truth status or fact authority.

F1 admission (§4B.2-4B.3): JEF, B1/B2, Salience, World prediction and A4 file AttentionRequests; F1 grants them under a
per-event budget ordered by priority x target gain. Answers are GRANTED or the canonical NOT_AVAILABLE / TOO_EXPENSIVE.
Teacher views exist only at Age 0, are tagged and carry no extra priority (rule 6).

A4 (§51.5): text-span salience proposal over PerceptPacket segments. No chunk ever disappears: suppression is capped at
A4.suppression_max and every segment keeps its SourceRef; high-res re-looks become AttentionRequests.

Learning (§4B.4): a grant touches the eligibility trace of path `attention_policy` in WP-N10; a reported outcome sends a
typed modulator there and updates a per (reason,target) usefulness prior. That learned prior runs SHADOW at Age 0
(rule 8): it is computed and logged next to the scaffold score but only blends into admission after an explicit human
switch to ACTIVE. Native body attention is never patched (rule 9, L9.1).
All numbers are BOOT priors from the blueprint (§51.5, §60) or marked BOOT here, not measured optima.
"""
import json
import math
import re
import time
from .common import dumps
from .contracts import packet
from .neuromod import step

KEY='N5_ATTENTION';REVISION='n5-attention-v1';PATH='attention_policy'
GAIN={'perceptual':.55,'callosum':.40,'workspace':.60,'focal':.65,'action':.55}  # §60
SAL={'novelty':.35,'conflict':.65,'prediction_error':.55,'goal_violation':.75,'external_interrupt':.80}  # §60
CAUT={'source_risk':.70,'B1_B2_disagreement':.55,'world_surprise':.45,'router_instability':.35,'teacher_dependence':.25}  # §60
A4={'salience_gain':.45,'goal_topdown_gain':.45,'novelty_gain':.35,'teacher_hint_gain':.20,'raw_relook_authority':.70,
    'suppression_max':.70,  # §51.5
    'attention_temperature':.25,'reentry_threshold':.35,'max_highres_regions':3}  # BOOT (§0 A4 knobs are TUNE/USER)
# BOOT: how salience recruits and caution reshapes each coupling (§5.1). Caution raises re-look and B1<->B2 cross-check,
# lowers action authority; salience recruits perception, workspace and focus but never action.
SAL_EFFECT={'perceptual':.5,'callosum':.3,'workspace':.5,'focal':.4,'action':0.}
CAUT_EFFECT={'perceptual':.2,'callosum':.4,'workspace':0.,'focal':.1,'action':-.6}
GAIN_RATE=.5;RELAX=.7;GAIN_MIN=.05;GAIN_MAX=1.  # BOOT: move half-way per modulation, relax per experience event
INTERRUPT=.6       # BOOT: salience at/above which bottom-up may interrupt the JEF focus (rule 3)
EDGES={'E_A_B':'perceptual','E_A4_B':'perceptual','E_B1_B2':'callosum','E_B2_B1':'callosum','E_B_C4':'workspace',
       'E_B1_C1_OFFER':'workspace','E_B2_C1_OFFER':'workspace','E_C4_B4_GAIN':'focal','E_C4_C5':'action'}
TARGETS=('A_SOURCE','B1','B2','MEMORY','WORLD','TOOL','SELF')  # §4B.2
REASONS=('novelty','conflict','exactness','goal','verify','recall')
REQUESTERS=('JEF','B1','B2','SALIENCE','WORLD','A4','TEACHER')
TARGET_GAIN={'A_SOURCE':'perceptual','B1':'callosum','B2':'callosum','MEMORY':'workspace','WORLD':'workspace','TOOL':'action','SELF':'workspace'}
DELIVERY={'A_SOURCE':'high_res_source_span','B1':'b1_fine_slots','B2':'b2_gist_slots','MEMORY':'exact_memory',
          'WORLD':'world_prediction','TOOL':'tool_result','SELF':'self_state'}  # §4B.3
STATUSES=('GRANTED','NOT_AVAILABLE','TOO_EXPENSIVE')
EVENT_BUDGET=1024  # BOOT abstract cost units (~tokens) per event and body (rule 7)
PRESSURE_CUT=.75   # BOOT: full resource pressure leaves a quarter of the budget
LEARNED_MAX=.25;POLICY_RATE=.2  # BOOT: ACTIVE learned prior may shift a score by at most a quarter
STOP=frozenset('the a an and or of to in on for is are was be it this that with as at by from what how why which who you your i we they'.split())
NEGATION=frozenset('not no never none nothing nicht kein keine nie without except unless'.split())
RECENT_EVENTS=3   # BOOT: modulators of the last prior events of the session feed the next gain step, decayed by RELAX
SOURCE_DELIVERY='high_res_source_span'

def clamp(x,lo=0.,hi=1.):
    x=float(x)
    if not math.isfinite(x):raise ValueError('Wert nicht endlich')
    return min(hi,max(lo,x))
def oplus(values):
    out=1.
    for v in values:out*=1-clamp(v)
    return 1-out
def terms(text):return [t for t in re.findall(r"[\w']+",str(text).lower()) if len(t)>2 and t not in STOP]
def empty():return {'revision':REVISION,'gains':dict(GAIN),'seq':0,'mode':'SHADOW','policy':{},'last':None}

def salience(**x):
    """§5.2 bottom-up salience in [0,1]; unknown channels are an error, not silently ignored."""
    if set(x)-set(SAL):raise ValueError('Unbekannter Salienz-Kanal')
    return oplus(SAL[k]*clamp(v) for k,v in x.items())
def caution(**x):
    if set(x)-set(CAUT):raise ValueError('Unbekannter Vorsichts-Kanal')
    return oplus(CAUT[k]*clamp(v) for k,v in x.items())
def from_modulators(ch):
    """Map WP-N10 modulator channels onto salience/caution inputs (shared vocabulary, separate effects)."""
    s={'novelty':max(0.,ch.get('novelty',0.)),'prediction_error':max(0.,ch.get('surprise',0.),ch.get('world_prediction_error',0.))}
    c={'world_surprise':max(0.,ch.get('world_prediction_error',0.)),'source_risk':max(0.,ch.get('calibration_error',0.))}
    if ch.get('rule_violation',0.)>0:s['goal_violation']=ch['rule_violation']
    return {k:v for k,v in s.items() if v},{k:v for k,v in c.items() if v}
def offer_features(offer):
    """Admission features of a B1/B2 OfferPacket for WP-N1. Uncertainty stays a separate field (§93)."""
    o=offer['offer'];refs=len(offer.get('evidence_refs') or [])
    conflict=1. if o.get('needs_reentry') else 0.
    return {'id':offer['packet_id'],'kind':'B1' if offer['role']=='B1_DETAIL' else 'B2','priority':.5,
            'salience':salience(conflict=conflict),'exactness':min(1.,refs/2),'uncertainty':1. if o.get('uncertainty') else 0.,
            'needs_reentry':bool(o.get('needs_reentry'))}

def cues(text):
    """Exact cues of a span (numbers, quoted strings, negations): what a high-res re-look exists to preserve."""
    t=str(text);out={m for m in re.findall(r"\d+(?:[.,]\d+)*",t)}|{q.strip().lower() for q in re.findall(r'"([^"]{1,60})"',t) if q.strip()}
    return out|{w for w in re.findall(r"[\w']+",t.lower()) if w in NEGATION}
def coverage(span,output):
    """Fraction of a span's exact cues that reach the output; None when the span has no exact cue (no label)."""
    c=cues(span)
    if not c:return None
    o=str(output).lower();nums=set(re.findall(r"\d+(?:[.,]\d+)*",o));words=set(re.findall(r"[\w']+",o))
    return sum((x in nums) if re.fullmatch(r"\d+(?:[.,]\d+)*",x) else (x in words) if x in NEGATION else (x in o) for x in c)/len(c)

class Attention:
    def __init__(self,store,age=None,neuromod=None):
        self.s=store;self.age=age;self.n=neuromod
    # -- state ------------------------------------------------------------------------------------------
    def _seq(self):return int(self.s.one('SELECT COALESCE(MAX(rowid),0) AS n FROM events')['n'])
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st=empty()
        if st.get('revision')!=REVISION:raise ValueError('Attention state revision mismatch')
        return st,v
    def _relax(self,st):
        """Homeostasis: each new experience event pulls every gain back towards its base (§5.1, lazy)."""
        seq=self._seq();d=RELAX**max(0,seq-st['seq'])
        st['gains']={k:GAIN[k]+(st['gains'].get(k,GAIN[k])-GAIN[k])*d for k in GAIN};st['seq']=seq
    def _mutate(self,fn):
        for attempt in (0,1):
            st,v=self._load();self._relax(st);out=fn(st);dumps(st)
            try:self.s.set_state(KEY,st,expected=v);return out
            except ValueError:
                if attempt:raise
    def gains(self):
        st,_=self._load();self._relax(st);return {k:round(v,6) for k,v in st['gains'].items()}
    def coupling(self,edge):
        """Coupling strength of a PathSpec edge (§0 E_*); unknown edges get no implicit gain."""
        if edge not in EDGES:raise ValueError('Unbekannte Kante: '+str(edge))
        return self.gains()[EDGES[edge]]
    # -- thalamic gain (§5.1, §48.14) -------------------------------------------------------------------
    def modulate(self,event_id,sal=None,caut=None,modulators=None):
        """One gain step from separate salience and caution inputs. Returns gains, S, C and the interrupt decision."""
        sal=dict(sal or {});caut=dict(caut or {})
        if modulators:
            ms,mc=from_modulators(modulators)
            for k,v in ms.items():sal[k]=max(sal.get(k,0.),v)
            for k,v in mc.items():caut[k]=max(caut.get(k,0.),v)
        S=salience(**sal);C=caution(**caut)
        def f(st):
            for k,base in GAIN.items():
                target=clamp(base*(1+SAL_EFFECT[k]*S)*(1+CAUT_EFFECT[k]*C),GAIN_MIN,GAIN_MAX)
                st['gains'][k]=st['gains'][k]+GAIN_RATE*(target-st['gains'][k])
            top=max(sal,key=lambda k:SAL[k]*clamp(sal[k])) if sal else None
            st['last']={'event_id':event_id,'salience':round(S,6),'caution':round(C,6),'top':top}
            return {k:round(v,6) for k,v in st['gains'].items()},top
        g,top=self._mutate(f);interrupt=S>=INTERRUPT
        out={'gains':g,'salience':round(S,6),'caution':round(C,6),'interrupt':interrupt,'interrupt_reason':top if interrupt else None,
             'truth_authority':0}
        self.s.log('attention_gain',event_id,{'salience':out['salience'],'caution':out['caution'],'interrupt':interrupt}|{'gain_'+k:v for k,v in g.items()})
        return out
    # -- workspace admission for WP-N1 (F1d) ------------------------------------------------------------
    def rank(self,candidates,goal_terms=None):
        """Order focal candidates by admission score; adds `admission_score`, keeps every input field untouched.
        candidate: {'id','kind' in TARGETS or B1/B2,'priority','salience','exactness'?,'goal_binding'?}."""
        g=self.gains();out=[]
        for c in candidates:
            base=.4*clamp(c.get('priority',.5))+.35*clamp(c.get('salience',0.))+.15*clamp(c.get('goal_binding',0.))+.1*clamp(c.get('exactness',0.))
            out.append(dict(c,admission_score=round(base*g['workspace']/GAIN['workspace'],6)))
        return sorted(out,key=lambda c:(-c['admission_score'],str(c.get('id'))))
    # -- F1 request / response (§4B.2-4B.4) -------------------------------------------------------------
    def request(self,event_id,requester,target,reason,priority=.5,budget=64,resolution='default',source_ref=None,expires_at=None,refs=None):
        if requester not in REQUESTERS:raise ValueError('Unbekannter Anforderer')
        if target not in TARGETS:raise ValueError('Unbekanntes Ziel')
        if reason not in REASONS:raise ValueError('Unbekannter Grund')
        if isinstance(budget,bool) or not isinstance(budget,int) or budget<1:raise ValueError('Budget muss positive Ganzzahl sein')
        if requester=='TEACHER':priority=min(clamp(priority),A4['teacher_hint_gain'])  # rule 6: no special right
        if resolution=='teacher_view' and requester!='TEACHER':raise ValueError('Lehrer-Sicht nur von der Lehrer-Spur')
        p=packet('AttentionRequest','F1_ATTENTION',event_id,self.s.generation_id,refs or ([source_ref] if source_ref else []),
                 requester=requester,target=target,reason=reason,priority=clamp(priority),budget=budget,resolution=str(resolution),
                 source_ref=source_ref,expires_at=expires_at)
        return self.s.add_packet('AttentionRequest',p)
    def _learned(self,st,r):
        q=st['policy'].get(r['reason']+'|'+r['target'])
        return 0. if not q else clamp(q['mean'],-1.,1.)*min(1.,q['n']/5)
    def admit(self,event_id,requests,budget=EVENT_BUDGET,pressure=0.,providers=None,clock=None):
        """Grant requests under the event budget. providers: optional {target: fn(request)->payload|None}.
        Without a provider a grant is an admission decision the caller fulfils itself."""
        now=time.time() if clock is None else clock
        cap=int(budget*(1-PRESSURE_CUT*clamp(pressure)));left=cap;st,_=self._load();self._relax(st);g=st['gains'];active=st['mode']=='ACTIVE'
        stage=self._stage();scored=[]
        for r in requests:
            scaffold=r['priority']*g[TARGET_GAIN[r['target']]]/max(g.values());learned=self._learned(st,r)
            score=scaffold*(1+LEARNED_MAX*learned) if active else scaffold
            scored.append((score,scaffold,learned,r))
        scored.sort(key=lambda x:(-x[0],x[3]['packet_id']));responses=[]
        for score,scaffold,learned,r in scored:
            status,detail,payload='GRANTED',None,None
            if r['event_id']!=event_id:status,detail='NOT_AVAILABLE','other_event'
            elif r.get('expires_at') is not None and r['expires_at']<now:status,detail='NOT_AVAILABLE','expired'
            elif r['resolution']=='teacher_view' and stage!=0:status,detail='NOT_AVAILABLE','teacher_view_age0_only'
            elif r['budget']>left:status,detail='TOO_EXPENSIVE','event_budget'
            elif providers is not None:
                fn=providers.get(r['target'])
                payload=fn(r) if fn else None
                if payload is None:status,detail='NOT_AVAILABLE','no_provider' if not fn else 'empty'
            if status=='GRANTED':left-=r['budget']
            resp=packet('AttentionResponse','F1_ATTENTION',event_id,self.s.generation_id,r.get('provenance') or [],
                        request_packet_id=r['packet_id'],status=status,detail=detail,delivery=DELIVERY[r['target']] if status=='GRANTED' else None,
                        granted_budget=r['budget'] if status=='GRANTED' else 0,score=round(score,6),scaffold_score=round(scaffold,6),
                        learned_shadow=round(learned,6),policy_mode=st['mode'],teacher_tagged=r['resolution']=='teacher_view',
                        truth_authority=0,payload=payload)
            self.s.add_packet('AttentionResponse',resp);responses.append(resp)
            if status=='GRANTED' and self.n is not None:
                self.n.touch(PATH,event_id,activity=clamp(score),detail={'request':r['packet_id'],'reason':r['reason'],'target':r['target']})
        self.s.log('attention_round',event_id,{'requests':len(requests),'granted':sum(x['status']=='GRANTED' for x in responses),
                   'too_expensive':sum(x['status']=='TOO_EXPENSIVE' for x in responses),'budget':cap,'left':left,'mode':st['mode']})
        return responses
    def outcome(self,response_packet_id,usefulness,source_class='internal_crosscheck'):
        """§4B.4: was the granted resource useful? usefulness in [-1,1]. Updates the shadow prior + N10 modulator."""
        u=clamp(usefulness,-1.,1.)
        row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='AttentionResponse'",(response_packet_id,))
        if not row:raise ValueError('Unbekannte Attention-Antwort')
        resp=json.loads(row['payload'])
        if resp['status']!='GRANTED':raise ValueError('Nur gewährte Anfragen haben ein Ergebnis')
        req=json.loads(self.s.one("SELECT payload FROM packets WHERE id=? AND kind='AttentionRequest'",(resp['request_packet_id'],))['payload'])
        key=req['reason']+'|'+req['target'];sc=step(self.n,PATH)  # WP-U6 §12.7
        def f(st):
            q=st['policy'].setdefault(key,{'n':0,'mean':0.,'outcomes':[]})
            if response_packet_id in q['outcomes']:raise ValueError('Ergebnis schon verbucht')
            q['n']+=1;q['mean']+=sc*max(POLICY_RATE,1/q['n'])*(u-q['mean']);q['outcomes']=(q['outcomes']+[response_packet_id])[-32:]
            return dict(q,outcomes=len(q['outcomes']))
        q=self._mutate(f)
        if self.n is not None:
            ch={'task_success':u} if u>0 else {'action_error':-u} if u<0 else {}
            self.n.signal(resp['event_id'],path=PATH,source_class=source_class,refs=[],**ch)
        self.s.log('attention_outcome',resp['event_id'],{'key':key,'usefulness':u,'n':q['n'],'mean':round(q['mean'],6)})
        return {'key':key,'n':q['n'],'mean':round(q['mean'],6)}
    def recent_modulators(self,event_id,session=None,limit=RECENT_EVENTS):
        """N10 channels of the last `limit` prior events (same session), max per channel, decayed RELAX per event back.
        Feeds modulate(); only positive magnitudes count (salience/caution are unsigned)."""
        rows=self.s.rows("SELECT p.event_id,p.payload FROM packets p JOIN events e ON e.id=p.event_id WHERE p.kind='ModulatorPacket' AND e.rowid<(SELECT rowid FROM events WHERE id=?) AND (? IS NULL OR e.session_id=?) ORDER BY p.rowid DESC LIMIT 64",(event_id,session,session))
        order=[];ch={}
        for r in rows:
            if r['event_id'] not in order:
                if len(order)>=limit:break
                order.append(r['event_id'])
            w=RELAX**order.index(r['event_id'])
            try:from .neuromod import channels_from;c=channels_from(json.loads(r['payload']))
            except Exception:continue
            for k,v in c.items():
                if v>0:ch[k]=max(ch.get(k,0.),w*v)
        return {k:round(v,6) for k,v in ch.items()}
    def source_outcome(self,event_id,source_text,output):
        """§4B.4 outcome for A4 high-res re-looks: did the exact cues of the granted span reach the answer?
        usefulness = .75*coverage - .25 in [-.25,.5]; spans without exact cues get no label. Internal cross-check only."""
        done=[]
        for r in self.s.rows("SELECT id,payload FROM packets WHERE kind='AttentionResponse' AND event_id=?",(event_id,)):
            resp=json.loads(r['payload'])
            if resp['status']!='GRANTED' or resp.get('delivery')!=SOURCE_DELIVERY:continue
            req=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='AttentionRequest'",(resp['request_packet_id'],))
            ref=(json.loads(req['payload']).get('source_ref') or {}) if req else {}
            cov=coverage(str(source_text)[int(ref.get('char_start',0)):int(ref.get('char_end',0))],output)
            if cov is None:continue
            try:q=self.outcome(r['id'],round(.75*cov-.25,6))
            except ValueError:continue
            done.append({'response':r['id'],'coverage':round(cov,4),'key':q['key']})
        return done
    def set_mode(self,mode,authority):
        """Learned attention leaves SHADOW only on an explicit human decision (rule 8, Age 0 conservative)."""
        if mode not in {'SHADOW','ACTIVE'}:raise ValueError('Modus SHADOW|ACTIVE')
        if mode=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE braucht ausdrückliche Nutzerfreigabe')
        def f(st):st['mode']=mode;return mode
        out=self._mutate(f);self.s.log('attention_mode',None,{'mode':mode,'authority':authority});return out
    def _stage(self):
        if self.age is None:return 0
        try:return int(self.age.ceiling('language') if hasattr(self.age,'ceiling') else self.age.system_stage())  # WP-T2: language capability's Age
        except Exception:return 0
    # -- A4 perceptual salience (§51.5) -----------------------------------------------------------------
    def perceive(self,event_id,segments,goal='',known_terms=None,teacher_hints=None,file_requests=True):
        """Score text segments; returns one entry per segment (none dropped) and files high-res AttentionRequests."""
        goal_t=set(terms(goal));seen=set(known_terms or ());hints=teacher_hints or {};g=self.gains()['perceptual']/GAIN['perceptual']
        rows=[]
        for i,seg in enumerate(segments):
            t=terms(seg['text']);raw=re.findall(r"\S+",seg['text'])
            cues=sum(bool(re.search(r'\d',w)) for w in raw)+sum(w.lower().strip('.,;:!?') in NEGATION for w in raw)+seg['text'].count('?')+seg['text'].count('"')
            bottom=min(1.,cues/max(1.,.25*len(raw)))
            top=len(goal_t&set(t))/len(goal_t) if goal_t else 0.
            nov=sum(x not in seen for x in t)/len(t) if t else 0.
            hint=min(clamp(hints.get(i,0.)),A4['teacher_hint_gain'])  # capped teacher bias
            score=clamp(g*(A4['salience_gain']*bottom+A4['goal_topdown_gain']*top+A4['novelty_gain']*nov+hint))
            parts={'exactness':A4['salience_gain']*bottom,'goal':A4['goal_topdown_gain']*top,'novelty':A4['novelty_gain']*nov}
            rows.append({'index':i,'source_ref':seg['source_ref'],'score':round(score,6),'bottom_up':round(bottom,6),'top_down':round(top,6),
                         'novelty':round(nov,6),'teacher_hint':round(hint,6),'reason':max(parts,key=parts.get)})
            seen.update(t)
        if rows:
            T=A4['attention_temperature'];m=max(r['score'] for r in rows);z=[math.exp((r['score']-m)/T) for r in rows];Z=sum(z)
            for r,w in zip(rows,z):
                r['weight']=round(w/Z,6)
                r['suppression']=round(A4['suppression_max']*(1-r['score']/m) if m>0 else 0.,6)  # never 1: chunk stays
                r['recoverable']=True
        relook=sorted((r for r in rows if r['score']>=A4['reentry_threshold']),key=lambda r:(-r['score'],r['index']))[:A4['max_highres_regions']]
        reqs=[]
        if file_requests:
            for r in relook:
                reqs.append(self.request(event_id,'A4','A_SOURCE',r['reason'],priority=r['score']*A4['raw_relook_authority'],
                                         budget=max(1,(r['source_ref']['char_end']-r['source_ref']['char_start'])//4+1),
                                         resolution='high_res',source_ref=r['source_ref']))
        return {'segments':rows,'highres':[r['index'] for r in relook],'requests':reqs,'truth_authority':0}
    def perceive_packet(self,percept,goal='',known_terms=None):
        return self.perceive(percept['event_id'],percept['segments'],goal,known_terms)
    def report(self):
        st,_=self._load();self._relax(st)
        return {'revision':REVISION,'gains':{k:round(v,6) for k,v in st['gains'].items()},'base':GAIN,'mode':st['mode'],'last':st['last'],
                'policy':{k:{'n':q['n'],'mean':round(q['mean'],6)} for k,q in sorted(st['policy'].items())},
                'claim_limit':'Gain scales admission and coupling only; no truth, confidence or native-attention authority'}

def controller(runtime):
    """Runtime-scoped instance without touching runtime.py (like age/neuromod controllers)."""
    a=getattr(runtime,'attention',None)
    if a is None:
        age=n=None
        try:
            from .age import controller as age_controller
            age=age_controller(runtime)
        except Exception:age=None
        try:
            from .neuromod import controller as neuromod_controller
            n=neuromod_controller(runtime)
        except Exception:n=None
        a=runtime.attention=Attention(runtime.store,age,n)
    return a

def operator_command(r,args):
    """:attention [status|edge <Kante>|shadow|active]"""
    a=controller(r)
    if not args or args==['status']:return dumps(a.report())
    if args[0]=='edge' and len(args)==2:return dumps({'edge':args[1],'gain':a.coupling(args[1])})
    if args==['shadow']:return dumps({'mode':a.set_mode('SHADOW','EXPLICIT_HUMAN')})
    if args==['active']:return dumps({'mode':a.set_mode('ACTIVE','EXPLICIT_HUMAN')})  # typed by the operator = explicit
    raise ValueError(':attention [status|edge <Kante>|shadow|active]')
