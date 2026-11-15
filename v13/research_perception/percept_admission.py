"""Bounded, provenance-preserving A5 admission for a downstream C3 budget.

Callers must supply measured token counts from the actual tokenizer.
No implicit truncation, summary, capture, model training or device action.
"""
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class Segment:
    source_id: str
    modality: str
    token_count: int
    priority: int
    consented: bool
    text: str

@dataclass(frozen=True)
class Admission:
    accepted: Tuple[Segment, ...]
    deferred: Tuple[Segment, ...]
    tokens: int
    status: str

def admit(segments: Tuple[Segment, ...], capacity: int, reserved: int = 0) -> Admission:
    if capacity < 0 or reserved < 0 or reserved > capacity:
        raise ValueError('invalid capacity/reserve')
    if len({s.source_id for s in segments}) != len(segments):
        raise ValueError('duplicate source id')
    if any(s.token_count < 0 or not s.source_id or s.modality not in ('text','audio','visual','ui') for s in segments):
        raise ValueError('invalid segment')
    available = capacity - reserved
    accepted, deferred = [], []
    for s in sorted(segments, key=lambda s: (-s.priority, s.source_id)):
        if s.consented and s.token_count <= available:
            accepted.append(s)
            available -= s.token_count
        else:
            deferred.append(s)
    return Admission(tuple(accepted), tuple(deferred), capacity - reserved - available,
                     'FULL' if not deferred else 'PARTIAL' if accepted else 'NO_ADMISSION')
