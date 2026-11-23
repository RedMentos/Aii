"""WP-T5 body view and access (B1, B4, B5, §3.2A).

B1 detail windows: granted A4 high-res spans (F1 AttentionResponse, A_SOURCE) become wider exact windows for B1
  (span ± PAD chars, merged, at most MAX_WINDOWS / MAX_CHARS), so B1 is not limited to fixed 240-char chunks where
  attention says detail matters. Windows are exact substrings of the event source, so quotes from them verify.
B4 distributed state: B2 may carry one prior coalition offer across sessions when the topic clearly matches (shared
  named entity, or high relevance). Default SHADOW: candidates are only logged; `:bodyview b4 on` lets them in.
B5 body state: a compact world/self/skill state is stored as a source (SourceRef) and handed to B1/B2 as state, never
  as a fact. `:bodyview state off` removes it from prompts.
"""
import json
from .attention import SOURCE_DELIVERY
from .common import dumps

KEY='bodyview';PAD=240;MAX_WINDOWS=3;MAX_CHARS=1200;B4_SCAN=60;B4_RELEVANCE=.5;STATE_CHARS=700
DEFAULT={'state_source':'on','b4':'shadow'}

def modes(store):return DEFAULT|(store.state(KEY)[0] or {})

def set_mode(store,name,value):
    allowed={'state_source':('on','off'),'b4':('off','shadow','on')}
    if name not in allowed or value not in allowed[name]:raise ValueError(':bodyview state on|off / :bodyview b4 off|shadow|on')
    for attempt in (0,1):
        st,v=store.state(KEY);st=dict(st or {});st[name]=value
        try:store.set_state(KEY,st,expected=v);return modes(store)
        except ValueError:
            if attempt:raise

def granted_spans(store,event_id):
    out=[]
    for r in store.rows("SELECT payload FROM packets WHERE kind='AttentionResponse' AND event_id=?",(event_id,)):
        resp=json.loads(r['payload'])
        if resp['status']!='GRANTED' or resp.get('delivery')!=SOURCE_DELIVERY:continue
        req=store.one("SELECT payload FROM packets WHERE id=? AND kind='AttentionRequest'",(resp['request_packet_id'],))
        ref=(json.loads(req['payload']).get('source_ref') or {}) if req else {}
        if 'char_start' in ref and 'char_end' in ref:out.append(ref)
    return out

def detail_windows(store,event_id,text,ref,pad=PAD):
    """Exact B1 windows around granted spans (offsets are relative to the event source)."""
    base=int(ref.get('char_start',0));n=len(text);iv=[]
    for s in granted_spans(store,event_id):
        if s.get('source_id')!=ref.get('source_id'):continue
        a=max(0,int(s['char_start'])-base-pad);b=min(n,int(s['char_end'])-base+pad)
        if b>a:iv.append([a,b])
    iv.sort();merged=[]
    for a,b in iv:
        if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],b)
        else:merged.append([a,b])
    out=[];used=0
    for a,b in merged[:MAX_WINDOWS]:
        b=min(b,a+MAX_CHARS-used)
        if b<=a:break
        out.append({'text':text[a:b],'source_ref':ref|{'char_start':base+a,'char_end':base+b}});used+=b-a
    return out

def body_state(r,e,role,text):
    """B5: compact world/self/skill state as a stored source (SourceRef), STATE_NOT_FACT."""
    if modes(r.store)['state_source']!='on':return None
    world=r.store.state('WORLD_STATE:'+r.session,{})[0] or {}
    me=r.store.state('SELF_MODEL:'+r.session,{})[0] or {}
    action_mode=world.get('mode','NO_OBSERVATIONS')
    if action_mode=='NO_OBSERVATIONS':action_mode='NO_COMPLETED_OWN_DIGITAL_ACTIONS'
    view={'world':{'scope':'OWN_DIGITAL_ACTION_OUTCOMES_ONLY','mode':action_mode,'observed_actions':world.get('observed_action_count',0),
                   'recent':[{k:x.get(k) for k in ('channel','status','outcome') if k in x} for x in (world.get('recent') or [])[-3:] if isinstance(x,dict)]},
          'self':{'learning':(me.get('learning') or {}).get('mode'),'unfinished_actions':me.get('unfinished_actions'),
                  'external_tools':(me.get('permissions') or {}).get('external_tools'),'system_stage':(me.get('permissions') or {}).get('system_stage')}}
    try:
        from .agi import hub
        view['skills']=hub(r).skills.select(text)[:3]
    except Exception:view['skills']=[]
    s=dumps(view)
    if len(s)>STATE_CHARS:view['world']['recent']=[];s=dumps(view)
    ref=r.store.source(s,'BODY_STATE')
    return {'view':view|{'authority':'STATE_NOT_FACT','role':role},'source_ref':ref}

def cross_session(r,e,role,current_text,native,budget):
    """B4: one prior coalition offer from another session on the same topic (SHADOW logs only)."""
    mode=modes(r.store)['b4']
    if mode=='off' or role!='B2_GIST':return []
    from .memory import entities,relevance
    from .inputs import looks_like_terminal_log
    cur=entities(current_text);found=[]
    for row in r.store.rows("SELECT p.id,p.payload FROM packets p JOIN events v ON v.id=p.event_id WHERE p.kind='OfferPacket' AND v.session_id!=? AND json_extract(p.payload,'$.role')=? ORDER BY p.rowid DESC LIMIT ?",(r.session,role,B4_SCAN)):
        p=json.loads(row['payload'])
        if p['brain_generation_id']!=e['brain_generation_id'] or p.get('model_revision')!=r.models.revision(role):continue
        if not r.store.one("SELECT 1 FROM packets WHERE kind='FocalItem' AND json_extract(payload,'$.item_id')=?",(p['packet_id'],)):continue  # only offers that reached a coalition
        ev=r.store.one('SELECT packet FROM events WHERE id=?',(p['event_id'],))
        if not ev:continue
        ref=json.loads(ev['packet'])['source_ref']
        try:source=r.store.read_source(ref)
        except (ValueError,OSError):continue
        if looks_like_terminal_log(source):continue
        prior=entities(source)
        if not ((cur and prior and cur&prior) or relevance(current_text,source)>=B4_RELEVANCE):continue
        excerpt_ref=ref|{'char_end':min(ref['char_end'],ref['char_start']+240)}
        try:excerpt=r.store.read_source(excerpt_ref)
        except (ValueError,OSError):continue
        item={'exact_source_excerpt':excerpt,'hypothesis':p['offer'].get('summary','')[:120],'authority':'PRIOR_HYPOTHESIS_NOT_FACT','cross_session':True}
        if len(dumps(native+[item]))>budget:continue
        found.append({'offer_id':p['packet_id'],'source_ref':excerpt_ref,'native_context':item});break
    r.store.log('b4_cross_session',e['event_id'],{'mode':mode,'candidates':len(found)})
    return found if mode=='on' else []
