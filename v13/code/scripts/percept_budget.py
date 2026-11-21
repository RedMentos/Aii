"""Conservative A-plane percept admission; preserves source pointers, never raw content.
Not trained A3, native latent transfer, or an integrated runtime consumer.
"""
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class Percept:
    source_id: str
    modality: str
    start_ms: int
    end_ms: int
    salience: float
    estimated_tokens: int
    consent: bool
    provenance: str = "source_exact"

def admit(percepts: Sequence[Percept], token_budget: int) -> dict:
    """Prioritize consented source metadata; defer rather than silently discard."""
    if token_budget < 0:
        raise ValueError("negative token budget")
    for p in percepts:
        if not p.source_id or p.start_ms < 0 or p.end_ms < p.start_ms:
            raise ValueError("invalid source/timing")
        if p.estimated_tokens < 0 or not 0 <= p.salience <= 1:
            raise ValueError("invalid cost/salience")
        if p.provenance not in ("source_exact", "teacher_provisional", "teacher_final"):
            raise ValueError("untrusted provenance")
    eligible = [p for p in percepts if p.consent]
    ordered = sorted(eligible, key=lambda p: (-p.salience, p.end_ms, p.source_id))
    selected, deferred, used = [], [], 0
    for p in ordered:
        packet = dict(source_id=p.source_id, modality=p.modality,
                      interval_ms=[p.start_ms, p.end_ms], provenance=p.provenance,
                      estimated_tokens=p.estimated_tokens)
        if used + p.estimated_tokens <= token_budget:
            selected.append(packet)
            used += p.estimated_tokens
        else:
            deferred.append(packet)
    return {"selected": selected, "deferred": deferred,
            "consent_denied_count": len(percepts)-len(eligible),
            "budget_tokens": token_budget, "used_tokens": used,
            "latent_status": "UNAVAILABLE", "a3_status": "UNAVAILABLE"}
