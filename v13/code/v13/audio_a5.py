"""Synthetic RAW EAR -> persisted A5 PerceptPacket, no Android capture authority.

A0 must first persist a canonical source descriptor as an EventEnvelope.
The descriptor is NOT a microphone permission receipt. The PCM hash is bound
to the acoustic packet, and source integrity is rechecked before A5 persistence.
"""
from __future__ import annotations
from .contracts import packet

def audio_source_descriptor(raw):
    """Exact A0 text to store as an event; never includes raw PCM or ASR."""
    return "v13.audio_pcm_sha256:" + raw.source_sha256 + "\\n"

def persist_audio_percept(store, event, raw):
    """Persist timed acoustic A5 observations with zero native/action authority.

    Only synthetic or externally pre-authorized PCM may reach this path.
    Android permissions MUST be independently enforced by Core/QA bridge.
    """
    ref = event["source_ref"]
    if ref.get("modality") != "text":
        raise ValueError("A0 descriptor must be a text SourceRef")
    descriptor = store.read_source(ref)
    if descriptor != audio_source_descriptor(raw):
        raise ValueError("RAW EAR PCM hash does not match persisted A0 descriptor")
    if event.get("event_id") is None or event.get("brain_generation_id") is None:
        raise ValueError("persisted event identity required")
    if raw.asr_text is not None:
        raise ValueError("ASR must use a separately verified teacher source")
    if not raw.frames or raw.duration_ms <= 0:
        raise ValueError("empty RAW EAR")
    segments = [
        {"start_ms": f.start_ms, "end_ms": f.end_ms, "rms": f.rms,
         "pitch_hz": f.pitch_hz, "voiced_probability": f.voiced_probability,
         "non_speech_probability": f.non_speech_probability,
         "source_ref": ref}
        for f in raw.frames
    ]
    percept = packet(
        "PerceptPacket", "A5_PERCEPT", event["event_id"],
        event["brain_generation_id"], [ref], source_ref=ref,
        segments=segments, modality="audio_acoustic",
        raw_ear=raw.to_record(), native_receiver_authority=0,
        android_capture_verified=False, action_authority=0,
        training_authority=0,
    )
    return store.add_packet("PerceptPacket", percept)
