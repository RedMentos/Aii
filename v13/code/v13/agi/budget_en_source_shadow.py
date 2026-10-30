"""Run11Y: bounded Store-source budget arithmetic for JEF, SHADOW without authority.

A deterministic baseline, not semantic language understanding, a model output
repair, permission to act, or a STEP2/Body-JEPA learning result.
"""
from __future__ import annotations

import hashlib
import json
import re

REVISION = "jef-budget-en-source-shadow-run11y-v1"
MODE = "SHADOW_NO_AUTHORITY"
MAX_CHARS = 1024
REF_KEYS = frozenset({"source_id", "sha256", "char_start", "char_end", "modality"})
IDENT = r"[A-Za-z][A-Za-z0-9_-]{0,39}"
NAME = r"[A-Za-z][A-Za-z-]{0,31}"
NUM = r"[1-9][0-9]{0,5}"

# Both grammars are intentionally closed-world. Unsupported paraphrases abstain.
STYLE_ONE = re.compile(
    rf"For (?P<project>{IDENT}), I have a spending ceiling of (?P<budget>{NUM}) Euro\. "
    rf"(?P<a>{NAME}) uses (?P<a_cost>{NUM}) Euro and needs (?P<a_days>{NUM}) days\. "
    rf"(?P<b>{NAME}) uses (?P<b_cost>{NUM}) Euro and needs (?P<b_days>{NUM}) days\. "
    r"Everything stays local on my device; no cloud\. "
    r"How many Euro would remain after each named choice, and which one finishes sooner\?",
    re.ASCII,
)
STYLE_TWO = re.compile(
    rf"Project (?P<project>{IDENT}) has a local budget of (?P<budget>{NUM}) EUR\. "
    rf"Option (?P<a>{NAME}) costs (?P<a_cost>{NUM}) EUR and takes (?P<a_days>{NUM}) days; "
    rf"option (?P<b>{NAME}) costs (?P<b_cost>{NUM}) EUR and takes (?P<b_days>{NUM}) days\. "
    r"Report both remaining budgets and the faster option\.",
    re.ASCII,
)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _ref_digest(ref):
    raw = json.dumps(ref, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return _sha(raw)


def _result(reason, *, candidate=None, source_ref_digest=None):
    return {
        "revision": REVISION,
        "status": MODE,
        "reason": reason,
        "candidate": candidate,
        "source_ref_sha256": source_ref_digest,
        "authority": 0,
        "user_approved": False,
        "model_called": False,
        "native_calls": 0,
        "weight_updates": False,
        "learning_mode": "RECORD_ONLY",
        "jepa_weight": 0,
        "step2_status": "UTILITY_FAIL",
        "b3_status": "NO_PROMOTION",
        "body_jepa_status": "UNAVAILABLE",
        "redmi_measured": False,
        "whole_system_complete": False,
    }


def _full_source(store, ref):
    if (type(ref) is not dict or set(ref) != REF_KEYS
            or type(ref["source_id"]) is not str
            or not ref["source_id"]
            or type(ref["sha256"]) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", ref["sha256"], re.ASCII)
            or type(ref["char_start"]) is not int
            or type(ref["char_end"]) is not int
            or ref["char_start"] != 0
            or not 0 < ref["char_end"] <= MAX_CHARS
            or ref["modality"] != "text"):
        raise ValueError("SOURCE_REF_SHAPE_RED")
    value = store.read_source(ref)
    if (type(value) is not str
            or len(value) != ref["char_end"]
            or len(value.encode("utf-8")) > MAX_CHARS
            or _sha(value.encode("utf-8")) != ref["sha256"]):
        raise ValueError("SOURCE_FULLSPAN_OR_SHA_RED")
    return value


def _parse(value):
    match = STYLE_ONE.fullmatch(value) or STYLE_TWO.fullmatch(value)
    if match is None:
        raise ValueError("SOURCE_GRAMMAR_RED")
    fields = match.groupdict()
    if fields["a"].casefold() == fields["b"].casefold():
        raise ValueError("DUPLICATE_OPTIONS_RED")
    budget, ca, cb, da, db = (
        int(fields[k]) for k in ("budget", "a_cost", "b_cost", "a_days", "b_days")
    )
    if (budget > 999999 or not (0 < ca < budget and 0 < cb < budget)
            or not (0 < da <= 365 and 0 < db <= 365) or da == db):
        raise ValueError("ARITHMETIC_SCOPE_RED")
    return {
        "project": fields["project"],
        "option_a": fields["a"],
        "option_b": fields["b"],
        "remaining_a_eur": budget - ca,
        "remaining_b_eur": budget - cb,
        "faster_option": fields["a"] if da < db else fields["b"],
    }


def propose(store, source_ref):
    """Read-only Store-backed SHADOW proposal; never turn bytes into approval.

    A second Store read narrows, but cannot eliminate, a later revocation race.
    A future consumer MUST revalidate authorization at dispatch.
    """
    try:
        text = _full_source(store, source_ref)
        candidate = _parse(text)
        if _full_source(store, source_ref) != text:
            raise ValueError("SOURCE_CHANGED_DURING_READ")
        return _result("EXACT_SOURCE_ARITHMETIC_SHADOW",
                       candidate=candidate, source_ref_digest=_ref_digest(source_ref))
    except (KeyError, ValueError, TypeError, OSError, UnicodeError,
            AttributeError, OverflowError):
        return _result("SOURCE_INTEGRITY_OR_GRAMMAR_RED")
