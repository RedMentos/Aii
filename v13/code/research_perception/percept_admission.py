"""A5 SHADOW source-bound admission; native tokenizer and Android unverified."""
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
    """No silent truncation. Only accepted packets reserve source IDs.

    Rejected provisional/unconsented packets cannot poison later final packets.
    This is NOT an OS permission boundary or native token-budget proof.
    """
    if type(budget) is not int or budget < 0:
        raise ValueError("budget must be a nonnegative integer")
    accepted, rejected, used, seen = [], [], 0, set()
    for p in percepts:
        source = getattr(p, "source_id", None)
        if not isinstance(source, str) or not source or len(source) > 256:
            rejected.append((source, "INVALID_SOURCE"))
            continue
        if source in seen:
            rejected.append((source, "DUPLICATE_OR_MISSING_SOURCE"))
            continue
        if not isinstance(p.text, str) or len(p.text) > 65536:
            rejected.append((source, "INVALID_TEXT"))
        elif type(p.consent) is not bool or not p.consent:
            rejected.append((source, "NO_CONSENT"))
        elif type(p.final) is not bool or not p.final:
            rejected.append((source, "PROVISIONAL"))
        elif p.modality not in allowed_modalities:
            rejected.append((source, "MODALITY_OFF"))
        elif type(p.token_estimate) is not int or p.token_estimate < 0:
            rejected.append((source, "INVALID_ESTIMATE"))
        elif used + p.token_estimate > budget:
            rejected.append((source, "BUDGET_EXCEEDED"))
        else:
            accepted.append(p)
            seen.add(source)
            used += p.token_estimate
    return {"accepted": tuple(accepted), "rejected": tuple(rejected),
            "estimated_tokens": used, "native_tokenizer_verified": False}
