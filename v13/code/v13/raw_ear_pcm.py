"""Bounded local PCM16 RAW EAR acoustic features; no microphone access or ASR.

Caller owns OS consent, source registration and lifecycle. Input bytes never persist
or leave this function. This is a deterministic feature baseline, not a teacher.
"""
from math import sqrt
from .audio_percept_contract import audio_percept_packet


def pcm16_audio_percept(*, pcm, sample_rate, event_id, generation_id,
                        source_id, source_sha256, consent_receipt,
                        start_ms=0, finality="FINAL"):
    """Convert a <=1-second mono signed little-endian PCM16 frame to A5.

    Source hash must refer to a separately registered source; this routine does
    not register or authorize the source. Consumer must revalidate it.
    """
    if type(sample_rate) is not int or not 8000 <= sample_rate <= 48000:
        raise ValueError("unsupported sample rate")
    if not isinstance(pcm, bytes) or len(pcm) < 4 or len(pcm) % 2:
        raise ValueError("PCM16 requires at least two complete samples")
    count = len(pcm) // 2
    if count > sample_rate:
        raise ValueError("audio frame exceeds one-second budget")
    # The packet time range is integral milliseconds: require exact ms frames
    # rather than silently misrepresenting a sub-ms source interval.
    if (count * 1000) % sample_rate:
        raise ValueError("frame duration must be whole milliseconds")
    duration_ms = count * 1000 // sample_rate
    previous = None
    crossings = 0
    square_sum = 0
    for offset in range(0, len(pcm), 2):
        sample = int.from_bytes(pcm[offset:offset+2], "little", signed=True)
        square_sum += sample * sample
        sign = 1 if sample > 0 else -1 if sample < 0 else 0
        if previous is not None and sign and previous and sign != previous:
            crossings += 1
        if sign:
            previous = sign
    rms = sqrt(square_sum / count) / 32768.0
    zcr = crossings / (count - 1)
    return audio_percept_packet(
        event_id=event_id, generation_id=generation_id,
        source_id=source_id, source_sha256=source_sha256,
        start_ms=start_ms, end_ms=start_ms+duration_ms,
        rms=rms, zcr=zcr, finality=finality,
        consent_receipt=consent_receipt,
    )
