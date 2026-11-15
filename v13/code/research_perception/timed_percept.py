"""Consent-bound, dependency-free A-plane timed audio/UI percept prototype.

No microphone access, ASR, speaker identification or device control.
"""
from dataclasses import dataclass, asdict
from math import sqrt
from typing import Optional

@dataclass(frozen=True)
class TimedPercept:
    modality: str
    source_kind: str
    start_ms: int
    end_ms: int
    consent_scope: str
    provenance: str
    phase: str
    features: dict
    teacher_text: Optional[str] = None

    def __post_init__(self):
        if self.modality not in ('audio', 'android_ui'):
            raise ValueError('unsupported modality')
        if not (isinstance(self.start_ms, int) and isinstance(self.end_ms, int)
                and 0 <= self.start_ms < self.end_ms):
            raise ValueError('invalid time interval')
        if self.phase not in ('provisional', 'final'):
            raise ValueError('invalid phase')
        if self.provenance not in ('synthetic', 'authorized_device'):
            raise ValueError('untrusted provenance')
        if not self.consent_scope or self.consent_scope == 'none':
            raise PermissionError('explicit scope required')
        if self.teacher_text is not None and self.modality != 'audio':
            raise ValueError('teacher ASR belongs to audio')

    def to_packet(self):
        return {'schema': 'v13.a5.timed-percept/1', **asdict(self),
                'gate': 'SYNTHETIC_ONLY' if self.provenance == 'synthetic' else 'DEVICE_UNVERIFIED'}

def audio_fixture(samples, sample_rate, start_ms, consent_scope,
                  *, phase='provisional', teacher_text=None):
    """Synthetic PCM fixture; acoustic evidence preserved independently of ASR."""
    if not isinstance(sample_rate, int) or sample_rate <= 0 or not samples:
        raise ValueError('nonempty PCM and positive sample rate required')
    if len(samples) > sample_rate * 10:
        raise ValueError('fixture exceeds 10 seconds')
    if any(not isinstance(v, (int, float)) or not -1 <= v <= 1 for v in samples):
        raise ValueError('invalid normalized PCM')
    duration_ms = max(1, (len(samples) * 1000 + sample_rate - 1) // sample_rate)
    rms = sqrt(sum(v * v for v in samples) / len(samples))
    crossings = sum((a < 0) != (b < 0) for a, b in zip(samples, samples[1:]))
    return TimedPercept('audio', 'pcm_fixture', start_ms, start_ms + duration_ms,
                        consent_scope, 'synthetic', phase,
                        {'rms': round(rms, 6),
                         'zero_crossing_rate': round(crossings / max(1, len(samples)-1), 6),
                         'sample_rate_hz': sample_rate, 'sample_count': len(samples),
                         'speaker_identity': None, 'prosody_model': 'UNAVAILABLE',
                         'non_speech_classifier': 'UNAVAILABLE'}, teacher_text)

def ui_fixture(start_ms, end_ms, consent_scope, *, node_count, phase='final'):
    if not isinstance(node_count, int) or node_count < 0:
        raise ValueError('invalid node count')
    return TimedPercept('android_ui', 'accessibility_fixture', start_ms, end_ms,
                        consent_scope, 'synthetic', phase,
                        {'node_count': node_count, 'screen_pixels': None,
                         'action_authority': False})
