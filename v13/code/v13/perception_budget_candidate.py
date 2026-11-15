"""Bounded source-aware A5-to-C3 shadow admission; no raw data retained."""
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class PerceptSummary:
    source: str
    modality: str
    text: str
    priority: int
    consent: bool
    provenance: str
    timestamp_ms: int

def admit_percepts(items: Iterable[PerceptSummary], max_chars: int = 384,
                   now_ms: int = 0, max_age_ms: int = 10000) -> tuple[str, ...]:
    """No partial packets, silent truncation, or permission bypass."""
    if max_chars < 0 or max_age_ms < 0:
        raise ValueError("negative budget")
    remaining = max_chars
    selected = []
    valid = [p for p in items if p.consent
             and p.provenance in ("final", "provisional")
             and p.modality in ("audio", "ui", "vision") and p.source
             and 0 <= now_ms - p.timestamp_ms <= max_age_ms]
    for p in sorted(valid, key=lambda x: (-x.priority, x.timestamp_ms, x.source)):
        content = " ".join(p.text.split())
        if not content:
            continue
        entry = f"[{p.modality}/{p.provenance}/{p.source}] {content}"
        if len(entry) <= remaining:
            selected.append(entry)
            remaining -= len(entry)
    return tuple(selected)
