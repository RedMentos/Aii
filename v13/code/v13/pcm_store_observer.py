"""Explicitly authorized synthetic PCM -> real SQLite Store -> A3 shadow inference.

This is not a microphone capture API, Android permission check or canonical A5
promotion. The caller must independently establish the right to use the PCM.
"""
from .pcm_bridge import pcm_to_timed_source
from .a3_timed_audio import observe_timed_audio

def observe_stored_pcm(runtime, projector, pcm, sample_rate_hz, *,
                       consent=False, start_ms=0, frame_ms=20, final=True):
    if consent is not True:
        raise PermissionError("explicit source consent required")
    store = getattr(runtime, "store", None)
    if not callable(getattr(store, "source", None)) or not callable(getattr(store, "read_source", None)):
        raise TypeError("real V13 Store.source/read_source required")
    # Validate the entire bounded observation before creating persistent data.
    raw = pcm_to_timed_source(pcm, sample_rate_hz, start_ms=start_ms,
                              frame_ms=frame_ms, final=final)
    if final is not True:
        raise PermissionError("provisional audio cannot enter A3 final evidence")
    ref = store.source(raw, kind="AUTHORIZED_SYNTHETIC_AUDIO")
    result = observe_timed_audio(runtime, projector, ref)
    return {"source_ref": ref, "observation": result}
