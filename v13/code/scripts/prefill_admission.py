"""Non-authoritative V13 phone prefill admission; does not bypass organs or truncate sources."""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class NativeProfile:
    organ: str
    device: str
    input_tokens: int
    prefill_seconds: float
    output_tokens: int
    decode_seconds: float
    evidence: str

    def __post_init__(self):
        if self.device != "REDMI_NATIVE" or self.evidence != "CONSENTED_DEVICE":
            raise ValueError("phone evidence required")
        if not self.organ or self.input_tokens <= 0 or self.output_tokens <= 0:
            raise ValueError("invalid token sample")
        if not all(isfinite(v) and v > 0 for v in (self.prefill_seconds, self.decode_seconds)):
            raise ValueError("invalid timings")

@dataclass(frozen=True)
class Admission:
    admitted: bool
    reason: str
    estimated_seconds: float | None
    available_seconds: float

def admit(profile: NativeProfile | None, organ: str, prompt_tokens: int,
          minimum_output_tokens: int, deadline_seconds: float,
          elapsed_seconds: float = 0.0, reserve_seconds: float = 2.0) -> Admission:
    """Heuristic only. Caller must preserve exact sources and normal C/B routes."""
    if not all(isfinite(v) and v >= 0 for v in (deadline_seconds, elapsed_seconds, reserve_seconds)):
        raise ValueError("invalid deadline")
    if prompt_tokens < 0 or minimum_output_tokens < 1:
        raise ValueError("invalid token request")
    available = max(0.0, deadline_seconds - elapsed_seconds - reserve_seconds)
    if profile is None or profile.organ != organ:
        return Admission(False, "NO_MATCHING_REDMI_PROFILE", None, available)
    estimate = (prompt_tokens * profile.prefill_seconds / profile.input_tokens
                + minimum_output_tokens * profile.decode_seconds / profile.output_tokens)
    if estimate > available:
        return Admission(False, "PREFILL_OUTPUT_BUDGET_EXCEEDED", estimate, available)
    return Admission(True, "HEURISTIC_ADMISSION_NOT_GUARANTEE", estimate, available)
