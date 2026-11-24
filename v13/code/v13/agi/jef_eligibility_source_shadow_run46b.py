"""Run46B: bounded non-generative JEF source-verified eligibility SHADOW.

No live consumer, model inference, Store write, tool dispatch or age authority.
The caller supplies two user-event SourceRefs from the same session.
"""
from __future__ import annotations

import hashlib
import json
import re

from .eligibility import recipe

REVISION = "jef-eligibility-source-shadow-run46b-v1"
MODE = "SHADOW_NO_AUTHORITY"
MAX_CHARS = 2048
REF_KEYS = frozenset(("source_id", "sha256", "char_start", "char_end", "modality"))
ID = r"[A-Za-z][A-Za-z0-9_-]{0,39}"
POS = r"[1-9][0-9]{0,5}"

PRIOR_ONE = re.compile(
    rf"Project (?P<id>{ID})\. "
    rf"(?:Budget (?P<budget>{POS}) euros\.|No budget has been supplied\.) "
    rf"Deadline (?P<deadline>{POS}) days\. "
    r"Local-only requirement: (?P<local>true|false)\. "
    r"These are the binding project rules\.", re.ASCII,
)
PRIOR_TWO = re.compile(
    rf"Project (?P<id>{ID})\. Spending limit: (?P<budget>{POS}) euros\. "
    rf"Finish within (?P<deadline>{POS}) days\. "
    r"Must remain local: (?P<local>yes|no)\. This policy is binding\.",
    re.ASCII,
)
CURRENT_ONE = re.compile(
    rf"Project (?P<id>{ID})\. Apply the earlier project rules\. "
    rf"Option A costs (?P<ac>{POS}) euros, takes (?P<ad>{POS}) days, and is (?P<al>not local|local)\. "
    rf"Option B costs (?P<bc>{POS}) euros, takes (?P<bd>{POS}) days, and is (?P<bl>not local|local)\. "
    r"Choose the cheapest eligible option and state its remaining budget\.",
    re.ASCII,
)
CURRENT_TWO = re.compile(
    rf"Project (?P<id>{ID})\. Decide using the saved policy\. "
    rf"Option A: cost (?P<ac>{POS}) euros, duration (?P<ad>{POS}) days, local (?P<al>true|false)\. "
    rf"Option B: cost (?P<bc>{POS}) euros, duration (?P<bd>{POS}) days, local (?P<bl>true|false)\. "
    r"Pick the cheapest eligible option and give remaining euros\.",
    re.ASCII,
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(ref):
    return _sha(json.dumps(ref, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False).encode("utf-8"))


def _result(reason, *, candidate=None, refs=()):
    return {"revision": REVISION, "status": MODE, "reason": reason,
            "candidate": candidate,
            "source_ref_sha256": [_digest(r) for r in refs],
            "authority": 0, "user_approved": False,
            "model_called": False, "native_calls": 0, "store_writes": 0,
            "tool_dispatches": 0, "weight_updates": False,
            "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "world_jepa_authority": "SHADOW",
            "redmi_measured": False, "whole_system_complete": False}


def _read_full_user_event(store, ref):
    if (type(ref) is not dict or set(ref) != REF_KEYS
            or type(ref["source_id"]) is not str or not ref["source_id"]
            or type(ref["sha256"]) is not str
            or re.fullmatch("[0-9a-f]{64}", ref["sha256"], re.ASCII) is None
            or type(ref["char_start"]) is not int or ref["char_start"] != 0
            or type(ref["char_end"]) is not int
            or not 0 < ref["char_end"] <= MAX_CHARS
            or ref["modality"] != "text"):
        raise ValueError("SOURCE_REF_SHAPE_RED")
    row = store.one(
        "SELECT e.session_id AS session_id, s.kind AS kind FROM events e "
        "JOIN sources s ON s.id=e.source_id WHERE e.source_id=?",
        (ref["source_id"],))
    if not row or row["kind"] != "USER":
        raise ValueError("USER_EVENT_REQUIRED")
    text = store.read_source(ref)
    if (type(text) is not str or len(text) != ref["char_end"]
            or len(text.encode("utf-8")) > MAX_CHARS
            or _sha(text.encode("utf-8")) != ref["sha256"]):
        raise ValueError("SOURCE_FULLSPAN_OR_SHA_RED")
    return text, row["session_id"]


def _prior(text):
    match = PRIOR_ONE.fullmatch(text)
    if match is not None:
        d = match.groupdict()
        return {"id": d["id"], "budget": int(d["budget"]) if d["budget"] else None,
                "deadline": int(d["deadline"]), "local_only": d["local"] == "true"}
    match = PRIOR_TWO.fullmatch(text)
    if match is not None:
        d = match.groupdict()
        return {"id": d["id"], "budget": int(d["budget"]),
                "deadline": int(d["deadline"]), "local_only": d["local"] == "yes"}
    raise ValueError("PRIOR_GRAMMAR_RED")


def _current(text):
    match = CURRENT_ONE.fullmatch(text)
    style = 1
    if match is None:
        match = CURRENT_TWO.fullmatch(text)
        style = 2
    if match is None:
        raise ValueError("CURRENT_GRAMMAR_RED")
    d = match.groupdict()
    def local(v):
        return (v == "local") if style == 1 else (v == "true")
    options = [
        {"entity": "A", "cost": int(d["ac"]), "days": int(d["ad"]), "local": local(d["al"])},
        {"entity": "B", "cost": int(d["bc"]), "days": int(d["bd"]), "local": local(d["bl"])},
    ]
    return d["id"], options


def propose(store, prior_ref, current_ref):
    """Source-bound candidate only. Does not authorize use or verify user consent."""
    try:
        if prior_ref == current_ref:
            raise ValueError("SAME_SOURCE_REF_RED")
        prior_text, prior_session = _read_full_user_event(store, prior_ref)
        current_text, current_session = _read_full_user_event(store, current_ref)
        if prior_session != current_session:
            raise ValueError("FOREIGN_SESSION_RED")
        policy = _prior(prior_text)
        project, options = _current(current_text)
        if policy["id"] != project:
            raise ValueError("PROJECT_MISMATCH_RED")
        action, evaluated = recipe(policy["budget"], policy["deadline"],
                                   policy["local_only"], options)
        remaining = next((o["remaining"] for o in evaluated
                          if o["entity"] == action), None)
        if (_read_full_user_event(store, prior_ref) != (prior_text, prior_session)
                or _read_full_user_event(store, current_ref) != (current_text, current_session)):
            raise ValueError("SOURCE_CHANGED_DURING_READ")
        return _result("EXACT_USER_SOURCE_RECIPE_SHADOW",
                       candidate={"choice": action, "remaining": remaining},
                       refs=(prior_ref, current_ref))
    except (KeyError, ValueError, TypeError, OSError, UnicodeError,
            AttributeError, OverflowError, IndexError):
        return _result("SOURCE_INTEGRITY_OR_GRAMMAR_RED")
