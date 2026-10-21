"""WP-N1 JEF focal loop (C4), B4 multi-slot workspace, Inquisition P1<->P2 (§10) and C5 action gate.

Blueprint: §3.2A, §3.3.7, §3.4.5-3.4.6, §4.4, §6.4, §8.1-8.2A, §10-10.1, §59, §60, §85.3-85.5, §93, G3D, G5.

FOCAL_LOOP (§3.3.7) is system recurrence, not LM recurrence: read coalition -> deliberate
(Inquisition) -> decide (incorporate / targeted re-entry) -> receive offer -> update -> repeat
until halt, cycle budget or deadline. The coalition is a small, prioritised, versioned set of
FocalItems (§93) drawn from B1/B2 offers, memory and items retained from earlier turns.

Claim limits (honest scope):
- Every gain/threshold is a BOOT value (§59/§60) or a labelled BOOT engineering choice; nothing
  here is learned or Redmi-measured. Conflict/uncertainty are lexical proxies over offer text
  (numbers, negation, hedges), not calibrated semantic judgements.
- P1/P2 are deterministic scaffold roles (Age 0/1 forced P1->P2 sequence, §10); no trained
  deliberation space exists yet. Mode selection beyond that needs Age right ``deliberation_modes``.
- Halting is fixed-budget (§10.1 Phase B). An existing learned halt readout may only advise once,
  inside the budget; hard deadline stays with the runtime governor.
- Body hypotheses never become facts; prior-turn items stay PRIOR_HYPOTHESIS and are never fed to
  the report as current offers. C5 BOOT utilities reproduce the former route->role table; focal
  support can only reorder within a margin, permission/resource gates can suppress.
"""
import json
import math
import re
import time
from .common import dumps,now
from .contracts import packet,offer_is_fresh,SLOT_FIELDS
from .memory import ENTITY_LABELS,entities,relevance,terms
from .attention import GAIN as ATT_BASE

BODY=('B1_DETAIL','B2_GIST')
STATE_TYPES=('ACTIVE','REACTIVATABLE','EPISODIC_POINTER')
# §59 / §60 / §85.4 BOOT values; engineering BOOT values are marked ENG.
BOOT={'coalition_threshold':.45,'disagreement_trigger':.40,'uncertainty_trigger':.45,'salience_trigger':.65,
      'inquisition_depth':.35,'max_cycles_age0':3,'gain_focal':.65,'gain_action':.55,'sal_interrupt':.80,
      'uncertainty_coupling_gain':.50,  # ENG: §85.4 names the knob without a value
      'turn_decay':.6,'reactivatable_floor':.25,'drop_floor':.05,'workspace_factor':2}  # ENG
WEIGHTS={'goal':.30,'conflict':.15,'uncertainty':.15,'salience':.10,'utility':.20,'source_quality':.20,'redundancy':-.25,'cost':-.10}  # §93 structure, ENG weights
# WP-Z5c note recency (switch focal_note_recency, default 0): stored notes whose keys differ only by calendar words are versions
# of one slot; the newest stored version gets `recency`, older ones `superseded`. ENG weights, preregistered before any run.
WEIGHTS|={'recency':.10,'superseded':-.30}
CALENDAR=set('january february march april may june july august september october november december '
             'januar februar märz maerz mai juni juli oktober dezember monday tuesday wednesday thursday friday saturday sunday '
             'montag dienstag mittwoch donnerstag freitag samstag sonntag'.split())
SCALE={'B1_DETAIL':'fine','B2_GIST':'gist','MEMORY':'event'}
NUM=re.compile(r'(?<![\w.])-?\d+(?:[.,]\d+)?')
NEG=re.compile(r"\b(?:not|no|never|none|false|incorrect|wrong|nicht|kein\w*|nie|falsch)\b|n't",re.I)
HEDGE=re.compile(r'unclear|unsure|uncertain|unknown|not sure|missing|ambig|maybe|might|could be|depends|conflict|contradict|unklar|unsicher|fehlt|vielleicht|widerspr',re.I)
CALM=re.compile(r'^\s*(?:none|low|no|n/?a|keine?|gering|niedrig)\b',re.I)
DEEPER=re.compile(r'think (?:hard|deeply|carefully)|step by step|double.?check|verify|be thorough|gründlich|schritt für schritt|genau prüfen|nochmal prüfen',re.I)

def clip(x):return max(0.,min(1.,float(x)))
def numbers(t):return {x.replace(',','.') for x in NUM.findall(t or '')}
def disagreement(a,b):
    """Lexical contradiction proxy in [0,1]: same topic but different numbers or negation polarity."""
    shared=len(terms(a or '')&terms(b or ''))
    if not shared:return 0.
    na,nb=numbers(a),numbers(b);num=len(na^nb)/len(na|nb) if na and nb else 0.
    neg=1. if shared>=2 and bool(NEG.search(a))!=bool(NEG.search(b)) else 0.
    return round(clip(.6*num+.4*neg),4)
FIELD=r'"(%s)"\s*:\s*"((?:[^"\\]|\\.)*)'
def token_confidence(pairs,field='summary'):
    """Compact confidence from native (token, logprob) pairs of one JSON offer. Raw model probabilities: grammar-forced
    JSON syntax tokens can be improbable, so the value span of `field` is reported separately."""
    pairs=[(str(t),float(lp)) for t,lp in pairs if isinstance(lp,(int,float)) and math.isfinite(lp)]
    text='';starts=[]
    for t,_ in pairs:starts.append(len(text));text+=t
    m=re.search(FIELD%re.escape(field),text)
    lo,hi=(m.start(2),m.end(2)) if m else (0,-1)
    alls=[lp for t,lp in pairs if t.strip()];span=[lp for (t,lp),st in zip(pairs,starts) if t.strip() and lo<=st<hi]
    mean=lambda v:round(math.exp(sum(v)/len(v)),4) if v else None
    return {'n':len(pairs),'mean_prob':mean(alls),'field':field,'field_tokens':len(span),'field_mean_prob':mean(span),
            'field_min_prob':round(math.exp(min(span)),4) if span else None}
