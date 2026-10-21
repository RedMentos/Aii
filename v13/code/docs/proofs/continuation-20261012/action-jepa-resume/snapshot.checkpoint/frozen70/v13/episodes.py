"""WP-N8: event segmentation, causal memory graph, memory admission/forgetting (A1, §9.3–9.5, §48.15, §51.2).

Experiences are grouped into episodes, not just chat messages. A boundary is cut from several signals
together (prediction error, context shift, goal shift, action transition, source transition, pause,
correction, failure), never from surprise alone (§48.15). Gains are §51.2 BOOT values; every boundary
stores its signal vector so the policy can be learned later (A1.learn_gain stays 0 here).

The graph keeps correlation and causality apart (§9.4): co-occurrence only ever raises a CORRELATIONAL
edge; a CAUSAL edge needs intervention evidence (an own committed action with observed outcome, or a
human correction); dream/sleep links stay HYPOTHESIS and are never promoted by counting.

Storage is `states` only (ids, hashes, numbers; no text), so no schema migration is needed.
"""
import json
import math
import re
from .common import uid,now,digest

REVISION='episodes-v1'
GAINS={'context_shift':.35,'prediction_error':.25,'goal_shift':.30,'action_transition':.30,'source_transition':.30,
       'correction':.60,'failure':.30,'pause':1.}  # §51.2 A1.* BOOT gains; pause is a hard boundary
EVIDENCE={'SEQUENCE':'TEMPORAL','CO_RETRIEVED':'CORRELATIONAL','RECALLED_IN':'CORRELATIONAL','SIMILAR':'CORRELATIONAL',
          'HUMAN_CORRECTION':'CAUSAL','OWN_ACTION_OUTCOME':'CAUSAL','DREAM':'HYPOTHESIS','TEACHER':'HYPOTHESIS'}
CAUSAL_EVIDENCE={'HUMAN_CORRECTION','OWN_ACTION_OUTCOME'}
SPREAD=.6;SPREAD_MAX=2;SPREAD_MIN_COUNT=2  # BOOT: associative recall scores a neighbour at .6 x its parent, at most 2 per turn,
                                          # only along edges seen at least twice (one co-retrieval is chance)
SPREAD_MODES=('off','shadow','on')
EDGE='mgraph:'

def clamp(x):return 0. if x is None or not math.isfinite(x) else max(0.,min(1.,float(x)))

# --- A1 inside one text (§51.2): event segments instead of fixed character chunks ---------------------------------
TEXT_GAINS={'fixed_chunk_prior':.40,'semantic_boundary':.25,'context_shift':.35,'goal_change':.30,'action_transition':.30}  # §51.2 BOOT
TEXT_THRESHOLD=.5;TEXT_MAX=1.5;TEXT_MIN=.25  # BOOT: cut score, hard cap and minimum share of the target width per segment
UNIT=re.compile(r'[^\n]*?(?:[.!?](?=\s|$)|\n|$)',re.S)
KIND=re.compile(r'^\s*(?:```|[-*•]\s|\d+[.)]\s|>\s|\$ |#)')
def _units(text):
    """Sentence/line units as (start, end) covering the text without gaps."""
    out=[];i=0
    for m in UNIT.finditer(text):
        if m.end()<=i:continue
        e=m.end()
        while e<len(text) and text[e] in ' \t':e+=1
        if e>i:out.append((i,e));i=e
        if i>=len(text):break
    if i<len(text):out.append((i,len(text)))
    return out
def _kind(t):return 'question' if t.rstrip().endswith('?') else ('structured' if KIND.match(t) else 'prose')
def text_signals(prev,unit,seg_len,width):
    """A1 boundary signals between the running segment (prev text) and the next unit; all in [0,1]."""
    gap=prev[-2:]+unit[:1] if prev else ''
    sem=1. if '\n\n' in prev[-3:]+unit[:1] else (.6 if prev.endswith('\n') else (.4 if prev.rstrip()[-1:] in '.!?' else 0.))
    shift=lexical_shift(prev[-240:],unit) if words(unit) and words(prev[-240:]) else 0.
    pk,uk=_kind(prev.splitlines()[-1] if prev.strip() else ''),_kind(unit)
    return {'fixed_chunk_prior':clamp(seg_len/max(1,width)),'semantic_boundary':sem,'context_shift':shift,
            'goal_change':float((pk=='question')!=(uk=='question')),'action_transition':float((pk=='structured')!=(uk=='structured'))}
