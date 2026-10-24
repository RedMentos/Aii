"""§94 / §15 / §37 / G8 Replay queue and offline sleep phases.

Sleep A  real replay: spaced rehearsal of recorded human corrections, interleaving
         new and protected-old items, a real retention probe through Memory.recall,
         and candidate consolidation staging (human approval stays mandatory).
Sleep B  counterfactual / dream: route alternatives, skill recombination and world
         hypotheses. Writes hypotheses only (fact_write_authority = 0); nothing here
         reaches memories, indexes, feedback or weights.
Sleep C  homeostasis: trace decay, homeostatic replay-mix gains, plasticity
         reconciliation, stale cleanup, index rebuild, resource compaction.

Every phase checks cancel, deadline and resource state between items, so a user
turn (which sets the runtime cancel event) is never blocked. RED (CRITICAL) = no
sleep at all; YELLOW (PRESSURE) = Sleep C only.

Claim limits: Sleep A's retention probe is retrieval-level (lexical/approved
recall path), not native model re-evaluation (that stays the explicit :replay
job). Sleep B produces structured, source-anchored hypotheses, not generated
text; native C3 dreaming stays the explicit :dream job. No weight consolidation.
"""
import itertools
import json
import math
import time
from pathlib import Path
from .common import uid,dumps,atomic_write,Cancelled
from .contracts import packet
from .memory import entities,relevance

SCHEDULE_KEY='SLEEP_REPLAY_SCHEDULE'
POLICY_KEY='SLEEP_POLICY'
LAST_KEY='SLEEP_LAST'
REVISION='sleep-replay-v1'
TYPES=('EPISODIC','PROCEDURAL','SEMANTIC','COUNTERFACTUAL','RETENTION_PROBE')
# §67 Layer 17 Age-0 gains (BOOT values from the blueprint, not measurements).
BASE_GAIN={'EPISODIC':.70,'RETENTION_PROBE':.75,'PROCEDURAL':.50,'SEMANTIC':.30,'COUNTERFACTUAL':.20}
DREAM_FACT_WRITE_GAIN=0  # L8.2 DREAM.fact_write_gain [LOCKED=0]: dreams never write facts, memories or weights
HYP_NEIGHBOR=.5     # WP-T11 BOOT: lexical relevance for a stored memory to count as evidence about a hypothesis
HYP_RECHECK_S=86400  # WP-T11 BOOT: UNVERIFIED hypotheses are re-checked at most daily
ROUTES=('simple','detail','gist','both')
RECALL_KINDS={'fact','style','preference'}
MAX_ITEMS=2048
DAY=86400.
# name: (default, lo, hi). Booleans and the mix are validated separately.
POLICY={'tick_seconds':(5.,1.,300.),'wake_replay_idle_s':(20.,5.,3600.),'sleep_idle_s':(600.,30.,86400.),
        'sleep_interval_s':(3600.,60.,7*DAY),'max_minutes':(10.,.1,120.),'batch':(8,1,64),'wake_batch':(2,1,8),
        'wake_min_priority':(.8,0.,1.),'spacing_s':(600.,10.,DAY),'max_interval_days':(30.,1.,365.),
        'ttl_days':(365.,1.,3650.),'trace_decay_per_day':(.98,.5,1.),'priority_floor':(.05,0.,.5),
        'dream_gain':(.05,0.,1.),'dream_max':(4,0,32),'retention_required':(.95,.5,1.),'tmp_max_age_days':(1.,.1,30.)}
MIX={'recent':.50,'protected_old':.35,'failure':.15}  # §67 replay sampling, Age 0
LOCKED={'dream_fact_write_gain':0.,'base_merge_authority':0.,'validation_required':True}

def default_policy():
    return {k:v[0] for k,v in POLICY.items()}|{'revision':REVISION,'enabled':True,'quiet_hours':None,'mix':dict(MIX)}|LOCKED
