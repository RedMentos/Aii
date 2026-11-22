"""Compose exact tokenizer admission with measured native prefill profile.

No model call, no evidence promotion and no source truncation. A positive
result is compute admission, never Android functional acceptance.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class RouteGate:
    execute: bool
    reason: str
    exact_tokens: int
    native_profile: dict


def gate_route(prompt_decision, samples, *, device, model_revision, threads,
               batch, concurrent, remaining_s, reserve_s=3.0):
    from .native_prefill_profile import estimate
    count = prompt_decision.exact_prompt_tokens
    if prompt_decision.status != "VERIFIED":
        return RouteGate(False, "EXACT_PROMPT_NOT_ADMITTED", count, {})
    if type(count) is not int or count <= 0:
        return RouteGate(False, "INVALID_EXACT_TOKENS", count, {})
    if type(remaining_s) not in (int, float) or not isfinite(remaining_s) or remaining_s <= 0:
        return RouteGate(False, "INVALID_TIME", count, {})
    if not all(type(x) is int and x > 0 for x in (threads, batch, concurrent)):
        return RouteGate(False, "INVALID_NATIVE_CONFIG", count, {})
    profile = estimate(samples, device=device, model_revision=model_revision,
                       threads=threads, batch=batch, concurrent=concurrent,
                       prompt_tokens=count, remaining_s=remaining_s,
                       reserve_s=reserve_s)
    return RouteGate(bool(profile["admit"]), profile["reason"], count, profile)