def text_segments(text,ref,width=240,threshold=TEXT_THRESHOLD):
    """Event segments of one text (§51.2 A1, 'Boundary nicht nur aus Surprise'): cut where the noisy-OR of the BOOT
    gains reaches the threshold, never below TEXT_MIN of the width, always at TEXT_MAX of it. Over-long units are split
    boundary-aware without cutting exact spans (gist.group). Lossless: segments tile the text and keep their SourceRef."""
    if not text:return []
    from .gist import group
    pieces=[]
    for s,e in _units(text):
        if e-s>width*TEXT_MAX:
            for g in group(text[s:e],{'char_start':s},max(8,width//5),'boundary'):pieces.append((g['source_ref']['char_start'],g['source_ref']['char_end']))
            if pieces[-1][1]<e:pieces.append((pieces[-1][1],e))
        else:pieces.append((s,e))
    tiled=[];i=0  # close tiny gaps (whitespace between gist groups) so the segments tile the text exactly
    for s,e in pieces:
        if e<=i:continue
        tiled.append((i,e));i=e
    if i<len(text):tiled.append((i,len(text)))
    segs=[];start,end=tiled[0];why={'reason':'first'}
    def emit(s,e,meta):segs.append({'text':text[s:e],'source_ref':ref|{'char_start':s,'char_end':e},'scale':'event',**meta})
    for s,e in tiled[1:]:
        prev=text[start:end];unit=text[s:e];sig=text_signals(prev,unit,end-start,width);score=noisy_or(sig,TEXT_GAINS)
        cap=end-start+e-s>width*TEXT_MAX;cut=cap or (score>=threshold and end-start>=width*TEXT_MIN)
        if cut:
            emit(start,end,why);start=s
            why={'reason':'max_width' if cap and score<threshold else 'signals','boundary':round(score,4),
                 'signals':{k:round(v,3) for k,v in sig.items() if v}}
        end=e
    emit(start,end,why)
    return segs
def noisy_or(signals,gains):
    keep=1.
    for k,v in signals.items():
        if v is not None:keep*=1-gains.get(k,0.)*clamp(v)
    return 1-keep
def words(text):return set(re.findall(r'\w{3,}',text.lower()))
def lexical_shift(a,b):
    wa,wb=words(a),words(b)
    return 1.-len(wa&wb)/len(wa|wb) if wa and wb else 1.
def cosine(a,b):
    na=math.sqrt(sum(x*x for x in a));nb=math.sqrt(sum(x*x for x in b))
    return sum(x*y for x,y in zip(a,b))/(na*nb) if na>1e-12 and nb>1e-12 else 0.
def task_hash(task):return digest(json.dumps(task,sort_keys=True,ensure_ascii=False)) if task else None

class Episodes:
    def __init__(self,store,cfg,memory=None):self.s=store;self.cfg=cfg;self.memory=memory

    # ---------- segmentation ----------
    def _open_key(self,session):return 'episode-open:'+session
    def current(self,session):return self.s.state(self._open_key(session))[0]
    def signals(self,prev,cur):
        """Boundary signal vector between the open episode's last turn and this turn (None = unavailable)."""
        sig={k:None for k in GAINS}
        if prev is None:return sig
        if prev.get('vector') and cur.get('vector'):  # semantic shift: cosine at the recall floor counts as half a shift
            sig['context_shift']=clamp((1-cosine(prev['vector'],cur['vector']))/(1-self.cfg.get('memory_embed_threshold',.84)+1e-9)*.5)
        sig['goal_shift']=float(prev.get('task')!=cur.get('task')) if (prev.get('task') or cur.get('task')) else 0.
        sig['action_transition']=float(prev.get('route')!=cur.get('route')) if prev.get('route') and cur.get('route') else None
        sig['source_transition']=float(prev.get('modality')!=cur.get('modality'))
        sig['prediction_error']=cur.get('prediction_error')
        sig['correction']=1. if prev.get('correction_pending') else 0.
        sig['failure']=1. if prev.get('status') not in (None,'FINAL') else 0.
        gap=cur['time']-prev['time'];sig['pause']=1. if gap>=self.cfg.get('episode_pause_seconds',1800) else 0.
        return sig
    def observe(self,event_id,session,text,route=None,status='FINAL',task=None,modality='text',prediction_error=None,vector=None,memory_ids=(),clock=None,associative_ids=()):
        """Called once per finished turn. Returns the boundary decision; never blocks the turn."""
        t=now() if clock is None else clock;open_=self.current(session);prev=open_['last'] if open_ else None
        cur={'event_id':event_id,'time':t,'route':route,'status':status,'task':task_hash(task),'modality':modality,'prediction_error':prediction_error,
             'vector':[round(x,5) for x in vector] if vector else None}
        sig=self.signals(prev,cur)
        if prev and sig['context_shift'] is None:sig['context_shift']=lexical_shift(self._text_of(prev['event_id']),text)
        score=noisy_or(sig,GAINS);limit=self.cfg.get('episode_max_events',24)
        cut=open_ is None or score>=self.cfg.get('episode_boundary_threshold',.30) or len(open_['events'])>=limit
        reason='first' if open_ is None else ('max_events' if len(open_['events'])>=limit and score<self.cfg.get('episode_boundary_threshold',.30) else 'signals')
        if cut and open_:self._close(open_,sig,score,reason,t)
        if cut:open_={'id':uid('episode'),'session':session,'started':t,'events':[],'boundary':{'score':round(score,4),'signals':sig,'reason':reason},
                      'previous':open_['id'] if open_ else self._last_closed(session),'memory_ids':[],'corrections':0,'failures':0,'revision':REVISION}
        elif prev:self.link(prev['event_id'],event_id,'SEQUENCE')
        if cut and open_['previous']:self.link(open_['previous'],open_['id'],'SEQUENCE')
        open_['events'].append(event_id);open_['failures']+=status!='FINAL'
        for mid in memory_ids:
            if mid not in open_['memory_ids']:open_['memory_ids'].append(mid)
            self.link(event_id,mid,'RECALLED_IN')
        direct=[m for m in memory_ids if m not in set(associative_ids)]  # spread-added memories never strengthen their own edge
        for i,a in enumerate(direct):
            for b in direct[i+1:]:self.link(a,b,'CO_RETRIEVED')
        if memory_ids:self.reinforce(memory_ids,t)
        open_['last']=cur;self.s.set_state(self._open_key(session),open_)
        self.s.log('episode_boundary',event_id,{'cut':cut,'score':round(score,4),'reason':reason,'signals':{k:v for k,v in sig.items() if v is not None}})
        return {'episode_id':open_['id'],'cut':cut,'score':score,'signals':sig,'reason':reason}
    def _text_of(self,event_id):
        e=self.s.one('SELECT packet FROM events WHERE id=?',(event_id,))
        try:return self.s.read_source(json.loads(e['packet'])['source_ref']) if e else ''
        except Exception:return ''
    def _last_closed(self,session):return self.s.state('episode-last:'+session)[0]
    def _close(self,ep,sig,score,reason,t):
        ep=dict(ep);ep.pop('last',None);ep.update(ended=t,closed_by={'score':round(score,4),'signals':sig,'reason':reason})
        ep['admission']=self.admission(ep);ep['tier']='SEMANTIC_STAGING_CANDIDATE' if ep['admission']>=self.cfg.get('episode_admission_threshold',.5) else 'FAST_EPISODIC'
        self.s.set_state('episode:'+ep['id'],ep);self.s.set_state('episode-last:'+ep['session'],ep['id']);return ep
    def close(self,session,reason='operator'):
        """Explicit boundary (e.g. :episodes cut, sleep start)."""
        open_=self.current(session)
        if not open_:return None
        ep=self._close(open_,{},1.,reason,now());self.s.set_state(self._open_key(session),None);return ep
    def close_all(self,reason):
        n=0
        for r in self.s.rows("SELECT key FROM states WHERE key LIKE 'episode-open:%'"):n+=self.close(r['key'].split(':',1)[1],reason) is not None
        return n
    def on_correction(self,event_id,memory_id,session):
        """Human correction: CAUSAL edge event→memory and a forced boundary at the next turn."""
        self.link(event_id,memory_id,'HUMAN_CORRECTION')
        open_=self.current(session)
        if open_:
            open_['corrections']+=1;open_['last']['correction_pending']=True
            if memory_id not in open_['memory_ids']:open_['memory_ids'].append(memory_id)
            self.s.set_state(self._open_key(session),open_)
    def on_outcome(self,event_id,action_id,status):
        """Own committed action with observed outcome = intervention evidence."""
        self.link(event_id,'outcome:'+action_id,'OWN_ACTION_OUTCOME',detail={'status':status})
    def episode_of(self,event_id,session):
        open_=self.current(session)
        if open_ and event_id in open_['events']:return open_
        for r in self.s.rows("SELECT payload FROM states WHERE key LIKE 'episode:%'"):
            ep=json.loads(r['payload'])
            if ep and event_id in ep['events']:return ep
        return None
    def episodes(self,session,limit=20):
        rows=[json.loads(r['payload']) for r in self.s.rows("SELECT payload FROM states WHERE key LIKE 'episode:%'")]
        rows=[e for e in rows if e and e.get('session')==session];rows.sort(key=lambda e:e['started'],reverse=True)
        return rows[:limit]

    # ---------- causal memory graph (§9.4) ----------
    def _edge_key(self,a,b,kind):return EDGE+EVIDENCE[kind]+':'+kind+':'+a+'>'+b
    def link(self,a,b,kind,detail=None):
        if kind not in EVIDENCE:raise ValueError('Kantenart unbekannt')
        if kind=='CO_RETRIEVED' and b<a:a,b=b,a  # undirected correlation
        key=self._edge_key(a,b,kind);old,_=self.s.state(key);t=now()
        e=old or {'a':a,'b':b,'kind':kind,'evidence':EVIDENCE[kind],'count':0,'first':t,'directed':kind!='CO_RETRIEVED','authority':'NOT_A_FACT'}
        e['count']+=1;e['last']=t
        if detail:e['detail']=detail
        self.s.set_state(key,e);return e
    def hypothesize(self,cause,effect,source='DREAM'):
        """Dream/teacher causal guess: HYPOTHESIS only, never promoted by repetition."""
        if source not in {'DREAM','TEACHER'}:raise ValueError('Hypothese: DREAM|TEACHER')
        return self.link(cause,effect,source)
    def edges(self,node=None,evidence=None):
        rows=[json.loads(r['payload']) for r in self.s.rows("SELECT payload FROM states WHERE key LIKE ?",(EDGE+(evidence or '')+'%',))]
        return [e for e in rows if e and (node is None or node in (e['a'],e['b']))]
    def relation(self,a,b):
        """How a and b are related: CAUSAL only with intervention evidence, else CORRELATIONAL/HYPOTHESIS/TEMPORAL/NONE."""
        found={e['evidence'] for e in self.edges(a) if b in (e['a'],e['b'])}
        for level in ('CAUSAL','CORRELATIONAL','HYPOTHESIS','TEMPORAL'):
            if level in found:return {'relation':level,'kinds':sorted(found)}
        return {'relation':'NONE','kinds':[]}
    def causes(self,effect):return [e for e in self.edges(effect,'CAUSAL') if e['b']==effect]
    def effects(self,cause):return [e for e in self.edges(cause,'CAUSAL') if e['a']==cause]
    def related_memories(self,memory_ids,limit=3):
        """Associative spread: memories co-retrieved with or caused alongside the given ones (ranked by count)."""
        score={}
        for mid in memory_ids:
            for e in self.edges(mid):
                other=e['b'] if e['a']==mid else e['a']
                if other in memory_ids or not other.startswith('mem'):continue
                score[other]=score.get(other,0)+e['count']*(2 if e['evidence']=='CAUSAL' else 1)
        return [m for m,_ in sorted(score.items(),key=lambda x:-x[1])][:limit]
    def spread_mode(self):return (self.s.state('episodes-spread-mode')[0] or 'shadow')
    def set_spread_mode(self,mode):
        if mode not in SPREAD_MODES:raise ValueError('spread off|shadow|on')
        self.s.set_state('episodes-spread-mode',mode);return mode
    def spread(self,query,session,memories,top_k=3):
        """§9.4 associative recall: neighbours of the recalled memories in the graph (CORRELATIONAL/CAUSAL, count >= 2).
        SHADOW (default) only reports them; ON adds them as retrieval_channel='associative' with score SPREAD x parent,
        still inside memory_top_k. Value + SourceRef come from Memory.candidate (provenance re-checked); never a fact boost."""
        mode=self.spread_mode();ids=[m['id'] for m in memories]
        if mode=='off' or not ids or self.memory is None:return memories,[]
        score={};parent={}
        for m in memories:
            for e in self.edges(m['id']):
                other=e['b'] if e['a']==m['id'] else e['a']
                if other in ids or not other.startswith('mem') or e['evidence'] not in ('CORRELATIONAL','CAUSAL') or e['count']<SPREAD_MIN_COUNT:continue
                w=e['count']*(2 if e['evidence']=='CAUSAL' else 1)
                if w>score.get(other,0):score[other]=w;parent[other]=m
        found=[]
        for mid in sorted(score,key=lambda k:(-score[k],k))[:SPREAD_MAX]:
            try:c=self.memory.candidate(mid,session)
            except Exception:continue
            if not c or not c.get('active',1):continue
            p=parent[mid];c=dict(c,retrieval_score=round(SPREAD*float(p.get('retrieval_score') or 0.),4),retrieval_channel='associative',
                     retrieval_policy=None,embedding_similarity=None,associated_with=p['id'])
            if 'source_ref' not in c or 'value' not in c:continue
            found.append(c)
        if mode=='on' and found:
            merged=sorted(memories+found,key=lambda x:(x['retrieval_score'],x['created']),reverse=True)[:max(top_k,len(memories))]
        else:merged=memories
        self.s.log('memory_spread',None,{'mode':mode,'found':len(found),'applied':sum(m.get('retrieval_channel')=='associative' for m in merged)})
        return merged,[{'memory_id':c['id'],'score':c['retrieval_score'],'via':c['associated_with']} for c in found]
    def forget_node(self,node):
        with self.s.tx() as c:return c.execute("DELETE FROM states WHERE key LIKE ? AND (key LIKE ? OR key LIKE ?)",(EDGE+'%','%:'+node+'>%','%>'+node)).rowcount

    # ---------- admission + forgetting (§9.5) ----------
    def admission(self,ep):
        """Episode → semantic staging candidate? Corrections, failures, recall use and length raise it (noisy-OR)."""
        n=len(ep['events'])
        sig={'correction':min(1.,ep['corrections']),'failure':min(1.,ep['failures']/max(n,1)*2),'recall':min(1.,len(ep['memory_ids'])/3),'length':min(1.,n/8)}
        return round(noisy_or(sig,{'correction':.6,'failure':.3,'recall':.3,'length':.2}),4)
    def strength(self,memory_id,clock=None):
        st,_=self.s.state('mstrength:'+memory_id)
        if not st:return None
        days=((now() if clock is None else clock)-st['last'])/86400;half=self.cfg.get('memory_half_life_days',30)
        return st['s']*0.5**(days/half)
    def reinforce(self,memory_ids,clock=None):
        t=now() if clock is None else clock
        for mid in memory_ids:
            s=self.strength(mid,t) or 0.;st,_=self.s.state('mstrength:'+mid);hits=(st or {}).get('hits',0)+1
            self.s.set_state('mstrength:'+mid,{'s':min(1.,s+.5*(1-s)),'last':t,'hits':hits})
    def forgetting_candidates(self,session=None,clock=None,floor=None):
        """Weak, rarely used memories as *proposals*; deletion stays an explicit :forget by the user."""
        floor=self.cfg.get('memory_forget_floor',.05) if floor is None else floor;t=now() if clock is None else clock
        sql="SELECT id,created FROM memories WHERE active=1"+(" AND session_id=?" if session else "");out=[]
        for m in self.s.rows(sql,(session,) if session else ()):
            s=self.strength(m['id'],t)
            if s is None:s=0.5**(((t-m['created'])/86400)/self.cfg.get('memory_half_life_days',30))*.5  # never recalled: half strength at creation
            if s<floor:out.append({'memory_id':m['id'],'strength':round(s,4),'proposal':':forget '+m['id']})
        return out

def staging_events(store):
    """Event ids inside closed episodes whose admission tier is SEMANTIC_STAGING_CANDIDATE (§9.5 -> consolidation priority)."""
    out=set()
    for r in store.rows("SELECT payload FROM states WHERE key LIKE 'episode:%'"):
        ep=json.loads(r['payload'])
        if ep and ep.get('tier')=='SEMANTIC_STAGING_CANDIDATE':out.update(ep.get('events') or [])
    return out

def recall_turn(runtime,text,memories,meta):
    """runtime._turn hook after Memory.recall: associative spread (SHADOW unless `:episodes spread on`)."""
    ep=controller(runtime);merged,found=ep.spread(text,runtime.session,memories,runtime.cfg.get('memory_top_k',3))
    if found:meta['associative_shadow' if ep.spread_mode()!='on' else 'associative']=found
    added=[m['id'] for m in merged if m.get('retrieval_channel')=='associative']
    if added:meta['associative_memory_ids']=added
    return merged

def controller(runtime):
    e=getattr(runtime,'episodes',None)
    if e is None:e=runtime.episodes=Episodes(runtime.store,runtime.cfg,runtime.memory)
    return e

def observe_turn(runtime,e,meta,status):
    """runtime._turn hook: gather signals from what the turn already produced (no extra model call)."""
    eid=e['event_id'];text=runtime.store.read_source(e['source_ref'])
    task=None
    row=runtime.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='JEFBroadcastPacket' ORDER BY created DESC LIMIT 1",(eid,))
    if row:task=json.loads(row['payload']).get('active_task')
    err=None
    row=runtime.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='PredictionOutcome' ORDER BY created DESC LIMIT 1",(eid,))
    if row:
        ob=json.loads(row['payload'])['observation']
        if ob.get('digital_latent_error') is not None:err=clamp(ob['digital_latent_error'])
        elif ob.get('timing_error_s') is not None:err=clamp(abs(ob['timing_error_s'])/max(ob['observed'].get('action_duration_s') or 1e-3,1e-3))
    ep=controller(runtime)
    for act in runtime.store.rows("SELECT id,status FROM actions WHERE event_id=? AND outcome IS NOT NULL",(eid,)):ep.on_outcome(eid,act['id'],act['status'])
    vector=None;keys=getattr(runtime.memory,'semantic_keys',None)
    if keys is not None and keys.last_query and keys.last_query['digest']==digest(text):vector=keys.last_query['vector']
    return ep.observe(eid,e.get('session_id') or runtime.session,text,route=meta.get('route'),status=status,task=task,
                                       prediction_error=err,vector=vector,memory_ids=list(meta.get('memory_ids') or []),associative_ids=list(meta.get('associative_memory_ids') or []))

def operator_command(r,args):
    ep=controller(r)
    if not args or args==['status']:
        cur=ep.current(r.session)
        return {'open':{k:cur[k] for k in ('id','started','events','boundary','memory_ids','corrections')} if cur else None,'closed':len(ep.episodes(r.session,10**6)),
                'edges':{lvl:len(ep.edges(evidence=lvl)) for lvl in ('TEMPORAL','CORRELATIONAL','CAUSAL','HYPOTHESIS')},'revision':REVISION}
    if args==['list']:return [{k:x.get(k) for k in ('id','started','ended','events','tier','admission','closed_by')} for x in ep.episodes(r.session)]
    if args==['cut']:return ep.close(r.session)
    if args[0]=='graph' and len(args)==2:return ep.edges(args[1])
    if args[0]=='relation' and len(args)==3:return ep.relation(args[1],args[2])
    if args==['forgetting']:return ep.forgetting_candidates(r.session)
    if args[0]=='spread' and len(args)<=2:return {'spread':ep.set_spread_mode(args[1]) if len(args)==2 else ep.spread_mode()}
    if args[0]=='route' and len(args)<=2:  # WP-U10 fast episodic route reuse
        from .episodic_route import mode,set_mode
        return {'episodic_route':set_mode(r.store,args[1]) if len(args)==2 else mode(r.store)}
    raise ValueError(':episodes [status|list|cut|graph <id>|relation <a> <b>|forgetting|spread [off|shadow|on]|route [off|shadow|active]]')
