"""Source-preserving A5-to-C3 optional context admission; no tokenizer claims.

Isolated candidate; runtime must explicitly opt in after review.
"""
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class A5Item:
    source_id: str
    summary: str
    consent: bool
    final: bool
    priority: int = 0

@dataclass(frozen=True)
class A5Envelope:
    current_source: str
    optional_context: str
    included_ids: tuple[str, ...]
    omitted_ids: tuple[str, ...]
    budget_chars: int

def admit_a5(current_source: str, items: Iterable[A5Item], *, budget_chars: int = 320) -> A5Envelope:
    """Bound optional context, never truncate current source.

    Char prefilter is NOT a native tokenizer budget guarantee.
    """
    if not isinstance(current_source, str) or not current_source:
        raise ValueError("nonempty current source required")
    if type(budget_chars) is not int or not 0 <= budget_chars <= 4096:
        raise ValueError("invalid optional context budget")
    seen, eligible, omitted = set(), [], []
    for item in items:
        if (not isinstance(item, A5Item) or not isinstance(item.source_id, str)
            or not item.source_id or "\n" in item.source_id
            or not isinstance(item.summary, str) or type(item.consent) is not bool
            or type(item.final) is not bool or type(item.priority) is not int):
            raise ValueError("malformed A5 item")
        if item.source_id in seen:
            raise ValueError("duplicate source id")
        seen.add(item.source_id)
        if not item.consent or not item.final:
            omitted.append(item.source_id)
        else:
            eligible.append(item)
    eligible.sort(key=lambda x: (-x.priority, x.source_id))
    lines, included, used = [], [], 0
    for item in eligible:
        line = f"[{item.source_id}] {item.summary}"
        cost = len(line) + (1 if lines else 0)
        if used + cost <= budget_chars:
            lines.append(line)
            included.append(item.source_id)
            used += cost
        else:
            omitted.append(item.source_id)
    return A5Envelope(current_source, "\n".join(lines), tuple(included), tuple(omitted), budget_chars)
