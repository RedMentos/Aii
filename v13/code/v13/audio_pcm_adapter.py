"""Bounded PCM16 RAW EAR feature adapter; no microphone permission or live capture.

Caller supplies independently authorized source hash and consent receipt.
Only aggregate acoustic features enter A5; raw PCM is not persisted here.
"""
import math
import struct
from .audio_percept_contract import audio_percept_packet


def pcm16_to_a5(*, pcm, sample_rate, start_ms, event_id, generation_id,
                source_id, source_sha256, consent_receipt, finality="PROVISIONAL"):
    # Reject unauthorized input before any PCM traversal or feature computation.
    if not isinstance(consent_receipt, str) or not consent_receipt.strip():
        raise PermissionError("explicit local audio consent receipt required")
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
    # Streaming accumulation: no per-sample Python float array, bounded memory.
    power = 0.0
    crossings = 0
    previous_negative = None
    for (sample,) in struct.iter_unpack("<h", pcm):
        x = sample / 32768.0
        power += x * x
        negative = sample < 0
        if previous_negative is not None and previous_negative != negative:
            crossings += 1
        previous_negative = negative
    rms = math.sqrt(power / n)
    zcr = crossings / max(1, n - 1)
    return audio_percept_packet(
        event_id=event_id, generation_id=generation_id,
        source_id=source_id, source_sha256=source_sha256,
        start_ms=start_ms, end_ms=start_ms + duration_ms,
        rms=rms, zcr=zcr, finality=finality,
        consent_receipt=consent_receipt)
