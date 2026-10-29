"""Default-off Context OS source-scope composition; software-only control.

Combine independently reviewed project-history selection and typed A/B pair
attribution refusal. Upstream Store must authenticate exact source strings.
No runtime wiring, model calls, oracle access, learning or decision authority.
"""
from __future__ import annotations

from scripts import context_option_pair_scope_candidate as pair
from scripts import context_option_project_scope_candidate as project
from v13.agi import eligibility as original


SCOPE = "POSTHOC_EXACT_SOURCE_SOFTWARE_CONTROL_NO_GATE"


def _history(current, earlier):
    if type(current) is not str or type(earlier) not in (tuple, list) or any(
        type(x) is not str for x in earlier
    ):
        raise ValueError("CONTEXT_SOURCE_INPUT_INVALID")
    key = project.project_key(current)
    if key is project.AMBIGUOUS:
        return None
    return [] if key is None else [
        source for source in earlier if project.project_key(source) == key
    ]


def read_fixed_safe(current, earlier=()):
    """READ_SCHEMA values; never borrow foreign/unattributed option values."""
    history = _history(current, earlier)
    if history is None:
        return {"budget": None, "deadline": None, "local_only": None, "options": None}
    return pair.read_fixed_pair_scope(current, history)


def decide_safe(current, earlier=()):
    """Deterministic software decision only; UNKNOWN is never a commitment."""
    history = _history(current, earlier)
    values = ({"budget": None, "deadline": None, "local_only": None, "options": None}
              if history is None else pair.read_fixed_pair_scope(current, history))
    if values["options"] is None or any(values[k] is None for k in (
        "budget", "deadline", "local_only"
    )):
        return {"action": "UNKNOWN", "values": values,
                "rejected": ["SOURCE_UNAVAILABLE_OR_AMBIGUOUS"], "scope": SCOPE}
    result = original.decide(
        {key: values[key] for key in ("budget", "deadline", "local_only")},
        values["options"], current, history
    )
    return {"action": result["action"], "values": values,
            "rejected": result["rejected"], "scope": SCOPE}