# WP-KAL2: offer uncertainty from token log-probabilities (KALIBRIERUNG.md: HEDGE regex never fired, AUROC .50).
# key = which token_confidence value; pivot = token uncertainty (1-p) per body that maps onto BOOT uncertainty_trigger.
# Measured 2026-10-09 (kalibrierung2-20261009/offers.json, n=40 each, solve prompt): least probable summary token is the
# best error signal (AUROC B1 .88, B2 .72; all-token mean .59/.71). Youden pivots differ per model, so they are per
# role and bound to the model revision: after a body swap they are REFIT values, not facts.
TOKEN_UNC={'key':'field_min_prob','pivot':{'B1_DETAIL':.65,'B2_GIST':.86},'default_pivot':.75}
def offer_uncertainty(p):
    o=p['offer'];tc=(p.get('native_metrics') or {}).get('token_confidence') or {}
    conf=tc.get(TOKEN_UNC['key'])
    if isinstance(conf,(int,float)):
        tu=1-clip(conf);t=TOKEN_UNC['pivot'].get(p.get('role'),TOKEN_UNC['default_pivot']);trig=BOOT['uncertainty_trigger']
        u=trig*tu/t if tu<=t else trig+(1-trig)*(tu-t)/(1-t)   # piecewise linear: pivot -> trigger
        if o.get('needs_reentry'):u=max(u,.6)
    else:  # runner without logprobs: legacy text proxy
        u=.6 if o.get('needs_reentry') else .15
        text=o.get('uncertainty','')
        if text and not CALM.search(text) and HEDGE.search(text):u+=.25
    if not p['evidence_refs']:u+=.1
    return round(clip(u),4)
def source_quality(p):
    n=len(p['evidence_refs']);bad=p.get('rejected_quotes',0)
    return round(n/(n+bad),4) if n else (.4 if not bad else .2)

def priority(t):return round(clip(sum(WEIGHTS[k]*t.get(k,0.) for k in WEIGHTS)),4)

def covered(refs):
    """§8.2 covered range: union of exact source spans per source, in source order."""
    by={}
    for r in refs or ():
        if isinstance(r,dict) and isinstance(r.get('source_id'),str) and isinstance(r.get('char_start'),int) and isinstance(r.get('char_end'),int):
            by.setdefault(r['source_id'],[]).append((r['char_start'],r['char_end']))
    out=[]
    for sid,spans in by.items():
        cur=None
        for a,b in sorted(spans):
            if cur and a<=cur[1]:cur[1]=max(cur[1],b)
            else:
                if cur:out.append({'source_id':sid,'char_start':cur[0],'char_end':cur[1]})
                cur=[a,b]
        out.append({'source_id':sid,'char_start':cur[0],'char_end':cur[1]})
    return out

END=re.compile(r'[.!?;:\n]\s*$')
def boundary(store,refs):
    """§8.2 boundary confidence as a labelled lexical proxy: share of span ends that sit on a sentence/clause edge
    (source start/end, or . ! ? ; : newline) in the exact source. Unreadable sources contribute nothing."""
    hits=[]
    for r in refs or ():
        try:
            row=store.one('SELECT hash,deleted FROM sources WHERE id=?',(r['source_id'],))
            if not row or row['deleted'] or row['hash']!=r.get('sha256'):continue
            src=store.blob_bytes(row['hash']).decode();a,b=r['char_start'],r['char_end']
            if not 0<=a<=b<=len(src):continue
        except (KeyError,TypeError,ValueError,OSError,UnicodeDecodeError):continue
        hits.append(1. if a==0 or END.search(src[:a]) else 0.)
        hits.append(1. if b==len(src) or END.search(src[a:b]) or src[b:b+1] in '.!?;:\n' else 0.)
    if not hits:return {'boundary_confidence':None,'boundary_source':'NONE'}
    return {'boundary_confidence':round(sum(hits)/len(hits),4),'boundary_source':'LEXICAL_ALIGNMENT_PROXY'}

def turns_left(decay):
    """§8.2 expiry under the BOOT turn decay: further turns before the slot falls under the drop floor."""
    if decay<BOOT['drop_floor']:return 0
    return int(math.floor(math.log(BOOT['drop_floor']/decay)/math.log(BOOT['turn_decay'])+1e-9))

def item(kind,payload_ref,refs,text,event_id,*,uncertainty,salience,goal,utility,sq,conflict=0.,cost=0.,
         state_type='ACTIVE',status='HYPOTHESIS',confidence=None,goal_ids=(),decay=1.,turns=0,created=None,bounds=None,self_generated=None):
    """§93 FOCAL_ITEM with the §8.2 slot minimum. ``text`` stays in memory only; persisted slots re-read it from its packet.
    ``created``: wall time of the underlying offer/memory (timestamp + age); ``bounds``: result of ``boundary()``."""
    t={'goal':goal,'conflict':conflict,'uncertainty':uncertainty,'salience':salience,'utility':utility,'source_quality':sq,'redundancy':0.,'cost':cost}
    wall=now();created=wall if created is None else float(created);cov=covered(refs);n=sum(c['char_end']-c['char_start'] for c in cov)
    exact=[r for r in refs or () if isinstance(r,dict) and r.get('sha256')]
    return {'item_id':payload_ref,'source_kind':kind,'source_refs':list(refs),'payload_ref':payload_ref,'reactivation_key':kind+':'+payload_ref,
            'confidence':round(clip(sq*(1-uncertainty) if confidence is None else confidence),4),'confidence_type':'BOOT_EVIDENCE_PROXY',
            'salience':round(clip(salience),4),'uncertainty':round(clip(uncertainty),4),'decay':round(decay,4),'turns_retained':turns,
            'bound_goal_ids':list(goal_ids),'fact_hypothesis_status':status,'state_type':state_type,'scale':SCALE.get(kind,'event'),
            'origin_event_id':event_id,'home_type':state_type,'priority_terms':t,'priority':priority(t),'text':(text or '')[:400],
            'self_generated':kind in BODY if self_generated is None else bool(self_generated),'created_wall':created,'age_ms':int(max(0.,wall-created)*1000),
            'expiry':{'policy':'BOOT_TURN_DECAY','turns_left':turns_left(decay),'turn_decay':BOOT['turn_decay'],'drop_floor':BOOT['drop_floor']},
            'exact_fallback':'SOURCE_REF' if exact else 'NONE','exact_fallback_refs':exact,'covered_range':cov,
            'compression_ratio':round(n/len(text),4) if n and text else None,
            **(bounds or {'boundary_confidence':None,'boundary_source':'NONE'}),'children':[],'parents':[]}

def note_slot(key):
    """Topic slot of a stored note key: key terms without entity, entity label, calendar words and numbers."""
    return frozenset(t for t in terms(key or '') if t not in CALENDAR and t not in ENTITY_LABELS and t not in entities(key or '') and not t.isdigit())

