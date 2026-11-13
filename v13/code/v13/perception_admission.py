"""A5 source-bound native prompt admission. Token counts must come from native tokenizer."""
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class Evidence:
    source_id: str
    text: str
    tokens: int
    kind: str
    consent: bool = True
    required: bool = False

@dataclass(frozen=True)
class Admission:
    accepted: tuple[Evidence, ...]
    omitted: tuple[str, ...]
    status: str
    token_count: int
    budget: int

def admit(evidence: Sequence[Evidence], budget: int, reserve: int = 0) -> Admission:
    """No silent clipping. Required source preserved; optional source omitted whole."""
    if budget < 0 or reserve < 0 or reserve > budget:
        raise ValueError("invalid budget/reserve")
    ids = [e.source_id for e in evidence]
    if len(set(ids)) != len(ids) or any(not s for s in ids):
        raise ValueError("missing/duplicate source ID")
    if any(e.tokens < 0 or (e.text and e.tokens == 0) for e in evidence):
        raise ValueError("invalid native token count")
    if any(e.required and not e.consent for e in evidence):
        return Admission((), tuple(ids), "CONSENT_BLOCKED", 0, budget)
    required = [e for e in evidence if e.required]
    if sum(e.tokens for e in required) > budget - reserve:
        return Admission((), tuple(ids), "REQUIRED_OVER_BUDGET", 0, budget)
    remaining = budget - reserve - sum(e.tokens for e in required)
    selected = {e.source_id for e in required}
    for e in evidence:
        if not e.required and e.consent and e.tokens <= remaining:
            selected.add(e.source_id)
            remaining -= e.tokens
    accepted = tuple(e for e in evidence if e.source_id in selected)
    omitted = tuple(e.source_id for e in evidence if e.source_id not in selected)
    return Admission(accepted, omitted, "ADMITTED" if not omitted else "PARTIAL_SOURCE_BOUND", sum(e.tokens for e in accepted), budget)
