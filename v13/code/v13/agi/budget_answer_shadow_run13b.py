"""Run13B: human-readable exact-source JEF budget answer, SHADOW only.

Uses the existing Run11Y Store/SourceRef grammar and arithmetic. This module
does not run models, dispatch tools, repair live output or grant answer authority.
It is a narrow software answer-form baseline, NOT native STEP2 utility.
"""
from __future__ import annotations

import hashlib
import re

from v13.agi import budget_en_source_shadow as jef

REVISION = "run13b-jef-budget-answer-shadow-v1"
NAME = re.compile(r"[A-Za-z][A-Za-z-]{0,31}", re.ASCII)
PROJECT = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,39}", re.ASCII)
KEYS = frozenset({
    "project", "option_a", "option_b", "remaining_a_eur",
    "remaining_b_eur", "faster_option",
})


def _closed(result, reason=None):
    """No text, no candidate, no authority on any integrity/grammar failure."""
    out = dict(result)
    if reason is not None:
        out["reason"] = reason
    out.update(candidate=None, answer=None, answer_sha256=None,
               answer_kind="SOURCE_EXACT_SHADOW_ONLY",
               delivery_authority=0, operator_only=True)
    return out


def _render(candidate):
    if type(candidate) is not dict or set(candidate) != KEYS:
        raise ValueError("CANDIDATE_SHAPE_RED")
    project = candidate["project"]
    a, b = candidate["option_a"], candidate["option_b"]
    faster = candidate["faster_option"]
    if (type(project) is not str or PROJECT.fullmatch(project) is None
            or type(a) is not str or NAME.fullmatch(a) is None
            or type(b) is not str or NAME.fullmatch(b) is None
            or a.casefold() == b.casefold()
            or type(faster) is not str or faster not in (a, b)):
        raise ValueError("CANDIDATE_NAMES_RED")
    ra, rb = candidate["remaining_a_eur"], candidate["remaining_b_eur"]
    if (type(ra) is not int or type(rb) is not int
            or not 0 < ra <= 999999 or not 0 < rb <= 999999):
        raise ValueError("CANDIDATE_AMOUNTS_RED")
    return (f"Project {project}.\n"
            f"{a} leaves {ra} Euro remaining.\n"
            f"{b} leaves {rb} Euro remaining.\n"
            f"{faster} finishes sooner.")


def propose_text(store, query_ref, source_ref):
    """Render exact source values with a second independent Store revalidation.

    No dispatch follows. A future live consumer must revalidate at egress;
    this double read is not a concurrency/authorization proof.
    """
    first = jef.propose(store, query_ref, source_ref)
    if first.get("reason") != "EXACT_SOURCE_ARITHMETIC_SHADOW":
        return _closed(first)
    try:
        answer = _render(first["candidate"])
        second = jef.propose(store, query_ref, source_ref)
        if second != first:
            return _closed(first, "SOURCE_CHANGED_BEFORE_SHADOW_RENDER")
        return {
            **first, "revision": REVISION,
            "reason": "SOURCE_EXACT_ANSWER_FORM_SHADOW",
            "answer": answer,
            "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
            "answer_kind": "SOURCE_EXACT_SHADOW_ONLY",
            "delivery_authority": 0,
            "operator_only": True,
        }
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return _closed(first, "CANDIDATE_RENDER_INTEGRITY_RED")