def note_versions(cands,memories):
    """WP-Z5c: per slot with >1 recalled note the newest stored note gets recency 1, older ones superseded 1 (sets terms only)."""
    info={m['id']:(note_slot(m.get('key_text')),float(m.get('created') or 0.)) for m in memories}
    groups={}
    for c in cands:
        if c['source_kind']=='MEMORY' and c['item_id'] in info and info[c['item_id']][0]:groups.setdefault(info[c['item_id']][0],[]).append(c)
    for g in groups.values():
        if len(g)<2:continue
        g.sort(key=lambda c:(info[c['item_id']][1],c['item_id']));newest=g[-1]
        newest['priority_terms']['recency']=1.;newest['supersedes']=[c['item_id'] for c in g[:-1]]
        for c in g[:-1]:c['priority_terms']['superseded']=1.;c['superseded_by']=newest['item_id']
    return cands

def link_scales(items):
    """§3.2A/§8.2A: gist slots point to fine/event slots over overlapping source spans and back."""
    for x in items:x['children']=[];x['parents']=[]
    for g in items:
        if g['scale']!='gist':continue
        for f in items:
            if f is g or f['scale']=='gist':continue
            if any(a['source_id']==b['source_id'] and a['char_start']<b['char_end'] and b['char_start']<a['char_end'] for a in g['source_refs'] for b in f['source_refs']):
                g['children'].append(f['item_id']);f['parents'].append(g['item_id'])
    return items

def admit(cands,capacity,threshold,interrupt=BOOT['sal_interrupt']):
    """Capacity-limited competition (§85.3 G-FOCAL-CAPACITY-003): priority, redundancy, salience interrupt."""
    active=[];rest=[]
    for c in sorted(cands,key=lambda x:(-x['priority'],x['item_id'])):
        if c['state_type']=='DROPPED':rest.append(c);continue
        red=max([relevance(c['text'],a['text']) for a in active if c['text'] and a['text']],default=0.)
        c['priority_terms']['redundancy']=round(red,4);c['priority']=priority(c['priority_terms'])*c['decay']
        if c['salience']>=interrupt and len(active)>=capacity and capacity:
            low=min((a for a in active if a['salience']<interrupt),key=lambda a:a['priority'],default=None)
            if low:active.remove(low);low['admission']='DISPLACED_BY_SALIENCE_INTERRUPT';rest.append(low)
        if len(active)<capacity and (c['priority']>=threshold or c['salience']>=interrupt):
            c['admission']='SALIENCE_INTERRUPT' if c['priority']<threshold else 'PRIORITY';active.append(c)
        else:c['admission']='BELOW_THRESHOLD' if c['priority']<threshold else 'CAPACITY';rest.append(c)
    for c in active:c['state_type']='ACTIVE'
    for c in rest:
        if c['state_type']=='ACTIVE':c['state_type']=c['home_type'] if c['home_type']!='ACTIVE' else 'REACTIVATABLE'
    return active,rest

def assess(active,cands,sig):
    """Coalition-level state: conflict, memory contradiction, uncertainty, re-entry target."""
    bodies=[x for x in active if x['source_kind'] in BODY]
    pair=max([disagreement(a['text'],b['text']) for i,a in enumerate(bodies) for b in bodies[i+1:]],default=0.)
    mem=max([disagreement(a['text'],m['text']) for a in bodies for m in cands if m['source_kind']=='MEMORY'],default=0.)
    prior=max([disagreement(a['text'],m['text']) for a in bodies for m in cands if m['fact_hypothesis_status']=='PRIOR_HYPOTHESIS'],default=0.)
    unc=max([x['uncertainty'] for x in bodies],default=sig.get('uncertainty',0.))
    return {'conflict':round(max(pair,prior),4),'memory_contradiction':mem,'uncertainty':round(unc,4),'salience':sig.get('salience',0.),
            'bodies':sorted({x['source_kind'] for x in bodies}),'active':len(active)}

def choose(view,target,queries_left):
    """§3.4.6/§4.4 BOOT decision; returns (decision, reason)."""
    if target and queries_left>0:return ('QUERY_A' if target=='B1_DETAIL' else 'QUERY_B'),'TARGETED_REENTRY'
    b=view['bodies']
    if not b:return 'IGNORE','NO_BODY_IN_COALITION'
    return {('B1_DETAIL',):'INCORPORATE_A',('B2_GIST',):'INCORPORATE_B'}.get(tuple(b),'INCORPORATE_AB'),'COALITION_BOUND'


STABLE_DELTA=.15  # WP-T1: re-entry offer this close to the previous one of the same body = stable trajectory

