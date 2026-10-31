"""Default-OFF B1/B2 -> C3 exact-source envelope; software SHADOW only.

This is an internal C3 prompt-construction candidate, NOT a model call,
output authorization, source-truth assertion, or Runtime integration.
"""
from __future__ import annotations

import hashlib
import json

from .common import dumps
from .f1f5_event_finalizer_candidate import _event_snapshot
from .b1b2_causal_context_candidate import _project_scope
from .b1b2_topic_partition_candidate import _TopicStateView

ROLES = ("B1_DETAIL", "B2_GIST")


def _result(status, **extra):
    return {"schema": "v13.b1b2_c3_source_envelope_shadow.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False, **extra}


def _latest_authoritative_user(store, session):
    for row in store.rows(
            "SELECT id,packet FROM events WHERE session_id=? ORDER BY rowid DESC",
            (session,)):
        env = json.loads(row["packet"])
        if env.get("authority") == "AUTHORITATIVE" and env.get("kind") == "USER_TEXT":
            return row["id"]
    return None


def build_c3_source_envelope(runtime, event, offer_packet_ids, *,
                             operator_opt_in=False):
    """Read both current-turn persisted offers through frozen Cognition.

    Only the actual current USER source and source-verified quote spans are
    evidence. Body summaries are model hypotheses, not source facts.
    """
    if operator_opt_in is not True:
        return _result("OFF")
    if (type(event) is not dict or type(offer_packet_ids) is not dict
            or set(offer_packet_ids) != set(ROLES)
            or any(type(offer_packet_ids[k]) is not str or not offer_packet_ids[k]
                   for k in ROLES)
            or len(set(offer_packet_ids.values())) != 2):
        return _result("INVALID_EVENT_OR_OFFER_IDS")
    try:
        store = runtime.store
        session = runtime.session
        snapshot = _event_snapshot(runtime.memory, event["event_id"], session)
        if (event.get("source_ref") != snapshot["ref"]
                or event.get("brain_generation_id") != snapshot["generation"]
                or event.get("event_id") is None):
            return _result("CURRENT_USER_SOURCE_RED")
        if _latest_authoritative_user(store, session) != event["event_id"]:
            return _result("STALE_USER_EVENT_RED")
        scope = _project_scope(snapshot["query"])
        if len(scope) != 1:
            return _result("TOPIC_SCOPE_RED")
        topic = next(iter(scope))
        offers = []
        raw = []
        for role in ROLES:
            row = store.one(
                "SELECT event_id,payload FROM packets "
                "WHERE id=? AND kind='OfferPacket'",
                (offer_packet_ids[role],))
            if row is None or row["event_id"] != event["event_id"]:
                return _result("OFFER_PACKET_NOT_CURRENT")
            offer = json.loads(row["payload"])
            if (offer.get("packet_id") != offer_packet_ids[role]
                    or offer.get("role") != role
                    or offer.get("event_id") != event["event_id"]
                    or offer.get("brain_generation_id") != snapshot["generation"]
                    or offer.get("model_revision") != runtime.models.revision(role)):
                return _result("OFFER_ROLE_OR_REVISION_RED")
            view = _TopicStateView(
                store, role, session, snapshot["generation"],
                runtime.models.revision(role), topic)
            retained, _ = view.state(role + ":" + session, {})
            if (type(retained) is not dict
                    or retained.get("packet_id") != offer_packet_ids[role]
                    or {k: v for k, v in retained.items()
                        if k != "retained_offer_ids"} != offer):
                return _result("RETAINED_OFFER_BINDING_RED")
            offers.append(offer)
            raw.append(row["payload"])
        # Frozen analyst_context rechecks stored Offer/Query identity, age,
        # quote SourceRefs, exact source substrings and model revisions.
        rendered = runtime.cognition.analyst_context(offers, event, 0)
        if (len(rendered) != 2 or [x["role"] for x in rendered] != list(ROLES)
                or any(x.get("hypothesis_authority") != "MODEL_HYPOTHESIS_NOT_FACT"
                       or any(q.get("semantic_truth_authority") is not False
                              for q in x["verified_quotes"])
                       for x in rendered)):
            return _result("EVIDENCE_AUTHORITY_RED")
        payload = {
            "schema": "v13.c3_b1b2_source_envelope.v1",
            "evidence_policy": "CURRENT_USER_SOURCE_AND_EXACT_QUOTES_ONLY",
            "current_source": {"text": snapshot["query"],
                               "source_ref": snapshot["ref"]},
            "body_observations": rendered,
            "body_hypotheses_are_facts": False,
        }
        messages = [
            {"role": "system",
             "content": "The current_source is authoritative USER text. "
                        "verified_quotes are exact source spans, not proof of "
                        "semantic truth. Body hypotheses are NOT facts. "
                        "Never invent missing source evidence."},
            {"role": "user", "content": dumps(payload)},
        ]
        # No output follows, but detect any source/packet drift during build.
        if (_event_snapshot(runtime.memory, event["event_id"], session) != snapshot
                or _latest_authoritative_user(store, session) != event["event_id"]):
            return _result("SOURCE_CHANGED_DURING_ENVELOPE")
        for role, before in zip(ROLES, raw):
            row = store.one("SELECT payload FROM packets WHERE id=? AND "
                            "kind='OfferPacket'", (offer_packet_ids[role],))
            if row is None or row["payload"] != before:
                return _result("OFFER_CHANGED_DURING_ENVELOPE")
        digest = hashlib.sha256(dumps(messages).encode("utf-8")).hexdigest()
        return _result("C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL",
                       messages=messages, messages_sha256=digest,
                       offer_packet_ids=dict(offer_packet_ids),
                       verified_quote_count=sum(len(x["verified_quotes"])
                                                for x in rendered),
                       source_ref=snapshot["ref"],
                       prompt_only=True)
    except Exception:
        return _result("SOURCE_OR_OFFER_INTEGRITY_RED")
