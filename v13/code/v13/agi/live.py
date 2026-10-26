"""WP-N13: AG modules in the live turn (runtime._turn), not only via :growth/sleep/scheduler.

  AG9  metacognition -> effort: answer quality ratings can request extra thinking,
       but only grounded correctness evidence can request factual abstention.
       Legacy mixed answer labels remain preserved but have no decision authority.
  AG2  grounding     -> every answer action: prediction before acting, grounded outcome after.
  AG11 user model    -> C1: explicit preference/style feedback becomes evidence-bound beliefs; the turn
       carries the belief summary (no inference about protected attributes).
  AG4  skills        -> C5: a TRUSTED route-only skill whose trigger matches sets the route (procedural fast path).
  AG9  abstain       -> C5: a calibrated abstention makes ASK_USER (clarify instead of guessing) win the action gate;
       SHADOW (default) only records it, ACTIVE needs the explicit human (`:live ask active`).
  AG11 -> C1/answer  beliefs (confidence >= BELIEF_MIN) go into ExecState.user_beliefs and the answer context as a
       labelled USER_MODEL layer (beliefs, not facts; fixed rules stay the only constraints).
  AG0  slots         -> ModelManager: installed models are mirrored into slots; a changed revision becomes a
       swap proposal so learned assets get a shadow/parity plan instead of silently going stale.

Every hook is fail-open: an AG error is logged and the turn continues unchanged.
"""
import json
from . import hub
from .base import clamp01

STATE='agi-live:'
RATING_GOOD=6;RATING_BAD=4
BELIEF_MIN=.5;CONFIG='agi-live:config'
ANSWER_GROUNDED='answer_grounded_v2'
ANSWER_QUALITY='answer_quality_v2'
LEGACY_ANSWER='answer'  # historical mixed quality/correctness; retained, never used for active decisions

def _log(r,eid,stage,exc):r.store.log('agi_live_unavailable',eid,{'stage':stage,'error':type(exc).__name__})
def _save(store,eid,**kw):
    st,_=store.state(STATE+eid);store.set_state(STATE+eid,(st or {})|kw)
def _load(store,eid):return store.state(STATE+eid)[0] or {}

def route_confidence(info):
    info=info or {}
    if info.get('control_calibration'):return info['control_calibration'].get('calibrated_confidence')
    d=info.get('decision') or {}
    if 'margin' in d:return clamp01(.5+d['margin'])
    return None

def skill_route(r,e,text,route,direct,meta):
    """AG4 -> C5: TRUSTED route-only skill = known safe route without deliberation (§6.2, §24.3)."""
    if direct:return route
    try:
        g=hub(r);names=g.skills.select(text)
        for n in names:
            steps=g.skills.get(n)['steps'];routes=[s['route'] for s in steps if 'route' in s]
            if routes and len(routes)==len(steps) and routes[0] in {'simple','detail','gist','both'}:
                meta['skill']={'name':n,'route':routes[0],'prior_route':route};_save(r.store,e['event_id'],skill=n);return routes[0]
        if names:meta['skill_candidates']=names
    except Exception as exc:_log(r,e['event_id'],'skill',exc)
    return route

def before_effort(r,e,meta,sig):
    """AG9 -> effort (+ AG11 summary for C1). Returns the (possibly raised) effort signals."""
    try:
        g=hub(r);raw=round(1-sig.get('uncertainty',0.),4);out=dict(sig);notes={'answer_raw_confidence':raw}
        grounded=g.metacog.decide(ANSWER_GROUNDED,raw)
        quality=g.metacog.decide(ANSWER_QUALITY,raw)
        notes['answer']=grounded  # factual gate, never a quality-only rating
        notes['answer_quality']=quality
        notes['legacy_mixed_answer_ignored']=True
        if grounded['reason']=='CALIBRATED':
            if grounded['abstain']:
                out['uncertainty']=max(out['uncertainty'],.8)
                meta['metacog_abstain']=True
            elif grounded['second_attempt']:
                out['uncertainty']=max(out['uncertainty'],.6)
        if quality['reason']=='CALIBRATED' and (quality['second_attempt'] or quality['abstain']):
            # Dissatisfaction may justify another pass, but cannot assert
            # factual incorrectness or unlock C5's ASK_USER abstention.
            out['uncertainty']=max(out['uncertainty'],.6)
        info=meta.get('route') if isinstance(meta.get('route'),dict) else {}
        rc=route_confidence(info);comp='route:'+info.get('source','BOOT_SCAFFOLD')
        if rc is not None:
            rd=g.metacog.decide(comp,rc);notes['route']=rd|{'component':comp}
            if rd['reason']=='CALIBRATED' and rd['second_attempt']:out['uncertainty']=max(out['uncertainty'],.6)
        beliefs=g.users.context()
        meta['metacognition']=notes;meta['user_model']={'beliefs':len(beliefs),'aspects':sorted({b['aspect'] for b in beliefs})}
        meta['user_beliefs']=[{k:b[k] for k in ('aspect','topic','value','confidence','authority')} for b in beliefs if b['confidence']>=BELIEF_MIN]
        _save(r.store,e['event_id'],answer_confidence=raw,route_component=comp,route_confidence=rc,route=info.get('route_hint') or sig.get('route_hint'))
        return out
    except Exception as exc:_log(r,e['event_id'],'metacog',exc);return sig

