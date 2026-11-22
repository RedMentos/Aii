"""Consent-bound, transcript-independent PCM16 A-plane acoustic observations.

No microphone access, persistence, speaker identity inference, or native-model claim.
The caller owns capture. Mutable sample copies are overwritten after feature extraction.
"""
import math
from hashlib import sha256

from .audio_pcm_memory import pcm16_byte_view, pcm16_sample_buffer


def observe_pcm16(pcm, sample_rate, start_ms, *, consent, source_id, max_seconds=5):
    if consent is not True:
        raise PermissionError('audio observation requires explicit consent')
    view = pcm16_byte_view(pcm)
    if not view.nbytes:
        raise ValueError('empty or over-budget audio')
    if not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 48000:
        raise ValueError('sample_rate must be 8000..48000')
    if not isinstance(start_ms, int) or start_ms < 0 or not isinstance(source_id, str) or not source_id:
        raise ValueError('invalid time or source id')
    n = view.nbytes // 2
    if n > sample_rate * max_seconds:
        raise ValueError('empty or over-budget audio')
    with pcm16_sample_buffer(view) as samples:
        energy = sum(x * x for x in samples) / n
        rms = math.sqrt(energy) / 32768
        peak = max(abs(x) for x in samples) / 32768
        crossings = sum((a < 0) != (b < 0) for a, b in zip(samples, samples[1:]))
        digest = sha256(view).hexdigest()
        return {
            'modality': 'audio',
            'source_ref': {
                'source_id': source_id,
                'sha256': digest,
                'char_start': 0,
                'char_end': view.nbytes,
                'modality': 'audio/pcm16le',
            },
            'segments': [{
                'start_ms': start_ms,
                'end_ms': start_ms + (1000 * n) // sample_rate,
                'acoustic': {
                    'rms': round(rms, 6),
                    'peak': round(peak, 6),
                    'zero_crossing_rate': round(crossings / max(1, n - 1), 6),
                },
                'transcript': None,
                'provenance': 'RAW_EAR_PCMC16',
                'finality': 'FINAL_WINDOW',
                'speaker_identity': None,
            }],
            'authority': 'ACOUSTIC_FEATURES_ONLY',
            'learning_authority': False,
        }