class Inquisition:
    """§10 P1<->P2 scaffold. P1 proposes, P2 critiques/verifies; effects change later focal state (G5)."""
    MODES=('HYPOTHESIS','CRITIQUE','VERIFY','CONSTRAINT_CHECK','COMPARE')
    def __init__(self,store):self.s=store
    def triggers(self,view,sig,deeper=False,world_error=False,verify=False):
        t=[]
        if view['conflict']>=BOOT['disagreement_trigger']:t.append('AB_DISAGREEMENT')
        if view['memory_contradiction']>=BOOT['disagreement_trigger']:t.append('MEMORY_CONTRADICTION')
        if view['salience']>=BOOT['salience_trigger']:t.append('SALIENCE')
        if world_error:t.append('WORLD_PREDICTION_ERROR')
        if deeper:t.append('USER_DEEPER_REQUEST')
        if verify:t.append('EFFORT_VERIFY')
        return t
    def plan(self,deliberation,view,rules,max_steps):
        if not deliberation:return ['HYPOTHESIS','CRITIQUE']  # Age 0/1: forced simple sequence
        modes=['HYPOTHESIS','CRITIQUE','VERIFY']
        if len(view['bodies'])==2:modes.append('COMPARE')
        if rules:modes.append('CONSTRAINT_CHECK')
        modes+=['HYPOTHESIS','CRITIQUE']
        return modes[:max(2,max_steps)]
    def _refs_ok(self,x):
        try:
            for ref in x['source_refs']:self.s.read_source(ref)
            return True
        except (ValueError,OSError,KeyError,TypeError):return False
    def run(self,e,active,cands,view,*,deliberation,max_steps,rules=(),trigger=()):
        """Returns (steps, reentry_target). Steps are persisted InquisitionStep packets."""
        steps=[];target=None;hyp=None;rejected=set()
        bodies=lambda:[x for x in active if x['source_kind'] in BODY and x['state_type']=='ACTIVE']
        modes=self.plan(deliberation,view,list(rules),max_steps);self.last_order=None
        try:  # WP-N2: learned deliberation order (needs the Age right + :delib active; SHADOW only proposes)
            from .deliberation import Deliberation
            modes,proposal,applied=Deliberation(self.s).order(modes,trigger,bool(deliberation));self.last_order={'proposal':proposal,'applied':applied}
        except Exception:pass
        for i,mode in enumerate(modes):
            verdict='NO_TARGET';ev={};tgt=None
            if mode=='HYPOTHESIS':
                pool=[x for x in bodies() if x['item_id'] not in rejected] or [x for x in active if x['item_id'] not in rejected]
                hyp=max(pool,key=lambda x:x['priority'],default=None)
                if hyp:tgt=hyp;verdict='PROPOSED' if not rejected else 'ALTERNATIVE_PROPOSED'
            elif mode=='CRITIQUE' and hyp:
                tgt=hyp;rivals=[(disagreement(hyp['text'],x['text']),x) for x in cands if x is not hyp and x['text']]
                dis,rival=max(rivals,key=lambda r:r[0],default=(0.,None));ok=self._refs_ok(hyp)
                ev={'max_disagreement':dis,'rival_item_id':rival['item_id'] if rival else None,'source_refs_valid':ok,'quotes':len(hyp['source_refs']) if hyp['priority_terms']['source_quality']>.4 else 0}
                if not ok:verdict='SOURCE_LOSS';hyp['state_type']='DROPPED';rejected.add(hyp['item_id'])
                elif dis>=BOOT['disagreement_trigger']:
                    verdict='CONTESTED';rejected.add(hyp['item_id'])
                    for x in (hyp,rival):
                        x['uncertainty']=max(x['uncertainty'],.6);x['priority_terms']['uncertainty']=x['uncertainty']
                        if x['fact_hypothesis_status'] in ('HYPOTHESIS','CRITIQUE_SUPPORTED_HYPOTHESIS'):x['fact_hypothesis_status']='CONTESTED_HYPOTHESIS'
                    weak=min((x for x in (hyp,rival) if x['source_kind'] in BODY and x['origin_event_id']==e['event_id']),key=lambda x:x['priority_terms']['source_quality'],default=None)
                    target=weak['source_kind'] if weak else None
                elif hyp['priority_terms']['source_quality']<.5 and hyp['uncertainty']>=.5:
                    verdict='UNSUPPORTED';hyp['fact_hypothesis_status']='UNSUPPORTED_HYPOTHESIS';hyp['decay']*=.5;rejected.add(hyp['item_id'])
                else:
                    verdict='SUPPORTED';hyp['fact_hypothesis_status']='CRITIQUE_SUPPORTED_HYPOTHESIS'
                    hyp['uncertainty']=round(hyp['uncertainty']*.7,4);hyp['priority_terms']['uncertainty']=hyp['uncertainty']
            elif mode=='VERIFY':
                bad=[x['item_id'] for x in active if not self._refs_ok(x)]
                for x in active:
                    if x['item_id'] in bad:x['state_type']='DROPPED'
                    elif x['source_kind'] in BODY and x['priority_terms']['source_quality']>.4:x['source_verified']=True
                verdict='SOURCE_CHECKED';ev={'dropped':bad,'verified':[x['item_id'] for x in active if x.get('source_verified')]}
            elif mode=='CONSTRAINT_CHECK':
                hits=[(x['item_id'],r) for x in bodies() for r in rules if isinstance(r,str) and disagreement(r,x['text'])>=BOOT['disagreement_trigger']]
                for x in bodies():
                    if any(h[0]==x['item_id'] for h in hits):x['fact_hypothesis_status']='CONSTRAINT_CONFLICT';x['decay']*=.5
                verdict='VIOLATION' if hits else 'CONSISTENT';ev={'violations':[h[0] for h in hits]}
            elif mode=='COMPARE':
                b=bodies()
                if len(b)>=2:
                    best=max(b,key=lambda x:x['priority_terms']['source_quality']+x['priority_terms']['goal'])
                    for x in b:
                        if x is not best and x['fact_hypothesis_status']=='HYPOTHESIS':x['fact_hypothesis_status']='ALTERNATIVE_HYPOTHESIS'
                    tgt=best;verdict='PREFERRED';ev={'alternatives':[x['item_id'] for x in b if x is not best]}
            for x in active:x['priority']=priority(x['priority_terms'])*x['decay']
            p=packet('InquisitionStep','C4_INQUISITION',e['event_id'],e['brain_generation_id'],(tgt or {}).get('source_refs',[]),
                     step=i,mode=mode,speaker='P1' if mode=='HYPOTHESIS' else 'P2',target_item_id=(tgt or {}).get('item_id',''),verdict=verdict,
                     evidence=ev,trigger=list(trigger),mode_policy='AGE_FORCED_P1_P2' if not deliberation else 'BOOT_MODE_SEQUENCE',fact_authority=False)
            self.s.add_packet('InquisitionStep',p);steps.append({'step':i,'mode':mode,'speaker':p['speaker'],'target':p['target_item_id'],'verdict':verdict,'packet_id':p['packet_id']})
        return steps,target


