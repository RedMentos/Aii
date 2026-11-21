"""Conservative prefill admission for the Android native role scheduler.

This is an estimate, not tokenizer evidence. Refuses over-budget plans rather
than silently truncating source or claiming native runtime speed improvements.
"""
from dataclasses import dataclass
from math import isfinite

ROLES = ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")

@dataclass(frozen=True)
class Admission:
    role: str
    accepted: bool
    reason: str
    prompt_tokens: int
    output_tokens: int
    estimated_seconds: float
    remaining_seconds: float

def admit(role, *, prompt_tokens, output_tokens, remaining_seconds,
          prefill_tokens_per_second, decode_tokens_per_second,
          cold_load_seconds=0.0, safety_margin_seconds=1.0):
    """Return a non-authoritative scheduling decision before native invocation.

    All rates must originate from measured role-specific telemetry, not
    fabricated defaults. Unknown measurements refuse admission.
    """
    if role not in ROLES:
        raise ValueError("Unknown native role")
    if type(prompt_tokens) is not int or prompt_tokens < 0:
        raise ValueError("Invalid prompt token count")
    if type(output_tokens) is not int or output_tokens < 1:
        raise ValueError("Invalid output token count")
    for value in (remaining_seconds, cold_load_seconds, safety_margin_seconds):
        if type(value) not in (int, float) or not isfinite(value) or value < 0:
            raise ValueError("Invalid time budget")
    for value in (prefill_tokens_per_second, decode_tokens_per_second):
        if value is not None and (type(value) not in (int, float)
                                  or not isfinite(value) or value <= 0):
            raise ValueError("Invalid measured rate")
    if prefill_tokens_per_second is None or decode_tokens_per_second is None:
        return Admission(role, False, "NO_MEASURED_RATE", prompt_tokens,
                         output_tokens, float("inf"), remaining_seconds)
    estimated = (cold_load_seconds + prompt_tokens / prefill_tokens_per_second
                 + output_tokens / decode_tokens_per_second
                 + safety_margin_seconds)
    return Admission(role, estimated <= remaining_seconds,
                     "ADMITTED" if estimated <= remaining_seconds else "PREFILL_DECODE_BUDGET",
                     prompt_tokens, output_tokens, estimated, remaining_seconds)

def admit_coalition(requests, *, remaining_seconds, rates):
    """Sequential native roles; never silently remove either body.

    Caller must explicitly handle a refused coalition. This does not route
    around B1/B2 or authorize C3-only promotion.
    """
    results = []
    left = remaining_seconds
    for role, prompt_tokens, output_tokens in requests:
        rate = rates.get(role)
        if not isinstance(rate, dict):
            rate = {}
        result = admit(role, prompt_tokens=prompt_tokens,
                       output_tokens=output_tokens, remaining_seconds=max(0, left),
                       prefill_tokens_per_second=rate.get("prefill_tps"),
                       decode_tokens_per_second=rate.get("decode_tps"),
                       cold_load_seconds=rate.get("cold_load_s", 0))
        results.append(result)
        if not result.accepted:
            break
        left -= result.estimated_seconds
    return tuple(results)
