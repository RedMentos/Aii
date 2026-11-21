"""Strict SHADOW bridge from A5 RAW EAR packets to bounded C3 percept admission.

Does not authorize capture, infer consent from a receipt, or perform native tokenization.
"""
from .percept_admission import Percept, admit


def audio_to_admission(packet, *, consent_active: bool, priority: int = 0):
    """Return an admission candidate only after *current* external consent check.

    A packet receipt is provenance, never proof that Android permission is still active.
    PROVISIONAL events are retained upstream, not promoted into prompt truth.
    """
    if type(consent_active) is not bool or not consent_active:
        raise PermissionError("current external audio consent required")
    if type(priority) is not int or not -100 <= priority <= 100:
        raise ValueError("invalid priority")
    if not isinstance(packet, dict) or packet.get("modality") != "audio":
        raise ValueError("expected A5 audio packet")
    source = packet.get("source_ref")
    segments = packet.get("segments")
    if not isinstance(source, dict) or not isinstance(segments, list) or len(segments) != 1:
        raise ValueError("invalid A5 source/segments")
    sid = source.get("source_id")
    digest = source.get("sha256")
    if not isinstance(sid, str) or not sid or len(sid) > 128:
        raise ValueError("invalid source ID")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid source hash")
    seg = segments[0]
    if not isinstance(seg, dict) or not isinstance(seg.get("consent_receipt_ref"), str) or not seg["consent_receipt_ref"].strip():
        raise PermissionError("missing receipt reference")
    start, end = seg.get("start_ms"), seg.get("end_ms")
    if type(start) is not int or type(end) is not int or not 0 <= start < end or end-start > 1000:
        raise ValueError("invalid interval")
    finality = seg.get("finality")
    if finality not in ("FINAL", "PROVISIONAL"):
        raise ValueError("invalid finality")
    acoustic = seg.get("acoustic")
    if not isinstance(acoustic, dict):
        raise ValueError("missing acoustic features")
    import math
    values = []
    for key in ("rms", "zcr"):
        value = acoustic.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("invalid acoustic feature")
        values.append(float(value))
    if seg.get("learning_authority") is not False or seg.get("action_authority") is not False:
        raise PermissionError("audio observation cannot grant authority")
    summary = f"audio rms={values[0]:.3f} zcr={values[1]:.3f} interval_ms={end-start}"
    return Percept(sid, "audio", start, end, summary, True, finality == "FINAL", priority)


def admit_audio(packet, *, consent_active: bool, token_budget: int):
    candidate = audio_to_admission(packet, consent_active=consent_active)
    return admit((candidate,), token_budget)
