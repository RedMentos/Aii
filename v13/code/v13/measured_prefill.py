"""Role-specific measured prefill forecast; never claims that a forecast is native proof."""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class Sample:
    role: str
    tokens: int
    seconds: float
    verified: bool = False
    def __post_init__(self):
        if not self.role or self.tokens <= 0 or not isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError('invalid sample')

def forecast(role, tokens, deadline_s, decode_reserve_s, samples):
    """Return (status, max_tokens), without editing messages or bypassing ContextOS."""
    if tokens < 0 or deadline_s <= 0 or decode_reserve_s < 0:
        raise ValueError('invalid budget')
    matches = [s for s in samples if s.role == role and s.verified]
    if not matches:
        return ('UNVERIFIED', 0)
    slowest = max(s.seconds / s.tokens for s in matches)
    cap = max(0, int((deadline_s - decode_reserve_s) / slowest))
    if cap < 32:
        return ('DEFER', 0)
    return ('ADMIT' if cap >= tokens else 'REDUCE_UPSTREAM', min(cap, tokens))
