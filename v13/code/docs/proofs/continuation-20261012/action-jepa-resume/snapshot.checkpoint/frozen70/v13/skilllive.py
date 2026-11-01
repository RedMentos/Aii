"""WP-T6 skills and proceduralisation live (§6.1-6.3, §41.6, §75, F2).

1. Automatic path without C_fast: a TRUSTED/INTERNALISED route-only skill whose trigger matches sets the route before
   C2 control runs, so the turn skips the Needle call (`TRUSTED_SKILL_AUTOMATIC`). Fallback: an approved skill head
   veto (WP-T1) or a failing skill reopens the full C_fast route; a route correction by the user reopens the skill
   (TRUSTED -> SHADOW, skills.reopen).
2. Selector in the normal turn: CANDIDATE/SHADOW route-only skills that match are compared with the route the full
   path chose (parity) and recorded with the turn outcome, so skills advance from live use, not only from :growth.
3. Habits: repeated procedure cues (same cue key, same final route, FINAL answers) propose a CANDIDATE route skill
   (origin SELF). It still climbs the normal lifecycle; TRUSTED for SELF needs Age procedural_memory or the user.
"""
import re
from .common import digest

HABIT_KEY='skilllive-habits';HABIT_N=5;HABIT_AGREE=.9;HABIT_MAX=200;CUE_WORDS=3
STOP=set('a an the and or but of to in on at for from by with is are was were be do does did can could should would will i you we it this that '
         'please me my your our what which who when where why how'.split())
LIVE=('TRUSTED','INTERNALISED');LEARNING=('CANDIDATE','SHADOW')

def _route_only(sk):
    routes=[s['route'] for s in sk['steps'] if 'route' in s]
    return routes[0] if routes and len(routes)==len(sk['steps']) and routes[0] in {'simple','detail','gist','both'} else None

def matches(lib,text,stages):
    words=set(re.findall(r'\w+',str(text).casefold()));out=[]
    for sk in lib.box.load()[0]['skills'].values():
        t=set(re.findall(r'\w+',sk['trigger'].casefold()))
        if sk['stage'] in stages and t and t<=words and _route_only(sk):out.append(sk)
    return sorted(out,key=lambda s:(-len(s['trigger']),s['name']))

def automatic(r,e,text,meta):
    """Before C_fast: (route, info) from a trusted route-only skill, else None (full path runs)."""
    try:
        from .agi import hub
        from .agi.live import _save
        from .cognition import scaffold_route
        live=matches(hub(r).skills,text,LIVE)
        if not live:return None
        sk=live[0];route=_route_only(sk)
        meta['skill']={'name':sk['name'],'route':route,'prior_route':scaffold_route(text),'automatic':True};_save(r.store,e['event_id'],skill=sk['name'])
        return route,{'source':'TRUSTED_SKILL_AUTOMATIC','skill':sk['name'],'skipped':['C2_CONTROL']}
    except Exception as exc:
        r.store.log('skilllive_unavailable',e['event_id'],{'stage':'automatic','error':type(exc).__name__});return None

def shadow_candidates(r,e,text,meta):
    """Learning-stage skills that match: remember their route for the parity record after the turn."""
    try:
        from .agi import hub
        from .agi.live import _save
        c=[{'name':sk['name'],'route':_route_only(sk)} for sk in matches(hub(r).skills,text,LEARNING)][:4]
        if c:meta['skill_shadow']=c;_save(r.store,e['event_id'],skill_shadow=c)
        return c
    except Exception as exc:
        r.store.log('skilllive_unavailable',e['event_id'],{'stage':'shadow','error':type(exc).__name__});return []

def cue_key(text):
    words=[w for w in re.findall(r'[a-zäöüß]+',str(text).casefold()) if w not in STOP and len(w)>2]
    return ' '.join(words[:CUE_WORDS]) if len(words)>=CUE_WORDS else None

def after_turn(r,e,meta,status,route):
    """Parity for shadow skills, habit counting, habit -> CANDIDATE skill. Never changes the answer."""
    sk=meta.get('skill') or {}
    if sk.get('automatic') and status not in ('FINAL','CANCELLED'):  # failing automatic path: back to the full route next time
        try:
            from .agi import hub
            hub(r).skills.reopen(sk['name'],'failure');r.store.log('skilllive_reopened',e['event_id'],{'skill':sk['name'],'status':status})
        except Exception as exc:r.store.log('skilllive_unavailable',e['event_id'],{'stage':'reopen','error':type(exc).__name__})
    if status!='FINAL':return None
    out={}
    try:
        from .agi import hub
        lib=hub(r).skills
        for c in meta.get('skill_shadow') or []:
            out.setdefault('parity',[]).append([c['name'],lib.record(c['name'],True,parity=float(c['route']==route))])
        if meta.get('skill',{}).get('automatic'):return out
        text=r.store.read_source(e['source_ref']);key=cue_key(text)
        if not key or route not in {'simple','detail','gist','both'}:return out
        for attempt in (0,1):
            st,v=r.store.state(HABIT_KEY);st=st or {}
            h=st.setdefault(key,{'routes':{},'n':0,'proposed':None});h['n']+=1;h['routes'][route]=h['routes'].get(route,0)+1
            if len(st)>HABIT_MAX:
                for k in sorted(st,key=lambda k:st[k]['n'])[:len(st)-HABIT_MAX]:st.pop(k)
            best=max(h['routes'],key=h['routes'].get);ready=h['n']>=HABIT_N and h['routes'][best]/h['n']>=HABIT_AGREE and not h['proposed']
            name='habit_'+digest(key)[:10] if ready else None
            if ready:h['proposed']=name
            try:r.store.set_state(HABIT_KEY,st,expected=v);break
            except ValueError:
                if attempt:raise
        if name:
            try:lib.propose(name,[{'route':best}],trigger=key,origin='SELF',source_traces=[e['event_id']]);out['habit']=name
            except ValueError as exc:out['habit_error']=str(exc)[:80]
            r.store.log('skilllive_habit',e['event_id'],{'skill':name,'route':best})
    except Exception as exc:r.store.log('skilllive_unavailable',e['event_id'],{'stage':'after_turn','error':type(exc).__name__})
    return out

def on_route_correction(store,event_id,value):
    """A user route correction on a turn that a live skill routed reopens that skill (fallback to the full path)."""
    from .agi.live import _load
    from .agi.skills import SkillLibrary
    st=_load(store,event_id);name=st.get('skill')
    if not name:return None
    lib=SkillLibrary(store);sk=lib.get(name)
    if _route_only(sk)==value:return None
    lib.reopen(name,'route_correction');store.log('skilllive_reopened',event_id,{'skill':name});return name

def report(r):
    from .agi import hub
    st=r.store.state(HABIT_KEY)[0] or {}
    lib=hub(r).skills.box.load()[0]['skills']
    return {'live_skills':sorted(n for n,s in lib.items() if s['stage'] in LIVE and _route_only(s)),
            'learning_skills':sorted(n for n,s in lib.items() if s['stage'] in LEARNING and _route_only(s)),
            'habits':{k:{'n':h['n'],'routes':h['routes'],'proposed':h['proposed']} for k,h in sorted(st.items(),key=lambda x:-x[1]['n'])[:10]},
            'claim_limit':'Route-only procedures; tool skills still run only through :growth and the ToolRegistry gates'}
