"""P0 #1904: source-preserving compute admission for technical prompt envelopes.

This is an advisory budget gate, NOT a tokenizer or an Android performance claim.
No source text enters the diagnostics. All dropped envelopes remain addressable.
"""
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class Envelope:
    organ: str
    source_id: str
    estimated_tokens: int
    priority: int = 0
    mandatory: bool = False

def admit(envelopes: Sequence[Envelope], token_budget: int):
    """Return admitted envelopes and explicit deferred source references.

    Mandatory source context must fit; never truncate or silently omit it.
    Priority is advisory only for optional envelopes. Stable input order on ties.
    """
    if token_budget < 0:
        raise ValueError("negative token budget")
    if any(e.estimated_tokens < 0 or not e.source_id or not e.organ for e in envelopes):
        raise ValueError("invalid source-bound envelope")
    required = [e for e in envelopes if e.mandatory]
    required_cost = sum(e.estimated_tokens for e in required)
    if required_cost > token_budget:
        return {"status": "INSUFFICIENT_REQUIRED_BUDGET",
                "admitted": [], "deferred": list(envelopes),
                "required_tokens": required_cost, "remaining_tokens": token_budget}
    admitted = list(required)
    remaining = token_budget - required_cost
    optional = [(i,e) for i,e in enumerate(envelopes) if not e.mandatory]
    optional.sort(key=lambda pair: (-pair[1].priority, pair[0]))
    deferred = []
    for _,e in optional:
        if e.estimated_tokens <= remaining:
            admitted.append(e)
            remaining -= e.estimated_tokens
        else:
            deferred.append(e)
    return {"status": "ADMITTED", "admitted": admitted,
            "deferred": deferred, "required_tokens": required_cost,
            "remaining_tokens": remaining}

def technical_summary(result):
    """Safe for metrics: source IDs are deliberately not exported."""
    return {"status": result["status"], "admitted_count": len(result["admitted"]),
            "deferred_count": len(result["deferred"]),
            "required_tokens": result["required_tokens"],
            "remaining_tokens": result["remaining_tokens"]}
