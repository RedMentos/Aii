"""Run139 default-off fail-closed ambiguity guard for source-grounded eligibility.

This candidate is not wired into production or the frozen STEP2 cohort.
It accepts only source-verified quotes from its caller; it does not authenticate
source_refs or infer historical revision ordering. Original eligibility.decide
and the deterministic recipe remain unchanged.
"""
from __future__ import annotations

from v13.agi import eligibility as original

RULES = ("budget", "deadline", "local_only")


def strict_decide(rules, options, current, verified_quotes=()):
    """Refuse contradictory stated rule values before the existing guard.

    An unambiguous current source overrides older quotes. Without a current
    rule, contradictory verified quotes are ambiguous; quote order cannot be
    used as a chronology proof. All non-ambiguous inputs pass through exactly.
    """
    if type(rules) is not dict or type(current) is not str:
        raise ValueError("RULE_AMBIGUITY_INPUT_INVALID")
    if type(verified_quotes) not in (list, tuple) or any(
        type(quote) is not str for quote in verified_quotes
    ):
        raise ValueError("VERIFIED_QUOTES_INPUT_INVALID")

    checked = dict(rules)
    conflicts = []
    for rule in RULES:
        current_values = original.stated_values(rule, current)
        if len(current_values) > 1:
            checked[rule] = None
            conflicts.append(rule + ":ambiguous_current")
            continue
        if not current_values:
            quote_values = set().union(
                *(original.stated_values(rule, q) for q in verified_quotes)
            )
            if len(quote_values) > 1:
                checked[rule] = None
                conflicts.append(rule + ":ambiguous_quotes")

    result = original.decide(checked, options, current, verified_quotes)
    if not conflicts:
        return result
    return dict(result, rejected=[*result["rejected"], *conflicts])
