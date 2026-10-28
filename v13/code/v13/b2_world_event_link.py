"""Run73: read-only, source-exact B2 OfferPacket ↔ committed WorldTransition link.

A structural cross-organ *SHADOW* data path. No model/Store construction,
writes, native inference, learning, output, routing or external-world claim.
"""
from __future__ import annotations

import hashlib
import json
import math

REVISION = "run73-b2-world-source-link-v1"
ROLES = frozenset(("SOURCE_COPY", "C3_LANGUAGE", "B1_DETAIL", "B2_GIST"))
MAX_PACKETS = 32


def _base(status):
    return {"revision": REVISION, "status": status, "source_ref": None,
            "outcome_source_ref": None, "b2_offer_packet_id": None,
            "world_transition_packet_id": None, "action_id": None,
            "action_role": None, "authority": "SHADOW_NO_AUTHORITY",
            "b2_hypothesis_is_truth": False, "semantic_coupling_proven": False,
            "native_executed": False, "phone_measured": False,
            "jepa_weight": 0, "canonical_gate_pass": False,
            "whole_system_complete": False}


def _ref(v):
    return (type(v) is dict and type(v.get("source_id")) is str
            and bool(v["source_id"]) and type(v.get("sha256")) is str
            and len(v["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in v["sha256"])
            and type(v.get("char_start")) is int
            and type(v.get("char_end")) is int
            and 0 <= v["char_start"] <= v["char_end"]
            and v.get("modality") == "text")


def _json(v):
    if type(v) is not str:
        raise ValueError("INVALID_JSON")
    obj = json.loads(v)
    if type(obj) is not dict:
        raise ValueError("INVALID_OBJECT")
    return obj


def _rows(store, kind, event_id, limit):
    rows = store.rows(
        "SELECT id,payload,created FROM packets WHERE kind=? AND event_id=? "
        "ORDER BY created DESC LIMIT ?", (kind, event_id, limit + 1))
    if type(rows) is not list or len(rows) > limit:
        raise ValueError("UNBOUNDED_PACKETS")
    return rows


def link(store, event_id, session_id, generation_id, b2_model_revision,
         *, scan_limit=MAX_PACKETS):
    """Return at most one source-bound digital event link, or abstain.

    Caller must own an authorized already-open Store; never open a real Store
    implicitly. Both SourceRefs are revalidated immediately before returning.
    """
    if (any(type(v) is not str or not 1 <= len(v) <= 128
            for v in (event_id, session_id, generation_id, b2_model_revision))
            or type(scan_limit) is not int or not 1 <= scan_limit <= MAX_PACKETS):
        raise ValueError("RUN73_INVALID_SCOPE")
    out = _base("ABSTAIN_NO_EXACT_EVENT")
    row = store.one(
        "SELECT id,session_id,generation_id,source_id,packet,created "
        "FROM events WHERE id=? AND session_id=?", (event_id, session_id))
    if not row:
        return out
    try:
        env = _json(row["packet"])
        ref = env.get("source_ref")
        if (row["id"] != event_id or row["session_id"] != session_id
                or row["generation_id"] != generation_id
                or env.get("event_id") != event_id
                or env.get("brain_generation_id") != generation_id
                or env.get("authority") != "AUTHORITATIVE"
                or not _ref(ref) or row["source_id"] != ref["source_id"]):
            return _base("ABSTAIN_EVENT_SCOPE_OR_SOURCE")
        current = store.read_source(ref)
        if type(current) is not str:
            return _base("ABSTAIN_EVENT_SCOPE_OR_SOURCE")
        offers = _rows(store, "OfferPacket", event_id, scan_limit)
        worlds = _rows(store, "WorldTransition", event_id, scan_limit)
        # Both B1_DETAIL and B2_GIST normally offer on the same Age0 turn.
        # Only B2 is the target organ; unrelated B1 offers are not ambiguous.
        parsed = [(candidate, _json(candidate["payload"])) for candidate in offers]
        b2 = [(candidate, packet) for candidate, packet in parsed
              if packet.get("role") == "B2_GIST"]
        if len(b2) != 1 or len(worlds) != 1:
            return _base("ABSTAIN_MISSING_OR_AMBIGUOUS_PACKET")
        offer_row, offer = b2[0]
        world_row = worlds[0]
        world = _json(world_row["payload"])
        outcome_ref = world.get("outcome_source_ref")
        if (offer_row["id"] != offer.get("packet_id")
                or offer.get("event_id") != event_id
                or offer.get("brain_generation_id") != generation_id
                or offer.get("role") != "B2_GIST"
                or offer.get("model_revision") != b2_model_revision
                or type(offer.get("provenance")) is not list
                or ref not in offer["provenance"]
                or world_row["id"] != world.get("packet_id")
                or world.get("event_id") != event_id
                or world.get("brain_generation_id") != generation_id
                or world.get("source_ref") != ref
                or not _ref(outcome_ref)
                or type(world.get("provenance")) is not list
                or ref not in world["provenance"]
                or outcome_ref not in world["provenance"]
                or world.get("teacher_truth_authority") is not False
                or world.get("external_world_observation") is not False
                or world.get("semantic_success", "INVALID") is not None
                or world.get("action_role") not in ROLES
                or type(world.get("action_id")) is not str):
            return _base("ABSTAIN_PACKET_PROVENANCE")
        times = (row["created"], offer_row["created"], world_row["created"])
        if (any(type(t) not in (int, float) or not math.isfinite(t) for t in times)
                or not times[0] <= times[1] <= times[2]):
            return _base("ABSTAIN_EVENT_ORDER")
        aid = world["action_id"]
        action = store.one(
            "SELECT id,event_id,status,outcome,expected,kind,corollary_id "
            "FROM actions WHERE id=? AND event_id=?", (aid, event_id))
        if not action or action["status"] != "FINAL":
            return _base("ABSTAIN_UNCOMMITTED_ACTION")
        actual, expected = _json(action["outcome"]), _json(action["expected"])
        role = world["action_role"]
        forecast = expected.get("forecast")
        if (action["id"] != aid or action["event_id"] != event_id
                or actual.get("role") != role
                or type(forecast) is not dict
                or type(forecast.get("profile")) is not dict
                or forecast["profile"].get("role") != role
                or action["corollary_id"] != world.get("corollary_packet_id")):
            return _base("ABSTAIN_ACTION_BINDING")
        corollary_row = store.one(
            "SELECT id,payload FROM packets WHERE id=? AND kind='CorollaryCopy'",
            (action["corollary_id"],))
        if not corollary_row:
            return _base("ABSTAIN_COROLLARY")
        copy = _json(corollary_row["payload"])
        if (copy.get("packet_id") != corollary_row["id"]
                or copy.get("event_id") != event_id
                or copy.get("brain_generation_id") != generation_id
                or copy.get("action_id") != aid
                or copy.get("self_caused") is not True
                or copy.get("expected") != expected):
            return _base("ABSTAIN_COROLLARY")
        intents = _rows(store, "ActionIntent", event_id, scan_limit)
        matched = []
        for candidate in intents:
            intent = _json(candidate["payload"])
            if intent.get("action_id") == aid:
                matched.append(intent)
        if (len(matched) != 1 or matched[0].get("event_id") != event_id
                or matched[0].get("brain_generation_id") != generation_id
                or matched[0].get("permission") != "local_text_only"
                or matched[0].get("action_type") != action["kind"]):
            return _base("ABSTAIN_ACTION_INTENT")
        messages = store.rows(
            "SELECT text FROM messages WHERE event_id=? AND role='assistant' "
            "AND status='FINAL' ORDER BY id DESC LIMIT 2", (event_id,))
        if type(messages) is not list or len(messages) != 1:
            return _base("ABSTAIN_FINAL_MESSAGE")
        own = messages[0]["text"]
        if (type(own) is not str
                or hashlib.sha256(own.encode()).hexdigest()
                   != actual.get("self_candidate_hash")):
            return _base("ABSTAIN_OUTCOME_MISMATCH")
        outcome = store.read_source(outcome_ref)
        if type(outcome) is not str or outcome != own:
            return _base("ABSTAIN_OUTCOME_MISMATCH")
        if store.read_source(ref) != current or store.read_source(outcome_ref) != own:
            return _base("ABSTAIN_SOURCE_CHANGED")
    except (ValueError, TypeError, KeyError, OverflowError, OSError):
        return _base("ABSTAIN_CORRUPT_OR_REVOKED_SOURCE")
    return {**_base("SHADOW_SOURCE_BOUND_DIGITAL_LINK"),
            "source_ref": dict(ref), "outcome_source_ref": dict(outcome_ref),
            "b2_offer_packet_id": offer["packet_id"],
            "world_transition_packet_id": world["packet_id"],
            "action_id": aid, "action_role": role}
