"""WP-N4 rest / §6.4, §11.1-11.2, §85.5, IH-H29: learned C5 action selection + C6 egress schema adapter.

Learned selection (§85.5, basal-ganglia analogy without a naive GO logit):
  per (context, action) two separate learned pathways, never collapsed into one scalar during learning:
    promote  (direct-pathway-like)   fed by task_success, human approval
    suppress (indirect-pathway-like) fed by cost_error, action_prediction_error, rule_violation, human_correction,
                                     world_mismatch
  Each modulator keeps its own running mean per (context, action), so `:c5` shows *why* an action is promoted or held
  back. The score shift is promote - suppress, bounded by LEARNED_MAX. SHADOW (Age 0 default) logs the learned choice
  next to the BOOT route table in the ActionSelection packet; ACTIVE (`:c5 active`, explicit human) applies the shift.
  Permissions and suppression reasons are never overridden by learning.
C6 egress (§11.1-11.2, IH-H29): typed schema check per action type before C7 (TEXT_REPORT, EXACT_RENDER, CLARIFY,
  TOOL_CALL). It reports violations and feeds rule_violation; it never rewrites an answer. TOOL_CALL accepts only a
  registered tool name with a dict of typed arguments, never a shell string (for WP-K).
  WP-T7 adds the remaining egress kinds of the output broker (`broker.py`): SYSTEM_REPORT (source-bound diagnostic),
  SNAPSHOT (operator-forced current state), CORRECTION (late evidence after the commit point, must name the corrected
  message) and ACTION_PREVIEW (proposed, not executed tool call with its approval command).
"""
import json
import re
from .common import dumps
from .contracts import packet
from .neuromod import step

KEY='N4_C5_LEARNING';REVISION='n4-c5-learning-v1'
PROMOTE=('task_success','human_approval')
SUPPRESS=('cost_error','action_prediction_error','rule_violation','human_correction','world_mismatch')
WEIGHT={'task_success':.5,'human_approval':1.,'cost_error':.4,'action_prediction_error':.3,'rule_violation':1.,'human_correction':1.,'world_mismatch':.4}  # BOOT
LEARNED_MAX=.2;MIN_N=3;RATE=.2   # BOOT
MAX_TEXT=20000
CTRL=re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
SHELLISH=re.compile(r'[;&|`$<>]|\b(rm|sudo|curl|wget|chmod|sh|bash)\b')

def clip(x,lo=0.,hi=1.):return min(hi,max(lo,float(x)))
def empty():return {'revision':REVISION,'mode':'SHADOW','q':{},'agree':{'n':0,'same':0}}
def context(route,effort=None):
    band='low' if (effort or 0)<.35 else 'mid' if (effort or 0)<.7 else 'high'
    return (route or 'simple')+'|'+band

class C5Learning:
    def __init__(self,store,neuromod=None):self.s=store;self.n=neuromod
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st=empty()
        if st.get('revision')!=REVISION:raise ValueError('C5 learning state revision mismatch')
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
    @staticmethod
    def pathways(q):
        if not q or q['n']<MIN_N:return 0.,0.
        m=q['mods'];promote=sum(WEIGHT[k]*m.get(k,0.) for k in PROMOTE);suppress=sum(WEIGHT[k]*m.get(k,0.) for k in SUPPRESS)
        return round(promote,4),round(suppress,4)
    def shifts(self,ctx,action_ids):
        st,_=self._load();out={}
        for a in action_ids:
            p,s=self.pathways(st['q'].get(ctx+'|'+a));out[a]=round(max(-LEARNED_MAX,min(LEARNED_MAX,(p-s)*LEARNED_MAX)),4)
        return out,st['mode']
    def note_choice(self,scaffold,learned):
        def fn(st):st['agree']['n']+=1;st['agree']['same']+=int(scaffold==learned)
        self._mutate(fn)
    def learn(self,ctx,action_id,event_id=None,**mods):
        """One outcome of a taken action; each modulator keeps its own running mean (no scalar reward)."""
        bad=[k for k in mods if k not in PROMOTE+SUPPRESS]
        if bad:raise ValueError('Unbekannter C5-Modulator: '+','.join(bad))
        sc=step(self.n,'c5_action_selection')  # WP-U6 §12.7
        def fn(st):
            q=st['q'].setdefault(ctx+'|'+action_id,{'n':0,'mods':{}});q['n']+=1
            for k,v in mods.items():
                if v is None:continue
                old=q['mods'].get(k);q['mods'][k]=round(clip(v) if old is None else old+sc*RATE*(clip(v)-old),4)
            return q
        q=self._mutate(fn)
        if self.n is not None and event_id:
            ch={k:v for k,v in {'task_success':mods.get('task_success'),'cost_error':mods.get('cost_error'),'action_error':mods.get('action_prediction_error'),
                                'rule_violation':mods.get('rule_violation'),'human_correction':mods.get('human_correction')}.items() if v is not None}
            try:
                self.n.touch('c5_action_selection',event_id)
                if ch:self.n.signal(event_id,path='c5_action_selection',source_class='internal_crosscheck',**ch)
            except Exception:pass
        return q
    def report(self):
        st,_=self._load();a=st['agree']
        return {'revision':REVISION,'mode':st['mode'],'agreement_with_boot':round(a['same']/a['n'],3) if a['n'] else None,
                'actions':{k:{'n':q['n'],'promote':self.pathways(q)[0],'suppress':self.pathways(q)[1],'modulators':q['mods']} for k,q in st['q'].items()},
                'claim_limit':'Learning shifts scores within ±0.2; permissions and suppression reasons always win'}

