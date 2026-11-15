"""Bounded, source-preserving A5 admission candidate; not live runtime wiring."""
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
    """Admit whole consented segments; caller must retain all deferred sources.

    token_count must come from the downstream actual tokenizer; no estimation here.
    Current user turn is mandatory and must be admitted by a separate hard gate.
    """
    if type(capacity) is not int or type(reserved) is not int or capacity < 0 or not 0 <= reserved <= capacity:
        raise ValueError('invalid capacity/reserve')
    if any(not isinstance(s, Segment) for s in segments):
        raise ValueError('invalid segment type')
    if len({s.source_id for s in segments}) != len(segments):
        raise ValueError('duplicate source id')
    for s in segments:
        if (not isinstance(s.source_id, str) or not s.source_id.strip()
            or s.modality not in ('text', 'audio', 'visual', 'ui')
            or type(s.token_count) is not int or s.token_count < 0
            or type(s.priority) is not int or type(s.consented) is not bool
            or not isinstance(s.text, str)
            or (s.text and s.token_count == 0)):
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
