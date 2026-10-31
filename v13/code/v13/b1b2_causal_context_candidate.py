"""B1/B2 causal source-context filter candidate for older-event replay/probe.

Not wired into Cognition.offer. The frozen Run52 source/score is untouched.
Uses durable USER message sequence, not unreliable wall timestamps.
"""
from __future__ import annotations
import json


def _bound_user_event(store, event_id, session):
    row = store.one("SELECT id,session_id,source_id,generation_id,packet "
                    "FROM events WHERE id=? AND session_id=?", (event_id, session))
    if not row:
        raise ValueError("EVENT_NOT_IN_SESSION")
    env = json.loads(row["packet"])
    if (type(env) is not dict or env.get("authority") != "AUTHORITATIVE"
            or env.get("kind") != "USER_TEXT" or env.get("event_id") != event_id
            or env.get("brain_generation_id") != row["generation_id"]):
        raise ValueError("NOT_AUTHORITATIVE_USER")
    ref = env.get("source_ref")
    if (type(ref) is not dict or ref.get("source_id") != row["source_id"]
            or ref.get("modality") != "text" or ref.get("char_start") != 0):
        raise ValueError("EVENT_REF_INVALID")
    source = store.one("SELECT kind,deleted,chars FROM sources WHERE id=?",
                       (row["source_id"],))
    if (not source or source["kind"] != "USER" or source["deleted"]
            or ref.get("char_end") != source["chars"]):
        raise ValueError("SOURCE_INVALID")
    text = store.read_source(ref)
    msgs = store.rows("SELECT id,text,status FROM messages WHERE event_id=? AND role='user' "
                      "ORDER BY id LIMIT 2", (event_id,))
    if (len(msgs) != 1 or msgs[0]["status"] != "FINAL"
            or msgs[0]["text"] != text):
        raise ValueError("USER_MESSAGE_BINDING_RED")
    return {"message_id": msgs[0]["id"], "source_ref": ref,
            "generation": row["generation_id"], "text": text}


def causal_body_context(runtime, role, event, *, operator_opt_in=False):
    """Read original B1/B2 context, conservatively filter out future sources.

    This is a software SHADOW candidate only, not an actual native body
    consumer. B4 cross-session is excluded pending separate provenance gates.
    """
    base = {"schema": "v13.b1b2_causal_context_shadow.v1",
            "status": "OFF", "context": [], "delivery_authority": 0,
            "native_calls": 0, "learning_authority": 0}
    if operator_opt_in is not True:
        return base
    if role not in ("B1_DETAIL", "B2_GIST") or type(event) is not dict:
        return dict(base, status="INVALID_ROLE_OR_EVENT")
    store = runtime.store
    try:
        current_id = event["event_id"]
        session = runtime.session
        current = _bound_user_event(store, current_id, session)
        if (event.get("source_ref") != current["source_ref"]
                or event.get("brain_generation_id") != current["generation"]
                or current["generation"] != store.generation_id):
            raise ValueError("CURRENT_EVENT_BINDING_RED")
        original = runtime.cognition.body_context(role, event)
        if type(original) is not list:
            raise ValueError("CONTEXT_TYPE_RED")
        accepted = []
        for item in original:
            try:
                if type(item) is not dict or type(item.get("offer_id")) is not str:
                    continue
                offer_row = store.one("SELECT event_id,payload FROM packets "
                                      "WHERE id=? AND kind='OfferPacket'",
                                      (item["offer_id"],))
                if not offer_row:
                    continue
                offer = json.loads(offer_row["payload"])
                if (offer.get("role") != role
                        or offer.get("brain_generation_id") != current["generation"]
                        or offer.get("model_revision") != runtime.models.revision(role)):
                    continue
                prior_id = offer_row["event_id"]
                if offer.get("event_id") != prior_id or prior_id == current_id:
                    continue
                prior = _bound_user_event(store, prior_id, session)
                if prior["message_id"] >= current["message_id"]:
                    continue
                ref = item.get("source_ref")
                native = item.get("native_context")
                if (type(ref) is not dict or type(native) is not dict
                        or ref.get("source_id") != prior["source_ref"]["source_id"]
                        or ref.get("sha256") != prior["source_ref"]["sha256"]
                        or ref.get("modality") != "text"
                        or ref.get("char_start") != 0
                        or type(ref.get("char_end")) is not int
                        or not 0 < ref["char_end"] <= prior["source_ref"]["char_end"]
                        or store.read_source(ref) != native.get("exact_source_excerpt")):
                    continue
                accepted.append(item)
            except Exception:
                continue
        if _bound_user_event(store, current_id, session) != current:
            raise ValueError("CURRENT_SOURCE_CHANGED")
        return dict(base, status="SHADOW_CONTEXT_FILTERED", context=accepted,
                    filtered_count=len(original)-len(accepted))
    except Exception:
        return dict(base, status="EVENT_OR_CONTEXT_RED")
