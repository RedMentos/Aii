"""Conservative source-preserving prompt admission for native Android inference.

This is a preflight contract, not a tokenizer or a claim of native performance.
Callers must provide exact tokenizer counts when available; the fallback upper
estimate is intentionally pessimistic. No model-authored text gains authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable


class PromptAdmissionError(ValueError):
    """An essential source cannot fit; do not silently discard it."""


@dataclass(frozen=True)
class Segment:
    role: str
    text: str
    authority: str
    essential: bool = False
    token_count: int | None = None

    def __post_init__(self):
        if self.role not in {
            "SYSTEM", "USER_EXACT", "STREAM_A", "STREAM_B", "B1_DETAIL",
            "B2_GIST", "B3_CALLOSUM", "C4_FOCAL", "MEMORY",
            "WORLD", "SELF", "ENLIGHTENED_SPACE",
        }:
            raise ValueError("unknown prompt role")
        if self.authority not in {"SOURCE", "CONTROL", "HYPOTHESIS", "MEMORY_CUE"}:
            raise ValueError("unknown authority")
        if not isinstance(self.text, str):
            raise TypeError("prompt text must be str")
        if self.token_count is not None and (
            isinstance(self.token_count, bool)
            or not isinstance(self.token_count, int)
            or self.token_count < 0
        ):
            raise ValueError("invalid token count")
        if self.role == "USER_EXACT" and (
            not self.essential or self.authority != "SOURCE"
        ):
            raise ValueError("user exact source must be essential and source-bound")
        if self.authority == "HYPOTHESIS" and self.essential:
            raise ValueError("model hypothesis cannot be essential source")


@dataclass(frozen=True)
class Admission:
    accepted: tuple[Segment, ...]
    omitted: tuple[str, ...]
    estimated_prompt_tokens: int
    reserved_output_tokens: int
    budget_tokens: int
    status: str


def conservative_tokens(segment: Segment) -> int:
    """Overestimate for planning, never certify a native tokenizer count."""
    if segment.token_count is not None:
        return segment.token_count
    data = segment.text.encode("utf-8")
    # Worst case up to one token per UTF-8 byte, plus formatting margin.
    return len(data) + 12


def admit(
    segments: Iterable[Segment], *,
    context_tokens: int,
    output_tokens: int,
    prompt_cap_tokens: int,
    framing_reserve: int = 32,
) -> Admission:
    """Admit essential text intact; omit optional segments by priority.

    The returned segments preserve original order. An optional segment is
    dropped *whole*, never silently clipped. A source ref should be carried
    alongside the selected Segment by its caller; this function does not
    invent, mutate, or validate provenance.
    """
    for name, value in (
        ("context_tokens", context_tokens),
        ("output_tokens", output_tokens),
        ("prompt_cap_tokens", prompt_cap_tokens),
        ("framing_reserve", framing_reserve),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("invalid " + name)
    if not context_tokens or not output_tokens or not prompt_cap_tokens:
        raise ValueError("zero inference budget")
    if output_tokens + framing_reserve >= context_tokens:
        raise PromptAdmissionError("no room for input after output reservation")
    available = min(prompt_cap_tokens, context_tokens - output_tokens - framing_reserve)
    seq = tuple(segments)
    if len(seq) > 128:
        raise ValueError("too many segments")
    for s in seq:
        if not isinstance(s, Segment):
            raise TypeError("expected Segment")
    essential = sum(conservative_tokens(s) for s in seq if s.essential)
    if essential > available:
        raise PromptAdmissionError(
            "essential source exceeds prompt budget; ask for a smaller request"
        )
    used = essential
    selected = {i for i, s in enumerate(seq) if s.essential}
    # Prioritize grounded exact evidence and bilateral body input, not the
    # order in which optional organ messages happened to arrive.
    priority = {
        "STREAM_B": 0, "B1_DETAIL": 1, "B2_GIST": 1,
        "C4_FOCAL": 2, "ENLIGHTENED_SPACE": 3, "STREAM_A": 4,
        "MEMORY": 5, "WORLD": 6, "SELF": 7, "B3_CALLOSUM": 8,
        "SYSTEM": 9, "USER_EXACT": 0,
    }
    optional = sorted(
        ((i, s) for i, s in enumerate(seq) if not s.essential),
        key=lambda pair: (priority[pair[1].role], pair[0]),
    )
    for i, s in optional:
        cost = conservative_tokens(s)
        if used + cost <= available:
            selected.add(i)
            used += cost
    accepted = tuple(s for i, s in enumerate(seq) if i in selected)
    omitted = tuple(s.role for i, s in enumerate(seq) if i not in selected)
    return Admission(
        accepted, omitted, used, output_tokens, available,
        "ADMITTED" if not omitted else "PARTIAL_CONTEXT",
    )
