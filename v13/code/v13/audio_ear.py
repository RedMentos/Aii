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
    if not isinstance(pcm, bytes) or len(pcm) % 2:
        raise ValueError('expected complete little-endian mono PCM16 bytes')
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


def observe_pcm16_for_a5(pcm, sample_rate, start_ms, *, consent,
                         source_id, consent_receipt_ref, max_seconds=1):
    """Convert a consented PCM window to the existing strict A5 audio admission contract.

    The receipt is a reference only; external Android permission MUST be rechecked
    by audio_to_admission(consent_active=...). No audio bytes are persisted.
    """
    if not isinstance(consent_receipt_ref, str) or not consent_receipt_ref.strip() or len(consent_receipt_ref) > 256:
        raise PermissionError("nonempty bounded external consent receipt reference required")
    if type(max_seconds) is not int or max_seconds != 1:
        raise ValueError("A5 admission permits at most one second")
    packet = observe_pcm16(pcm, sample_rate, start_ms, consent=consent,
                           source_id=source_id, max_seconds=max_seconds)
    segment = packet["segments"][0]
    if segment["end_ms"] <= segment["start_ms"]:
        raise ValueError("audio window must have positive millisecond duration")
    segment["acoustic"]["zcr"] = segment["acoustic"]["zero_crossing_rate"]
    segment["consent_receipt_ref"] = consent_receipt_ref
    segment["finality"] = "FINAL"
    segment["learning_authority"] = False
    segment["action_authority"] = False
    return packet
