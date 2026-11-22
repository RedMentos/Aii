"""Consent-bound, transcript-independent PCM16 A-plane acoustic observations.

No microphone access, persistence, speaker identity inference, or native-model claim.
The caller owns audio capture and must supply explicit permission and a source digest.
"""
import math
import struct
from hashlib import sha256


def observe_pcm16(pcm, sample_rate, start_ms, *, consent, source_id, max_seconds=5):
    if consent is not True:
        raise PermissionError('audio observation requires explicit consent')
    if not isinstance(pcm, (bytes, bytearray)) or len(pcm) % 2:
        raise ValueError('expected complete little-endian mono PCM16 bytes or mutable buffer')
    if not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 48000:
        raise ValueError('sample_rate must be 8000..48000')
    if not isinstance(start_ms, int) or start_ms < 0 or not isinstance(source_id, str) or not source_id:
        raise ValueError('invalid time or source id')
    n = len(pcm) // 2
    if not n or n > sample_rate * max_seconds:
        raise ValueError('empty or over-budget audio')
    samples = struct.unpack('<' + 'h' * n, pcm)
    energy = sum(x*x for x in samples) / n
    rms = math.sqrt(energy) / 32768
    peak = max(abs(x) for x in samples) / 32768
    crossings = sum((a < 0) != (b < 0) for a,b in zip(samples,samples[1:]))
    return {'modality':'audio', 'source_ref':{'source_id':source_id,
            'sha256':sha256(pcm).hexdigest(),'char_start':0,'char_end':len(pcm),
            'modality':'audio/pcm16le'}, 'segments':[{'start_ms':start_ms,
            'end_ms':start_ms + (1000*n)//sample_rate,
            'acoustic':{'rms':round(rms,6),'peak':round(peak,6),
                        'zero_crossing_rate':round(crossings/max(1,n-1),6)},
            'transcript':None,'provenance':'RAW_EAR_PCMC16',
            'finality':'FINAL_WINDOW','speaker_identity':None}],
            'authority':'ACOUSTIC_FEATURES_ONLY','learning_authority':False}
