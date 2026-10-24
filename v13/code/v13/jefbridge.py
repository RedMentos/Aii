"""WP-N3 / §3.4.2-3.4.7, L4.3, L4.4, G3C, §24.25-24.26: JEF <-> brain learning.

JEF_BROADCAST_CACHE (§3.4.2)  small, versioned export of the executive state for A/B: goal/executive latents, focal slot
                              refs, constraints, recent action intent, corollary ref, uncertainty, body state, source
                              pointers. There is no native JEF KV in the GGUF runners, so the latents are *hashed
                              symbolic* feature vectors (marked as such), never presented as native latents.
Bridges JEF2B (§3.4.2)        per body a learned field gate: which JBC fields help that body's offers. SHADOW sends only
                              what B already got (state_version, goal, constraints, source_refs). ACTIVE adds learned
                              fields; extra fields are explored by deterministic per-event sampling so their effect can
                              be estimated as utility(with) - utility(without) (§24.26: a bad bridge cannot silently hurt).
Offer utility (§3.4.4, L4.4)  online logistic model: which offers help the answer. Labels: answer coverage of the offer
                              (internal cross-check, low weight) and human ratings (`:note`, implicit praise/criticism).
                              SHADOW logs the learned JEF decision (§3.4.6 IGNORE/INCORPORATE_*/QUERY_*) next to the
                              scaffold; ACTIVE blends the prediction into the focal `utility` term (max ±LEARNED_MAX).
Top-down query (§3.4.7, L4.3) per (trigger, target) value of targeted re-entries (did the queried body's offer end in the
                              coalition / help the answer); recommends desired_scale fine|gist|mixed, logged as a
                              structured QUERY_PACKET proposal.
Observer-pass utility (§24.25) per observer mode (none / A / B / AB): useful-offer rate, unnecessary offers, conflict
                              detection, latency. Informs an adaptive-frequency recommendation (SHADOW only).
All learning runs in SHADOW at Age 0; `:jef active` (explicit human) lets it act. Paths for WP-N10:
jef_offer_utility, jef_topdown_query, jef_broadcast_bridge (kind control). Numbers are BOOT.
"""
import hashlib
import json
import math
import re
from .common import dumps
from .contracts import packet
from .neuromod import step

KEY='N3_JEF_BRIDGE';REVISION='n3-jef-bridge-v1'
PATHS={'offer':'jef_offer_utility','query':'jef_topdown_query','bridge':'jef_broadcast_bridge'}
DIM=32                       # BOOT hashed latent width
BASE_FIELDS=('state_version','goal','constraints','source_refs')   # what cognition.offer sends today
EXTRA_FIELDS=('focal_slot_refs','recent_action_intent','corollary','uncertainty_summary','body_state','active_task','open_questions')
FEATURES=('bias','b1','b2','confidence','uncertain','needs_reentry','evidence','goal_overlap','in_coalition','supported','contested','reentry')
LR={'internal_crosscheck':.05,'human':.3}   # BOOT learning rates per label source
L2=1e-3;LEARNED_MAX=.25;MIN_UPDATES=5;EXPLORE=.5;FIELD_MIN_N=4;FIELD_GAIN=.05
OBS_MIN_N=8;OBS_FLOOR=.5     # BOOT: observer stats needed before the frequency advice; lowest observer-time scale it may set
OBS_MODE={'detail':'A','gist':'B','both':'AB'}
TURNS_KEEP=64
WORD=re.compile(r'[a-zA-ZäöüÄÖÜß0-9_]{3,}')
STOP=frozenset('the and for that this with from what how why which who you your are was were have has not but'.split())

def terms(t):return {w.lower() for w in WORD.findall(t or '')}-STOP
def coverage(part,whole):
    a=terms(part)
    return len(a&terms(whole))/len(a) if a else 0.
def sigmoid(x):return 1/(1+math.exp(-max(-30.,min(30.,x))))
def clip(x,lo=0.,hi=1.):return min(hi,max(lo,float(x)))
def sampled(event_id,key,rate):
    h=int(hashlib.sha256((str(event_id)+'|'+key).encode()).hexdigest()[:8],16)/0xffffffff
    return h<rate

def hashed_latent(text,dim=DIM):
    """Signed feature hashing of terms, L2-normalized. A symbolic stand-in, not a native model latent."""
    v=[0.]*dim
    for w in terms(text):
        h=int(hashlib.sha256(w.encode()).hexdigest()[:8],16);v[h%dim]+=1. if (h>>16)&1 else -1.
    n=math.sqrt(sum(x*x for x in v)) or 1.
    return [round(x/n,4) for x in v]

