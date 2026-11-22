"""Bridge V14 offline PCM feature packets to existing V13 A5 audio admission.

No capture, action, learning, or Android permission authority is granted.
"""
from .timed_perception import validate_packet_sequence


def to_v13_a5_audio(packets, source, *, consent_active: bool):
    """Return V13 admission-compatible packets; caller checks current OS consent."""
    if consent_active is not True:
        raise PermissionError("CURRENT_AUDIO_CONSENT_REQUIRED")
    validate_packet_sequence(packets, source)
    if not packets:
        return []
    from v13.a5_audio_admission_bridge import audio_to_admission
    result = []
    for packet in packets:
        if packet["sample_end"] <= packet["sample_start"]:
            raise ValueError("EMPTY_AUDIO_FRAME")
        # V13 bridge requires positive millisecond intervals.
        start = packet["time_start_ms"]
        end = packet["time_end_ms"]
        if end <= start:
            end = start + 1
        v13_packet = {
            "modality": "audio",
            "source_ref": {"source_id": (source.source_id[:80] + ":" + str(packet["sample_start"])), "sha256": source.pcm_sha256},
            "segments": [{
                "consent_receipt_ref": source.consent_id,
                "start_ms": start, "end_ms": end,
                "finality": "PROVISIONAL" if source.provisional else "FINAL",
                "acoustic": {"rms": packet["rms"], "zcr": packet["zero_crossing_rate"]},
                "learning_authority": False, "action_authority": False,
            }],
        }
        # Invoke actual existing consumer validation rather than treating JSON as integration.
        percept = audio_to_admission(v13_packet, consent_active=consent_active)
        result.append(percept)
    return result