def validate_policy(p):
    for k,(d,lo,hi) in POLICY.items():
        v=p[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not lo<=v<=hi:raise ValueError(f'{k}: Bereich {lo}..{hi}')
        if isinstance(d,int) and not isinstance(v,int):raise ValueError(k+' muss ganzzahlig sein')
    if not isinstance(p['enabled'],bool):raise ValueError('enabled true|false')
    # §94: malformed persisted/operator policies must fail before replay sampling.
    from .sleep_policy_finite import validate_quiet_hours,validate_mix
    validate_quiet_hours(p['quiet_hours'])
    validate_mix(p['mix'],MIX)
    for k,v in LOCKED.items():
        if p.get(k)!=v:raise ValueError(k+' ist gesperrt')
    return p
def empty_schedule():
    return {'revision':REVISION,'items':{},'gains':dict(BASE_GAIN),'usage':{t:0. for t in TYPES},'last_full':0.,'signatures':[],'cycles':0}
def in_quiet_hours(policy,wall):
    q=policy.get('quiet_hours')
    if not q:return False
    h=time.localtime(wall).tm_hour;a,b=q
    return a<=h<b if a<=b else (h>=a or h<b)

class ReplayQueue:
    """Spaced, prioritised replay schedule over the durable `replay` table (§94.1)."""
    def __init__(self,store,clock=time.time):self.s=store;self.clock=clock
    def load(self):
        st,v=self.s.state(SCHEDULE_KEY,empty_schedule())
        if st.get('revision')!=REVISION:raise ValueError('Replay schedule revision mismatch')
        return st,v
    def save(self,st,v):return self.s.set_state(SCHEDULE_KEY,st,expected=v)
    def enqueue(self,event_id,replay_type,priority,evidence_class,source_refs,max_authority='HYPOTHESIS_NO_LEARNING',
                unresolved_errors=(),affected_paths=(),ttl_days=None,extra=None):
        """New queue item in the shared table. SLEEP_QUEUED keeps it out of the native :replay job."""
        if replay_type not in TYPES:raise ValueError('replay_type')
        if not 0<=priority<=1:raise ValueError('priority 0..1')
        rid=uid('replay');now=self.clock()
        with self.s.tx() as c:c.execute('INSERT INTO replay VALUES (?,?,?,?,?,?)',(rid,event_id,replay_type,float(priority),'SLEEP_QUEUED',now))
        p=packet('ReplayItem','F9_SLEEP_QUEUE',event_id,self.s.generation_id,source_refs,replay_type=replay_type,source_refs=source_refs,
                 priority=float(priority),max_authority=max_authority,replay_id=rid,evidence_class=evidence_class,stage='QUEUED',
                 unresolved_errors=list(unresolved_errors),affected_paths=list(affected_paths),ttl_days=ttl_days,fact_write_authority=0,**(extra or {}))
        self.s.add_packet('ReplayItem',p);return rid
    def sync(self,st,policy):
        """Index rebuild: every replay row gets a schedule entry; vanished rows retire."""
        rows=self.s.rows('SELECT r.*,e.session_id FROM replay r JOIN events e ON e.id=r.event_id ORDER BY r.created LIMIT ?',(MAX_ITEMS+1,))
        seen=set();added=0
        for r in rows[:MAX_ITEMS]:
            seen.add(r['id'])
            if r['id'] in st['items']:continue
            kind=r['kind'] if r['kind'] in TYPES else 'EPISODIC'
            if r['kind']=='HUMAN_CORRECTION' and self.s.one("SELECT id FROM memories WHERE event_id=? AND kind='route' LIMIT 1",(r['event_id'],)):kind='PROCEDURAL'
            st['items'][r['id']]={'event_id':r['event_id'],'session_id':r['session_id'],'type':kind,'evidence_class':r['kind'],
                'priority':min(1.,max(0.,float(r['priority']))),'reps':0,'failures':0,'last':None,'last_outcome':None,
                'next_due':r['created'],'created':r['created'],'expires':r['created']+policy['ttl_days']*DAY,
                'retired':None,'unresolved_errors':[],'affected_paths':[]}
            added+=1
        for rid,it in st['items'].items():
            if rid not in seen and not it['retired'] and len(rows)<=MAX_ITEMS:it['retired']='ROW_GONE'
        if len(st['items'])>MAX_ITEMS:
            # Bound state: forget retired entries first (their replay rows and packets remain).
            for rid in sorted((k for k,v in st['items'].items() if v['retired']),key=lambda k:st['items'][k]['created'])[:len(st['items'])-MAX_ITEMS]:del st['items'][rid]
        return added,len(rows)>MAX_ITEMS
    @staticmethod
    def bucket(it):
        if it['last_outcome']=='FAIL' or it['failures']>it['reps']:return 'failure'
        return 'recent' if it['reps']==0 else 'protected_old'
    def due(self,st,now,types=None,min_priority=0.):
        return [(rid,it) for rid,it in st['items'].items() if not it['retired'] and it['next_due']<=now and it['priority']>=min_priority
                and it['type']!='COUNTERFACTUAL' and (types is None or it['type'] in types)]
    def sample(self,st,n,mix,now,min_priority=0.):
        """Bucketed sampling by `mix` (largest remainder), leftovers by score, then old/new interleave."""
        score=lambda kv:(kv[1]['priority']*st['gains'].get(kv[1]['type'],.5),-kv[1]['next_due'])
        buckets={b:sorted([kv for kv in self.due(st,now,min_priority=min_priority) if self.bucket(kv[1])==b],key=score,reverse=True) for b in MIX}
        from .sleep_policy_finite import normalized_quota
        quota=normalized_quota(mix,n);take={b:min(int(quota[b]),len(buckets[b])) for b in MIX}
        for b in sorted(MIX,key=lambda b:quota[b]-int(quota[b]),reverse=True):
            if sum(take.values())<n and take[b]<len(buckets[b]):take[b]+=1
        rest=sorted([kv for b in MIX for kv in buckets[b][take[b]:]],key=score,reverse=True)
        chosen={b:buckets[b][:take[b]] for b in MIX}
        extra=rest[:max(0,n-sum(take.values()))]
        for kv in extra:chosen[self.bucket(kv[1])].append(kv)
        new=chosen['recent']+chosen['failure'];old=chosen['protected_old']
        return [kv for pair in itertools.zip_longest(new,old) for kv in pair if kv]

class SleepCycle:
    def __init__(self,store,cfg,memory,consolidation=None,age=None,home=None,clock=time.time,monotonic=time.monotonic,plasticity=None):
        self.s=store;self.cfg=cfg;self.memory=memory;self.consolidation=consolidation;self.age=age
        self.home=Path(home or store.home);self.clock=clock;self.monotonic=monotonic;self.plasticity=plasticity
        self.neuromod=None
        if plasticity is not None:  # production wiring (SleepRuntime); direct test cycles stay independent
            from .neuromod import Neuromod
            self.neuromod=Neuromod(store,age)
        self.queue=ReplayQueue(store,clock)
    # policy -------------------------------------------------------------------------------------------
    def policy(self):
        p,_=self.s.state(POLICY_KEY,None)
        return validate_policy(default_policy()|(p or {}))
    def set_policy(self,name,value):
        p=self.policy()
        if name in LOCKED:raise ValueError(name+' ist gesperrt')
        if name=='quiet_hours':p[name]=None if value in (None,'off') else [int(x) for x in str(value).split('-')]
        elif name=='enabled':p[name]=str(value).lower() in {'1','true','on','ja'}
        elif name.startswith('mix.'):p['mix']=dict(p['mix'])|{name[4:]:float(value)}
        elif name in POLICY:p[name]=type(POLICY[name][0])(float(value)) if isinstance(POLICY[name][0],float) else int(value)
        else:raise ValueError('Unbekannter Sleep-Parameter: '+name)
        self.s.set_state(POLICY_KEY,validate_policy(p));return p
    # helpers ------------------------------------------------------------------------------------------
    def _allowed(self,right,resource_state):
        if self.age is None:return False
        try:return self.age.may(right,resource_mode=self._mode(resource_state))
        except Exception:return False
    def _budget(self,resource_state):
        if self.age is None:return None
        try:return self.age.budgets('system',self._mode(resource_state))
        except Exception:return None
    def _mode(self,resource_state):
        """§97.2 mode: the live guard's finer mode while its state matches (YELLOW is invisible in legacy states)."""
        from .resource_modes import LEGACY_MODE,RANK,mode_of
        g=getattr(getattr(self,'runtime',None),'guard',None)
        if g is not None and getattr(g,'state',None)==resource_state:return mode_of(g)
        return resource_state if resource_state in RANK else LEGACY_MODE.get(resource_state,'RED')  # unknown: no background work
    def _checkpoint(self,cancel,deadline,resource,allowed=('NORMAL','RECOVERY')):
        if cancel is not None and cancel.is_set():raise Cancelled('Sleep unterbrochen (Nutzer-Eingabe/Abbruch)')
        if deadline is not None and self.monotonic()>deadline:raise TimeoutError('Sleep-Zeitbudget erreicht')
        state=resource() if resource else 'NORMAL'
        if state not in allowed:raise ResourceWarning('Ressourcen-Modus '+state)
        return state
    # Sleep A ------------------------------------------------------------------------------------------
    def _probe(self,it):
        """Real retention test for one recorded episode. Returns (outcome, details)."""
        ev=self.s.one('SELECT * FROM events WHERE id=?',(it['event_id'],))
        if not ev:return 'RETIRE','EVENT_GONE',{}
        env=json.loads(ev['packet'])
        try:text=self.s.read_source(env['source_ref'])
        except ValueError:return 'RETIRE','SOURCE_DELETED',{}
        mems=self.s.rows('SELECT m.id,m.kind,m.value,m.source_id,s.hash,s.chars FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.event_id=? AND m.active=1 AND s.deleted=0',(it['event_id'],))
        if not mems:return 'RETIRE','SUPERSEDED_OR_FORGOTTEN',{}
        errors=[];checks=[];refs=[env['source_ref']];paths=set()
        recallable=[m for m in mems if m['kind'] in RECALL_KINDS]
        if recallable:
            found=self.memory.recall(text,ev['session_id'])
            ids={r.get('id') for r in found};values={r.get('value') for r in found}
            for m in recallable:
                ok=m['id'] in ids or m['value'] in values;checks.append({'memory_id':m['id'],'probe':'RECALL','pass':ok})
                if not ok:errors.append('RECALL_MISS:'+m['id']);paths.add('memory_retrieval')
        for m in mems:
            ref={'source_id':m['source_id'],'sha256':m['hash'],'char_start':0,'char_end':m['chars'],'modality':'text'}
            try:ok=self.s.read_source(ref)==m['value'];refs.append(ref)
            except ValueError:ok=False
            if m['kind']=='route' and self.consolidation is not None:
                try:
                    r=self.consolidation.route(text,ev['session_id'])
                    if r is not None and r.get('route') not in (None,m['value']):ok=False;errors.append('PROCEDURE_CONFLICT:'+m['id']);paths.add('procedural_index')
                except Exception:pass
            if m['kind'] not in RECALL_KINDS:checks.append({'memory_id':m['id'],'probe':'PROVENANCE','pass':ok})
            if not ok and not any(m['id'] in e for e in errors):errors.append('PROVENANCE_BROKEN:'+m['id']);paths.add('memory_provenance')
        return ('FAIL' if errors else 'PASS'),errors,{'checks':checks,'source_refs':refs,'affected_paths':sorted(paths)}
    def sleep_a(self,st,policy,n,cancel=None,deadline=None,resource=None,min_priority=0.,stage_candidates=True):
        now=self.clock();picked=self.queue.sample(st,n,policy['mix'],now,min_priority)
        rep={'phase':'SLEEP_A','selected':len(picked),'passed':0,'failed':0,'retired':0,'items':[],'by_bucket':{},'status':'DONE'}
        old=[0,0];new=[0,0]
        try:
            for rid,it in picked:
                self._checkpoint(cancel,deadline,resource)
                bucket=self.queue.bucket(it);outcome,errors,detail=self._probe(it)
                rep['by_bucket'][bucket]=rep['by_bucket'].get(bucket,0)+1;st['usage'][it['type']]=st['usage'].get(it['type'],0.)+1
                if outcome=='RETIRE':
                    it['retired']=errors;rep['retired']+=1;rep['items'].append({'replay_id':rid,'outcome':'RETIRED','reason':errors});continue
                it['last']=now;it['last_outcome']=outcome
                if outcome=='PASS':
                    it['reps']+=1;it['unresolved_errors']=[]
                    it['next_due']=now+min(policy['spacing_s']*2**it['reps'],policy['max_interval_days']*DAY)
                    if it['reps']>=3 and it['type']=='EPISODIC':it['type']='RETENTION_PROBE'
                    rep['passed']+=1
                else:
                    it['failures']+=1;it['unresolved_errors']=errors[:16];it['affected_paths']=detail['affected_paths']
                    it['priority']=min(1.,it['priority']+.1);it['next_due']=now+policy['spacing_s']/2;rep['failed']+=1
                tally=old if bucket=='protected_old' else new;tally[0]+=outcome=='PASS';tally[1]+=1
                p=packet('ReplayItem','F9_SLEEP_A',it['event_id'],self.s.generation_id,detail['source_refs'],replay_type=it['type'],
                         source_refs=detail['source_refs'],priority=it['priority'],max_authority='RETENTION_TEST_NO_LEARNING',replay_id=rid,
                         stage='SLEEP_A',outcome=outcome,bucket=bucket,checks=detail['checks'],unresolved_errors=errors[:16],
                         affected_paths=detail['affected_paths'],evidence_class=it['evidence_class'],fact_write_authority=0)
                self.s.add_packet('ReplayItem',p);rep['items'].append({'replay_id':rid,'outcome':outcome,'bucket':bucket,'packet_id':p['packet_id']})
        except (Cancelled,TimeoutError,ResourceWarning) as exc:rep['status']='INTERRUPTED';rep['reason']=type(exc).__name__+': '+str(exc)
        rep['retention_old']=old[0]/old[1] if old[1] else None;rep['retention_new']=new[0]/new[1] if new[1] else None
        # Regression shield hint (G8): protected-old retention below the BOOT gate is flagged, never auto-fixed.
        rep['regression_flag']=rep['retention_old'] is not None and rep['retention_old']<policy['retention_required']
        rep['consolidation']=self._stage(st,picked,cancel,deadline) if stage_candidates and rep['status']=='DONE' else {'status':'SKIPPED'}
        return rep
    def _stage(self,st,picked,cancel,deadline):
        """Candidate consolidation: staging only; approval stays human (§94.2, CONSOLIDATE.base_merge_authority_age0=0)."""
        if self.consolidation is None:return {'status':'UNAVAILABLE'}
        if self.cfg['learning_mode']=='RECORD_ONLY':return {'status':'SKIPPED_RECORD_ONLY'}
        sessions=sorted({it['session_id'] for _,it in picked if it['last_outcome']=='PASS'});out={'status':'DONE','requests':[],'errors':[]}
        for sid in sessions:
            for comp in ('semantic','procedural'):
                try:out['requests']+=self.consolidation.stage(sid,comp,cancel=cancel,deadline=deadline)['requests']
                except Exception as exc:out['errors'].append(type(exc).__name__+': '+str(exc)[:200])
        out['automatic_activation']=False;return out
    # Sleep B ------------------------------------------------------------------------------------------
    def _hypothesis(self,st,signature,event_id,kind,text,anchors,payload):
        if signature in st['signatures']:return None
        ref=self.s.source(text,'DREAM_HYPOTHESIS')
        conf=(payload.get('counterfactual') or {}).get('confidence')  # WP-T8: replay priority from coverage-based confidence
        prio=round(BASE_GAIN['COUNTERFACTUAL']*(.25+.75*float(conf)),4) if isinstance(conf,(int,float)) else BASE_GAIN['COUNTERFACTUAL']
        rid=self.queue.enqueue(event_id,'COUNTERFACTUAL',prio,'DREAM_'+kind,anchors+[ref],max_authority='HYPOTHESIS_NO_LEARNING',
                               extra={'hypothesis_kind':kind,'hypothesis':payload,'hypothesis_source_ref':ref,'validation_required':True})
        st['signatures']=(st['signatures']+[signature])[-1024:]
        try:
            from .episodes import Episodes
            Episodes(self.s,self.cfg).hypothesize(event_id,'hyp:'+ref['source_id'],'DREAM')  # WP-N8: HYPOTHESIS edge, never causal
        except Exception as exc:self.s.log('episodes_unavailable',event_id,{'stage':'dream','error':type(exc).__name__})
        return {'replay_id':rid,'kind':kind,'hypothesis_source_ref':ref}
    def sleep_b(self,st,policy,cancel=None,deadline=None,resource=None,limit=None):
        rep={'phase':'SLEEP_B','hypotheses':[],'status':'DONE','fact_write_authority':DREAM_FACT_WRITE_GAIN}
        real=sum(1 for it in st['items'].values() if not it['retired'] and it['type']!='COUNTERFACTUAL')
        budget=limit if limit is not None else min(policy['dream_max'],max(1,math.ceil(policy['dream_gain']*real))) if real else 0
        rep['budget']=budget
        if not budget:return rep
        rows=self.s.rows("SELECT m.id,m.event_id,m.kind,m.key_text,m.value,m.session_id,s.hash,s.chars,m.source_id FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.active=1 AND s.deleted=0 ORDER BY m.created DESC LIMIT 512")
        ref=lambda m:{'source_id':m['source_id'],'sha256':m['hash'],'char_start':0,'char_end':m['chars'],'modality':'text'}
        def candidates():
            # 1) route alternatives on real anchored episodes (counterfactual replay, §37)
            # WP-T8 §7.2.2: alternatives ordered by counterfactual confidence (action coverage), not by table order
            from .world_model import for_event,load as wm_load
            wm=wm_load(self.s)
            for m in (m for m in rows if m['kind']=='route'):
                cfs=sorted(((alt,for_event(self.s,m['event_id'],alt) if wm else None) for alt in ROUTES if alt!=m['value']),key=lambda x:-(x[1] or {}).get('confidence',0.))
                for alt,cf in cfs:
                    yield ('ROUTE_ALTERNATIVE','route:'+m['id']+':'+alt,m['event_id'],[ref(m)],
                           f'Hypothese (kein Fakt): Ereignis {m["event_id"]} könnte mit Route {alt} statt {m["value"]} gleich gut oder besser beantwortet werden.',
                           {'observed_route':m['value'],'alternative_route':alt,'memory_id':m['id'],
                            'counterfactual':cf or {'confidence':None,'label':'SIMULATION_UNCERTAIN','reason':'NO_WORLD_MODEL','authority':'HYPOTHESIS'}})
            # 2) skill recombination: distinct cues that share one human route decision
            by_route={}
            for m in (m for m in rows if m['kind']=='route'):by_route.setdefault(m['value'],[]).append(m)
            for route,ms in by_route.items():
                for a,b in itertools.combinations(ms[:8],2):
                    if a['key_text'].strip().lower()!=b['key_text'].strip().lower():
                        yield ('SKILL_RECOMBINATION','skill:'+':'.join(sorted((a['id'],b['id']))),a['event_id'],[ref(a),ref(b)],
                               f'Hypothese (kein Fakt): Zwei Anfragen mit gleicher Route {route} könnten eine gemeinsame Routine bilden.',
                               {'route':route,'memory_ids':[a['id'],b['id']]})
            # 3) world hypotheses: different entities sharing one exact corrected value
            by_value={}
            for m in (m for m in rows if m['kind']=='fact'):by_value.setdefault(m['value'].strip().lower(),[]).append(m)
            for value,ms in by_value.items():
                for a,b in itertools.combinations(ms[:8],2):
                    ea,eb=entities(a['key_text']),entities(b['key_text'])
                    if ea and eb and not ea&eb:
                        yield ('WORLD_RELATION','world:'+':'.join(sorted((a['id'],b['id']))),a['event_id'],[ref(a),ref(b)],
                               f'Hypothese (kein Fakt): {sorted(ea)[0]} und {sorted(eb)[0]} teilen denselben korrigierten Wert; mögliche Beziehung, nicht geprüft.',
                               {'entities':[sorted(ea)[0],sorted(eb)[0]],'memory_ids':[a['id'],b['id']]})
        try:
            for kind,sig,eid,anchors,text,payload in candidates():
                if len(rep['hypotheses'])>=budget:break
                self._checkpoint(cancel,deadline,resource)
                h=self._hypothesis(st,sig,eid,kind,text,anchors,payload)
                if h:rep['hypotheses'].append(h)
            rep['validation']=self.validate_hypotheses(st,policy,cancel,deadline,resource)
        except (Cancelled,TimeoutError,ResourceWarning) as exc:rep['status']='INTERRUPTED';rep['reason']=type(exc).__name__+': '+str(exc)
        return rep
    # WP-T11 §15.4 / L8.2 DREAM.validation_required: hypotheses are checked against stored sources, never written as facts.
    def _memory(self,mid):
        return self.s.one("SELECT m.id,m.kind,m.key_text,m.value,m.active,m.source_id,s.hash,s.chars,s.deleted FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=?",(mid,))
    def _neighbors(self,kind,key,exclude):
        rows=self.s.rows("SELECT m.id,m.key_text,m.value FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.active=1 AND s.deleted=0 AND m.kind=? ORDER BY m.created DESC LIMIT 512",(kind,))
        return [m for m in rows if m['id'] not in exclude and (m['key_text'].strip().lower()==key.strip().lower() or relevance(key,m['key_text'])>=HYP_NEIGHBOR)]
    def check_hypothesis(self,item):
        """SUPPORTED / CONTRADICTED / UNVERIFIED / STALE against the stored memories and sources; evidence = memory ids."""
        for ref in item['source_refs']:
            try:self.s.read_source(ref)
            except Exception:return {'verdict':'STALE','reason':'SOURCE_GONE','evidence':[]}
        kind=item.get('hypothesis_kind');h=item.get('hypothesis') or {}
        ids=h.get('memory_ids') or ([h['memory_id']] if h.get('memory_id') else [])
        ms=[self._memory(i) for i in ids]
        if not ms or any(m is None or not m['active'] or m['deleted'] for m in ms):return {'verdict':'STALE','reason':'MEMORY_INACTIVE','evidence':[]}
        if kind=='ROUTE_ALTERNATIVE':
            m=ms[0];nb=self._neighbors('route',m['key_text'],{m['id']})
            sup=[x['id'] for x in nb if x['value']==h['alternative_route']];con=[x['id'] for x in nb if x['value']==h['observed_route']]
        elif kind=='SKILL_RECOMBINATION':
            if len({m['value'] for m in ms})>1:return {'verdict':'CONTRADICTED','reason':'ROUTES_DIVERGED','evidence':ids}
            nb={x['id']:x for m in ms for x in self._neighbors('route',m['key_text'],set(ids))}
            sup=[i for i,x in nb.items() if x['value']==h['route']];con=[i for i,x in nb.items() if x['value']!=h['route']]
            con=con if len(con)>len(sup) else []
        elif kind=='WORLD_RELATION':
            if len({m['value'].strip().lower() for m in ms})>1:return {'verdict':'CONTRADICTED','reason':'VALUES_DIVERGED','evidence':ids}
            ents=[e.lower() for e in h.get('entities',[])];sup=[];con=[]
            for row in self.s.rows("SELECT m.id,m.key_text,m.value FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.active=1 AND s.deleted=0 ORDER BY m.created DESC LIMIT 512"):
                if row['id'] in ids:continue
                text=(row['key_text']+' '+row['value']).lower()
                if ents and all(e in text for e in ents):sup.append(row['id'])
        else:return {'verdict':'UNVERIFIED','reason':'UNKNOWN_KIND','evidence':[]}
        if len(sup)>len(con):return {'verdict':'SUPPORTED','reason':'STORED_EVIDENCE','evidence':sup[:8]}
        if len(con)>len(sup):return {'verdict':'CONTRADICTED','reason':'STORED_COUNTER_EVIDENCE','evidence':con[:8]}
        return {'verdict':'UNVERIFIED','reason':'NO_STORED_EVIDENCE','evidence':[]}
    def validate_hypotheses(self,st,policy,cancel=None,deadline=None,resource=None,limit=None):
        """Checks queued dream hypotheses once (re-checked when new evidence may exist: UNVERIFIED after HYP_RECHECK_S).
        Verdicts are ReplayItem packets with fact_write_authority 0; CONTRADICTED/STALE hypotheses retire from the queue."""
        checks=st.setdefault('hypothesis_checks',{});now=self.clock();out={'checked':0,'by_verdict':{}}
        budget=policy['dream_max'] if limit is None else limit
        rows=self.s.rows("SELECT payload FROM packets WHERE kind='ReplayItem' AND json_extract(payload,'$.stage')='QUEUED' AND json_extract(payload,'$.replay_type')='COUNTERFACTUAL' ORDER BY created DESC LIMIT 256")
        for row in rows:
            if out['checked']>=budget:break
            item=json.loads(row['payload']);rid=item['replay_id'];prev=checks.get(rid)
            if not item.get('validation_required') or (prev and (prev['verdict']!='UNVERIFIED' or now-prev['at']<HYP_RECHECK_S)):continue
            self._checkpoint(cancel,deadline,resource)
            v=self.check_hypothesis(item);checks[rid]={'verdict':v['verdict'],'at':now}
            refs=item['source_refs']
            self.s.add_packet('ReplayItem',packet('ReplayItem','F9_SLEEP_B',item['event_id'],self.s.generation_id,refs,replay_type='COUNTERFACTUAL',source_refs=refs,
                priority=item['priority'],max_authority='HYPOTHESIS_NO_LEARNING',replay_id=rid,evidence_class=item['evidence_class'],stage='SLEEP_B_VALIDATION',
                outcome=v['verdict'],validation=v,hypothesis_kind=item.get('hypothesis_kind'),fact_write_authority=DREAM_FACT_WRITE_GAIN))
            if v['verdict'] in ('CONTRADICTED','STALE') and rid in st['items']:st['items'][rid]['retired']='HYPOTHESIS_'+v['verdict']
            out['checked']+=1;out['by_verdict'][v['verdict']]=out['by_verdict'].get(v['verdict'],0)+1
        if len(checks)>1024:
            for k in sorted(checks,key=lambda k:checks[k]['at'])[:len(checks)-1024]:del checks[k]
        return out
    # Sleep C ------------------------------------------------------------------------------------------
    def sleep_c(self,st,policy,cancel=None,deadline=None,resource=None):
        rep={'phase':'SLEEP_C','status':'DONE'};now=self.clock()
        try:
            self._checkpoint(cancel,deadline,resource,('NORMAL','RECOVERY','PRESSURE'))
            added,overflow=self.queue.sync(st,policy);rep['index_rebuild']={'added':added,'overflow':overflow}
            # §94.4: elapsed-time decay must not compound old elapsed days on
            # every Sleep C tick. Validate the whole schedule before mutation.
            from .sleep_trace_decay import plan_trace_decay,apply_trace_decay
            trace_plan=plan_trace_decay(st['items'].values(),now,policy['trace_decay_per_day'],policy['priority_floor'])
            decayed,expired=apply_trace_decay(trace_plan)
            rep['trace_decay']={'decayed':decayed,'expired':expired}
            self._checkpoint(cancel,deadline,resource,('NORMAL','RECOVERY','PRESSURE'))
            rep['homeostasis']=self._homeostasis(st,now)
            if getattr(self,'runtime',None) is not None:  # WP-T11 §16.2: measured parameter drift/saturation with a gate
                try:
                    from .homeostasis import run as homeo_run
                    rep['homeostasis_gate']=homeo_run(self.runtime,st['gains'])['gate']
                except Exception as exc:rep['homeostasis_gate']={'status':'ERROR','error':type(exc).__name__}
            try:
                from .archive import run as archive_run
                rep['archive']=archive_run(self.s,self.clock)  # WP-U4 §9.5: cold exact sources go to compressed storage
            except Exception as exc:rep['archive']={'status':'ERROR','error':type(exc).__name__}
            if self.plasticity is not None:
                try:self.plasticity.reconcile();rep['plasticity']='RECONCILED'
                except Exception as exc:rep['plasticity']='ERROR: '+type(exc).__name__
            if self.neuromod is not None:
                try:rep['neuromodulation']=self.neuromod.sleep()  # WP-N10 §16.3: fast traces end with sleep, tags re-checked
                except Exception as exc:rep['neuromodulation']='ERROR: '+type(exc).__name__
            self._checkpoint(cancel,deadline,resource,('NORMAL','RECOVERY','PRESSURE'))
            removed=0;tmp=self.home/'tmp'
            if tmp.is_dir():
                for f in tmp.iterdir():
                    try:
                        if f.is_file() and now-f.stat().st_mtime>policy['tmp_max_age_days']*DAY:f.unlink();removed+=1
                    except OSError:pass
            rep['stale_cleanup']={'tmp_files_removed':removed}
            stale=self.s.one("SELECT COUNT(*) AS n FROM updates WHERE status IN ('ABORTED','EVALUATED_FAIL','REJECTED','ROLLED_BACK')")['n']
            rep['stale_deltas']={'count':stale,'action':'REPORT_ONLY_ROLLBACK_WINDOW'}
            pruned=self.s.prune_telemetry()
            with self.s.mutex:ck=self.s.db.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()
            rep['compaction']={'telemetry_pruned':pruned,'wal_checkpoint':list(ck) if ck else None}
        except (Cancelled,TimeoutError,ResourceWarning) as exc:rep['status']='INTERRUPTED';rep['reason']=type(exc).__name__+': '+str(exc)
        return rep
    def _homeostasis(self,st,now):
        """§16.2: damp dominant replay types, reopen starved ones; bounded to 0.5..1.5 x base, specialisation allowed."""
        usage=st['usage'];total=sum(usage.values());changes={}
        present={it['type'] for it in st['items'].values() if not it['retired'] and it['type']!='COUNTERFACTUAL'}
        if total<=0 or not present:return {'changes':changes,'usage_total':total}
        gsum=sum(st['gains'][t] for t in present)
        for t in present:
            share=usage.get(t,0.)/total;expected=st['gains'][t]/gsum;g=st['gains'][t]
            if share>min(.9,1.5*expected):g*=.95
            elif share==0 and self.queue.due(st,now,types={t}):g*=1.05
            g=min(1.5*BASE_GAIN[t],max(.5*BASE_GAIN[t],g))
            if g!=st['gains'][t]:changes[t]=round(g,6);st['gains'][t]=g
        st['usage']={t:usage.get(t,0.)*.5 for t in TYPES}  # slow EMA of usage
        return {'changes':changes,'usage_total':total}
    # orchestration ------------------------------------------------------------------------------------
    def run(self,mode='full',cancel=None,resource=None,origin='USER',batch=None):
        """mode: full | wake | a | b | c. Returns a report; persists schedule even when interrupted."""
        if mode not in {'full','wake','a','b','c'}:raise ValueError('Sleep-Modus full|wake|a|b|c')
        policy=self.policy();started=self.monotonic();deadline=started+policy['max_minutes']*60
        state=resource() if resource else 'NORMAL'
        report={'kind':'V13_SLEEP','revision':REVISION,'mode':mode,'origin':origin,'resource_state':state,'started':self.clock(),'phases':[],
                'fact_write_authority':DREAM_FACT_WRITE_GAIN,'weight_updates':False,'generation':self.s.generation_id}
        if state=='CRITICAL':
            report['status']='SKIPPED_RESOURCE_RED';self._finish(report,None,None,started);return report
        if mode=='full':
            try:
                from .episodes import Episodes
                report['episodes_closed']=Episodes(self.s,self.cfg).close_all('sleep')  # WP-N8: sleep is an event boundary
            except Exception as exc:self.s.log('episodes_unavailable',None,{'stage':'sleep','error':type(exc).__name__})
        st,v=self.queue.load()
        try:
            self.queue.sync(st,policy)
            budget=self._budget(state) if origin!='USER' else None
            n=batch or (policy['wake_batch'] if mode=='wake' else policy['batch'])
            if budget is not None:n=min(n,max(1,budget['replay_items']))  # Age envelope caps autonomous replay
            from .resource_modes import scaled
            report['resource_mode']=self._mode(state);n=scaled(n,report['resource_mode'],'replay_scale') or n  # §97.2 YELLOW halves replay (ORANGE/RED skip Sleep A below)
            report['replay_budget']=n
            if mode in {'full','wake','a'} and state!='PRESSURE':
                report['phases'].append(self.sleep_a(st,policy,n,cancel,deadline,resource,
                                        min_priority=policy['wake_min_priority'] if mode=='wake' else 0.,stage_candidates=mode!='wake'))
                if mode in {'full','a'} and report['phases'][-1]['status']!='INTERRUPTED':  # WP-S7 offline compute: day digest, predictor passes, TTT candidates
                    from . import sleep_offline
                    report['phases'].append(sleep_offline.run(self,state,cancel,deadline,resource,origin))
            if mode in {'full','b'} and state!='PRESSURE':
                from .inputs import paused
                if paused(self.s,'traum'):report['phases'].append({'phase':'SLEEP_B','status':'SKIPPED_PAUSED_TRAUM'})
                elif origin=='USER' or self._allowed('short_dream',state):report['phases'].append(self.sleep_b(st,policy,cancel,deadline,resource))
                else:report['phases'].append({'phase':'SLEEP_B','status':'SKIPPED_AGE_RIGHT','right':'short_dream'})
            if mode in {'full','c'}:report['phases'].append(self.sleep_c(st,policy,cancel,deadline,resource))
            if mode=='full':st['last_full']=self.clock()
            st['cycles']+=1
            statuses={p['status'] for p in report['phases']}
            report['status']='INTERRUPTED' if 'INTERRUPTED' in statuses else ('SKIPPED_RESOURCE_YELLOW' if state=='PRESSURE' and mode not in {'full','c'} else 'DONE')
        except BaseException as exc:
            report['status']='ERROR';report['error']=type(exc).__name__+': '+str(exc)[:500];raise
        finally:self._finish(report,st,v,started)
        return report
    def _finish(self,report,st,v,started):
        if st is not None:
            try:self.queue.save(st,v)
            except ValueError:
                # A concurrent explicit edit won; re-run is safe because every step is idempotent per item.
                report['schedule_saved']=False
        report['duration_s']=round(self.monotonic()-started,3)
        path=self.home/'exports/sleep-last.json';atomic_write(path,dumps(report));report['artifact']=str(path)
        self.s.set_state(LAST_KEY,{k:report[k] for k in ('mode','origin','status','resource_state','started','duration_s')}|{'phases':[{k:p.get(k) for k in ('phase','status','selected','passed','failed','retired','retention_old','regression_flag')} for p in report['phases']]})
        a=next((p for p in report['phases'] if p['phase']=='SLEEP_A'),{});b=next((p for p in report['phases'] if p['phase']=='SLEEP_B'),{})
        self.s.log('sleep_cycle',None,{'phase':report['mode'],'status':report['status'],'origin':report['origin'],'resource_state':report['resource_state'],
                   'items':a.get('selected',0),'passed':a.get('passed',0),'failed':a.get('failed',0),'retired':a.get('retired',0),
                   'retention_rate':a.get('retention_old'),'hypotheses':len(b.get('hypotheses',[])),'duration_s':report['duration_s']})
    def status(self):
        st,v=self.queue.load();now=self.clock();live=[it for it in st['items'].values() if not it['retired']]
        return {'revision':REVISION,'policy':self.policy(),'last':self.s.state(LAST_KEY,None)[0],'items':len(st['items']),'live':len(live),
                'due':len(self.queue.due(st,now)),'by_type':{t:sum(it['type']==t for it in live) for t in TYPES},
                'by_bucket':{b:sum(ReplayQueue.bucket(it)==b for it in live if it['type']!='COUNTERFACTUAL') for b in MIX},
                'gains':st['gains'],'cycles':st['cycles'],'last_full':st['last_full'],
                'claim_limit':'Retrieval-level retention probes and structured hypotheses; no native re-evaluation, no weight consolidation'}

class SleepRuntime:
    """Coordinator glue: idle/timer/resource wakes → background sleep jobs. Never blocks a user turn."""
    def __init__(self,runtime,clock=time.time,monotonic=time.monotonic):
        from .scheduler import EventScheduler
        from .plasticity import Plasticity
        self.r=runtime;self.clock=clock;self.monotonic=monotonic;self.age=None
        try:
            from .age import controller
            self.age=controller(runtime)
        except Exception:self.age=None  # conservative: no self-initiative, no autonomous dream
        self.scheduler=EventScheduler(runtime.store,runtime.cfg,clock,self.age)
        self.cycle=SleepCycle(runtime.store,runtime.cfg,runtime.memory,getattr(runtime,'consolidation',None),self.age,runtime.home,clock,monotonic,Plasticity(runtime.store))
        self.cycle.runtime=runtime  # WP-T11 homeostasis reads the learned heads through their runtime controllers
        self.scheduler.recover();self.last_tick=-1e18;self.last_resource=None
        runtime.store.set_meta('sleep_boot_wall',clock())  # idle clock restarts with the process
    def resource_state(self):
        try:return self.r.guard.update(self.r.resources())
        except Exception:return 'CRITICAL'  # unknown resources: do not start background work
    def idle_seconds(self):
        row=self.r.store.one("SELECT MAX(COALESCE(finished_at,started_at,accepted_at)) AS t FROM accepted_turns")
        last=max(row['t'] or 0.,self.r.store.meta('sleep_boot_wall',0.) or 0.)
        return max(0.,self.clock()-last)
    def tick(self,force=False):
        policy=self.cycle.policy()
        if not force and self.monotonic()-self.last_tick<policy['tick_seconds']:return None
        self.last_tick=self.monotonic()
        if not self.r.idle():return None
        state=self.resource_state()
        if state!=self.last_resource:
            if self.last_resource is not None:self.scheduler.post('RESOURCE_CHANGE',payload={'from':self.last_resource,'to':state})
            self.last_resource=state
        if policy['enabled']:
            idle=self.idle_seconds();st,_=self.cycle.queue.load();now=self.clock()
            if idle>=policy['sleep_idle_s'] and now-st['last_full']>=policy['sleep_interval_s']:
                self.scheduler.post('IDLE',action='sleep_full',dedup='idle-sleep-full')
            elif idle>=policy['wake_replay_idle_s'] and self.cycle.queue.due(st,now,min_priority=policy['wake_min_priority']):
                # G13 soak finding: one wake replay per idle period. Back-to-back wake replays (Age-0 budget: one item
                # each) outranked IDLE and used up the burn-out budget, so the night's full sleep never ran.
                period=round(now-idle,3)
                if self.r.store.meta('sleep_wake_replay_period',None)!=period and self.scheduler.post('REPLAY_DUE',action='wake_replay',dedup='wake-replay'):
                    self.r.store.set_meta('sleep_wake_replay_period',period)
            if idle>=policy['wake_replay_idle_s']:
                try:  # WP-T10 §14.3: medium timescale (authority review) on idle, at most every authority.MEDIUM_S
                    from .authority import medium_due
                    if medium_due(self.r.store,self.clock()):self.scheduler.post('IDLE',action='learn_medium',dedup='learn-medium')
                except Exception as exc:self.r.store.log('job_error',None,{'kind':'learn_medium_post','error':type(exc).__name__})
        e=self.scheduler.next(idle=True,resource_state=state,quiet=in_quiet_hours(policy,self.clock()))
        if not e:return None
        if e['action'] in (None,'notice'):
            if e['action']=='notice' and e['payload'].get('text'):self.r.notice(str(e['payload']['text'])[:500])
            self.scheduler.complete(e['id'],'DONE',{'recorded':True});return e
        with self.r.lock:
            if self.r.idle() and not self.r.jobs.full():self.r.jobs.put_nowait(('sleep',e,0,time.monotonic()));queued=True
            else:queued=False
        if not queued:self.scheduler.complete(e['id'],'RETRY',{'reason':'BUSY'})
        self.r.wake.set();return e
    def job(self,e):
        if str(e['action']).startswith('growth_'):return self._growth(e)
        if str(e['action']).startswith('learn_'):return self._learn(e)
        mode={'sleep_full':'full','wake_replay':'wake','sleep_a':'a','sleep_b':'b','sleep_c':'c'}[e['action']]
        try:rep=self.cycle.run(mode,self.r.cancel_event,self.resource_state,'USER' if e['origin']=='USER' else 'SYSTEM')
        except BaseException as exc:
            self.scheduler.complete(e['id'],'FAILED',{'error':type(exc).__name__});raise
        self.scheduler.complete(e['id'],'CANCELLED' if rep['status']=='INTERRUPTED' else 'DONE',{'status':rep['status']})
        if e['origin']=='USER':self.r.notice('Sleep '+mode+': '+rep['status']+' ('+rep['artifact']+')')
        try:
            from .agi import after_sleep
            rep['growth']=after_sleep(self,e,rep)  # WP-AG6/AG12 hooks; never fails the sleep job
        except Exception as exc:self.r.store.log('job_error',None,{'kind':'growth_after_sleep','error':type(exc).__name__})
        if mode=='full' and rep['status']=='DONE':
            try:self.scheduler.post('TIMER',action='learn_slow',dedup='learn-slow')  # WP-T10 §14.4 slow timescale after a full night
            except Exception as exc:self.r.store.log('job_error',None,{'kind':'learn_slow_post','error':type(exc).__name__})
        return rep
    def _learn(self,e):
        from .authority import job
        try:out=job(self.r,e['action'],e['origin'])
        except BaseException as exc:
            self.scheduler.complete(e['id'],'FAILED',{'error':type(exc).__name__});raise
        self.scheduler.complete(e['id'],'DONE',{'status':out.get('status')})
        if e['origin']=='USER':self.r.notice('Learn '+e['action']+': '+str(out.get('status')))
        return out
    def _growth(self,e):
        from .agi import job
        try:out=job(self,e)
        except BaseException as exc:
            self.scheduler.complete(e['id'],'FAILED',{'error':type(exc).__name__});raise
        self.scheduler.complete(e['id'],'DONE',{'status':(out or {}).get('status')})
        if e['origin']=='USER':self.r.notice('Growth '+e['action']+': '+str((out or {}).get('status')))
        return out
    def request(self,mode='full',delay_s=0.):
        action={'full':'sleep_full','wake':'wake_replay','a':'sleep_a','b':'sleep_b','c':'sleep_c'}[mode]
        eid=self.scheduler.post('TIMER',origin='USER',due=self.clock()+max(0.,float(delay_s)),action=action)
        self.tick(force=True);return eid

def operator_command(r,cmd,args):
    """:sleep [status|digest|run full|a|b|c|wake|in <Minuten> [Modus]|policy [Name Wert]] / :scheduler"""
    sl=r.sleep
    if cmd=='scheduler':return dumps(sl.scheduler.report())
    if not args or args==['status']:return dumps(sl.cycle.status())
    if args[0]=='run' and len(args)<=2:
        mode=args[1] if len(args)==2 else 'full';sl.request(mode);return 'Sleep '+mode+' eingeplant; startet sobald nichts anderes läuft.'
    if args[0]=='in' and len(args) in (2,3):
        mode=args[2] if len(args)==3 else 'full';sl.request(mode,float(args[1])*60);return 'Sleep '+mode+' in '+args[1]+' min eingeplant.'
    if args==['digest']:
        from .sleep_offline import view
        return dumps(view(r.store,r.session) or {'session':r.session,'text':'','entries':0})
    if args[0]=='policy':
        if len(args)==1:return dumps(sl.cycle.policy())
        if len(args)==3:return dumps(sl.cycle.set_policy(args[1],args[2]))
    raise ValueError(':sleep [status|run full|a|b|c|wake|in <Minuten> [Modus]|policy [Name Wert]] / :scheduler')
