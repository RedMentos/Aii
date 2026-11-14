"""Bounded synthetic/authorized PCM feature adapter for existing A5 contract.

No microphone access or consent creation. Source hash and consent receipt must
be supplied by independently authorized capture layer.
"""
import math
from .audio_percept_contract import audio_percept_packet


def pcm16_to_a5(*, pcm, sample_rate, start_ms, event_id, generation_id,
                source_id, source_sha256, consent_receipt, finality="PROVISIONAL"):
    if not isinstance(pcm, (bytes, bytearray, memoryview)):
        raise TypeError("PCM must be bytes-like")
    if type(sample_rate) is not int or not 8000 <= sample_rate <= 192000:
        raise ValueError("invalid sample rate")
    if not pcm or len(pcm) % 2 or len(pcm) > sample_rate * 2:
        raise ValueError("PCM16 must contain 1..sample_rate samples")
    n = len(pcm) // 2
    duration_ms = (n * 1000) // sample_rate
    if duration_ms < 1:
        raise ValueError("minimum duration 1 ms")
    values = [int.from_bytes(pcm[i:i+2], "little", signed=True) / 32768.0
              for i in range(0, len(pcm), 2)]
    rms = math.sqrt(sum(x*x for x in values) / n)
    zcr = sum((a < 0) != (b < 0) for a, b in zip(values, values[1:])) / max(1, n-1)
    return audio_percept_packet(
        event_id=event_id, generation_id=generation_id,
        source_id=source_id, source_sha256=source_sha256,
        start_ms=start_ms, end_ms=start_ms+duration_ms,
        rms=rms, zcr=zcr, finality=finality,
        consent_receipt=consent_receipt)