def ask_mode(store):return (store.state(CONFIG)[0] or {}).get('ask','SHADOW')
def set_ask_mode(store,mode,authority='SYSTEM'):
    if mode not in {'SHADOW','ACTIVE'}:raise ValueError('SHADOW|ACTIVE')
    if mode=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0)')
    st,v=store.state(CONFIG);store.set_state(CONFIG,(st or {})|{'ask':mode},expected=v);return mode

def clarify(r,meta):
    """AG9 -> C5: abstention proposes ASK_USER. Returns the C5 hint; `apply` only in ACTIVE."""
    if not meta.get('metacog_abstain'):return None
    try:mode=ask_mode(r.store)
    except Exception:mode='SHADOW'
    return {'abstain':True,'mode':mode,'apply':mode=='ACTIVE','reason':'METACOG_CALIBRATED_ABSTAIN'}

def user_layer(meta):
    """Answer-context payload for AG11 beliefs (None when there are none above BELIEF_MIN)."""
    b=meta.get('user_beliefs') or []
    return [{'aspect':x['aspect'],'topic':x['topic'],'value':x['value']} for x in b] or None

def expect(r,e,aid,role,route):
    """AG2: prediction before the action is executed."""
    try:
        gid,pred=hub(r).grounding.expect('answer:'+str(role),str(route),{'role':role,'action_id':aid},'text')
        _save(r.store,e['event_id'],grounding_id=gid,role=role,predicted=pred.get('outcome'))
    except Exception as exc:_log(r,e['event_id'],'grounding_expect',exc)

def after_turn(r,e,meta,status,aid=None):
    """AG2 outcome, AG4 skill outcome, AG0 slot sync."""
    eid=e['event_id']
    try:
        g=hub(r);st=_load(r.store,eid)
        if st.get('grounding_id'):
            rec=g.grounding.observe(st['grounding_id'],{'status':status},cause='SELF');_save(r.store,eid,grounding_id=None,grounded_error=rec['grounded_error'])
        if st.get('skill'):g.skills.record(st['skill'],status=='FINAL')
        sync_slots(r,g)
    except Exception as exc:_log(r,eid,'after_turn',exc)
    try:goal_turn(r,e,meta,status)  # WP-T8: open user goals and curiosity from live turns
    except Exception as exc:_log(r,eid,'goal_turn',exc)
    try:  # WP-T2: maturity evidence live from turns (rate-limited in maturity.turn_feed)
        from .maturity import turn_feed
        turn_feed(hub(r))
    except Exception as exc:_log(r,eid,'age_feed',exc)

GOAL_MATCH=.5  # WP-T8 BOOT: lexical relevance for a later FINAL turn to close an open user goal
GOAL_TTL_S=7*86400  # WP-T8 BOOT: an unanswered open request is dropped after a week

def goal_turn(r,e,meta,status):
    """§20.3: a user goal closes only after a related, actually persisted FINAL answer.

    Status alone is not a delivery receipt. This is a structural guard, not a
    semantic proof that the answer satisfied the request. Curiosity stays Age-gated.
    """
    from ..memory import relevance
    g=hub(r);eid=e['event_id'];text=r.store.read_source(e['source_ref'])
    sel=r.store.one("SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? ORDER BY rowid DESC LIMIT 1",(eid,))
    sel=json.loads(sel['payload']) if sel else {}
    asked=(sel.get('selected') or {}).get('action_id')=='CLARIFY' or bool((meta.get('clarify') or {}).get('apply'))
    gerr=_load(r.store,eid).get('grounded_error')
    g.curiosity.observe('route:'+str(sel.get('route_hint') or 'unknown'),float(gerr) if isinstance(gerr,(int,float)) else (0. if status=='FINAL' and not asked else 1.))
    opened=[x for x in g.goals.tree({'OPEN','ACTIVE','BLOCKED'}) if x['origin']=='USER' and any(str(v).startswith('event:') for v in x['evidence'])]
    for x in [x for x in opened if g.goals.clock()-x['created']>GOAL_TTL_S]:g.goals.set_status(x['id'],'ABANDONED','open request expired');opened.remove(x)
    final_answer=r.store.one(
        "SELECT id FROM messages WHERE event_id=? AND session_id=? AND role='assistant' "
        "AND status='FINAL' AND length(trim(text))>0 "
        "AND COALESCE(json_extract(metadata,'$.reference_only'),0)=0 "
        "ORDER BY id DESC LIMIT 1",
        (eid,r.session))
    delivered=status=='FINAL' and not asked and final_answer is not None
    if delivered:
        for x in opened:
            if relevance(x['title'].removeprefix('Open request: '),text)>=GOAL_MATCH:
                g.goals.set_status(x['id'],'DONE','related FINAL answer '+eid+' message '+str(final_answer['id']))
    elif not any('event:'+eid in x['evidence'] for x in opened):
        g.goals.add('Open request: '+' '.join(text.split())[:240],'USER',evidence=['event:'+eid])

