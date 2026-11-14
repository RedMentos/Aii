"""Bounded, read-only A5 audio observation for B/C organ input (SHADOW).

This is not an action intent, learning authorization, transcript or OS consent.
The runtime must supply a source reader backed by its real SourceStore.
"""
from .audio_source_gate import checked_audio_source_view


def audio_shadow_observation(percept_packet, read_source):
    """Validate source at consumption and emit a small B/C-readable observation.

    Reject provisional packets for final memory claims by preserving finality.
    Never return raw samples, transcript, speaker identity or consent tokens.
    """
    view = checked_audio_source_view(percept_packet, read_source)
    segments = view["segments"]
    if len(segments) > 64:
        raise ValueError("audio segment budget")
    return {
        "kind": "A5_AUDIO_OBSERVATION",
        "modality": "audio",
        "event_id": view["event_id"],
        "brain_generation_id": view["brain_generation_id"],
        "source_ref": view["source_ref"],
        "finality": "FINAL" if all(s["finality"] == "FINAL" for s in segments) else "PROVISIONAL",
        "windows": [
            {"start_ms": s["start_ms"], "end_ms": s["end_ms"],
             "rms": s["acoustic"]["rms"], "zcr": s["acoustic"]["zcr"],
             "finality": s["finality"]}
            for s in segments
        ],
        "interpretation": "UNINTERPRETED_ACOUSTIC_FEATURES",
        "authority": "SHADOW_ONLY",
        "action_authority": False,
        "learning_authority": False,
        "semantic_truth_authority": False,
    }
