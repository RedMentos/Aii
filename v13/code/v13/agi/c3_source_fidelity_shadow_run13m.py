"""Run13M: deterministic JEF-verified C3 text fidelity candidate, SHADOW only.

A posthoc-motivated grammar gate, not an active answer path or semantic judge.
Never alters Run13J/K/L frozen native outputs, scorers, weights or age gates.
"""
from __future__ import annotations

import hashlib
import re

from scripts.run13k_c3_copy_native import prompt_for as require_source_bound_prompt

REVISION = "run13m-c3-source-fact-shadow-v1"
MAX_OUTPUT_BYTES = 768
WS = r"[ \t\r\n]+"
OWS = r"[ \t\r\n]*"
NAME = r"[A-Za-z][A-Za-z0-9_-]{0,63}"
INT = r"(?:0|[1-9][0-9]{0,5})"
TRUSTED = re.compile(
    rf"\AProject (?P<project>{NAME})\.\n"
    rf"(?P<a>{NAME}) leaves (?P<na>{INT}) Euro remaining\.\n"
    rf"(?P<b>{NAME}) leaves (?P<nb>{INT}) Euro remaining\.\n"
    rf"(?P<faster>{NAME}) finishes sooner\.\Z"
)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _closed(reason, *, verified=False, answer_hash=None, output_hash=None):
    return {
        "revision": REVISION, "status": "SHADOW_NO_AUTHORITY",
        "result": "FACTS_EXACT" if verified else "ABSTAIN",
        "reason": reason, "answer_sha256": answer_hash,
        "output_sha256": output_hash,
        "operator_only": True, "no_autonomous_egress": True,
        "delivery_authority": 0, "context_authority": 0,
        "native_calls": 0, "model_called": False,
        "weight_updates": False, "learning_mode": "RECORD_ONLY",
        "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
        "body_jepa_status": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }


def _candidate_pattern(parts):
    project, a, na, b, nb, faster = parts
    # Literal source names/numbers are escaped, never treated as regex code.
    project, a, na, b, nb, faster = map(
        re.escape, (project, a, na, b, nb, faster))
    return re.compile(
        rf"\A{OWS}(?:BEGIN_VERIFIED{WS})?"
        rf"Project{WS}{project}\.?"
        rf"{WS}{a}{WS}leaves{WS}{na}{WS}(?i:euros?){WS}remaining\.?"
        rf"{WS}{b}{WS}leaves{WS}{nb}{WS}(?i:euros?){WS}remaining\.?"
        rf"{WS}{faster}{WS}finishes{WS}sooner\.?"
        rf"(?:{WS}END_VERIFIED)?{OWS}\Z"
    )


def audit_source_facts(linked, candidate):
    """Accept only all four original facts, in order; never authorize delivery."""
    if type(candidate) is not str:
        return _closed("NON_TEXT_CANDIDATE")
    try:
        if len(candidate.encode("utf-8")) > MAX_OUTPUT_BYTES:
            return _closed("OUTPUT_BUDGET_RED")
    except UnicodeError:
        return _closed("OUTPUT_ENCODING_RED")
    output_hash = _sha(candidate)
    try:
        require_source_bound_prompt(linked, "COPY_DIRECT")
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError):
        return _closed("SOURCE_INTEGRITY_RED", output_hash=output_hash)
    answer = linked["answer"]
    answer_hash = _sha(answer)
    match = TRUSTED.fullmatch(answer)
    if match is None:
        return _closed("TRUSTED_GRAMMAR_RED", answer_hash=answer_hash,
                       output_hash=output_hash)
    parts = tuple(match.group(k) for k in
                  ("project", "a", "na", "b", "nb", "faster"))
    _, a, _, b, _, faster = parts
    if a == b or faster not in (a, b):
        return _closed("TRUSTED_RELATION_RED", answer_hash=answer_hash,
                       output_hash=output_hash)
    verified = _candidate_pattern(parts).fullmatch(candidate) is not None
    return _closed("SOURCE_FACTS_VERIFIED" if verified else "CANDIDATE_FACT_MISMATCH",
                   verified=verified, answer_hash=answer_hash,
                   output_hash=output_hash)