def empty():
    return {'revision':REVISION,'mode':'SHADOW','w':[0.]*len(FEATURES),'updates':0,'query':{},'fields':{},'observer':{},
            'turns':[],'scaffold_agree':{'n':0,'agree':0}}

def features(offer,goal,coalition_ids=(),verdicts=None,reentry=False):
    o=offer['offer'];verdicts=verdicts or {}
    return [1.,float(offer['role']=='B1_DETAIL'),float(offer['role']=='B2_GIST'),clip(offer.get('confidence',0.)),
            float(bool(o.get('uncertainty'))),float(bool(o.get('needs_reentry'))),clip(len(offer.get('evidence_refs',[]))/3),
            clip(coverage(goal,o.get('summary',''))*2),float(offer['packet_id'] in coalition_ids),
            float(verdicts.get(offer['packet_id'])=='SUPPORTED'),float(verdicts.get(offer['packet_id']) in ('CONTESTED','UNSUPPORTED','SOURCE_LOSS')),
            float(bool(reentry))]

class JEFBridge:
    def __init__(self,store,cfg,neuromod=None):
        self.s=store;self.cfg=cfg;self.n=neuromod
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st=empty()
        if st.get('revision')!=REVISION:raise ValueError('JEF bridge state revision mismatch')
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
    def _touch(self,key,event_id,activity=1.):
        if self.n is None:return
        try:self.n.touch(PATHS[key],event_id,activity=activity)
        except Exception:pass
    def _signal(self,key,event_id,source_class,**ch):
        if self.n is None:return
        try:self.n.signal(event_id,path=PATHS[key],source_class=source_class,**ch)
        except Exception:pass
    # -- broadcast cache + bridges (§3.4.2) -------------------------------------------------------------
    def broadcast_cache(self,e,broadcast,exec_state=None,workspace=(),corollary=None,body=None,uncertainty=None):
        exec_state=exec_state or {}
        jbc={'state_version':broadcast['state_version'],'goal':broadcast['goal'][:400],'constraints':broadcast['constraints'][:8],
             'source_refs':broadcast['source_refs'][:8],'goal_latent':hashed_latent(broadcast['goal']),
             'executive_latent':hashed_latent(dumps([broadcast['constraints'],exec_state.get('active_task')])),
             'focal_slot_refs':list(workspace)[:8],'recent_action_intent':(exec_state.get('current_action_intent') or {}).get('type'),
             'corollary':corollary,'uncertainty_summary':uncertainty,'body_state':body,
             'active_task':bool(exec_state.get('active_task')),'open_questions':len(exec_state.get('open_questions') or []),
             'latent_kind':'HASHED_SYMBOLIC_NOT_NATIVE'}
        p=self.s.add_packet('JEFBroadcastCache',packet('JEFBroadcastCache','C1_EXEC',e['event_id'],e['brain_generation_id'],broadcast['source_refs'][:8],
            state_version=broadcast['state_version'],cache=jbc,broadcast_packet_id=broadcast['packet_id'],size_bytes=len(dumps(jbc))))
        return p
    def bridge_view(self,role,e,version):
        """ACTIVE extra fields require intact event, generation, source and parent broadcast lineage.

        SHADOW stays inert. A stale/corrupt packet is never silently used as a
        substitute for an independently source-bound executive broadcast.
        """
        st,_=self._load()
        if st['mode']!='ACTIVE' or role not in ('B1_DETAIL','B2_GIST'):return {},[]
        row=self.s.one("SELECT payload FROM packets WHERE kind='JEFBroadcastCache' AND event_id=? ORDER BY created DESC LIMIT 1",(e['event_id'],))
        if not row:return {},[]
        try:
            jbc=json.loads(row['payload'])
            cache=jbc['cache']
            if (jbc['event_id']!=e['event_id'] or
                jbc['brain_generation_id']!=e['brain_generation_id'] or
                jbc['state_version']!=version or cache['state_version']!=version or
                jbc['size_bytes']!=len(dumps(cache))):
                return {},[]
            parent_row=self.s.one("SELECT payload FROM packets WHERE kind='JEFBroadcastPacket' AND id=? AND event_id=?",
                                  (jbc['broadcast_packet_id'],e['event_id']))
            if not parent_row:return {},[]
            parent=json.loads(parent_row['payload'])
            refs=parent['source_refs']
            if (parent['packet_id']!=jbc['broadcast_packet_id'] or
                parent['event_id']!=e['event_id'] or
                parent['brain_generation_id']!=e['brain_generation_id'] or
                parent['state_version']!=version or
                not isinstance(refs,list) or not refs or
                refs!=parent['provenance'] or refs!=jbc['provenance'] or
                refs!=cache['source_refs'] or
                cache['goal']!=parent['goal'][:400] or
                cache['constraints']!=parent['constraints'][:8]):
                return {},[]
            for ref in refs:self.s.read_source(ref)  # deletion, digest and span bounds
            out={};chosen=[]
            for f in EXTRA_FIELDS:
                q=st['fields'].get(role+'|'+f)
                learned_on=bool(q and q['with'][1]>=FIELD_MIN_N and q['without'][1]>=FIELD_MIN_N and q['with'][0]/q['with'][1]-q['without'][0]/q['without'][1]>=FIELD_GAIN)
                if learned_on or sampled(e['event_id'],role+'|'+f,EXPLORE):
                    out[f]=cache[f];chosen.append(f)
            return out,chosen
        except (ValueError,TypeError,KeyError,AttributeError,OSError,UnicodeError):
            return {},[]
    # -- offer utility (§3.4.4, L4.4) -------------------------------------------------------------------
    def predict(self,x,st=None):
        st=st or self._load()[0];return sigmoid(sum(a*b for a,b in zip(st['w'],x)))
    def offer_utility(self,offer,base,goal=''):
        """Focal `utility` term hook: unchanged in SHADOW; ACTIVE shifts it by the learned usefulness (bounded)."""
        try:
            st,_=self._load()
            if st['mode']!='ACTIVE' or st['updates']<MIN_UPDATES:return base
            p=self.predict(features(offer,goal),st);return clip(base+LEARNED_MAX*(p-.5)*2)
        except Exception:return base
    def _sgd(self,st,x,y,lr):
        p=self.predict(x,st);g=p-y
        st['w']=[w-lr*(g*xi+L2*w) for w,xi in zip(st['w'],x)];st['updates']+=1
    # -- per turn -------------------------------------------------------------------------------------
    def learn_turn(self,e,goal,offers,output,focal_run=None,pre_offer_ids=(),observer_s=None,queries=None):
        """After the answer: label offers by answer coverage, score re-entries, observer stats, shadow decision."""
        eid=e['event_id'];focal_run=focal_run or {}
        if queries is None:
            queries={}
            for r in self.s.rows("SELECT payload FROM packets WHERE kind='QueryPacket' AND event_id=?",(eid,)):
                q=json.loads(r['payload'])
                if 'jbc_fields' in q:queries.setdefault(q['target_role'],q['jbc_fields'])
            queries={k:v for k,v in queries.items() if v is not None}
        coalition={x['item_id'] for x in focal_run.get('coalition',[])}
        verdicts={s.get('target_item_id'):s.get('verdict') for s in focal_run.get('inquisition',[])}
        pre=set(pre_offer_ids);rows=[];useful=0
        for p in offers:
            x=features(p,goal,coalition,verdicts,reentry=p['packet_id'] not in pre)
            u=clip(coverage(p['offer'].get('summary',''),output)*1.5) if output else 0.
            rows.append({'id':p['packet_id'],'role':p['role'],'x':x,'u':round(u,4),'selected':p['packet_id'] in coalition,'reentry':p['packet_id'] not in pre})
            useful+=u>=.3
        roles={r['role'] for r in rows if not r['reentry']};mode={frozenset():'none',frozenset({'B1_DETAIL'}):'A',frozenset({'B2_GIST'}):'B'}.get(frozenset(roles),'AB')
        view=(focal_run.get('trajectory') or [{}])[-1].get('view') or {}
        trig='conflict' if view.get('conflict',0)>=.4 else 'uncertain' if view.get('uncertainty',0)>=.45 else 'calm'
        scaffold=focal_run.get('decision')
        sc=step(self.n,PATHS['offer'])  # WP-U6 §12.7
        def fn(st):
            for r in rows:self._sgd(st,r['x'],r['u'],sc*LR['internal_crosscheck'])
            preds={r['id']:self.predict(r['x'],st) for r in rows}
            inc=[r for r in rows if preds[r['id']]>=.5 and not r['reentry']]
            hi_unc=any(r['x'][4] or r['x'][5] for r in rows)
            if not inc:learned='QUERY_'+('A' if any(r['role']=='B1_DETAIL' for r in rows) else 'B') if hi_unc and rows else 'IGNORE'
            else:
                rs={r['role'] for r in inc};learned={'B1_DETAIL':'INCORPORATE_A','B2_GIST':'INCORPORATE_B'}.get(next(iter(rs)) if len(rs)==1 else '','INCORPORATE_AB')
            if scaffold:
                st['scaffold_agree']['n']+=1;st['scaffold_agree']['agree']+=int(scaffold==learned)
            for r in rows:
                if r['reentry']:
                    q=st['query'].setdefault(trig+'|'+r['role'],{'n':0,'value':0.})
                    q['n']+=1;q['value']+=(max(r['u'],1. if r['selected'] else 0.)-q['value'])/q['n']
            o=st['observer'].setdefault(mode,{'n':0,'useful':0,'unnecessary':0,'conflicts':0,'latency_s':0.})
            o['n']+=1;o['useful']+=useful;o['unnecessary']+=sum(1 for r in rows if r['u']<.1 and not r['selected']);o['conflicts']+=int(trig=='conflict')
            o['latency_s']+=float(observer_s or 0.)
            for role,fields in (queries or {}).items() if st['mode']=='ACTIVE' else []:  # field effects only measurable while exploring
                ur=[r['u'] for r in rows if r['role']==role]
                if not ur:continue
                for f in EXTRA_FIELDS:
                    q=st['fields'].setdefault(role+'|'+f,{'with':[0.,0],'without':[0.,0]});k='with' if f in fields else 'without'
                    q[k][0]+=max(ur);q[k][1]+=1
            st['turns']=(st['turns']+[{'event_id':eid,'rows':[{k:r[k] for k in ('id','role','x','selected')} for r in rows],'queries':queries or {},'trigger':trig}])[-TURNS_KEEP:]
            return learned,preds
        learned,preds=self._mutate(fn)
        rec=self.recommend_query(view)
        p=self.s.add_packet('JEFBridgeTurn',packet('JEFBridgeTurn','C1_EXEC',eid,e['brain_generation_id'],[e['source_ref']],
            scaffold_decision=scaffold or 'NONE',learned_decision=learned,observer_mode=mode,
            offers=[{'id':r['id'],'role':r['role'],'label':r['u'],'predicted':round(preds[r['id']],4),'selected':r['selected'],'reentry':r['reentry']} for r in rows],
            query_proposal=rec,mode=self._load()[0]['mode']))
        if rows:self._touch('offer',eid);self._signal('offer',eid,'internal_crosscheck',task_success=clip(useful/len(rows)))
        if any(r['reentry'] for r in rows):self._touch('query',eid)
        if queries:self._touch('bridge',eid)
        return p
    def recommend_query(self,view):
        """Structured QUERY_PACKET proposal (§3.4.7): best target by learned value for the current trigger."""
        st,_=self._load();view=view or {}
        trig='conflict' if view.get('conflict',0)>=.4 else 'uncertain' if view.get('uncertainty',0)>=.45 else 'calm'
        opts={r:st['query'].get(trig+'|'+r,{'n':0,'value':.5}) for r in ('B1_DETAIL','B2_GIST')}
        best=max(opts,key=lambda r:opts[r]['value']);known=all(o['n']>=3 for o in opts.values())
        both=known and abs(opts['B1_DETAIL']['value']-opts['B2_GIST']['value'])<.1 and trig=='conflict'
        return {'trigger':trig,'target':'BOTH' if both else best,'desired_scale':'mixed' if both else ('fine' if best=='B1_DETAIL' else 'gist'),
                'expected_value':round(opts[best]['value'],4),'evidence_need':round(clip(view.get('uncertainty',0.)),4),
                'conflict_to_resolve':trig=='conflict','learned':known,'compute_budget':int(self.cfg.get('observer_tokens',64))}
    def query_target(self,view,heuristic):
        """Focal loop hook (§3.4.7): which body a re-entry that the scaffold already wants should go to. The learned
        recommendation is always returned for the FocalCycle log; it replaces the BOOT target only in ACTIVE, once
        every option has evidence, and never creates a re-entry the scaffold did not ask for (BOTH keeps the scaffold)."""
        rec=self.recommend_query(view);mode=self._load()[0]['mode']
        learned=rec['target'] if rec['target'] in ('B1_DETAIL','B2_GIST') else heuristic
        applied=mode=='ACTIVE' and rec['learned'] and learned!=heuristic
        return (learned if applied else heuristic),{'heuristic':heuristic,'learned_target':learned,'applied':applied,'trigger':rec['trigger'],
                                                    'expected_value':rec['expected_value'],'learned':rec['learned'],'mode':mode}
    def observer_scale(self,wake):
        """Adaptive observer frequency (§24.25 -> WP-D): share of useful offers per observer mode scales the observer
        time down to OBS_FLOOR when observers mostly add unnecessary offers. Only lowers the effort plan's budget;
        applied only in ACTIVE."""
        st,_=self._load();key=OBS_MODE.get(wake);o=st['observer'].get(key) if key else None
        if not o or o['n']<OBS_MIN_N:return {'mode':key,'scale':1.,'applied':False,'reason':'TOO_FEW','n':o['n'] if o else 0}
        ratio=o['useful']/max(1,o['useful']+o['unnecessary']);scale=round(OBS_FLOOR+(1-OBS_FLOOR)*ratio,4)
        return {'mode':key,'scale':scale,'applied':st['mode']=='ACTIVE','useful_ratio':round(ratio,4),'n':o['n']}
    # -- human labels ---------------------------------------------------------------------------------
    def outcome(self,event_id,utility,source='human'):
        """Human rating of an answer: selected offers get the label, re-entry values and bridge fields too."""
        u=clip(utility);sc=step(self.n,PATHS['offer'])
        def fn(st):
            t=next((x for x in st['turns'] if x['event_id']==event_id),None)
            if not t:return 0
            n=0
            for r in t['rows']:
                if r['selected']:self._sgd(st,r['x'],u,sc*LR[source]);n+=1
            return n
        n=self._mutate(fn)
        if n:self._signal('offer',event_id,'human_correction',task_success=u)
        return {'updated_offers':n}
    def report(self):
        st,_=self._load();a=st['scaffold_agree']
        obs={m:{'n':o['n'],'useful_per_turn':round(o['useful']/o['n'],3),'unnecessary_per_turn':round(o['unnecessary']/o['n'],3),
                'conflict_rate':round(o['conflicts']/o['n'],3),'observer_latency_s':round(o['latency_s']/o['n'],3)} for m,o in st['observer'].items()}
        return {'revision':REVISION,'mode':st['mode'],'updates':st['updates'],'weights':dict(zip(FEATURES,[round(w,4) for w in st['w']])),
                'scaffold_agreement':round(a['agree']/a['n'],3) if a['n'] else None,'query_values':st['query'],'observer_utility':obs,
                'bridge_fields':{k:{'with':round(q['with'][0]/q['with'][1],3) if q['with'][1] else None,'without':round(q['without'][0]/q['without'][1],3) if q['without'][1] else None,'n':[q['with'][1],q['without'][1]]} for k,q in st['fields'].items()},
                'claim_limit':'Hashed symbolic latents; learned priors only rank/shape, never grant fact authority'}

