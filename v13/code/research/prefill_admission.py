"""Source-preserving native prompt preflight; estimate only, never proof of delivery."""
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

@dataclass(frozen=True)
class Admission:
    admitted: bool
    estimated_seconds: float | None
    kept_source_ids: tuple[str, ...]
    deferred_source_ids: tuple[str, ...]
    reason: str

def plan(envelopes, profile, deadline_seconds):
    """Source-preserving estimate, not native delivery or phone attestation.

    Caller must validate source IDs, resolve full bytes and count tokens with
    the actual tokenizer. A caller-set measured_on_redmi flag is NOT proof.
    """
    envelopes = tuple(envelopes)
    if (isinstance(deadline_seconds, bool) or
        not isinstance(deadline_seconds, (int, float)) or
        not isfinite(deadline_seconds) or deadline_seconds <= 0):
        raise ValueError("invalid deadline")
    if any(not isinstance(e, Envelope) for e in envelopes):
        raise ValueError("invalid envelope type")
    if len({e.source_id for e in envelopes}) != len(envelopes):
        raise ValueError("duplicate source")
    if any(not isinstance(e.source_id, str) or not e.source_id.strip() or
           not isinstance(e.organ, str) or not e.organ.strip() or
           type(e.tokens) is not int or e.tokens < 0 or
           type(e.required) is not bool for e in envelopes):
        raise ValueError("invalid envelope")
    ids = tuple(e.source_id for e in envelopes)
    if profile is None or not isinstance(profile, Profile) or not profile.measured_on_redmi:
        return Admission(False, None, ids, (), "NO_REDMI_PROFILE")
    rate, overhead, reserve = (profile.tokens_per_second_lower_bound,
                               profile.fixed_overhead_seconds,
                               profile.decode_reserve_seconds)
    if (any(isinstance(x, bool) or not isinstance(x, (int, float)) or
            not isfinite(x) for x in (rate, overhead, reserve)) or
        rate <= 0 or overhead < 0 or reserve < 0):
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
    estimate = cost()
    return Admission(estimate <= deadline_seconds, estimate,
                     tuple(e.source_id for e in kept), tuple(deferred),
                     "ESTIMATE_FITS" if estimate <= deadline_seconds
                     else "REQUIRED_EXCEEDS_DEADLINE")

def admit(envelopes, profile, deadline_seconds):
    """Backwards-compatible (admitted, estimate, deferred IDs) interface."""
    p = plan(envelopes, profile, deadline_seconds)
    return p.admitted, p.estimated_seconds, p.deferred_source_ids
