"""Default-OFF B1/B2 distinct prior-source offers -> C3 SHADOW envelope.

Four real Cognition.offer Store operations, two role-specific prior USER sources,
one current USER. Source-path separation is not native complementary utility.
"""
from __future__ import annotations

import hashlib
import json
import time

from .b1b2_causal_context_candidate import _bound_user_event, _project_scope
from .b1b2_c3_source_envelope_candidate import (
    build_c3_source_envelope, _latest_authoritative_user)
from .b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from .common import dumps


ROLES = ("B1_DETAIL", "B2_GIST")


def _result(status, **extra):
    return {"schema": "v13.b1b2_disjoint_prior_envelope_shadow.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False, **extra}


def stage_disjoint_prior_envelope(runtime, prior_b1, prior_b2, current, *,
                                  operator_opt_in=False,
                                  approval_receipt=None,
                                  deadline_seconds=120):
    """Opt-in source-separated B1/B2 current offers; never final output."""
    if operator_opt_in is not True:
        return _result("OFF", runner_called=False)
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED", runner_called=False)
    if (any(type(x) is not dict for x in (prior_b1, prior_b2, current))
            or type(deadline_seconds) not in (int, float)
            or not 0 < deadline_seconds <= 180):
        return _result("INVALID_INPUT", runner_called=False)
    try:
        session, store = runtime.session, runtime.store
        inputs = (prior_b1, prior_b2, current)
        ids = [e["event_id"] for e in inputs]
        if len(set(ids)) != 3:
            return _result("DUPLICATE_EVENT_RED", runner_called=False)
        bound = [_bound_user_event(store, eid, session) for eid in ids]
        if any(e.get("source_ref") != b["source_ref"]
               or e.get("brain_generation_id") != b["generation"]
               for e, b in zip(inputs, bound)):
            return _result("EVENT_REF_RED", runner_called=False)
        if (not bound[0]["message_id"] < bound[1]["message_id"]
                < bound[2]["message_id"]
                or _latest_authoritative_user(store, session) != ids[2]):
            return _result("TEMPORAL_OR_STALE_USER_RED", runner_called=False)
        scopes = [_project_scope(b["text"]) for b in bound]
        if any(len(s) != 1 for s in scopes) or not (scopes[0] == scopes[1] == scopes[2]):
            return _result("TOPIC_SCOPE_RED", runner_called=False)
        if (len({b["source_ref"]["source_id"] for b in bound}) != 3
                or bound[0]["source_ref"]["sha256"]
                == bound[1]["source_ref"]["sha256"]
                or bound[0]["text"] == bound[1]["text"]):
            return _result("NOT_DISJOINT_PRIOR_SOURCES_RED", runner_called=False)
        with store.tx():
            existing = store.one(
                "SELECT id FROM packets WHERE kind='OfferPacket' "
                "AND event_id IN (?,?,?) LIMIT 1", tuple(ids))
            if existing is not None:
                return _result("EXISTING_OFFER_RED", runner_called=False)
    except Exception:
        return _result("SOURCE_PREFLIGHT_INTEGRITY_RED", runner_called=False)

    consumer = TopicPartitionOfferConsumer(runtime)
    records = []
    try:
        for role, event in (
            ("B1_DETAIL", prior_b1), ("B2_GIST", prior_b2),
            ("B1_DETAIL", current), ("B2_GIST", current)):
            result = consumer.guarded_offer(
                role, event, 0, time.monotonic()+deadline_seconds,
                operator_opt_in=True)
            if result.get("status") != "SHADOW_OFFER_PRODUCED":
                return _result("ROLE_OFFER_RED", runner_called=True,
                               offer_status=result.get("status"),
                               shadow_packets_may_exist=True)
            records.append((role, event["event_id"], result))
        current_ids = {role: result["offer_packet_id"]
                       for role, eid, result in records if eid == ids[2]}
        context_hashes = {}
        for role, eid, result in records:
            if eid != ids[2]:
                continue
            row = store.one(
                "SELECT payload FROM packets WHERE id=? AND kind='QueryPacket'",
                (result["query_packet_id"],))
            if row is None:
                return _result("CURRENT_QUERY_MISSING_RED", runner_called=True,
                               shadow_packets_may_exist=True)
            query = json.loads(row["payload"])
            refs = query.get("context_source_refs")
            expected = bound[0 if role == "B1_DETAIL" else 1]["source_ref"]
            if (type(refs) is not list or len(refs) != 1
                    or type(refs[0]) is not dict
                    or refs[0].get("source_id") != expected["source_id"]
                    or refs[0].get("char_start") != 0
                    or type(refs[0].get("char_end")) is not int
                    or not 0 < refs[0]["char_end"] <= expected["char_end"]
                    or not bound[0 if role == "B1_DETAIL" else 1]["text"].startswith(
                        store.read_source(refs[0]))):
                return _result("ROLE_CONTEXT_SOURCE_RED", runner_called=True,
                               shadow_packets_may_exist=True)
            context_hashes[role] = hashlib.sha256(
                dumps(refs[0]).encode("utf-8")).hexdigest()
        envelope = build_c3_source_envelope(
            runtime, current, current_ids, operator_opt_in=True)
        if envelope.get("status") != "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL":
            return _result("C3_SOURCE_ENVELOPE_RED", runner_called=True,
                           envelope_status=envelope.get("status"),
                           shadow_packets_may_exist=True)
        if (_latest_authoritative_user(store, session) != ids[2]
                or [_bound_user_event(store, eid, session) for eid in ids] != bound):
            return _result("SOURCE_CHANGED_AFTER_ENVELOPE", runner_called=True,
                           shadow_packets_may_exist=True)
        return _result(
            "DISJOINT_PRIOR_C3_ENVELOPE_SHADOW_NO_MODEL_CALL",
            runner_called=True, body_offer_count=4,
            prior_source_ids={"B1_DETAIL": bound[0]["source_ref"]["source_id"],
                              "B2_GIST": bound[1]["source_ref"]["source_id"]},
            role_context_ref_sha256=context_hashes,
            current_offer_packet_ids=current_ids,
            messages=envelope["messages"],
            messages_sha256=envelope["messages_sha256"],
            source_rechecked=True, prompt_only=True)
    except Exception:
        return _result("ROLE_OR_SOURCE_INTEGRITY_RED", runner_called=True,
                       shadow_packets_may_exist=bool(records))
