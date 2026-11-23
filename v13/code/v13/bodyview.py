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

def _valid_sha256(value):
    return (
        type(value) is str and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _temporal_world_jepa_body_readout(r, e, role):
    """Read source-bound temporal T8 predictions for B1/B2 without blocking a turn."""
    if role not in ("B1_DETAIL", "B2_GIST"):
        return None, None
    history_length = 2 if role == "B1_DETAIL" else 3

    def omitted(reason, **details):
        audit = {
            "schema": "V14_TEMPORAL_WORLDJEPA_BODY_RECEIVER_AUDIT/1",
            "status": "OMITTED",
            "reason": reason,
            "role": role,
            "history_length": history_length,
            "event_id": e.get("event_id") if isinstance(e, dict) else None,
            "brain_generation_id": (
                e.get("brain_generation_id") if isinstance(e, dict) else None
            ),
            "body_state_created": True,
            "body_prompt_consumed": False,
            "native_body_consumed": False,
            "native_body_weights_changed": False,
            "decision_authority": "NONE",
        }
        audit.update(details)
        return None, audit

    try:
        from . import world_model
        from .world_jepa_temporal import runtime_consumer

        session_id = getattr(r, "session", None)
        if type(session_id) is not str or not session_id:
            return omitted("NO_SESSION")
        actions = tuple(world_model.ACTIONS)
        learner = runtime_consumer(r)
        matrix = learner.receiver_matrix(
            session_id, actions, history_length=history_length, nonblocking=True,
            warm_only=True,
        )
        matrix_status = matrix.get("status")
        if matrix_status != "SHADOW_READOUT_ONLY":
            return omitted(
                "MATRIX_UNAVAILABLE",
                matrix_status=matrix_status if type(matrix_status) is str else "UNKNOWN",
            )
        checkpoint_sha = matrix.get("checkpoint_sha256")
        source_sha = matrix.get("source_sha256")
        history_ids = matrix.get("history_action_ids")
        history_sources = matrix.get("history_source_sha256s")
        if (not _valid_sha256(checkpoint_sha) or not _valid_sha256(source_sha)
                or type(history_ids) is not list or len(history_ids) != history_length
                or type(history_sources) is not list or len(history_sources) != history_length
                or any(type(value) is not str or not value for value in history_ids)
                or any(not _valid_sha256(value) for value in history_sources)):
            return omitted("INVALID_PROVENANCE")

        entries = matrix.get("matrix")
        if not isinstance(entries, dict):
            return omitted("INVALID_MATRIX")
        rows, unsupported = [], []
        for action in actions:
            item = entries.get(action, {}).get(role)
            if not isinstance(item, dict):
                return omitted("MISSING_ACTION_ENTRY", action=action)
            item_status = item.get("status")
            if item_status == "ACTION_SUPPORT_INSUFFICIENT":
                unsupported.append(action)
                continue
            if item_status != "SHADOW_READOUT_ONLY":
                utility = item.get("receiver_utility")
                return omitted(
                    "RECEIVER_UTILITY_REJECTED" if item_status == "RECEIVER_UTILITY_REJECTED"
                    else "RECEIVER_STATUS_UNAVAILABLE",
                    action=action,
                    action_status=item_status,
                    utility_reason=(
                        utility.get("reason") if isinstance(utility, dict) else None
                    ),
                )
            if (item.get("checkpoint_sha256") != checkpoint_sha
                    or item.get("source_sha256") != source_sha
                    or item.get("history_action_ids") != history_ids
                    or item.get("history_source_sha256s") != history_sources
                    or item.get("history_length") != history_length
                    or item.get("native_body_consumed") is not False
                    or item.get("native_body_weights_changed") is not False
                    or item.get("decision_authority") != "NONE"):
                return omitted("READOUT_PROVENANCE_MISMATCH", action=action)
            utility, support = item.get("receiver_utility"), item.get("support_samples")
            if (not isinstance(utility, dict) or utility.get("accepted") is not True):
                return omitted(
                    "RECEIVER_UTILITY_REJECTED",
                    action=action,
                    utility_reason=utility.get("reason") if isinstance(utility, dict) else None,
                )
            if (type(support) is not int or support < 8
                    or item.get("support_min_samples") != 8
                    or item.get("support_scope") != "TRAIN_SPLIT_ONLY"):
                return omitted("ACTION_SUPPORT_INSUFFICIENT", action=action)
            prediction, uncertainty = item.get("prediction"), item.get("uncertainty")
            if (not isinstance(prediction, dict) or isinstance(uncertainty, bool)
                    or not isinstance(uncertainty, (int, float))
                    or not math.isfinite(float(uncertainty)) or float(uncertainty) < 0):
                return omitted("INVALID_PREDICTION", action=action)
            if role == "B1_DETAIL":
                duration = prediction.get("predicted_action_duration_s")
                output_chars = prediction.get("predicted_output_characters")
                if (isinstance(duration, bool) or not isinstance(duration, (int, float))
                        or not math.isfinite(float(duration))
                        or isinstance(output_chars, bool)
                        or not isinstance(output_chars, (int, float))
                        or not math.isfinite(float(output_chars))):
                    return omitted("INVALID_PREDICTION", action=action)
                row = [
                    action,
                    round(min(86400.0, max(0.0, float(duration))), 2),
                    int(round(min(1000000.0, max(0.0, float(output_chars))))),
                    round(float(uncertainty), 3),
                    support,
                ]
            else:
                success = prediction.get("predicted_success_probability")
                if (isinstance(success, bool) or not isinstance(success, (int, float))
                        or not math.isfinite(float(success))):
                    return omitted("INVALID_PREDICTION", action=action)
                row = [
                    action, round(min(1.0, max(0.0, float(success))), 3),
                    round(float(uncertainty), 3), support,
                ]
            rows.append(row)
        if not rows:
            return omitted("NO_SUPPORTED_ACTIONS", unsupported_actions=unsupported)

        target = (
            "B1_DURATION_OUTPUT_SIZE" if role == "B1_DETAIL"
            else "B2_P_FINAL_NOT_ANSWER_CORRECTNESS"
        )
        prompt_target = (
            "DURATION+OUTPUT_CHARS" if role == "B1_DETAIL"
            else "P_FINAL_NOT_CORRECTNESS"
        )
        # Keep the foreground view within its 700-character budget. The full
        # target semantics and complete source hashes remain in the stored audit;
        # the prompt gets compact labels and 8-hex source fingerprints only.
        context = {
            "status": "SHADOW_READOUT_ONLY",
            "history_length": history_length,
            "target": prompt_target,
            "checkpoint": checkpoint_sha[:12],
            "history_sources": [value[:8] for value in history_sources],
            "rows": rows,
            "native_body_consumed": False,
            "native_body_weights_changed": False,
            "decision_authority": "NONE",
        }
        # Unsupported-action detail remains in the stored audit. Do not spend
        # the 700-character B1/B2 prompt budget on optional diagnostics.

        episodic = {"status": "UNAVAILABLE", "items": []}
        try:
            episodic = learner.episodic_recall(
                session_id, history_length=history_length, limit=len(actions),
                nonblocking=True, budget_s=0.05, warm_only=True,
            )
        except (BlockingIOError, ValueError, TypeError, KeyError, OSError,
                OverflowError, ArithmeticError, AttributeError):
            episodic = {"status": "UNAVAILABLE", "items": []}
        if (episodic.get("checkpoint_sha256") != checkpoint_sha
                or episodic.get("query_history_action_ids") != history_ids
                or episodic.get("query_history_source_sha256s") != history_sources):
            episodic = {"status": "PROVENANCE_MISMATCH", "items": []}

        episodic_rows = []
        if episodic.get("status") in {"EPISODIC_RECALL_SHADOW", "EPISODIC_RECALL_PARTIAL"}:
            episodic_items = sorted(
                episodic.get("items", []),
                key=lambda item: float(item.get("distance", float("inf"))),
            )[:2]
            for item in episodic_items:
                outcome = item.get("observed_outcome")
                distance = item.get("distance")
                source_sha = item.get("source_sha256")
                if (not isinstance(outcome, dict)
                        or type(distance) not in (int, float)
                        or not math.isfinite(float(distance))
                        or not _valid_sha256(source_sha)
                        or item.get("action") not in actions):
                    continue
                duration = outcome.get("duration_s")
                success = outcome.get("success")
                output_chars = outcome.get("output_characters")
                if (type(duration) not in (int, float) or not math.isfinite(float(duration))
                        or type(success) is not bool
                        or type(output_chars) is not int or output_chars < 0):
                    continue
                episodic_rows.append([
                    item["action"], round(float(distance), 3),
                    round(min(86400.0, max(0.0, float(duration))), 1),
                    success, min(1000000, output_chars), source_sha[:8],
                ])
        episodic_rows = episodic_rows[:2]
        if episodic_rows:
            context["episodic"] = episodic_rows
            context["episodic_note"] = "nearest train episode; observed outcome, not forecast"

        audit = {
            "schema": "V14_TEMPORAL_WORLDJEPA_BODY_RECEIVER_AUDIT/1",
            "status": "READOUT_CREATED",
            "checkpoint_sha256": checkpoint_sha,
            "training_source_sha256": source_sha,
            "history_action_ids": history_ids,
            "history_source_sha256s": history_sources,
            "history_length": history_length,
            "event_id": e.get("event_id"),
            "brain_generation_id": e.get("brain_generation_id"),
            "role": role,
            "action_order": list(actions),
            "supported_action_samples": {
                action: item.get("support_samples")
                for action in actions
                for item in [entries.get(action, {}).get(role)]
                if isinstance(item, dict) and item.get("status") == "SHADOW_READOUT_ONLY"
            },
            "unsupported_actions": unsupported,
            "target_semantics": target,
            "action_horizon": "NEXT_ACTION_AFTER_HISTORY",
            "body_state_created": True,
            "body_prompt_consumed": False,
            "native_body_consumed": False,
            "native_body_weights_changed": False,
            "decision_authority": "NONE",
        }
        audit["episodic_recall"] = {
            "status": episodic.get("status", "UNAVAILABLE"),
            "checkpoint_sha256": episodic.get("checkpoint_sha256"),
            "training_source_sha256": episodic.get("training_source_sha256"),
            "history_length": episodic.get("history_length"),
            "query_history_action_ids": episodic.get("query_history_action_ids", history_ids),
            "query_history_source_sha256s": episodic.get(
                "query_history_source_sha256s", history_sources
            ),
            "candidate_window_count": episodic.get("candidate_window_count", 0),
            "train_window_count_before_cap": episodic.get("train_window_count_before_cap", 0),
            "train_window_count": episodic.get("train_window_count", 0),
            "candidate_cap": episodic.get("candidate_cap", 0),
            "candidate_sampling": episodic.get("candidate_sampling", "UNAVAILABLE"),
            "verified_item_count": episodic.get("verified_item_count", 0),
            "rejected_windows": episodic.get("rejected_windows", 0),
            "train_split_only": episodic.get("train_split_only") is True,
            "heldout_used": episodic.get("heldout_used") is True,
            "source_disjoint_from_query": episodic.get("source_disjoint_from_query") is True,
            "text_disclosed": episodic.get("text_disclosed") is True,
            "budget_exhausted": episodic.get("budget_exhausted", False),
            "items": [
                {
                    "action": item["action"],
                    "distance": item["distance"],
                    "window_id": item["window_id"],
                    "action_id": item["action_id"],
                    "event_id": item["event_id"],
                    "generation_id": item["generation_id"],
                    "target_status": item["target_status"],
                    "source_ref": item["source_ref"],
                    "source_sha256": item["source_sha256"],
                    "window_action_ids": item["window_action_ids"],
                    "window_source_sha256s": item["window_source_sha256s"],
                    "window_source_refs": item["window_source_refs"],
                    "observed_outcome": item["observed_outcome"],
                }
                for item in episodic.get("items", [])
            ],
            "decision_authority": "NONE",
            "native_memory_consumed": False,
            "native_body_consumed": False,
            "native_body_weights_changed": False,
        }
        return context, audit
    except BlockingIOError:
        return omitted("LOCK_BUSY")
    except (ValueError, TypeError, KeyError, OSError, OverflowError,
            ArithmeticError, AttributeError) as exc:
        return omitted("READOUT_ERROR", error_type=type(exc).__name__)

def body_state(r,e,role,text):
    """B5: compact world/self/skill state plus source-bound temporal prediction (STATE_NOT_FACT)."""
    if modes(r.store)['state_source']!='on':return None
    world=r.store.state('WORLD_STATE:'+r.session,{})[0] or {}
    me=r.store.state('SELF_MODEL:'+r.session,{})[0] or {}
    action_mode=world.get('mode','NO_OBSERVATIONS')
    if action_mode=='NO_OBSERVATIONS':action_mode='NO_COMPLETED_OWN_DIGITAL_ACTIONS'
    view={'world':{'scope':'OWN_DIGITAL_ACTION_OUTCOMES_ONLY','mode':action_mode,'observed_actions':world.get('observed_action_count',0),
                   'recent':[{k:x.get(k) for k in ('channel','status','outcome') if k in x} for x in (world.get('recent') or [])[-3:] if isinstance(x,dict)]},
          'self':{'learning':(me.get('learning') or {}).get('mode'),'unfinished_actions':me.get('unfinished_actions'),
                  'external_tools':(me.get('permissions') or {}).get('external_tools'),'system_stage':(me.get('permissions') or {}).get('system_stage')}}
    temporal_context, temporal_audit = _temporal_world_jepa_body_readout(r,e,role)
    if temporal_context is not None:
        view['world_jepa_temporal']=temporal_context
    try:
        from .agi import hub
        view['skills']=hub(r).skills.select(text)[:3]
    except Exception:view['skills']=[]
    def prompt_chars():
        # Count the exact final prompt envelope, not just the inner view.
        return len(dumps(view|{'authority':'STATE_NOT_FACT','role':role}))
    if prompt_chars()>STATE_CHARS:view['world']['recent']=[]
    if prompt_chars()>STATE_CHARS and temporal_context is not None:
        skills=view.get('skills')
        if isinstance(skills,list) and len(skills)>1:view['skills']=skills[:1]
        if prompt_chars()>STATE_CHARS and isinstance(view.get('skills'),list):view['skills']=[]
    if (prompt_chars()>STATE_CHARS and temporal_context is not None
            and isinstance(temporal_context.get("episodic"),list)
            and len(temporal_context["episodic"])>1):
        temporal_context["episodic"]=temporal_context["episodic"][:1]
    if (prompt_chars()>STATE_CHARS and temporal_context is not None
            and "episodic" in temporal_context):
        temporal_context.pop("episodic",None)
        temporal_context.pop("episodic_note",None)
        if isinstance(temporal_audit,dict):
            recall_audit=temporal_audit.get("episodic_recall")
            if isinstance(recall_audit,dict):
                recall_audit["status"]="OMITTED_PROMPT_BUDGET"
                recall_audit["items"]=[]
    if prompt_chars()>STATE_CHARS and temporal_context is not None:
        view.pop('world_jepa_temporal',None)
        temporal_audit=None
    if prompt_chars()>STATE_CHARS and isinstance(view.get('skills'),list):
        view['skills']=[]
    s=dumps(view)
    if temporal_audit is not None:
        s=dumps({
            'schema':'V14_BODY_STATE_WITH_WORLDJEPA_AUDIT/2',
            'view':view,
            'temporal_world_jepa_audit':temporal_audit,
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
