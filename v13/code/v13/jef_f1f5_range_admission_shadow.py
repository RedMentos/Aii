"""Run74 default-OFF human F1/F5 admission for deterministic mixed-range JEF.

Source-authenticated SHADOW proposal only. Record permission is not output,
tool, training, TTY or Age approval. Does not change the frozen max-only reader.
"""
from __future__ import annotations

import hashlib
import json

from . import jef_range_policy_shadow as range_fixed
from . import jef_typed_source_shadow as fixed
from .jef_f1f5_live_current_candidate import _latest_authoritative_user

REVISION = "jef-f1f5-mixed-range-admission-run74-v1"
READY = "F1F5_RANGE_SESSION_VERIFIED_SHADOW"


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _deny(reason):
    return {
        **range_fixed._result("UNKNOWN", reason),
        "admission_revision": REVISION,
        "admission_status": "F1F5_RANGE_DENIED_SHADOW",
        "human_source_lineage_verified": False,
        "memory_id_hashes": [],
    }


def decide(memory, session, event_id, current_ref, memory_ids, *,
           operator_opt_in=False, approval_receipt=None):
    """Require two independently verified human records and latest USER source.

    Source-only result; the final C5/C6 commit would need its own atomic
    recheck and explicit real-TTY approval, which this module cannot grant.
    """
    if operator_opt_in is not True:
        return _deny("OFF")
    if approval_receipt is not None:
        return _deny("REAL_TTY_APPROVAL_UNSUPPORTED")
    try:
        store = memory.s
        if (type(session) is not str or type(event_id) is not str
                or type(current_ref) is not dict
                or type(memory_ids) not in (tuple, list)
                or len(memory_ids) != 2
                or any(type(mid) is not str or not mid for mid in memory_ids)
                or memory_ids[0] == memory_ids[1]):
            return _deny("F1F5_RANGE_INPUT_SHAPE_RED")
        event = store.one(
            "SELECT session_id,source_id,generation_id,packet "
            "FROM events WHERE id=? AND session_id=?",
            (event_id, session))
        if event is None or event["generation_id"] != store.generation_id:
            return _deny("F1F5_RANGE_EVENT_SCOPE_RED")
        envelope = json.loads(event["packet"])
        if (type(envelope) is not dict
                or envelope.get("event_id") != event_id
                or envelope.get("authority") != "AUTHORITATIVE"
                or envelope.get("kind") != "USER_TEXT"
                or envelope.get("source_ref") != current_ref
                or type(envelope.get("provenance")) is not list
                or current_ref not in envelope["provenance"]
                or event["source_id"] != current_ref.get("source_id")
                or _latest_authoritative_user(store, session) != event_id):
            return _deny("F1F5_RANGE_CURRENT_AUTHORITY_RED")
        current = fixed._read_full(store, current_ref)
        request = fixed.CURRENT.fullmatch(current)
        if request is None:
            return _deny("F1F5_RANGE_CURRENT_GRAMMAR_RED")
        project, domain = request["id"], request["domain"]
        keys = {
            "policy": f"Project {project} archived {domain} policy",
            "sheet": f"Project {project} latest {domain} option sheet",
        }
        expected = set(keys.values())
        rows = {}
        for mid in memory_ids:
            keyref, _ = store.state("memory-key:" + mid, None)
            if keyref is None:
                return _deny("F1F5_RANGE_KEY_NOT_MATERIALIZED")
            row = memory.candidate(mid, session)
            if (row["kind"] != "fact" or row["scope"] != "session"
                    or row["session_id"] != session
                    or row["key_text"] not in expected
                    or row["key_text"] in rows
                    or row["key_ref"] != keyref
                    or store.read_source(keyref) != row["key_text"]
                    or store.read_source(row["source_ref"]) != row["value"]):
                return _deny("F1F5_RANGE_MEMORY_SCOPE_RED")
            verified = memory._verified_rows([row])
            if len(verified) != 1 or verified[0]["id"] != mid:
                return _deny("F1F5_RANGE_HUMAN_LINEAGE_RED")
            feedback = store.one(
                "SELECT permission FROM feedback WHERE source_id=?",
                (row["source_id"],))
            if feedback is None or feedback["permission"] != "record":
                return _deny("F1F5_RANGE_RECORD_PERMISSION_RED")
            rows[row["key_text"]] = row
        if set(rows) != expected:
            return _deny("F1F5_RANGE_MISSING_SIDE_RED")
        for key in expected:
            active = store.rows(
                "SELECT id FROM memories WHERE active=1 AND kind='fact' "
                "AND key_text=? AND (session_id=? OR scope='global')",
                (key, session))
            if len(active) != 1 or active[0]["id"] not in memory_ids:
                return _deny("F1F5_RANGE_CONFLICT_OR_HIDDEN_SOURCE_RED")
        refs = [rows[keys["policy"]]["source_ref"],
                rows[keys["sheet"]]["source_ref"]]
        decision = range_fixed.decide(
            store, current_ref, refs, operator_opt_in=True)
        if decision["reason"] != "FULL_SOURCE_FIXED_RANGE_DECISION":
            return _deny("F1F5_RANGE_FIXED_DECISION_RED")
        if _latest_authoritative_user(store, session) != event_id:
            return _deny("F1F5_RANGE_STALE_USER_RED")
        return {
            **decision, "admission_revision": REVISION,
            "admission_status": READY,
            "human_source_lineage_verified": True,
            "memory_id_hashes": [_sha(mid) for mid in memory_ids],
        }
    except (ValueError, TypeError, KeyError, AttributeError,
            OSError, UnicodeError, OverflowError, json.JSONDecodeError):
        return _deny("F1F5_RANGE_SOURCE_OR_LINEAGE_RED")
