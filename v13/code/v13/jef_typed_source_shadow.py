"""Default-off JEF typed Store SourceRef decision candidate; SHADOW, no output authority.

Only bounded exact two-source option tasks. Store.read_source proves integrity,
NOT human authorization. This module never mutates Store or invokes a model.
"""
from __future__ import annotations
import hashlib
import json
import re

REVISION = "jef-typed-source-shadow-v1"
MODE = "SHADOW_NO_AUTHORITY"
MAX_CHARS = 2048
ID = r"[A-Za-z][A-Za-z0-9_-]{0,39}"
LABEL = r"[A-Za-z][A-Za-z -]{0,39}"
UNIT = r"[A-Za-z]{1,20}"
NUM = r"(?:0|[1-9][0-9]{0,8})"
CURRENT = re.compile(
    rf"Project (?P<id>{ID})\. Choose Option A or Option B using the "
    rf"archived (?P<domain>{LABEL}) policy and latest option sheet\. "
    r"If neither qualifies, choose NONE\.", re.ASCII)
POLICY = re.compile(
    rf"Project (?P<id>{ID}) archived (?P<domain>{LABEL}) policy\. "
    rf"Maximum (?P<f1>{LABEL}): (?P<m1>{NUM}) (?P<u1>{UNIT})\. "
    rf"Maximum (?P<f2>{LABEL}): (?P<m2>{NUM}) (?P<u2>{UNIT})\. "
    rf"Required (?P<flag>{LABEL}): (?P<required>true|false)\.", re.ASCII)
SHEET = re.compile(
    rf"Project (?P<id>{ID}) latest (?P<domain>{LABEL}) option sheet\. "
    r"Option A: (?P<a>[^.]{1,300})\. Option B: (?P<b>[^.]{1,300})\.",
    re.ASCII)
REF_KEYS = frozenset({"source_id", "sha256", "char_start", "char_end", "modality"})


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _read_full(store, ref):
    if (type(ref) is not dict or set(ref) != REF_KEYS
            or type(ref["source_id"]) is not str
            or type(ref["sha256"]) is not str
            or type(ref["char_start"]) is not int
            or type(ref["char_end"]) is not int
            or ref["char_start"] != 0
            or ref["modality"] != "text"):
        raise ValueError("SOURCE_REF_SHAPE_RED")
    text = store.read_source(ref)
    if (type(text) is not str or len(text) > MAX_CHARS
            or len(text) != ref["char_end"]
            or _sha(text.encode("utf-8")) != ref["sha256"]):
        raise ValueError("SOURCE_FULLSPAN_OR_SHA_RED")
    return text


def _option(text, policy):
    parts = text.split("; ")
    if len(parts) != 3:
        raise ValueError("OPTION_CLAUSE_COUNT_RED")
    values = []
    for i in (1, 2):
        field, unit = policy["f" + str(i)], policy["u" + str(i)]
        match = re.fullmatch(re.escape(field) + rf" ({NUM}) " + re.escape(unit),
                             parts[i - 1], re.ASCII)
        if match is None:
            raise ValueError("OPTION_FIELD_UNIT_RED")
        values.append(int(match.group(1)))
    flag = re.fullmatch(re.escape(policy["flag"]) + r" (true|false)",
                        parts[2], re.ASCII)
    if flag is None:
        raise ValueError("OPTION_FLAG_RED")
    return values[0], values[1], flag.group(1) == "true"


def _result(action, reason, refs=()):
    return {
        "revision": REVISION, "status": MODE,
        "suggested_action": action, "reason": reason,
        "source_ref_sha256": [_sha(_canonical(r)) for r in refs],
        "authority": 0, "user_approved": False,
        "model_called": False, "native_calls": 0,
        "weight_updates": False, "jepa_weight": 0,
        "step2_status": "UTILITY_FAIL", "b3_status": "FAIL",
        "body_jepa_status": "UNAVAILABLE", "lp3_status": "FAIL",
        "ag6_approved": False, "redmi_measured": False,
        "whole_system_complete": False,
    }


def decide(store, current_ref, source_refs):
    """Pure SHADOW proposal from two complete Store-verified source texts.

    Never call on model-generated material as if it were F1/F5 authorization.
    This function does not establish that the Store sources are human-approved.
    """
    try:
        current = _read_full(store, current_ref)
        req = CURRENT.fullmatch(current)
        if req is None:
            return _result("UNKNOWN", "CURRENT_GRAMMAR_RED")
        if type(source_refs) not in (tuple, list) or len(source_refs) != 2:
            return _result("UNKNOWN", "EXACT_TWO_SOURCES_REQUIRED")
        if _canonical(source_refs[0]) == _canonical(source_refs[1]):
            return _result("UNKNOWN", "DUPLICATE_SOURCE_REF_RED")
        texts = [_read_full(store, r) for r in source_refs]
        policies = [POLICY.fullmatch(t) for t in texts]
        sheets = [SHEET.fullmatch(t) for t in texts]
        if sum(m is not None for m in policies) != 1 or sum(
                m is not None for m in sheets) != 1:
            return _result("UNKNOWN", "POLICY_SHEET_SHAPE_RED")
        policy = next(m.groupdict() for m in policies if m is not None)
        sheet = next(m.groupdict() for m in sheets if m is not None)
        if (policy["id"] != req["id"] or sheet["id"] != req["id"]
                or policy["domain"] != req["domain"]
                or sheet["domain"] != req["domain"]):
            return _result("UNKNOWN", "PROJECT_DOMAIN_MISMATCH_RED")
        if (policy["f1"] == policy["f2"]
                or policy["flag"] in (policy["f1"], policy["f2"])
                or policy["u1"] == policy["u2"] and policy["f1"] == policy["f2"]):
            return _result("UNKNOWN", "AMBIGUOUS_FIELD_RED")
        options = [_option(sheet[k], policy) for k in ("a", "b")]
        max1, max2 = int(policy["m1"]), int(policy["m2"])
        required = policy["required"] == "true"
        eligible = [(opt[0], opt[1], name) for opt, name in zip(options, "AB")
                    if opt[0] <= max1 and opt[1] <= max2
                    and (not required or opt[2])]
        action = min(eligible)[2] if eligible else "NONE"
        # The existing exact SourceRefs already contain the two signed
        # differences. Expose them only for complete grammar + integrity,
        # never as learned utility, model authority, or an approved answer.
        details = {}
        for name, opt in zip("AB", options):
            remaining = [max1 - opt[0], max2 - opt[1]]
            details[name] = {
                "used": [opt[0], opt[1]], "remaining": remaining,
                "flag": opt[2],
                "eligible": all(x >= 0 for x in remaining)
                            and (not required or opt[2]),
            }
        arithmetic = {
            "evidence_level": "STORE_INTEGRITY_ONLY",
            "mode": MODE,
            "project": req["id"], "domain": req["domain"],
            "fields": [
                {"name": policy["f1"], "unit": policy["u1"], "limit": max1},
                {"name": policy["f2"], "unit": policy["u2"], "limit": max2},
            ],
            "options": details,
        }
        return {
            **_result(action, "FULL_SOURCE_TYPED_DECISION", source_refs),
            "source_exact_arithmetic": arithmetic,
        }
    except (KeyError, ValueError, TypeError, OSError, UnicodeError,
            AttributeError, OverflowError):
        return _result("UNKNOWN", "SOURCE_INTEGRITY_OR_GRAMMAR_RED")
