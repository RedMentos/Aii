"""Consent-bound timed RAW EAR metadata -> A5 percept -> JEF consumer.
No microphone capture, no ASR, no storage of private waveform or transcript.
Synthetic contract until native Android acquisition and latency are verified.
"""
import math
import time

FEATURES = ("rms", "pitch_hz", "voicing", "speech_probability", "noise_probability")
MAX_FRAMES = 256

def timed_ear_packet(source_ref, frames, *, consent, provisional=True, teacher=None):
    if consent is not True:
        raise PermissionError("audio observation requires explicit local consent")
    if not isinstance(source_ref, str) or not source_ref or len(source_ref) > 256:
        raise ValueError("source_ref must be a bounded opaque local reference")
    if not isinstance(frames, (list, tuple)) or not 1 <= len(frames) <= MAX_FRAMES:
        raise ValueError("bounded nonempty frames required")
    clean = []
    last_end = -1
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("invalid frame")
        start, end = frame.get("start_ms"), frame.get("end_ms")
        if type(start) is not int or type(end) is not int or start < 0 or end <= start or start < last_end:
            raise ValueError("nonmonotonic frame timestamps")
        if end - start > 10000:
            raise ValueError("frame too long")
        features = {}
        for name in FEATURES:
            value = frame.get(name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("invalid acoustic feature")
            if name in ("voicing", "speech_probability", "noise_probability") and value > 1:
                raise ValueError("probability out of range")
            features[name] = float(value)
        clean.append({"start_ms": start, "end_ms": end, "acoustics": features})
        last_end = end
    if teacher is not None:
        if not isinstance(teacher, dict) or teacher.get("source_ref") != source_ref or teacher.get("kind") not in ("ASR", "ACOUSTIC"):
            raise ValueError("teacher provenance must match source")
        if not isinstance(teacher.get("model_revision"), str) or not teacher["model_revision"]:
            raise ValueError("teacher revision required")
        # Never insert teacher free-text into a source-authoritative packet.
        teacher = {"kind": teacher["kind"], "model_revision": teacher["model_revision"],
                   "source_ref": source_ref, "authority": "HYPOTHESIS"}
    return {"schema": "v13.a5.timed-ear/1", "modality": "AUDIO_RAW_EAR",
            "source_ref": source_ref, "provisional": bool(provisional),
            "time_start_ms": clean[0]["start_ms"], "time_end_ms": clean[-1]["end_ms"],
            "frames": clean, "teacher": teacher, "authority": "OBSERVED_ACOUSTIC_FEATURES",
            "android_verified": False}

def deliver_to_jef(runtime, packet, *, consent):
    """Actual consumer contract: bounded A5 -> executive log; no action or weight edit.
    Runtime must expose a persistent store; this function is explicitly invoked by
    an authorized Android acquisition adapter, never by a background microphone.
    """
    if consent is not True:
        raise PermissionError("consent revoked")
    if not isinstance(packet, dict) or packet.get("schema") != "v13.a5.timed-ear/1":
        raise ValueError("not an A5 timed-ear packet")
    if packet.get("android_verified") is not False:
        raise ValueError("caller cannot assert native verification")
    summary = {"modality": packet["modality"], "source_ref": packet["source_ref"],
               "start_ms": packet["time_start_ms"], "end_ms": packet["time_end_ms"],
               "frames": len(packet["frames"]), "provisional": packet["provisional"],
               "teacher_kind": (packet["teacher"] or {}).get("kind"),
               "authority": packet["authority"], "gate": "WIRED_SYNTHETIC_NOT_NATIVE"}
    runtime.store.log("a5_timed_ear_observed", None, summary)
    return summary
