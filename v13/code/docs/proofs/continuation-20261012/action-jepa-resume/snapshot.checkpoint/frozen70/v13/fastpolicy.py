"""WP-T1: JEF_FAST_POLICY heads, C2 executive packet, top-down re-entry focus (§3.3.0-3.3.3, §3.4.7, §4.4, G4).

Fast heads skill/memory/channel sit next to route/wake/halt: same frozen C2 embedding of the event source, same
`:feedback <head> <value> --learn` -> `:learn <head>` -> held-out gate -> `:approve` path (learning.decide). Without an
approved readout every head returns its scaffold baseline and only logs an ExecutiveDecision (the label anchor).
Effects of an approved head are bounded: memory may skip/deepen recall, skill may veto (never invent) a skill route,
channel may pick one of the configured B3 channels when the callosum policy did not already decide.

C2 executive packet: structured C2 output (route, tool proposal, memory key, answer type) per turn. BOOT parsers fill
each field; a native Needle field is used only when BOOT has none and it validates; every field carries its source.
truth_authority 0: tool goes through IH-H29, the key is only a recall cue, the answer type is a hint.

Re-entry focus: the focal loop asks B1/B2 a concrete executive question (the disputed claim or the uncertainty), not
the same prompt again. Mode on|off|measure (default measure = alternate per event); outcome counts per arm.
"""
import hashlib
import re
import time
from .common import Cancelled
from .contracts import packet

HEADS=('skill','memory','channel');FOCUS_KEY='jef-query-focus';FOCUS_MODES=('on','off','measure')
DEEP_EXTRA=2;NOT_UNCERTAIN=('','low','none','no','n/a')
ANSWER_TYPES=('copy','number','code','yes_no','list','summary','explanation','free')
ANSWER_RULES=(('copy',r'^\s*(?:copy exactly|kopiere exakt)\b'),
              ('code',r'```|\b(?:code|function|script|regex|python|javascript|sql|bash)\b'),
              ('number',r'\b(?:how many|how much|calculate|compute|sum of|percent|average)\b|\d\s*[-+*/x×÷^%]\s*\d'),
              ('summary',r'\b(?:summar\w*|tl;?dr|overview|gist|in short)\b'),
              ('list',r'\b(?:list|enumerate|name (?:\d+|some|all|three|five)|examples of|which ones)\b'),
              ('yes_no',r'^\s*(?:is|are|do|does|did|can|could|should|will|would|was|were|has|have|had)\b'),
              ('explanation',r'\b(?:why|how|explain|what happens|reason)\b'))
STOP=set('a an the and or but if then of to in on at for from by with about into over is are was were be been being do does did can could '
         'should would will shall may might must have has had i you he she it we they me my your our their this that these those what which '
         'who whom whose when where why how please tell show give make let explain list name some any all no not yes so as than too very just '
         'also more most much many few one two say said get got know think want like need use'.split())

def answer_type(text):
    t=str(text)[:2000].lower()
    return next((k for k,pat in ANSWER_RULES if re.search(pat,t)),'free')

def memory_key(text,limit=6):
    """BOOT retrieval key: capitalised names and numbers first, then longer content words, in source order."""
    words=re.findall(r"[A-Za-zÄÖÜäöüß][\w'-]*|\d+(?:[.,]\d+)?",str(text)[:2000]);seen=[];strong=[];weak=[]
    for w in words:
        k=w.lower()
        if k in STOP or len(k)<3 and not k.isdigit() or k in seen:continue
        seen.append(k);(strong if w[0].isupper() or k[0].isdigit() else weak).append(k)
    weak.sort(key=len,reverse=True)
    return ' '.join((strong+weak)[:limit])

def _native(control):
    """Typed fields a native C2 call may carry (optional; the current select_processing schema only has route)."""
    out={}
    def walk(o):
        if isinstance(o,dict):
            for k,v in o.items():
                if k in ('answer_type','memory_key','tool') and isinstance(v,str) and v.strip() and k not in out:out[k]=v.strip()[:200]
                walk(v)
        elif isinstance(o,list):
            for v in o:walk(v)
    walk(control);return out

def c2_packet(r,e,text,route,info=None):
    """One structured C2 packet per turn (BOOT fields first, validated native fields as fallback)."""
    from .toolstep import propose
    info=info if isinstance(info,dict) else {};native=_native(info.get('native_control'))
    tools=set()
    try:
        from .agi import hub
        tools=set(hub(r).tools.tools)
    except Exception:pass
    fields={}
    p=propose(text)
    if p:fields['tool']={'value':{'tool':p['tool'],'args':p['args'],'confidence':p['confidence']},'source':'BOOT'}
    elif native.get('tool') in tools:fields['tool']={'value':{'tool':native['tool'],'args':None,'confidence':None},'source':'NATIVE_C2'}
    key=memory_key(text)
    if key:fields['memory_key']={'value':key,'source':'BOOT'}
    elif native.get('memory_key'):fields['memory_key']={'value':native['memory_key'],'source':'NATIVE_C2'}
    at=answer_type(text)
    if at=='free' and native.get('answer_type') in ANSWER_TYPES:fields['answer_type']={'value':native['answer_type'],'source':'NATIVE_C2'}
    else:fields['answer_type']={'value':at,'source':'BOOT'}
    pk=packet('C2ExecutivePacket','C2_CONTROL',e['event_id'],e['brain_generation_id'],[e['source_ref']],route=route,route_source=info.get('source','BOOT_SCAFFOLD'),
              fields=fields,native_fields=sorted(native),truth_authority=0,parser='boot-c2-struct-v1')
    r.store.add_packet('C2ExecutivePacket',pk)
    return {'packet_id':pk['packet_id'],'route':route,**{k:v['value'] for k,v in fields.items()},'sources':{k:v['source'] for k,v in fields.items()}}

