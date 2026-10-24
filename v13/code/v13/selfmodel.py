"""WP-N9 / §7.3-7.5, §20.2, §20.4, §85.7, §24.28: self model, digital interoception, corollary copy, self-messaging, self-edit.

Self model (§7.3)      one structured view over what already exists: bodies, skills, tools, permissions, body capabilities,
                       memory health, calibration, learning status, Age per capability, resource state, teacher
                       dependencies, open goals, limits. Read-only aggregation; every part fails soft to UNAVAILABLE.
Interoception (§7.4)   RAM, heat, battery, storage, latency strain, error load -> bounded body signals [0,1] and the
                       modulations they may suggest (compute, dream, learning, context budget, wake/sleep pressure).
                       Self-generated load is attenuated in the *salience* channel (corollary-based sensory attenuation,
                       §85.7); safety (ResourceGuard) always reads the raw values.
Corollary (§7.5, §85.7) every own action gets a COROLLARY_PACKET before dispatch (intended effect, predicted observations,
                       uncertainty, causal hypothesis, expected cost, permission snapshot). Observations are attributed
                       SELF / EXTERNAL / MIXED / UNCLEAR; actual - predicted self component = residual, which becomes a
                       world-prediction-error modulator on WP-N10 (G-SELF-WORLD-005 cases are unit tests).
                       A compact corollary view goes back to B1/B2 before the next turn ("before the world answers").
Self-messaging (§20.4) relevance gate + rate limit + anti-spam; unsolicited delivery needs the Age right self_initiative
                       (Age 4). Below that, messages are HELD and visible via `:self messages`.
Self-edit (§20.2)      proposals only; a human approves (`:self edit approve`). Context policy applies via WP-N7,
                       safe config is handed to the AG8 sandbox (`agi/self_improve.py`); other targets are recorded for
                       their owners. Without-dialog commits need Age right safe_self_edit_without_dialog (Age 3) and are
                       limited to reversible context-policy edits. Hard rules are never editable.
All numbers are BOOT values, not measured optima.
"""
import json
import math
import time
from .common import dumps,digest,now
from .contracts import packet

KEY='N9_SELF';REVISION='n9-self-v1'
CLASSES=('SELF','EXTERNAL','MIXED','UNCLEAR')
FAR_K=20.   # BOOT (corollary candidate 2 calibration): a residual beyond FAR_K x tolerance of the nearest own prediction is UNCLEAR
ATTENUATION=.6        # BOOT: share of self-caused interoceptive change removed from salience (never from safety)
DELAY_FACTOR=3.       # BOOT: an outcome up to 3x the predicted window still counts as delayed self outcome
DEFAULT_WINDOW_S=120. # BOOT
OPEN_MAX=32
MSG_KINDS=('finding','open_goal','error','memory')
MSG_RELEVANCE=.6;MSG_PER_HOUR=3;MSG_GAP_S=600;MSG_DEDUP_S=86400;MSG_KEEP=64  # BOOT §20.4 gate
EDIT_TARGETS=('memory','world_notebook','context_policy','replay_priority','routing_candidate','skill_metadata','translator_gate','safe_config')
EDIT_AUTO={'context_policy'}  # reversible, bounded by WP-N7 knob guards
NEVER_EDIT={'hard_rules','age_caps','learning_mode','latents','channel'}

def clamp(x,lo=0.,hi=1.):
    x=float(x)
    if not math.isfinite(x):raise ValueError('Wert nicht endlich')
    return min(hi,max(lo,x))

def empty():return {'revision':REVISION,'open':{},'messages':[],'edits':{},'seq':0,'attribution_counts':{c:0 for c in CLASSES}}

