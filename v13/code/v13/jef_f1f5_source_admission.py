"""Read-only session-bound F1/F5 admission before JEF typed source SHADOW.

F1/F5 source lineage permits reading evidence, never grants live output or
training authority. No Store writes, model calls, or Runtime wiring.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3

from . import jef_typed_source_shadow as typed

REVISION = "jef-f1f5-source-admission-shadow-v1"


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _deny(reason):
    return {
        **typed._result("UNKNOWN", reason),
        "admission_revision": REVISION,
        "admission_status": "F1F5_DENIED_SHADOW",
        "human_source_lineage_verified": False,
        "memory_id_hashes": [],
    }


def decide(memory, session, event_id, current_ref, memory_ids):
    """Verify authoritative current event and two active human F1/F5 fact memories."""
    try:
        store = memory.s
        if (type(session) is not str or type(event_id) is not str
                or type(memory_ids) not in (tuple, list)
                or len(memory_ids) != 2
                or any(type(mid) is not str or not mid for mid in memory_ids)
                or memory_ids[0] == memory_ids[1]):
            return _deny("F1F5_INPUT_SHAPE_RED")
        event = store.one(
            "SELECT session_id,source_id,packet FROM events WHERE id=? AND session_id=?",
            (event_id, session))
        if event is None:
            return _deny("F1F5_CURRENT_EVENT_SCOPE_RED")
        envelope = json.loads(event["packet"])
        if (type(envelope) is not dict
                or envelope.get("event_id") != event_id
                or envelope.get("authority") != "AUTHORITATIVE"
                or envelope.get("kind") != "USER_TEXT"
                or envelope.get("source_ref") != current_ref
                or type(envelope.get("provenance")) is not list
                or current_ref not in envelope["provenance"]
                or event["source_id"] != current_ref.get("source_id")):
            return _deny("F1F5_CURRENT_AUTHORITY_RED")
        current = typed._read_full(store, current_ref)
        request = typed.CURRENT.fullmatch(current)
        if request is None:
            return _deny("F1F5_CURRENT_GRAMMAR_RED")
        project, domain = request["id"], request["domain"]
        keys = {
            "policy": f"Project {project} archived {domain} policy",
            "sheet": f"Project {project} latest {domain} option sheet",
        }
        expected = set(keys.values())
        rows = {}
        for mid in memory_ids:
            # Memory.candidate may lazily create a key SourceRef; reject that
            # prerequisite here to keep admission itself strictly read-only.
            keyref, _ = store.state("memory-key:" + mid, None)
            if keyref is None:
                return _deny("F1F5_KEY_PROVENANCE_NOT_MATERIALIZED")
            row = memory.candidate(mid, session)
            if (row["kind"] != "fact" or row["scope"] != "session"
                    or row["session_id"] != session
                    or row["key_text"] not in expected
                    or row["key_text"] in rows
                    or row["key_ref"] != keyref
                    or store.read_source(keyref) != row["key_text"]
                    or store.read_source(row["source_ref"]) != row["value"]):
                return _deny("F1F5_MEMORY_SCOPE_TOPIC_RED")
            verified = memory._verified_rows([row])
            if len(verified) != 1 or verified[0]["id"] != mid:
                return _deny("F1F5_HUMAN_DECISION_LINEAGE_RED")
            feedback = store.one(
                "SELECT permission FROM feedback WHERE source_id=?",
                (row["source_id"],))
            if feedback is None or feedback["permission"] != "record":
                return _deny("F1F5_RECORD_PERMISSION_RED")
            rows[row["key_text"]] = row
        if set(rows) != expected:
            return _deny("F1F5_MISSING_SIDE_RED")
        # Conflict veto: a global or second active same-topic memory cannot be
        # hidden by passing only two convenient IDs.
        for key in expected:
            active = store.rows(
                "SELECT id FROM memories WHERE active=1 AND kind='fact' "
                "AND key_text=? AND (session_id=? OR scope='global')",
                (key, session))
            if len(active) != 1 or active[0]["id"] not in memory_ids:
                return _deny("F1F5_CONFLICT_OR_HIDDEN_SOURCE_RED")
        refs = [rows[keys["policy"]]["source_ref"],
                rows[keys["sheet"]]["source_ref"]]
        decision = typed.decide(store, current_ref, refs)
        if decision["reason"] != "FULL_SOURCE_TYPED_DECISION":
            return _deny("F1F5_TYPED_DECISION_RED")
        return {
            **decision, "admission_revision": REVISION,
            "admission_status": "F1F5_SESSION_VERIFIED_SHADOW",
            "human_source_lineage_verified": True,
            "memory_id_hashes": [_sha(mid) for mid in memory_ids],
        }
    except (ValueError, TypeError, KeyError, AttributeError,
            OSError, UnicodeError, OverflowError, json.JSONDecodeError,
            sqlite3.Error):
        return _deny("F1F5_SOURCE_OR_LINEAGE_RED")
