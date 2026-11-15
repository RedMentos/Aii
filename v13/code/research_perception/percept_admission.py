"""A5 SHADOW source-bound admission; native tokenizer and Android remain unverified."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Percept:
    source_id: str
    text: str
    token_estimate: int
    consent: bool
    final: bool
    modality: str

def admit(percepts, budget, *, allowed_modalities=("text", "audio", "ui")):
    """No silent truncation; rejected packets retain explicit source and reason."""
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
        raise ValueError("budget must be a nonnegative integer")
    accepted, rejected, used, seen = [], [], 0, set()
    for p in percepts:
        if not p.source_id or p.source_id in seen:
            rejected.append((p.source_id, "DUPLICATE_OR_MISSING_SOURCE"))
            continue
        seen.add(p.source_id)
        if not p.consent:
            rejected.append((p.source_id, "NO_CONSENT"))
        elif not p.final:
            rejected.append((p.source_id, "PROVISIONAL"))
        elif p.modality not in allowed_modalities:
            rejected.append((p.source_id, "MODALITY_OFF"))
        elif not isinstance(p.token_estimate, int) or isinstance(p.token_estimate, bool) or p.token_estimate < 0:
            rejected.append((p.source_id, "INVALID_ESTIMATE"))
        elif used + p.token_estimate > budget:
            rejected.append((p.source_id, "BUDGET_EXCEEDED"))
        else:
            accepted.append(p)
            used += p.token_estimate
    return {"accepted": tuple(accepted), "rejected": tuple(rejected),
            "estimated_tokens": used, "native_tokenizer_verified": False}
