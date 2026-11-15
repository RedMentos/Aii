"""A-plane source-bound admission for the C3 prompt budget (Issue #1904).

This module never performs model inference or grants Android permissions.
It only selects bounded, provenance-preserving percept summaries. Raw audio,
screenshots and transcripts remain outside this interface.
"""
from dataclasses import dataclass
from typing import Iterable, Tuple

@dataclass(frozen=True)
class Percept:
    source_id: str
    modality: str
    start_ms: int
    end_ms: int
    summary: str
    consent: bool
    final: bool
    priority: int = 0

@dataclass(frozen=True)
class Admission:
    selected: Tuple[Percept, ...]
    omitted: Tuple[str, ...]
    used_tokens_upper_bound: int
    status: str

def admit(percepts: Iterable[Percept], token_budget: int, *, max_items: int = 12) -> Admission:
    """Fail closed on malformed/unauthorized data; deterministic stable ordering.

    Conservative UTF-8 byte upper bound avoids pretending to know the native
    tokenizer. Consumers MUST still measure actual GGUF prompt tokens and
    apply their own global C3 budget before inference.
    """
    if not isinstance(token_budget, int) or isinstance(token_budget, bool) or token_budget < 0:
        raise ValueError("token_budget must be a nonnegative integer")
    if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items < 0:
        raise ValueError("max_items must be a nonnegative integer")
    records = tuple(percepts)
    if len(records) > 4096:
        raise ValueError("too many percepts")
    seen = set()
    valid = []
    omitted = []
    for p in records:
        if not isinstance(p, Percept):
            raise TypeError("expected Percept")
        if not isinstance(p.source_id, str) or not p.source_id or len(p.source_id) > 128 or p.source_id in seen:
            raise ValueError("invalid or duplicate source_id")
        seen.add(p.source_id)
        if (not isinstance(p.modality, str) or p.modality not in ("audio", "visual", "ui", "text")\n                or type(p.start_ms) is not int or type(p.end_ms) is not int\n                or p.start_ms < 0 or p.end_ms < p.start_ms\n                or not isinstance(p.summary, str) or len(p.summary) > 4096\n                or type(p.priority) is not int):
            raise ValueError("invalid percept")
        if not p.consent or not p.final:
            omitted.append(p.source_id)
            continue
        valid.append(p)
    valid.sort(key=lambda p: (-p.priority, p.start_ms, p.source_id))
    selected = []
    used = 0
    for p in valid:
        # Account for provenance + framing, not just the summary.
        cost = len((p.source_id + p.modality + p.summary).encode("utf-8")) + 32
        if len(selected) >= max_items or used + cost > token_budget:
            omitted.append(p.source_id)
            continue
        selected.append(p)
        used += cost
    return Admission(tuple(selected), tuple(omitted), used,
                     "ADMITTED" if selected else "EMPTY_OR_UNAUTHORIZED")
