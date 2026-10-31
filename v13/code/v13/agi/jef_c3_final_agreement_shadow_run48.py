"""Run48 default-off final C3/JEF source agreement gate, SHADOW only.

No model invocation, Store writes, tool dispatch, live output selection or age authority.
"""
from __future__ import annotations

import hashlib
import json

from .jef_eligibility_source_shadow_run46b import propose

REVISION = "jef-c3-final-agreement-shadow-run48-v1"
MAX_C3_BYTES = 512


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _result(reason, *, matched_digest=None, c3_sha=None):
    return {"revision": REVISION, "status": "SHADOW_NO_AUTHORITY",
            "result": reason, "matched_candidate_sha256": matched_digest,
            "c3_output_sha256": c3_sha, "delivery_authority": 0,
            "live_enabled": False, "user_approved": False,
            "model_called": False, "native_calls": 0,
            "store_writes": 0, "tool_dispatches": 0,
            "weight_updates": False, "age0": "RECORD_ONLY",
            "step2": "UTILITY_FAIL", "b3": "NO_PROMOTION",
            "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
            "world_jepa_authority": "SHADOW",
            "redmi_measured": False, "whole_system_complete": False}


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_JSON")
        out[key] = value
    return out


def _nonfinite(_):
    raise ValueError("NONFINITE")


def _current_event_bound(store, current_ref, current_event_id, session_id):
    if (type(current_ref) is not dict
            or type(current_event_id) is not str or not current_event_id
            or type(session_id) is not str or not session_id):
        return False
    row = store.one(
        "SELECT e.session_id AS session_id, e.source_id AS source_id, "
        "s.kind AS kind, s.deleted AS deleted "
        "FROM events e JOIN sources s ON s.id=e.source_id WHERE e.id=?",
        (current_event_id,))
    return bool(row and row["session_id"] == session_id
                and row["source_id"] == current_ref.get("source_id")
                and row["kind"] == "USER" and row["deleted"] == 0)


def check(store, prior_ref, current_ref, current_event_id, session_id, c3_raw):
    """Return a digest-only SHADOW match; never grant delivery or action authority."""
    if type(c3_raw) is not str:
        return _result("C3_FORMAT_RED")
    try:
        raw = c3_raw.encode("utf-8")
        if not 0 < len(raw) <= MAX_C3_BYTES:
            return _result("C3_FORMAT_RED")
        output_sha = _sha(raw)
    except (UnicodeError, OverflowError):
        return _result("C3_FORMAT_RED")
    try:
        if not _current_event_bound(store, current_ref, current_event_id, session_id):
            return _result("EVENT_BINDING_RED", c3_sha=output_sha)
        jef = propose(store, prior_ref, current_ref)
        if (jef.get("reason") != "EXACT_USER_SOURCE_RECIPE_SHADOW"
                or jef.get("status") != "SHADOW_NO_AUTHORITY"
                or jef.get("authority") != 0
                or jef.get("model_called") is not False
                or jef.get("native_calls") != 0
                or type(jef.get("candidate")) is not dict):
            return _result("SOURCE_OR_JEF_RED", c3_sha=output_sha)
        try:
            obj = json.loads(c3_raw, object_pairs_hook=_unique,
                             parse_constant=_nonfinite)
            if (type(obj) is not dict or set(obj) != {"choice", "remaining"}
                    or type(obj["choice"]) is not str
                    or obj["choice"] not in ("A", "B", "NONE", "UNKNOWN")
                    or (obj["remaining"] is not None
                        and type(obj["remaining"]) is not int)):
                return _result("C3_FORMAT_RED", c3_sha=output_sha)
        except (ValueError, TypeError, OverflowError):
            return _result("C3_FORMAT_RED", c3_sha=output_sha)
        if obj != jef["candidate"]:
            return _result("C3_JEF_DISAGREE", c3_sha=output_sha)
        if (not _current_event_bound(store, current_ref, current_event_id, session_id)
                or propose(store, prior_ref, current_ref) != jef):
            return _result("SOURCE_CHANGED_BEFORE_FINAL", c3_sha=output_sha)
        return _result("MATCHED_NO_AUTHORITY",
                       matched_digest=_sha(_canonical(jef["candidate"])),
                       c3_sha=output_sha)
    except (KeyError, ValueError, TypeError, OSError, UnicodeError,
            AttributeError, OverflowError, IndexError):
        return _result("SOURCE_OR_JEF_RED", c3_sha=output_sha)
