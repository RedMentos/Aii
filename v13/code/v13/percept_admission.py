"""Consent-bound A5 perception admission. No capture, inference, or silent truncation."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Percept:
    source_id: str
    modality: str
    text: str
    consent: bool
    final: bool
    start_ms: int
    end_ms: int
    confidence: Optional[float] = None

    def __post_init__(self):
        if not self.source_id or self.modality not in ('text', 'audio', 'ui', 'vision'):
            raise ValueError('invalid source or modality')
        if self.start_ms < 0 or self.end_ms < self.start_ms:
            raise ValueError('invalid event interval')
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError('invalid confidence')

def admit(percepts, *, max_chars: int, current_user_source: str):
    """Return (accepted, excluded); source intact or explicit exclusion.

    Character limits are NOT token limits. Native tokenizer/template admission
    remains mandatory before invoking C3/B1/B2.
    """
    if max_chars < 0:
        raise ValueError('negative budget')
    accepted, excluded, used, seen = [], [], 0, set()
    ordered = sorted(percepts, key=lambda p: (p.source_id != current_user_source, -p.end_ms, p.source_id))
    for p in ordered:
        if p.source_id in seen:
            excluded.append((p.source_id, 'DUPLICATE_SOURCE'))
            continue
        seen.add(p.source_id)
        if not p.consent:
            excluded.append((p.source_id, 'NO_CONSENT'))
        elif not p.final:
            excluded.append((p.source_id, 'PROVISIONAL'))
        elif used + len(p.text) > max_chars:
            excluded.append((p.source_id, 'BUDGET_EXCEEDED'))
        else:
            accepted.append(p)
            used += len(p.text)
    if current_user_source not in {p.source_id for p in accepted}:
        raise ValueError('current user source cannot be admitted intact')
    return accepted, excluded