# -- interoception (§7.4) ---------------------------------------------------------------------------------
def interoception(snapshot,cfg,recent=(),own_active=False):
    """Body signals in [0,1] from a resources.snapshot(); `recent` = recent action rows (status, duration)."""
    s=snapshot or {};sig={};floor=cfg['minimum_free_mb']*1024*1024
    avail,total=s.get('mem_available_bytes'),s.get('mem_total_bytes')
    sig['ram_pressure']=clamp(1-(avail-floor)/max(1,4*floor)) if avail is not None else None   # 0 at >=5x floor, 1 at floor
    t=s.get('battery_temperature_c');lim=cfg['thermal_limit_c']
    sig['heat']=clamp((t-(lim-15))/15) if t is not None else None
    b=s.get('battery_percent');sig['energy_low']=None if b is None else (0. if s.get('charging') else clamp((40-b)/30))
    disk=s.get('free_disk_bytes');sig['storage_pressure']=None if disk is None else clamp(1-disk/(2*1024**3))
    durs=[x['duration_s'] for x in recent if isinstance(x.get('duration_s'),(int,float))]
    sig['latency_strain']=clamp(sorted(durs)[len(durs)//2]/max(1.,cfg['deadline_seconds'])) if durs else None
    sig['error_load']=clamp(sum(x.get('status') not in ('FINAL',None) for x in recent)/len(recent)) if recent else None
    own=sum(p.get('rss_bytes') or 0 for p in (s.get('processes') or []))
    self_share=clamp(own/max(1,total-avail)) if own_active and avail is not None and total else 0.
    known=[v for v in sig.values() if v is not None];strain=max(known) if known else 0.
    salience=dict(sig)
    if sig['ram_pressure'] is not None:salience['ram_pressure']=sig['ram_pressure']*(1-ATTENUATION*self_share)  # §85.7 attenuation
    mod={'compute_scale':round(1-.5*strain,4),'context_budget_scale':round(1-.4*max(sig['ram_pressure'] or 0,sig['heat'] or 0),4),
         'dream_allowed':strain<.5,'learning_allowed':strain<.7 and not (sig['energy_low'] or 0)>.5,
         'sleep_pressure':round(max(sig['heat'] or 0,sig['energy_low'] or 0,sig['error_load'] or 0),4)}
    feeling='strained' if strain>=.7 else 'loaded' if strain>=.4 else 'calm'
    return {'signals':{k:None if v is None else round(v,4) for k,v in sig.items()},'salience':{k:None if v is None else round(v,4) for k,v in salience.items()},
            'self_caused_share':round(self_share,4),'strain':round(strain,4),'feeling':feeling,'modulation':mod,
            'loaded_processes':len(s.get('processes') or []),'safety_reads_raw':True}

# -- attribution (§85.7) ------------------------------------------------------------------------------------
def _match(pred,value):
    """(matched, residual) for one predicted observation."""
    pv=pred.get('value')
    if isinstance(pv,(int,float)) and not isinstance(pv,bool) and isinstance(value,(int,float)):
        res=value-pv;tol=pred.get('tolerance');tol=abs(pv)*.5 if tol is None else tol
        return abs(res)<=tol,res
    if pv=='*':return True,None
    return value==pv,None if value==pv else {'expected':pv,'actual':value}

def attribute(open_corollaries,obs):
    """Classify one observation {'channel','value','t'} against open corollaries. Pure function (tested directly)."""
    t=obs.get('t',now());ch=obs['channel'];cands=[]
    for c in open_corollaries:
        start=c['issued_at'];w=c.get('window_s',DEFAULT_WINDOW_S)
        if t<start:continue
        for pred in c['predicted_observations']:
            if pred['channel']!=ch:continue
            pw=pred.get('window_s',w);delayed=t>start+pw
            if t>start+pw*DELAY_FACTOR:continue
            ok,res=_match(pred,obs['value']);tol=pred.get('tolerance');pv=pred.get('value')
            tol=(abs(pv)*.5 if isinstance(pv,(int,float)) and not isinstance(pv,bool) else None) if tol is None else tol
            cands.append({'action_id':c['action_id'],'matched':ok,'residual':res,'delayed':delayed,'tolerance':tol})
    if not cands:
        side=[c['action_id'] for c in open_corollaries if c['issued_at']<=t<=c['issued_at']+c.get('window_s',DEFAULT_WINDOW_S) and ch in c.get('affected',[])]
        if side:return {'class':'UNCLEAR','reason':'unexpected_side_effect','action_ids':side,'residual':None}
        return {'class':'EXTERNAL','reason':'no_own_action_predicts_this','action_ids':[],'residual':None}
    hits=[x for x in cands if x['matched']]
    if len({x['action_id'] for x in hits})>1:return {'class':'UNCLEAR','reason':'ambiguous_causality','action_ids':sorted({x['action_id'] for x in hits}),'residual':None}
    if hits:
        h=hits[0];return {'class':'SELF','reason':'delayed_predicted_outcome' if h['delayed'] else 'predicted_outcome','action_ids':[h['action_id']],'residual':h['residual'],'delayed':h['delayed']}
    num=[x for x in cands if isinstance(x['residual'],(int,float)) and not isinstance(x['residual'],bool)]
    if num:  # thread L 2026-10-12, preregistered corollary candidate 3 PASS (bench-results/corollary-unclear-20261012)
        c=min(num,key=lambda x:abs(x['residual']))  # residual against the nearest own prediction, not the first open action
        if abs(c['residual'])>FAR_K*c['tolerance']:  # far outside every own prediction: neither own error nor proven foreign
            return {'class':'UNCLEAR','reason':'far_outside_own_prediction','action_ids':[],'residual':None,'own_residual':c['residual'],'ceiling_k':FAR_K}
        return {'class':'MIXED','reason':'partial_or_mismatched_outcome','action_ids':[c['action_id']],'residual':c['residual'],'delayed':c['delayed']}
    c=cands[0];return {'class':'MIXED','reason':'partial_or_mismatched_outcome','action_ids':[c['action_id']],'residual':c['residual'],'delayed':c['delayed']}

class SelfSystem:
    def __init__(self,runtime,age=None,neuromod=None,clock=time.time):
        self.r=runtime;self.s=runtime.store;self.age=age;self.n=neuromod;self.clock=clock
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st=empty()
        if st.get('revision')!=REVISION:raise ValueError('Self state revision mismatch')
        return st,v
    def _mutate(self,fn):
        for attempt in (0,1):
            st,v=self._load();out=fn(st);dumps(st)
            try:self.s.set_state(KEY,st,expected=v);return out
            except ValueError:
                if attempt:raise
    def _allowed(self,right):
        if self.age is None:
            from .age import RIGHTS
            return RIGHTS.get(right,99)==0
        try:return self.age.allowed(right)
        except Exception:return False
    # -- interoception ----------------------------------------------------------------------------------
    def body(self,snapshot=None,own_active=None):
        rows=self.s.rows("SELECT status,outcome FROM actions ORDER BY created DESC LIMIT 16")
        recent=[{'status':r['status'],'duration_s':json.loads(r['outcome'] or '{}').get('action_duration_s')} for r in rows]
        snap=snapshot if snapshot is not None else self.r.resources()
        active=bool(getattr(self.r,'turn_event',None)) if own_active is None else own_active
        return interoception(snap,self.r.cfg,recent,active)
    # -- corollary --------------------------------------------------------------------------------------
    def issue(self,event_id,action_id,intended_effect,predicted_observations,affected=(),uncertainty=.5,causal_hypothesis='',expected_cost=None,window_s=DEFAULT_WINDOW_S,refs=None):
        for p in predicted_observations:
            if not isinstance(p,dict) or not isinstance(p.get('channel'),str):raise ValueError('predicted_observations: [{channel,value[,tolerance,window_s]}]')
        perms={'external_tools':False,'system_stage':int(self.r.cfg.get('system_stage',0)),'permission':'local_text_only'}
        issued=self.clock()
        p=self.s.add_packet('SelfCorollary',packet('SelfCorollary','F3_SELF',event_id,self.s.generation_id,refs or [],action_id=action_id,issued_at=issued,
            intended_effect=intended_effect,predicted_observations=list(predicted_observations),affected=list(affected),uncertainty=clamp(uncertainty),
            causal_hypothesis=causal_hypothesis or 'own action causes the predicted observations',expected_cost=expected_cost or {},permission_snapshot=perms))
        c={'action_id':action_id,'event_id':event_id,'packet_id':p['packet_id'],'issued_at':issued,'window_s':float(window_s),
           'predicted_observations':list(predicted_observations),'affected':list(affected),'intended_effect':intended_effect}
        def fn(st):
            st['open'][action_id]=c
            if len(st['open'])>OPEN_MAX:
                for k in sorted(st['open'],key=lambda a:st['open'][a]['issued_at'])[:len(st['open'])-OPEN_MAX]:del st['open'][k]
        self._mutate(fn);return p
    def observe(self,event_id,observations,close=None,path='world_predictor'):
        """Attribute observations; residuals of own predictions become world-prediction-error modulators (§24.28)."""
        st,_=self._load();opened=list(st['open'].values());out=[]
        for obs in observations:
            a=attribute(opened,obs)|{'channel':obs['channel']}
            p=self.s.add_packet('SelfWorldAttribution',packet('SelfWorldAttribution','F3_SELF',event_id,self.s.generation_id,[],
                channel=obs['channel'],attribution=a['class'],reason=a['reason'],action_ids=a['action_ids'],residual=a.get('residual'),delayed=bool(a.get('delayed'))))
            a['packet_id']=p['packet_id'];out.append(a)
            err=None
            if a['class']=='MIXED':
                r=a.get('residual');err=1. if not isinstance(r,(int,float)) else clamp(abs(r)/max(1e-9,abs(r)+1))
            elif a['class']=='SELF':err=0.
            if err is not None and self.n is not None:
                try:self.n.signal(event_id,path=path,source_class='real_deterministic_outcome',world_prediction_error=err,refs=[])
                except Exception:pass
        def fn(st):
            for a in out:st['attribution_counts'][a['class']]+=1
            for aid in (close or []):st['open'].pop(aid,None)
        self._mutate(fn);return out
    def corollary_view(self):
        """Compact self/world view for B1/B2 (no text, no fact authority)."""
        rows=self.s.rows("SELECT payload FROM packets WHERE kind='SelfWorldAttribution' ORDER BY created DESC LIMIT 4")
        if not rows:return None
        recent=[json.loads(r['payload']) for r in rows]
        return {'recent_own_action_outcomes':[{'channel':x['channel'],'attribution':x['attribution'],'reason':x['reason']} for x in recent],
                'authority':'SELF_STATE_NOT_FACT'}
    # -- self model (§7.3) ------------------------------------------------------------------------------
    def model(self):
        r=self.r;out={'revision':REVISION,'updated_wall_time':now()}
        def part(name,fn):
            try:out[name]=fn()
            except Exception as exc:out[name]={'status':'UNAVAILABLE','error':type(exc).__name__}
        part('base',lambda:r.world.self_state())
        part('body',lambda:self.body())
        def age_view():
            from .age import controller
            v=controller(r).view();return {'system_stage':v['system_stage'],'capabilities':{k:x['stage'] for k,x in v['capabilities'].items()}}
        part('age',age_view)
        def growth(attr):
            from .agi import hub
            return getattr(hub(r),attr).report()
        part('skills',lambda:growth('skills')['skills'])
        part('tools',lambda:{n:t['enabled'] for n,t in growth('tools')['tools'].items()})
        part('open_goals',lambda:{k:growth('goals')[k] for k in ('open','next')})
        def learning():
            from .neuromod import controller
            rep=controller(r).report();return {k:rep[k] for k in rep if k in ('paths','vetoed','tags')} or {'status':'NO_PATHS'}
        part('learning',learning)
        def capabilities():
            from .context_os import controller
            return {'context':controller(r).report()['capabilities']}
        part('body_capabilities',capabilities)
        part('memory_health',lambda:{'active':self.s.one('SELECT COUNT(*) AS n FROM memories WHERE active=1')['n'],
                                     'dangling_sources':self.s.one('SELECT COUNT(*) AS n FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.active=1 AND s.deleted=1')['n']})
        part('teacher_dependencies',lambda:{'teacher_enabled':bool(r.cfg['teacher_enabled']),'roles_needing_teacher':[]})
        part('limits',lambda:{k:r.cfg[k] for k in ('deadline_seconds','context_tokens','answer_tokens','minimum_free_mb','thermal_limit_c')})
        st,_=self._load()
        out['corollary']={'open_actions':len(st['open']),'attribution_counts':st['attribution_counts']}
        out['self_messages_held']=sum(m['status']=='HELD' for m in st['messages'])
        out['self_edits_pending']=sum(e['status']=='PENDING' for e in st['edits'].values())
        self.s.set_state('SELF_MODEL_N9:'+r.session,out);return out
    # -- self-messaging (§20.4) -------------------------------------------------------------------------
    def message(self,kind,text,relevance,refs=None,origin='SELF'):
        if kind not in MSG_KINDS:raise ValueError('Self-Message-Art: '+'|'.join(MSG_KINDS))
        rel=clamp(relevance);t=self.clock();h=digest((kind+'|'+text).encode())
        try:
            from .inputs import paused
            hold_pause=paused(self.s,'selfedit')
        except Exception:hold_pause=False
        allowed=origin=='USER' or self._allowed('self_initiative')
        def fn(st):
            msgs=st['messages'];recent=[m for m in msgs if m['status']=='DELIVERED' and t-m['t']<3600]
            if rel<MSG_RELEVANCE:status='BELOW_RELEVANCE'
            elif any(m['hash']==h and t-m['t']<MSG_DEDUP_S and m['status'] in ('DELIVERED','HELD') for m in msgs):status='SUPPRESSED_DUPLICATE'
            elif not allowed or hold_pause:status='HELD'
            elif len(recent)>=MSG_PER_HOUR or (recent and t-max(m['t'] for m in recent)<MSG_GAP_S):status='RATE_LIMITED'
            else:status='DELIVERED'
            m={'id':'smsg_'+h[:12]+'_'+str(len(msgs)),'kind':kind,'text':text[:400],'relevance':rel,'status':status,'t':t,'hash':h,'refs':refs or []}
            st['messages']=(msgs+[m])[-MSG_KEEP:];return m
        m=self._mutate(fn)
        if m['status']=='DELIVERED':
            try:self.r.notice('[V13] '+m['text'])
            except Exception:pass
        return m
    def late_offer(self,event_id,offer,output):
        """WP-F §5.2 / §3.4.3: an observer offer that arrives after commit and disagrees with the committed answer is
        salient. The answer is never rewritten; a gated 'finding' self-message (HELD below Age 4) carries the doubt."""
        import re
        o=offer.get('offer',{});summary=o.get('summary','')
        nums=lambda t:{x.replace(',','.') for x in re.findall(r'\d+(?:[.,]\d+)?',t or '')}
        missing=nums(summary)-nums(output)
        if not (o.get('needs_reentry') or missing):return None
        rel=min(1.,.6+(.2 if o.get('needs_reentry') else 0.)+(.2 if missing else 0.))
        return self.message('finding','A later '+offer.get('role','body')+' check may disagree with my last answer: '+summary[:200],rel,refs=offer.get('evidence_refs',[])[:2])
    # -- self-edit (§20.2) ------------------------------------------------------------------------------
    def propose_edit(self,target,change,reason='',origin='SELF'):
        if target in NEVER_EDIT or target not in EDIT_TARGETS:raise PermissionError('Nicht editierbar: '+str(target))
        if not isinstance(change,dict) or not change:raise ValueError('change muss ein nicht-leeres Objekt sein')
        auto=target in EDIT_AUTO and origin!='USER' and self._allowed('safe_self_edit_without_dialog')
        eid='sedit_'+digest(dumps([target,change,self.clock()]).encode())[:12]
        e={'id':eid,'target':target,'change':change,'reason':reason[:300],'origin':origin,'status':'PENDING','created':self.clock(),'undo':None}
        self._mutate(lambda st:st['edits'].__setitem__(eid,e))
        return self.approve_edit(eid,authority='AGE_SAFE_SELF_EDIT') if auto else e
    def approve_edit(self,eid,authority='EXPLICIT_HUMAN'):
        if authority not in {'EXPLICIT_HUMAN','AGE_SAFE_SELF_EDIT'}:raise PermissionError('Self-Edit braucht Nutzerfreigabe')
        st,_=self._load();e=st['edits'].get(eid)
        if not e or e['status']!='PENDING':raise ValueError('Kein offener Self-Edit: '+str(eid))
        undo=None;status='APPROVED_FOR_OWNER';result=None
        if e['target']=='context_policy':
            from .context_os import controller
            c=controller(self.r);undo={}
            for k,v in e['change'].items():
                if k=='layout':undo['layout']=c.report()['layout'];c.set_layout(v)
                else:undo[k]=c.knobs()[k];c.set_knob(k,v)
            status='APPLIED'
        elif e['target']=='safe_config':
            from .agi import hub
            result=hub(self.r).improve.propose('knob',e['change'],e['reason'],origin='SELF')
            status='HANDED_TO_AG8'
        def fn(st2):st2['edits'][eid].update(status=status,undo=undo,approved_by=authority,result=result);return st2['edits'][eid]
        return self._mutate(fn)
    def reject_edit(self,eid):
        def fn(st):
            if st['edits'].get(eid,{}).get('status')!='PENDING':raise ValueError('Kein offener Self-Edit')
            st['edits'][eid]['status']='REJECTED';return st['edits'][eid]
        return self._mutate(fn)
    def rollback_edit(self,eid):
        st,_=self._load();e=st['edits'].get(eid)
        if not e or e['status']!='APPLIED' or not e['undo']:raise ValueError('Nur angewendete Context-Policy-Edits sind rücknehmbar')
        from .context_os import controller
        c=controller(self.r)
        for k,v in e['undo'].items():
            if k=='layout':c.set_layout(v)
            else:c.set_knob(k,v,restore=True)  # back to the value that was valid before this edit
        def fn(st2):st2['edits'][eid]['status']='ROLLED_BACK';return st2['edits'][eid]
        return self._mutate(fn)
    def report(self):
        st,_=self._load()
        return {'revision':REVISION,'open_corollaries':len(st['open']),'attribution_counts':st['attribution_counts'],
                'messages':st['messages'][-8:],'edits':{k:{x:e[x] for x in ('target','status','change','origin')} for k,e in st['edits'].items()},
                'self_initiative_allowed':self._allowed('self_initiative'),'safe_self_edit_without_dialog':self._allowed('safe_self_edit_without_dialog')}

def controller(runtime):
    s=getattr(runtime,'selfsys',None)
    if s is None:
        age=n=None
        try:
            from .age import controller as age_controller
            age=age_controller(runtime)
        except Exception:age=None
        try:
            from .neuromod import controller as neuromod_controller
            n=neuromod_controller(runtime)
        except Exception:n=None
        s=runtime.selfsys=SelfSystem(runtime,age,n)
    return s

USAGE=':self [status|model|body|messages|edit list|edit approve <Id>|edit reject <Id>|edit rollback <Id>]'
def operator_command(r,args):
    s=controller(r)
    if not args or args==['status']:return dumps(s.report())
    if args==['model']:return dumps(s.model())
    if args==['body']:return dumps(s.body())
    if args==['messages']:return dumps(s._load()[0]['messages'])
    if args==['edit','list']:return dumps(s.report()['edits'])
    if len(args)==3 and args[0]=='edit':
        fn={'approve':s.approve_edit,'reject':s.reject_edit,'rollback':s.rollback_edit}.get(args[1])
        if fn:return dumps(fn(args[2]))
    raise ValueError(USAGE)