class Workspace:
    """B4 multi-slot workspace (§8.1-8.2A, §85.3): ACTIVE / REACTIVATABLE / EPISODIC_POINTER slots per session.

    Persisted slots hold IDs and refs only; content is re-read from its packet/memory row on load,
    so source erasure or a new brain generation drops the slot (L_B4_SOURCE_LOSS locked high).
    """
    def __init__(self,store,session):self.s=store;self.key='C4_WORKSPACE:'+session;self.session=session
    def _text(self,slot):
        if slot['source_kind'] in BODY:
            row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",(slot['payload_ref'],))
            return json.loads(row['payload'])['offer'].get('summary','') if row else None
        if slot['source_kind']=='MEMORY':
            row=self.s.one('SELECT value FROM memories WHERE id=? AND active=1',(slot['payload_ref'],))
            return row['value'] if row else None
        return None
    def load(self,e):
        st,_=self.s.state(self.key,{})
        if not st or st.get('generation')!=e['brain_generation_id']:return []
        out=[]
        from . import workspace_learn as WL
        for slot in st.get('slots',[]):
            if slot['origin_event_id']==e['event_id']:continue
            text=self._text(slot)
            if text is None:continue
            try:
                for ref in slot['source_refs']:self.s.read_source(ref)
            except (ValueError,OSError,KeyError,TypeError):
                try:WL.source_loss(self.s)  # L_B4_SOURCE_LOSS locked high: provenance beats stability
                except Exception:pass
                continue
            try:hold=WL.decay_factor(self.s,slot['source_kind'])  # WP-U8 learned hold per kind (1.0 in SHADOW)
            except Exception:hold=1.
            decay=min(slot['decay'],slot['decay']*BOOT['turn_decay']*hold)
            if decay<BOOT['drop_floor']:continue
            t=dict(slot['priority_terms']);t['goal']=0.  # goal relevance is recomputed against the new goal
            x=item(slot['source_kind'],slot['payload_ref'],slot['source_refs'],text,slot['origin_event_id'],uncertainty=slot['uncertainty'],salience=slot['salience'],
                   goal=0.,utility=t['utility'],sq=t['source_quality'],conflict=t['conflict'],cost=t['cost'],decay=decay,turns=slot.get('turns_retained',0)+1,
                   state_type='REACTIVATABLE' if decay>=BOOT['reactivatable_floor'] else 'EPISODIC_POINTER',
                   status='PRIOR_HYPOTHESIS' if slot['source_kind'] in BODY else slot['fact_hypothesis_status'],goal_ids=slot['bound_goal_ids'],
                   created=slot.get('created_wall',slot.get('admitted_wall')),bounds=boundary(self.s,slot['source_refs']),self_generated=slot.get('self_generated'))
            out.append(x)
        return out
    def save(self,e,active,rest,capacity):
        keep=[x for x in active if x['state_type']=='ACTIVE']
        for x in sorted((x for x in rest if x['state_type']!='DROPPED'),key=lambda x:-x['priority']):
            if len(keep)>=capacity:break
            if x['decay']>=BOOT['drop_floor']:keep.append(x)
        slots=[{k:v for k,v in x.items() if k not in ('text','children','parents','admission')}|{'admitted_wall':now()} for x in keep]
        old,_=self.s.state(self.key,{});known={s['item_id'] for s in old.get('slots',[])} if old else set()
        try:
            from .workspace_learn import observe
            observe(self.s,list(active),list(rest),slots,(old or {}).get('slots',[]))  # WP-U8 L3-B4 stability loop
        except Exception as exc:self.s.log('workspace_learn_error',e['event_id'],{'error':type(exc).__name__})
        for x in keep:
            if x['item_id'] in known:continue
            self.s.add_packet('WorkspaceSlot',packet('WorkspaceSlot','B4_WORKSPACE',e['event_id'],e['brain_generation_id'],x['source_refs'],owner=x['source_kind'],source_refs=x['source_refs'],
                content={'payload_ref':x['payload_ref'],'state_type':x['state_type'],'fact_hypothesis_status':x['fact_hypothesis_status'],
                         **{k:x[k] for k in SLOT_FIELDS}}))
        self.s.set_state(self.key,{'session_id':self.session,'generation':e['brain_generation_id'],'event_id':e['event_id'],'capacity':capacity,'slots':slots})
        return slots
    def view(self):
        st,v=self.s.state(self.key,{})
        return {'version':v,'event_id':st.get('event_id'),'capacity':st.get('capacity'),
                'slots':[{k:s[k] for k in ('item_id','source_kind','state_type','scale','priority','uncertainty','decay','fact_hypothesis_status')} for s in st.get('slots',[])]}