def head(r,component,e,baseline,deadline=None):
    """One fast head. Never raises (except cancellation); the scaffold baseline is the fallback."""
    try:
        d=r.learner.decide(component,e,baseline,deadline or time.monotonic()+r.cfg['control_seconds'],enabled=r.cfg['route_override']=='auto')
        return d['action'],d
    except Cancelled:raise
    except Exception as exc:
        r.store.log('fast_policy_unavailable',e['event_id'],{'component':component,'error':type(exc).__name__});return baseline,None

def recall_plan(r,e,text,deadline=None):
    """Memory head before recall: (top_k, cue, decision). skip -> 0, recall -> configured, deep -> more, with key cue."""
    k=int(r.cfg['memory_top_k']);action,d=head(r,'memory',e,'recall' if k else 'skip',deadline)
    if action=='skip':return 0,text,d
    if action=='deep':
        key=memory_key(text);return min(8,k+DEEP_EXTRA),(text+' '+key if key else text),d
    return k,text,d

# -- re-entry focus (top-down QUERY_PACKET content) ------------------------------------------------------
def focus_mode(store):
    st=store.state(FOCUS_KEY)[0] or {};return st.get('mode','measure')

def _mutate(store,fn):
    for attempt in (0,1):
        st,v=store.state(FOCUS_KEY);st=st or {};fn(st)
        try:store.set_state(FOCUS_KEY,st,expected=v);return st
        except ValueError:
            if attempt:raise

def set_focus_mode(store,mode):
    if mode not in FOCUS_MODES:raise ValueError(':fastpolicy focus on|off|measure')
    _mutate(store,lambda st:st.__setitem__('mode',mode));return mode

def focus_arm(store,event_id):
    m=focus_mode(store)
    if m!='measure':return m
    return 'on' if hashlib.sha256(event_id.encode()).digest()[0]%2==0 else 'off'

def focus_for(role,fresh,view,reason):
    """Executive question for a re-entry: the disputed claim (conflict) or the open uncertainty of the target body."""
    own=next((p for p in reversed(fresh) if p['role']==role),None);other=next((p for p in reversed(fresh) if p['role']!=role),None)
    s=lambda p:(p['offer'].get('summary','') if p else '')[:200]
    if other and own and view.get('conflict',0)>=.4:
        q=f'The other view says: "{s(other)}". Your last view said: "{s(own)}". Which one does the source support? Quote the deciding span.'
        kind='RESOLVE_CONFLICT'
    elif own and str(own['offer'].get('uncertainty','')).strip().lower() not in NOT_UNCERTAIN:
        q=f'Your last view was uncertain ({str(own["offer"]["uncertainty"])[:120]}). Find the exact source span that settles it, or say it is not in the source.'
        kind='RESOLVE_UNCERTAINTY'
    elif other:
        q=f'Check this claim against the source and quote the span that supports or contradicts it: "{s(other)}".';kind='VERIFY_PEER'
    else:
        q='Re-read the source for the detail that the current answer still lacks and quote it.';kind='FILL_GAP'
    return {'question':q,'kind':kind,'target_role':role,'reason':reason,'authority':'EXECUTIVE_QUESTION_NOT_FACT'}

def record_focus(store,arm,reached,stable):
    def fn(st):
        a=st.setdefault(arm,{'n':0,'in_coalition':0,'stable':0})
        a['n']+=1;a['in_coalition']+=int(bool(reached));a['stable']+=int(bool(stable))
    _mutate(store,fn)

def report(r):
    st=r.store.state(FOCUS_KEY)[0] or {}
    comps=r.store.components();out={'heads':{},'focus':{'mode':st.get('mode','measure')}}
    for h in ('wake','halt')+HEADS:
        rows=r.store.rows("SELECT json_extract(payload,'$.learned') AS l,COUNT(*) AS n FROM packets WHERE kind='ExecutiveDecision' AND json_extract(payload,'$.component')=? GROUP BY l",(h,))
        out['heads'][h]={'approved':bool(comps.get(h)),'decisions':sum(x['n'] for x in rows),'learned':sum(x['n'] for x in rows if x['l'])}
    for arm in ('on','off'):
        a=st.get(arm)
        if a:out['focus'][arm]=a|{'coalition_rate':round(a['in_coalition']/a['n'],4) if a['n'] else None}
    out['claim_limit']='Counts are local evidence only; a head acts only after :learn + held-out gate + :approve; the focus arm comparison needs real models (WP-T3)'
    return out