def controller(runtime):
    j=getattr(runtime,'jefbridge',None)
    if j is None:
        n=None
        try:
            from .neuromod import controller as neuromod_controller
            n=neuromod_controller(runtime)
        except Exception:n=None
        j=runtime.jefbridge=JEFBridge(runtime.store,runtime.cfg,n)
    return j

def on_rating(runtime_or_store,event_id,score):
    """inputs.record_rating hook: 1..10 rating -> utility label."""
    store=getattr(runtime_or_store,'store',runtime_or_store)
    return JEFBridge(store,{}).outcome(event_id,(score-1)/9)

USAGE=':jef [status|last|shadow|active|query|outcome <Event> <0..1>]'
def operator_command(r,args):
    j=controller(r)
    if not args or args==['status']:return dumps(j.report())
    if args==['last']:
        row=r.store.one("SELECT payload FROM packets WHERE kind='JEFBridgeTurn' ORDER BY created DESC LIMIT 1")
        return row['payload'] if row else dumps(None)
    if args==['shadow']:return dumps({'mode':j.set_mode('SHADOW')})
    if args==['active']:return dumps({'mode':j.set_mode('ACTIVE','EXPLICIT_HUMAN')})
    if args==['query']:return dumps(j.recommend_query({}))
    if len(args)==3 and args[0]=='outcome':return dumps(j.outcome(args[1],float(args[2])))
    raise ValueError(USAGE)
