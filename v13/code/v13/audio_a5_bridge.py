"""Loss-minimizing RAW EAR -> existing A5 timed-percept adapter (observation only).

Acoustic details remain in AudioPercept; A5 is a reduced routing view.
No microphone access, authority escalation, or model inference.
"""
from .audio_raw_ear_contract import AudioPercept
from .timed_percept import TimedPercept, provisional_to_final


def to_a5_audio(packet: AudioPercept) -> TimedPercept:
    packet.validate()
    # A5 has no peak/ZCR fields: callers must retain the RAW EAR packet.
    # Never represent imported/Android data as Android-verified.
    provenance = "teacher" if packet.teacher_transcript is not None else "synthetic"
    return TimedPercept(
        modality="audio", source=packet.source_id,
        start_ms=packet.start_ms, end_ms=packet.end_ms,
        consent_id=packet.consent_scope, stage=packet.phase,
        provenance=provenance, rms=packet.rms,
        speech_probability=packet.speech_probability,
        transcript=packet.teacher_transcript,
    )


def finalize_audio(old: AudioPercept, new: AudioPercept):
    """Validate lineage before accepting a revised observation."""
    old.validate()
    new.validate()
    if (old.sample_rate_hz, old.channel_count) != (new.sample_rate_hz, new.channel_count):
        raise ValueError("PCM format changed across revision")
    return provisional_to_final(to_a5_audio(old), to_a5_audio(new))
