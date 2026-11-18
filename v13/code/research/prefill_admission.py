"""Conservative source-bound prefill admission. Synthetic fixture is not Redmi proof."""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class Envelope:
    organ: str
    source_id: str
    tokens: int
    required: bool = True

@dataclass(frozen=True)
class Profile:
    tokens_per_second_lower_bound: float
    fixed_overhead_seconds: float
    decode_reserve_seconds: float
    measured_on_redmi: bool = False

def admit(envelopes, profile, deadline_seconds):
    """Return (admitted, estimated_seconds, deferred_source_ids); never truncate required evidence."""
    envelopes = tuple(envelopes)
    if not isfinite(deadline_seconds) or deadline_seconds <= 0:
        raise ValueError("invalid deadline")
    if len(set(e.source_id for e in envelopes)) != len(envelopes):
        raise ValueError("duplicate source")
    if any(not e.source_id or not e.organ or type(e.tokens) is not int or e.tokens < 0 for e in envelopes):
        raise ValueError("invalid envelope")
    if profile is None or not profile.measured_on_redmi:
        return False, None, ()
    rate, overhead, reserve = (profile.tokens_per_second_lower_bound,
                               profile.fixed_overhead_seconds, profile.decode_reserve_seconds)
    if not all(isfinite(x) for x in (rate, overhead, reserve)) or rate <= 0 or overhead < 0 or reserve < 0:
        raise ValueError("invalid profile")
    kept, deferred = list(envelopes), []
    def cost():
        return overhead + reserve + sum(e.tokens for e in kept) / rate
    for e in reversed(envelopes):
        if cost() <= deadline_seconds:
            break
        if not e.required:
            kept.remove(e)
            deferred.append(e.source_id)
    return cost() <= deadline_seconds, cost(), tuple(deferred)
