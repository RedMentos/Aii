"""Run14K source-bound six-slot C3 JSON extraction, SHADOW with zero delivery authority.

This is a deterministic candidate verifier, not a native result or a semantic judge.
The original trusted JEF answer remains the only text selected by the mux.
"""
from __future__ import annotations

import hashlib
import json

from scripts.run13k_c3_copy_native import prompt_for as require_source_bound_prompt
from .c3_source_fidelity_shadow_run13m import TRUSTED

REVISION = "run14k-c3-structured-source-facts-shadow-v1"
SYSTEM = ("You are a strict data extraction engine. Return only one JSON object "
          "with six exact fields; no commentary or invented facts.")
PREFIX = ("Extract project, option_a, remaining_a, option_b, remaining_b, faster "
          "from these verified facts. Return JSON with exactly those six keys; "
          "amounts must be integers.\nVERIFIED_FACTS:\n")
KEYS = frozenset(("project", "option_a", "remaining_a", "option_b", "remaining_b", "faster"))
MAX_PROMPT_BYTES = 1200
MAX_JSON_BYTES = 512


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _trusted(linked):
    require_source_bound_prompt(linked, "COPY_DIRECT")
    answer = linked["answer"]
    match = TRUSTED.fullmatch(answer)
    if match is None:
        raise ValueError("C3_STRUCTURED_TRUSTED_GRAMMAR_RED")
    fields = {"project": match.group("project"),
              "option_a": match.group("a"),
              "remaining_a": int(match.group("na")),
              "option_b": match.group("b"),
              "remaining_b": int(match.group("nb")),
              "faster": match.group("faster")}
    if fields["option_a"] == fields["option_b"] or fields["faster"] not in (
            fields["option_a"], fields["option_b"]):
        raise ValueError("C3_STRUCTURED_TRUSTED_RELATION_RED")
    return answer, fields


def prompt_for(linked):
    """Deterministic source-bound system and user prompt; no runner is invoked."""
    answer, _ = _trusted(linked)
    user = PREFIX + answer
    if len(user.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise ValueError("C3_STRUCTURED_PROMPT_BUDGET_RED")
    return SYSTEM, user


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("C3_STRUCTURED_DUPLICATE_KEY")
        out[key] = value
    return out


def _reject_constant(value):
    raise ValueError("C3_STRUCTURED_NONFINITE_JSON")


def _closed(reason, *, verified=False, answer=None, candidate=None):
    return {"revision": REVISION, "status": "SHADOW_NO_AUTHORITY",
            "result": "SLOTS_EXACT" if verified else "ABSTAIN",
            "reason": reason,
            "answer_sha256": _sha(answer) if type(answer) is str else None,
            "output_sha256": _sha(candidate) if type(candidate) is str else None,
            "delivery_authority": 0, "context_authority": 0,
            "model_called": False, "native_calls": 0,
            "store_writes": 0, "weight_updates": False,
            "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
            "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
            "jepa_weight": 0, "redmi_measured": False,
            "whole_system_complete": False}


def audit_slots(linked, candidate):
    """Verify six exact typed JSON slots against a source-bound JEF answer."""
    if type(candidate) is not str:
        return _closed("C3_STRUCTURED_NON_TEXT")
    try:
        size = len(candidate.encode("utf-8"))
        if not 0 < size <= MAX_JSON_BYTES:
            return _closed("C3_STRUCTURED_OUTPUT_BUDGET_RED")
    except UnicodeError:
        return _closed("C3_STRUCTURED_OUTPUT_ENCODING_RED")
    try:
        answer, expected = _trusted(linked)
        parsed = json.loads(candidate, object_pairs_hook=_unique_object,
                            parse_constant=_reject_constant)
        if type(parsed) is not dict or set(parsed) != KEYS:
            return _closed("C3_STRUCTURED_KEYS_RED", answer=answer, candidate=candidate)
        for key in KEYS:
            required_type = int if key in ("remaining_a", "remaining_b") else str
            if type(parsed[key]) is not required_type or parsed[key] != expected[key]:
                return _closed("C3_STRUCTURED_VALUE_RED", answer=answer, candidate=candidate)
        return _closed("C3_STRUCTURED_SLOTS_EXACT", verified=True,
                       answer=answer, candidate=candidate)
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError, UnicodeError):
        return _closed("C3_STRUCTURED_SOURCE_OR_JSON_RED", candidate=candidate)