class FocalLoop:
    """C4 JEF_FOCAL_LOOP (§3.3.7). ``query(role)`` performs one targeted body re-entry and returns an offer or None."""
    def __init__(self,runtime):self.r=runtime;self.s=runtime.store;self.inquisition=Inquisition(self.s)
    def _utility(self,offer,base,goal):
        try:  # WP-N3 L4.4: learned offer usefulness, only in :jef active (bounded); SHADOW returns base unchanged
            from .jefbridge import controller
            return controller(self.r).offer_utility(offer,base,goal)
        except Exception:return base
    def _focus(self,e,role,fresh,view,reason,query):
        """WP-T1 §3.4.7: executive question for this re-entry (arm on|off per fastpolicy mode); None = plain re-entry."""
        try:
            import inspect
            from .fastpolicy import focus_arm,focus_for
            if 'focus' not in inspect.signature(query).parameters:return None
            self._focus_arm=focus_arm(self.s,e['event_id'])
            return focus_for(role,fresh,view,reason) if self._focus_arm=='on' else None
        except Exception as exc:self.s.log('fast_policy_unavailable',e['event_id'],{'stage':'focus','error':type(exc).__name__});return None
    def _jef_target(self,view,target):
        try:  # WP-N3 §3.4.7: learned re-entry target, ACTIVE only; SHADOW keeps the BOOT target and logs the proposal
            from .jefbridge import controller
            return controller(self.r).query_target(view,target)
        except Exception:return target,None
    def _candidates(self,e,goal,offers,memories,retained,sig,version):
        fresh=[p for p in offers if offer_is_fresh(p,e['event_id'],e['brain_generation_id'],version)];cands=[]
        for p in fresh:
            text=p['offer'].get('summary','')+' '+' '.join(self.s.read_source(r) for r in p['evidence_refs'])
            need=sig.get('detail_need' if p['role']=='B1_DETAIL' else 'gist_need',.5)
            cands.append(item(p['role'],p['packet_id'],p['evidence_refs'] or p['provenance'][:1],p['offer'].get('summary',''),e['event_id'],
                uncertainty=offer_uncertainty(p),salience=sig.get('salience',0.),goal=clip(3*relevance(goal,text)),utility=self._utility(p,max(.3,need),goal),sq=source_quality(p),goal_ids=[e['event_id']],
                created=p['created_wall_time'],bounds=boundary(self.s,p['evidence_refs'] or p['provenance'][:1])))
        for m in memories:
            cands.append(item('MEMORY',m['id'],[m['source_ref']],m.get('value',''),e['event_id'],uncertainty=.2,salience=0.,goal=clip(3*relevance(goal,m.get('value',''))),
                utility=.4,sq=1.,cost=.05,state_type='EPISODIC_POINTER',status='MEMORY_SOURCE',confidence=m.get('retrieval_score') or 0.,goal_ids=[e['event_id']],
                created=m.get('created'),bounds=boundary(self.s,[m['source_ref']]),self_generated=False))  # memories are human decisions
        for x in retained:
            x['priority_terms']['goal']=clip(3*relevance(goal,x['text']));x['priority']=priority(x['priority_terms'])*x['decay'];cands.append(x)
        if self.r.cfg.get('focal_note_recency'):note_versions(cands,memories)
        for c in cands:
            for k,v in self.memo.get(c['item_id'],{}).items():
                if k=='uncertainty':c['priority_terms']['uncertainty']=v
                c[k]=v
            c['priority_terms']['conflict']=max([disagreement(c['text'],o['text']) for o in cands if o is not c],default=0.)
            c['priority']=priority(c['priority_terms'])*c['decay']
        return fresh,cands
    def run(self,e,version,offers,*,goal,memories=(),plan=None,sig=None,age=None,deadline=None,query=None,halt=None,rules=(),deeper=None,world_error=False,session=None,attention=None,pressure=0.):
        plan=plan or {'focal_cycles':1,'focal_slots':self.r.cfg['focal_slots'],'max_reentry':0,'verify':False}
        sig=sig or {};age=age or {'stage':0,'deliberation':False,'focal_depth':1}
        deeper=bool(DEEPER.search(goal)) if deeper is None else deeper
        slots=max(1,min(int(plan.get('focal_slots') or 1),self.r.cfg['focal_slots']))
        ws=Workspace(self.s,session or self.r.session);retained=ws.load(e);self.memo={};grants=[]
        cycles=int(plan.get('focal_cycles') or 0);queries=int(plan.get('max_reentry') or 0)
        inq_left=0 if cycles==0 else (2 if not age.get('deliberation') else min(6,2+cycles))
        gain=BOOT['uncertainty_coupling_gain'];recalled=False;mem_grants=[];focus_log=[];self._focus_arm=None;trajectory=[];halt_decision=None;first_trig=[];inq_steps=[];decision,reason='IGNORE','NO_CYCLE';cycle=0;target=None
        while True:
            fresh,cands=self._candidates(e,goal,offers,memories,retained,sig,version)
            u=max([c['uncertainty'] for c in cands if c['source_kind'] in BODY],default=sig.get('uncertainty',0.))
            g_focal,g_ws=BOOT['gain_focal'],1.
            if attention is not None:  # WP-N5 thalamic gain: focal gain sets coupling, workspace gain scales admission
                pre=max([c['priority_terms']['conflict'] for c in cands if c['source_kind'] in BODY],default=0.)
                mod=self._attend(attention,e,pre,world_error,session or self.r.session)
                if mod:
                    g_focal=mod['gains']['focal'];g_ws=mod['gains']['workspace']/ATT_BASE['workspace']
                    if mod['interrupt']:
                        for c in cands:
                            if c['source_kind'] in BODY and c['priority_terms']['conflict']>=BOOT['disagreement_trigger']:c['salience']=max(c['salience'],BOOT['sal_interrupt']);c['interrupt']=mod['interrupt_reason']
            coupling=clip(g_focal+gain*u);threshold=round(clip(BOOT['coalition_threshold']*(1-.5*gain*u)/max(g_ws,1e-6)),4)
            if coupling>=.8:
                for c in cands:
                    if c['source_kind']=='MEMORY':c['priority_terms']['utility']=min(1.,c['priority_terms']['utility']+gain*u)
            active,rest=admit(cands,slots,threshold);view=assess(active,cands,sig)
            if attention is not None and not recalled and view['conflict']>=BOOT['disagreement_trigger']:
                recalled=True;new=self._attended_recall(attention,e,cands,memories,session or self.r.session,view,pressure,mem_grants)
                if new:  # WP-N5 §4B: conflict-driven second recall enters the coalition competition right away
                    memories=list(memories)+new;fresh,cands=self._candidates(e,goal,offers,memories,retained,sig,version)
                    active,rest=admit(cands,slots,threshold);view=assess(active,cands,sig)
            if cycle>=cycles:break
            cycle+=1;phase=[]
            trig=self.inquisition.triggers(view,sig,deeper,world_error,plan.get('verify'))
            if trig and inq_left>0:
                steps,t=self.inquisition.run(e,active,cands,view,deliberation=bool(age.get('deliberation')),max_steps=inq_left,rules=rules,trigger=trig)
                inq_left-=len(steps);inq_steps+=steps;target=t or target;phase.append('INQUISITION')
                for c in cands:self.memo[c['item_id']]={k:c[k] for k in ('fact_hypothesis_status','uncertainty','decay')}|({'state_type':'DROPPED'} if c['state_type']=='DROPPED' else {})|({'source_verified':True} if c.get('source_verified') else {})
                active,rest=admit(cands,slots,threshold);view=assess(active,cands,sig)
            last=fresh[-1] if fresh else None
            if not target and last and last['offer'].get('needs_reentry'):
                roles={p['role'] for p in fresh};target=next(r for r in BODY if r!=last['role']) if len(roles)==2 else last['role']
            jq=None
            if target and queries>0:target,jq=self._jef_target(view,target)
            decision,reason=choose(view,target,queries)
            first_trig=trig if cycle==1 else first_trig
            if halt and halt_decision is None and len({p['role'] for p in fresh})==2 and len(fresh)==2:
                halt_decision=halt(fresh,'continue' if decision.startswith('QUERY') else 'halt')
                halt_decision=halt_decision if isinstance(halt_decision,dict) else {};halt_decision['steering']=self._halt_ok(e,first_trig)  # readout always logged, steers only when stable
                if not halt_decision['steering']:pass
                elif halt_decision.get('action')=='halt' and decision.startswith('QUERY'):decision,reason=choose(view,None,0)[0],'HALT_READOUT'
                elif halt_decision.get('action')=='continue' and not decision.startswith('QUERY') and queries>0:decision,reason,target='QUERY_A','HALT_READOUT_CONTINUE','B1_DETAIL'
            rec={'cycle':cycle,'phase':phase,'decision':decision,'reason':reason,'coupling':round(coupling,4),'threshold':threshold,
                 'coalition':[x['item_id'] for x in active],'view':view,'queries_left':queries,'inquisition_steps_left':inq_left}
            if jq:rec['jef_query']=jq
            self.s.add_packet('FocalCycle',packet('FocalCycle','C4_FOCAL',e['event_id'],e['brain_generation_id'],[r for x in active for r in x['source_refs']][:16],
                cycle=cycle,decision=decision,coalition=rec['coalition'],signals=view,budget={'queries_left':queries,'inquisition_steps_left':inq_left,'cycles':cycles,'slots':slots},
                reason=reason,phase=phase,coupling=rec['coupling'],threshold=threshold,parameter_status='BOOT_HEURISTIC_NOT_LEARNED',**({'jef_query':jq} if jq else {})))
            trajectory.append(rec)
            if not decision.startswith('QUERY'):break
            role='B1_DETAIL' if decision=='QUERY_A' else 'B2_GIST';queries-=1;target=None
            focus=self._focus(e,role,fresh,view,reason,query)
            if query is None or (deadline is not None and time.monotonic()+2>=deadline):rec['query_skipped']='NO_TIME_OR_QUERY';break
            ask=(lambda r_,f=focus:query(r_,focus=f)) if focus else query
            got=self._attended_query(attention,e,role,ask,view,reason,pressure,grants) if attention is not None else ask(role)
            rec['query_offer_id']=got['packet_id'] if got else None
            if got:
                prev=next((p for p in reversed(offers) if p['role']==role),None);offers=list(offers)+[got]
                stable=bool(prev) and disagreement(prev['offer'].get('summary',''),got['offer'].get('summary',''))<STABLE_DELTA
                if focus is not None or self._focus_arm:rec['focus']=focus['kind'] if focus else None;focus_log.append((got['packet_id'],self._focus_arm,stable))
                if stable and queries>0:rec['stable_stop']=True;queries=0  # WP-T1: a re-entry that changes nothing ends the re-entry chain
        link_scales(active+rest)
        try:  # WP-N2: trajectory stability + per-mode informativeness
            from .deliberation import Deliberation
            Deliberation(self.s).record(e['event_id'],first_trig,decision,len(trajectory),inq_steps,(self.inquisition.__dict__.get('last_order') or {}).get('proposal'),(self.inquisition.__dict__.get('last_order') or {}).get('applied',False))
        except Exception as exc:self.s.log('deliberation_unavailable',e['event_id'],{'error':type(exc).__name__})
        for resp_id,oid in grants:  # §4B.4 internal cross-check: did the granted re-entry reach the coalition?
            try:attention.outcome(resp_id,.5 if any(x['item_id']==oid for x in active) else -.25)
            except Exception as exc:self.s.log('attention_outcome_failed',e['event_id'],{'error':type(exc).__name__})
        for oid,arm,stable in focus_log:  # WP-T1: re-entry focus on/off outcome (did the re-entry offer reach the coalition?)
            try:
                from .fastpolicy import record_focus
                record_focus(self.s,arm or 'off',any(x['item_id']==oid for x in active),stable)
            except Exception as exc:self.s.log('fast_policy_unavailable',e['event_id'],{'stage':'focus','error':type(exc).__name__})
        for resp_id,mids in mem_grants:  # did the second recall reach the coalition?
            try:attention.outcome(resp_id,.5 if any(x['item_id'] in mids for x in active) else -.25)
            except Exception as exc:self.s.log('attention_outcome_failed',e['event_id'],{'error':type(exc).__name__})
        for x in active:
            self.s.add_packet('FocalItem',packet('FocalItem','C4_FOCAL',e['event_id'],e['brain_generation_id'],x['source_refs'],**{k:v for k,v in x.items() if k not in ('text',)}))
        ws.save(e,active,rest,slots*BOOT['workspace_factor'])
        ids=[x['item_id'] for x in active if x['source_kind'] in BODY and x['origin_event_id']==e['event_id']]
        by={p['packet_id']:p for p in offers}
        selected=[by[i] for i in ids if i in by and offer_is_fresh(by[i],e['event_id'],e['brain_generation_id'],version)]
        return {'selected':selected,'offers':offers,'coalition':active,'decision':decision,'trajectory':trajectory,'inquisition':inq_steps,'halt_decision':halt_decision,
                'workspace':[x['item_id'] for x in active+rest if x['state_type']!='DROPPED'][:slots*BOOT['workspace_factor']]}


    def _halt_ok(self,e,trigger):
        """WP-N2 §10.1/G5: the learned halt readout may steer only after the scaffold trajectory is stable."""
        try:
            from .deliberation import Deliberation
            ok=Deliberation(self.s).halt_allowed(trigger)
        except Exception:ok=False
        if not ok:self.s.log('halt_gated',e['event_id'],{'reason':'TRAJECTORY_NOT_STABLE'})
        return ok
    def _attend(self,attention,e,conflict,world_error,session=None):
        try:  # N10 modulators of the last turns (surprise, world error, novelty) feed salience/caution next to the live conflict
            mods=attention.recent_modulators(e['event_id'],session) if hasattr(attention,'recent_modulators') else None
            return attention.modulate(e['event_id'],sal={'conflict':conflict},caut={'B1_B2_disagreement':conflict,'world_surprise':1. if world_error else 0.},modulators=mods)
        except Exception as exc:self.s.log('attention_unavailable',e['event_id'],{'error':type(exc).__name__});return None
    def _attended_recall(self,attention,e,cands,memories,session,view,pressure,mem_grants):
        """WP-N5 MEMORY provider: B1/B2 conflict -> JEF asks F1 for a second recall cued by the disagreeing offers."""
        mem=getattr(self.r,'memory',None)
        if mem is None:return []
        cue=' '.join(c['text'] for c in sorted((c for c in cands if c['source_kind'] in BODY),key=lambda c:-c['priority_terms']['conflict'])[:2])[:300]
        have={m['id'] for m in memories};got={}
        def provide(r):
            got['m']=[m for m in mem.recall(cue,session) if m['id'] not in have][:2]
            return {'memory_ids':[m['id'] for m in got['m']]} if got['m'] else None
        try:
            req=attention.request(e['event_id'],'JEF','MEMORY','recall',priority=clip(.5+.5*view['conflict']),budget=32,refs=[e['source_ref']])
            resp=attention.admit(e['event_id'],[req],pressure=pressure,providers={'MEMORY':provide})[0]
        except Exception as exc:self.s.log('attention_unavailable',e['event_id'],{'stage':'recall','error':type(exc).__name__});return []
        if resp['status']!='GRANTED':return []
        mem_grants.append((resp['packet_id'],[m['id'] for m in got['m']]));return got['m']
    def _attended_query(self,attention,e,role,query,view,reason,pressure,grants):
        """Targeted re-entry as an F1 AttentionRequest (§4B): JEF -> B1/B2, granted under the event budget."""
        got={}
        def provide(r):
            got['offer']=query(role);return {'offer_packet_id':got['offer']['packet_id']} if got.get('offer') else None
        target='B1' if role=='B1_DETAIL' else 'B2'
        try:
            req=attention.request(e['event_id'],'JEF',target,'conflict' if view['conflict']>=BOOT['disagreement_trigger'] else 'verify',
                                  priority=clip(.5+.5*view['uncertainty']),budget=int(self.r.cfg.get('observer_tokens',64)),refs=[e['source_ref']])
            resp=attention.admit(e['event_id'],[req],pressure=pressure,providers={target:provide})[0]
        except Exception as exc:
            self.s.log('attention_unavailable',e['event_id'],{'error':type(exc).__name__});return query(role)
        if resp['status']=='GRANTED' and got.get('offer'):grants.append((resp['packet_id'],got['offer']['packet_id']))
        return got.get('offer')


