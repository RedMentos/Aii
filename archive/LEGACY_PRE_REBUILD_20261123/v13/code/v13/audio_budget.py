"""Loss-aware bounded A5 acoustic summary; no capture, ASR inference or action authority."""
from math import isfinite


def summarize_acoustics(packet, max_frames=8):
    """Preserve boundary and salient derived events; report lossy omission explicitly."""
    if not isinstance(max_frames, int) or isinstance(max_frames, bool) or not 2 <= max_frames <= 32:
        raise ValueError("max_frames must be an integer in [2,32]")
    envelope = packet.percept_packet()
    frames = envelope["acoustics"]
    if not frames:
        raise ValueError("empty acoustics")
    if any(not isfinite(f["rms"]) or not isfinite(f["speech_probability"]) for f in frames):
        raise ValueError("non-finite feature")
    keep = {0, len(frames) - 1}
    if len(frames) > max_frames:
        ranked = sorted(range(1, len(frames) - 1), key=lambda i: (
            bool(frames[i]["non_speech"]), frames[i]["speech_probability"],
            frames[i]["rms"], -i), reverse=True)
        keep.update(ranked[:max_frames - len(keep)])
    selected = [frames[i] for i in sorted(keep)] if len(frames) > max_frames else frames
    return {
        "schema": "v13.a5.audio-budget/1",
        "source": envelope["source"], "consent_scope": envelope["consent_scope"],
        "provenance": envelope["provenance"], "start_ms": envelope["start_ms"],
        "end_ms": envelope["end_ms"], "provisional": envelope["provisional"],
        "teacher_asr": envelope["teacher_asr"], "acoustics": selected,
        "total_frames": len(frames), "omitted_frames": len(frames) - len(selected),
        "lossy": len(frames) != len(selected), "a3_projector": "UNAVAILABLE",
        "android_capture": "UNVERIFIED", "action_authority": False,
    }
