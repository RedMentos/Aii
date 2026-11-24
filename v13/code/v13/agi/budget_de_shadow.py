"""STEP2 German budget-minus-cost SHADOW candidate, source-exact and unwired.

Non-generative read-only local calculation. It cannot choose a project,
evaluate eligibility, call C5/ToolStep or change an Age/learning gate.
"""
from __future__ import annotations

import hashlib
import re

AUTHORITY = "SHADOW_ONLY"
REVISION = "step2-de-budget-remain-seed97-v1"
MAX_TEXT = 2000

_BUDGET = re.compile(
    r"\b(?:budget|kostenrahmen|obergrenze)\s*:?\s*(\d+)\s*(?:euro\b|€)",
    re.IGNORECASE)
_OPTION_MENTION = re.compile(
    r"\boption\s+([A-Za-zÄÖÜäöüß][\w-]{0,24})\b", re.IGNORECASE)
_OPTION_COST = re.compile(
    r"\boption\s+([A-Za-zÄÖÜäöüß][\w-]{0,24})\s+kostet\s+(\d+)\s*(?:euro\b|€)",
    re.IGNORECASE)
_ASK = re.compile(
    r"\bbudgetrest(?:e|en)?\b|\bwie\s+viel\s+budget\s+bleibt\b|"
    r"\bwie\s+viel\s+bleibt\s+vom\s+budget\b", re.IGNORECASE)
_UNTRUSTED = re.compile(
    r"\b(?:ignorier\w*|umgeh\w*|überspring\w*)\b[^.!?]{0,60}"
    r"\b(?:prüf\w*|regel\w*|validier\w*)\b", re.IGNORECASE)


def evaluate(text):
    """Return source-bound numeric proposal or fail-closed SHADOW_ABSTAIN."""
    result = {"status": "SHADOW_ABSTAIN", "authority": AUTHORITY,
              "revision": REVISION, "reason": None,
              "budget": None, "options": [],
              "evidence_level": "SOFTWARE_SOURCE_ONLY",
              "native_model_calls": 0, "live_tool_execution": False,
              "external_action_authority": False,
              "step2_gate_promoted": False, "b3_promoted": False,
              "body_jepa_available": False, "jepa_weight": 0,
              "redmi_measured": False, "whole_system_complete": False}
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        result["reason"] = "INVALID_SOURCE"
        return result
    result["source_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if _UNTRUSTED.search(text):
        result["reason"] = "UNTRUSTED_INSTRUCTION"
        return result
    if not _ASK.search(text):
        result["reason"] = "NO_REMAINDER_QUESTION"
        return result
    budgets = list(_BUDGET.finditer(text))
    if len(budgets) != 1:
        result["reason"] = "BUDGET_MISSING_OR_AMBIGUOUS"
        return result
    mentions = list(_OPTION_MENTION.finditer(text))
    costs = list(_OPTION_COST.finditer(text))
    if len(mentions) != 2 or len(costs) != 2:
        result["reason"] = "OPTIONS_MISSING_OR_AMBIGUOUS"
        return result
    names = [m.group(1).casefold() for m in mentions]
    bound = [m.group(1).casefold() for m in costs]
    if len(set(names)) != 2 or names != bound:
        result["reason"] = "OPTION_NAME_COST_BINDING_RED"
        return result
    budget = int(budgets[0].group(1))
    options = []
    for m in costs:
        cost = int(m.group(2))
        options.append({"name": m.group(1), "cost": cost,
                        "remaining": budget - cost,
                        "source_span": [m.start(), m.end()]})
    result.update(status="SHADOW_RESULT", reason="EXACT_SOURCE_BOUND_REMAINDER",
                  budget=budget, budget_source_span=[budgets[0].start(), budgets[0].end()],
                  options=options)
    return result