class ActionGate:
    """C5 (§6.4, §11.1, §85.5): candidate competition + permission gate + one intent stream.

    BOOT utilities reproduce the former route->role table; focal support adds at most
    GAIN.action*0.25 so it can only reorder candidates whose prior utilities are within that margin.
    """
    PRIOR={'simple':'C3_LANGUAGE','detail':'B1_DETAIL','gist':'B2_GIST','both':'B1_DETAIL'}
    def __init__(self,store):self.s=store
    def candidates(self,route,direct,coalition,view,age,tool=None):
        total=sum(x['priority'] for x in coalition) or 1.
        support={r:round(sum(x['priority'] for x in coalition if x['source_kind']==r)/total,4) for r in BODY}
        support['C3_LANGUAGE']=round(sum(x['priority'] for x in coalition)/total/2,4) if coalition else 0.
        unc=view.get('uncertainty',0.) if view else 0.;conf=view.get('conflict',0.) if view else 0.
        out=[]
        def add(aid,utility,cost,permission,rev,kind='TEXT_REPORT'):
            out.append({'action_id':aid,'action_type':kind,'expected_utility':utility,'expected_cost':cost,'confidence':round(1-unc,4),'reversibility':rev,
                        'evidence':[x['item_id'] for x in coalition if x['source_kind']==aid][:4],'permission_class':permission,'novelty':0.,'uncertainty':unc,
                        'habit_strength':.5 if aid==self.PRIOR.get(route) else 0.,'focal_support':support.get(aid,0.)})
        if direct:add('SOURCE_COPY',1.,0.,'local_text_only',1.,'EXACT_RENDER')
        for role in ('C3_LANGUAGE','B1_DETAIL','B2_GIST'):
            add(role,.8 if role==self.PRIOR.get(route) else (.5 if role=='C3_LANGUAGE' else .4),.1 if role=='C3_LANGUAGE' else .3,'local_text_only',1.)
        add('ASK_USER',round(.3+.3*unc*conf,4),.2,'local_text_only',1.,'CLARIFY')
        if tool:add('EXTERNAL_TOOL',tool['utility'],.1,'local_tool' if tool['risk']=='READ_LOCAL' else 'external_tool',1. if tool['risk']=='READ_LOCAL' else 0.,'TOOL_CALL')  # WP-K: concrete proposal
        else:add('EXTERNAL_TOOL',0.,.5,'external_tool',0.,'TOOL_CALL')
        return out
    def select(self,e,*,route,direct,resource_state,coalition=(),view=None,age=None,predicted=False,effort=None,gain_action=None,tool=None,clarify=None):
        age=age or {'tools':False};g_act=BOOT['gain_action'] if gain_action is None else BOOT['gain_action']*clip(gain_action)/ATT_BASE['action'];coalition=list(coalition);cands=self.candidates(route,direct,coalition,view,age,tool);suppressed=[]  # WP-N5: caution lowers action coupling
        for c in cands:
            why=None
            if c['action_type']=='TOOL_CALL' and tool:why='EXACT_OR_FIXED_OUTPUT' if direct else (None if tool['status']=='APPROVED' else 'TOOL_POLICY:'+str(tool['reason']))  # IH-H29 decided
            elif c['permission_class']=='external_tool' and not age.get('tools'):why='AGE_NO_TOOLS'
            elif c['permission_class']=='external_tool':why='NO_EXTERNAL_TOOL_REQUESTED'
            elif c['action_type']=='CLARIFY' and clarify and clarify.get('apply') and not direct:c['expected_utility']=1.  # WP-N13 AG9 abstain -> ask instead of guessing (explicit human ACTIVE)
            elif c['action_type']=='CLARIFY':why='WAIT_VS_ACT_BIAS_BOOT'  # §85.5 ask is available, not executed at BOOT
            elif direct and c['action_id']!='SOURCE_COPY':why='EXACT_OR_FIXED_OUTPUT'
            elif resource_state=='PRESSURE' and c['action_id'] in BODY:why='RESOURCE_PRESSURE'
            if why:c['suppressed']=why;suppressed.append(c)
            c['score']=round(c['expected_utility']-.25*c['expected_cost']+g_act*.25*c['focal_support'],4)
        learning=None
        if not predicted:
            from .actionlearn import apply as learned_c5
            learning,_=learned_c5(self.s,cands,route,effort)  # WP-N4: learned promote/suppress pathways (scores shift only in ACTIVE)
        live=sorted((c for c in cands if 'suppressed' not in c),key=lambda c:(-c['score'],c['action_id']))
        chosen=live[0];alternates=[c['action_id'] for c in live[1:]]
        p=packet('ActionSelection','C5_ACTION_GATE',e['event_id'],e['brain_generation_id'],[e['source_ref']],selected={k:chosen[k] for k in ('action_id','action_type','score','permission_class','focal_support')},
                 candidates=[{k:c[k] for k in ('action_id','action_type','score','expected_utility','expected_cost','focal_support','permission_class')} for c in cands],
                 suppressed=[{'action_id':c['action_id'],'reason':c['suppressed']} for c in suppressed],permission_class=chosen['permission_class'],
                 alternates=alternates,route_prior=self.PRIOR.get(route),stage='PREDICTION' if predicted else 'COMMIT',parameter_status='BOOT_REPRODUCES_ROUTE_TABLE',learning=learning,route_hint=route,action_gain=round(g_act,6),clarify=clarify)
        self.s.add_packet('ActionSelection',p)
        return {'role':chosen['action_id'],'packet_id':p['packet_id'],'alternates':alternates,'suppressed':p['suppressed']}


