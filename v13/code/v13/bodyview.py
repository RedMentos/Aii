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
import math
import time

from .attention import SOURCE_DELIVERY
from .common import dumps
from .resource_modes import MODE_LEGACY, mode_of

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

def _valid_sha256(value):
    return (isinstance(value, str) and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _world_jepa_body_readout(r, e, text, role):
    """Read persisted B1/B2 numeric heads without blocking a foreground turn."""
    if role not in ("B1_DETAIL", "B2_GIST"):
        return None, None
    try:
        from . import world_model
        from .world_jepa_receiver_matrix import receiver_matrix

        guard = getattr(r, "guard", None)
        resource_state = getattr(guard, "state", None)
        if resource_state not in world_model.PRESSURE:
            resource_state = MODE_LEGACY.get(mode_of(guard), "NORMAL")
        state = world_model.state_vec(
            len(text), resource_state, (time.time() % 86400.0) / 3600.0
        )
        actions = tuple(world_model.ACTIONS)
        matrix = receiver_matrix(
            r.store, state, actions, home=getattr(r, "home", None),
            nonblocking=True, warm_only=True,
        )
        entries = []
        unsupported_actions = []
        for action in actions:
            item = matrix[action][role]
            if not isinstance(item, dict):
                return None, None
            if (item.get("native_body_consumed") is not False
                    or item.get("native_body_weights_changed") is not False
                    or item.get("decision_authority") != "NONE"):
                return None, None
            if item.get("status") == "ACTION_SUPPORT_INSUFFICIENT":
                unsupported_actions.append(action)
                continue
            if item.get("status") != "SHADOW_READOUT_ONLY":
                return None, None
            entries.append((action, item))
        if not entries:
            return None, None

        checkpoint_shas = {item.get("checkpoint_sha256") for _, item in entries}
        source_shas = {item.get("source_sha256") for _, item in entries}
        if len(checkpoint_shas) != 1 or len(source_shas) != 1:
            return None, None
        checkpoint_sha = next(iter(checkpoint_shas))
        source_sha = next(iter(source_shas))
        if not _valid_sha256(checkpoint_sha) or not _valid_sha256(source_sha):
            return None, None

        prediction_rows = []
        for action, item in entries:
            utility = item.get("receiver_utility")
            if not isinstance(utility, dict) or utility.get("accepted") is not True:
                return None, None
            uncertainty = item.get("uncertainty")
            if (isinstance(uncertainty, bool)
                    or not isinstance(uncertainty, (int, float))
                    or not math.isfinite(float(uncertainty))
                    or float(uncertainty) < 0):
                return None, None
            support_samples = item.get("support_samples")
            if (type(support_samples) is not int
                    or support_samples < item.get("support_min_samples", 8)
                    or item.get("support_scope") != "TRAIN_SPLIT_ONLY"):
                return None, None
            prediction = item.get("prediction")
            if not isinstance(prediction, dict):
                return None, None

            if role == "B1_DETAIL":
                duration = prediction.get("predicted_action_duration_s")
                output_chars = prediction.get("predicted_output_characters")
                if (isinstance(duration, bool) or not isinstance(duration, (int, float))
                        or not math.isfinite(float(duration))
                        or isinstance(output_chars, bool)
                        or not isinstance(output_chars, (int, float))
                        or not math.isfinite(float(output_chars))):
                    return None, None
                row = [
                    action,
                    round(min(86400.0, max(0.0, float(duration))), 3),
                    int(round(min(1000000.0, max(0.0, float(output_chars))))),
                    round(float(uncertainty), 4),
                    support_samples,
                ]
            else:
                success = prediction.get("predicted_success_probability")
                if (isinstance(success, bool) or not isinstance(success, (int, float))
                        or not math.isfinite(float(success))):
                    return None, None
                row = [
                    action,
                    round(min(1.0, max(0.0, float(success))), 3),
                    round(float(uncertainty), 4),
                    support_samples,
                ]
            prediction_rows.append(row)

        # Keep the foreground prompt representation deliberately compact. Full
        # provenance and exact target semantics remain in the stored audit below.
        context = {
            "status": "SHADOW_READOUT_ONLY",
            "horizon": "NEXT_ACTION",
            "target": ("B1_DURATION_OUTPUT_SIZE" if role == "B1_DETAIL"
                       else "B2_P_FINAL_NOT_ANSWER_CORRECTNESS"),
            "checkpoint": checkpoint_sha[:12],
            "rows": prediction_rows,
            "native_body_consumed": False,
            "native_body_weights_changed": False,
            "decision_authority": "NONE",
        }
        if unsupported_actions:
            context["unsupported_actions"] = unsupported_actions
        audit = {
            "schema": "V14_WORLDJEPA_BODY_RECEIVER_AUDIT/1",
            "checkpoint_sha256": checkpoint_sha,
            "training_source_sha256": source_sha,
            "state_vector": [round(float(value), 6) for value in state],
            "event_id": e.get("event_id"),
            "brain_generation_id": e.get("brain_generation_id"),
            "role": role,
            "action_order": list(actions),
            "supported_action_samples": {action: item.get("support_samples") for action, item in entries},
            "unsupported_actions": unsupported_actions,
            "target_semantics": ("ACTION_DURATION_AND_OUTPUT_SIZE" if role == "B1_DETAIL"
                                 else "ACTION_STATUS_FINAL_NOT_ANSWER_CORRECTNESS"),
            "action_horizon": "NEXT_ACTION",
            "body_prompt_consumed": True,
            "native_body_consumed": False,
            "native_body_weights_changed": False,
            "decision_authority": "NONE",
        }
        return context, audit
    except (ValueError, TypeError, KeyError, OSError, OverflowError,
            ArithmeticError, AttributeError):
        return None, None


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
    world_jepa_context, world_jepa_audit = _world_jepa_body_readout(r,e,text,role)
    if world_jepa_context is not None:
        view['world_jepa'] = world_jepa_context
    try:
        from .agi import hub
        view['skills']=hub(r).skills.select(text)[:3]
    except Exception:view['skills']=[]
    def prompt_chars():
        return len(dumps(view | {'authority':'STATE_NOT_FACT','role':role}))

    if prompt_chars()>STATE_CHARS:
        view['world']['recent']=[]
    if prompt_chars()>STATE_CHARS and world_jepa_context is not None:
        # Preserve the primary temporal prediction and its explicit authority
        # boundary. Trim optional context before omitting the receiver readout.
        view['skills']=[]
        world_jepa_context.pop('unsupported_actions',None)
        for key in ('unfinished_actions','system_stage','learning'):
            if prompt_chars()>STATE_CHARS:
                view['self'].pop(key,None)
        if prompt_chars()>STATE_CHARS:
            view['world'].pop('observed_actions',None)
        if prompt_chars()>STATE_CHARS:
            view['self'].pop('external_tools',None)
        if prompt_chars()>STATE_CHARS:
            view['world'].pop('scope',None)
        if prompt_chars()>STATE_CHARS:
            view['self']={}
        if prompt_chars()>STATE_CHARS:
            view['world']={'mode':view['world'].get('mode')}
        if prompt_chars()>STATE_CHARS:
            view.pop('world_jepa',None)
            world_jepa_audit=None

    s=dumps(view)
    if world_jepa_audit is not None:
        s=dumps({
            'schema':'V14_BODY_STATE_WITH_WORLDJEPA_AUDIT/1',
            'view':view,
            'world_jepa_audit':world_jepa_audit,
        })
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