def apply(store,cands,route,effort=None):
    """ActionGate hook: returns (learned_choice, applied). Mutates scores only in ACTIVE."""
    try:
        c=C5Learning(store);ctx=context(route,effort);sh,mode=c.shifts(ctx,[x['action_id'] for x in cands])
        live=[x for x in cands if 'suppressed' not in x]
        if not live:return None,False
        learned=max(live,key=lambda x:(x['score']+sh[x['action_id']],x['action_id']))['action_id']
        boot=max(live,key=lambda x:(x['score'],x['action_id']))['action_id']
        if mode=='ACTIVE':
            for x in cands:x['learned_shift']=sh[x['action_id']];x['score']=round(x['score']+sh[x['action_id']],4)
        c.note_choice(boot,learned);return {'learned':learned,'boot':boot,'shifts':sh,'context':ctx},mode=='ACTIVE'
    except Exception:return None,False

# -- C6 egress schema adapter ---------------------------------------------------------------------------------
def egress(action_type,payload,source_text=None,tools=None):
    """Typed schema check before C7. Returns {'ok', 'violations'}; never rewrites."""
    v=[]
    if action_type in ('TEXT_REPORT','CLARIFY','EXACT_RENDER','SYSTEM_REPORT','SNAPSHOT'):
        if not isinstance(payload,str):v.append('not_text')
        else:
            if not payload.strip():v.append('empty')
            if len(payload)>MAX_TEXT:v.append('too_long')
            if CTRL.search(payload):v.append('control_characters')
            if action_type=='CLARIFY' and not payload.rstrip().endswith('?'):v.append('clarify_without_question')
            if action_type=='EXACT_RENDER' and source_text is not None and payload!=source_text:v.append('exact_render_differs_from_source')
            if action_type=='SNAPSHOT' and not payload.startswith('[CURRENT_OUTPUT_SNAPSHOT') and not payload.startswith('[Systembericht'):v.append('snapshot_without_marker')
    elif action_type=='CORRECTION':
        if not isinstance(payload,dict) or not isinstance(payload.get('text'),str) or not payload['text'].strip():v.append('correction_text')
        else:
            if CTRL.search(payload['text']) or len(payload['text'])>MAX_TEXT:v.append('correction_text')
            if not isinstance(payload.get('correction_of'),int):v.append('correction_without_target')
            if not payload.get('reason'):v.append('correction_without_reason')
    elif action_type=='ACTION_PREVIEW':
        if not isinstance(payload,dict) or not isinstance(payload.get('call_id'),str) or not isinstance(payload.get('tool'),str):v.append('preview_schema')
        else:
            if tools is not None and payload['tool'] not in tools:v.append('unknown_tool')
            if payload.get('status')!='PROPOSED':v.append('preview_not_pending')
            if not isinstance(payload.get('preview'),dict):v.append('preview_missing')
            if not isinstance(payload.get('text'),str) or ':tx approve '+payload['call_id'] not in payload['text']:v.append('preview_without_approval_command')
    elif action_type=='TOOL_CALL':
        if not isinstance(payload,dict) or set(payload)-{'tool','args'} or not isinstance(payload.get('tool'),str):v.append('tool_schema')
        else:
            if tools is not None and payload['tool'] not in tools:v.append('unknown_tool')
            args=payload.get('args',{})
            if not isinstance(args,dict):v.append('args_not_object')
            else:
                for k,a in args.items():
                    if not isinstance(a,(str,int,float,bool)) or isinstance(a,str) and SHELLISH.search(a):v.append('unsafe_arg:'+str(k)[:32])
    else:v.append('unknown_action_type')
    return {'ok':not v,'violations':v,'action_type':action_type}

def check_output(store,e,action_type,output,source_text=None):
    out=egress(action_type,output,source_text)
    store.add_packet('EgressCheck',packet('EgressCheck','C6_EGRESS',e['event_id'],e['brain_generation_id'],[e['source_ref']],
                     action_type=action_type,ok=out['ok'],violations=out['violations'],rewrites=0))
    return out

def controller(runtime):
    c=getattr(runtime,'c5learning',None)
    if c is None:
        n=None
        try:
            from .neuromod import controller as nc
            n=nc(runtime)
        except Exception:n=None
        c=runtime.c5learning=C5Learning(runtime.store,n)
    return c

def on_rating(store,event_id,score):
    """Human rating -> human_approval (promote) or human_correction (suppress) for the taken action."""
    row=store.one("SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? ORDER BY rowid DESC LIMIT 1",(event_id,))
    if not row:return None
    p=json.loads(row['payload']);ctx=(p.get('learning') or {}).get('context') or context(p.get('route_hint'))
    u=(score-1)/9
    return C5Learning(store).learn(ctx,p['selected']['action_id'],None,human_approval=u if u>=.5 else 0.,human_correction=1-u if u<.5 else 0.)

def operator_command(r,args):
    """:c5 [status|shadow|active]"""
    c=controller(r)
    if not args or args==['status']:return dumps(c.report())
    if args==['shadow']:return dumps({'mode':c.set_mode('SHADOW')})
    if args==['active']:return dumps({'mode':c.set_mode('ACTIVE','EXPLICIT_HUMAN')})
    raise ValueError(':c5 [status|shadow|active]')