def summary(store,session,limit=50):
    """Operator view: workspace slots, last focal trajectory, Inquisition steps, last C5 selection."""
    last=store.one("SELECT event_id FROM packets WHERE kind='FocalCycle' ORDER BY rowid DESC LIMIT 1")
    ev=last['event_id'] if last else None
    cyc=[json.loads(r['payload']) for r in store.rows("SELECT payload FROM packets WHERE kind='FocalCycle' AND event_id=? ORDER BY rowid",(ev,))] if ev else []
    inq=[json.loads(r['payload']) for r in store.rows("SELECT payload FROM packets WHERE kind='InquisitionStep' AND event_id=? ORDER BY rowid",(ev,))] if ev else []
    sel=store.one("SELECT payload FROM packets WHERE kind='ActionSelection' ORDER BY rowid DESC LIMIT 1")
    n=store.one("SELECT COUNT(*) n FROM packets WHERE kind='FocalCycle'")['n']
    return {'workspace':Workspace(store,session).view(),'event_id':ev,'cycles':[{k:c[k] for k in ('cycle','decision','reason','phase','coalition','coupling','threshold')} for c in cyc],
            'inquisition':[{k:s[k] for k in ('mode','speaker','verdict','target_item_id')} for s in inq],
            'action':(json.loads(sel['payload'])['selected']|{'suppressed':json.loads(sel['payload'])['suppressed']}) if sel else None,
            'total_cycles':n,'parameters':BOOT,'status':'BOOT_HEURISTIC_NOT_LEARNED'}