def sync_slots(r,g=None):
    """AG0: mirror installed models into slots; a new revision becomes a USER swap proposal."""
    from ..models import ROLES,OPTIONAL_ROLES,model_key
    from .slots import ModelSlots
    g=g or hub(r);slots=g.slots.box.load()[0]['slots'];done=[]
    for role in list(ROLES)+list(OPTIONAL_ROLES):
        entry=r.models.installed.get(model_key(role,r.models.b2_control))
        if not entry or not entry.get('download_complete'):continue
        spec=ModelSlots.from_installed(entry);sl=slots.get(role)
        if not sl or not sl.get('active'):g.slots.install(role,spec);done.append((role,'INSTALL'))
        elif sl['active']['revision']!=spec['revision'] and not sl.get('candidate'):g.slots.propose_swap(role,spec,origin='USER');done.append((role,'PROPOSE'))
    return done

def _answer_role(store,eid):
    st=_load(store,eid)
    return st.get('role'),st.get('answer_confidence')

def on_feedback(store,event_id,kind,value,memory_id=None,evidence_ref=None,key=None):
    """Labels for AG9 and evidence for AG11 from explicit human feedback (called by memory.feedback)."""
    from .metacog import Metacognition
    from .user_model import UserModel
    st=_load(store,event_id)
    if kind=='route' and st.get('route_confidence') is not None and st.get('route'):
        Metacognition(store).record(st['route_component'],st['route_confidence'],value==st['route'],evidence=memory_id)
    if kind=='fact' and st.get('answer_confidence') is not None:
        Metacognition(store).record(ANSWER_GROUNDED,st['answer_confidence'],False,evidence=memory_id)
    if kind=='route':  # WP-T6: a route correction on a skill-routed turn reopens the skill (back to the full path)
        try:
            from ..skilllive import on_route_correction
            on_route_correction(store,event_id,value)
            from ..jefoutcome import on_route_correction as outcome_route_correction
            outcome_route_correction(store,event_id,value)  # WP-U1: skill outcome label flips to none
        except Exception as exc:store.log('agi_live_unavailable',event_id,{'stage':'skill_reopen','error':type(exc).__name__})
    if kind in {'preference','style'}:
        try:UserModel(store).observe(kind if kind=='preference' else 'style',(key or '*')[:80],value[:200],evidence_ref or memory_id)
        except PermissionError:store.log('agi_live_unavailable',event_id,{'stage':'user_model','error':'PermissionError'})

def on_rating(store,event_id,score):
    """One effective quality label per answer, with explicit feedback taking priority.

    Rating edits replace rather than multiply calibration samples. A neutral
    explicit note suppresses an earlier implicit judgement; it does not claim
    factual correctness. Old unkeyed AG9 samples cannot be retroactively linked.
    """
    from .metacog import Metacognition
    from ..inputs import ratings
    st=_load(store,event_id)
    if st.get('answer_confidence') is None:return None
    rows=[x for x in ratings(store) if x.get('event_id')==event_id]
    explicit=[x for x in rows if x.get('origin')=='EXPLICIT_NOTE']
    effective=(explicit or rows)
    score=effective[-1]['score'] if effective else score
    label=None if RATING_BAD<score<RATING_GOOD else score>=RATING_GOOD
    Metacognition(store).record_keyed(ANSWER_QUALITY,st['answer_confidence'],label,'rating:'+event_id)
    return label is not None

def report(r):
    g=hub(r);mc=g.metacog.report()
    return {'metacognition':mc['components'],'answer_label_contract':'QUALITY_NOT_FACT_GROUNDED_ONLY_V2','grounding':g.grounding.report()['error_rate'],'user_beliefs':len(g.users.beliefs()),
            'skills_trusted':[n for n,s in g.skills.box.load()[0]['skills'].items() if s['stage'] in {'TRUSTED','INTERNALISED'}],
            'slots':{k:v['active']['revision'][:12] if v.get('active') else None for k,v in g.slots.box.load()[0]['slots'].items()},
            'ask_mode':ask_mode(r.store),'user_beliefs_in_context':len([b for b in g.users.context() if b['confidence']>=BELIEF_MIN]),
            'hooks':['AG4 skill_route','AG9 before_effort','AG9 clarify -> C5 ASK_USER','AG2 expect/after_turn','AG11 on_feedback','AG11 -> C1 user_beliefs + USER_MODEL layer','AG0 sync_slots']}

def operator_command(r,args):
    """:live [status|ask shadow|ask active]"""
    if not args or args==['status']:return report(r)
    if args==['ask','shadow']:return {'ask':set_ask_mode(r.store,'SHADOW')}
    if args==['ask','active']:return {'ask':set_ask_mode(r.store,'ACTIVE','EXPLICIT_HUMAN')}
    raise ValueError(':live [status|ask shadow|ask active]')
