"""Phone-profile prefill timing estimator; never an authority to drop evidence."""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class Observation:
    role: str
    prompt_tokens: int
    prefill_seconds: float
    device_verified: bool
    generated_tokens: int = 0

def estimate(role, prompt_tokens, deadline_seconds, reserve_seconds, observations):
    if prompt_tokens < 0 or deadline_seconds <= 0 or reserve_seconds < 0:
        raise ValueError('invalid budget')
    valid = [o for o in observations if o.device_verified and o.role == role
             and o.prompt_tokens > 0 and isfinite(o.prefill_seconds)
             and o.prefill_seconds >= 0]
    if not valid:
        return {'decision':'MEASURE_FIRST','predicted_prefill_seconds':None}
    seconds = max(o.prefill_seconds / o.prompt_tokens for o in valid) * prompt_tokens
    decision = 'DEFER_OR_REPLAN' if seconds + reserve_seconds > deadline_seconds else 'ADMIT_ESTIMATE_ONLY'
    return {'decision':decision,'predicted_prefill_seconds':round(seconds,3)}
