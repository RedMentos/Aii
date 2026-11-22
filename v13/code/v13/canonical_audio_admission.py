"""Canonical A5 audio -> bounded JEF admission envelope.

Does not grant Android microphone, action, learning, or source-truth authority.
The raw PerceptPacket stays outside C3 prompts; caller retains source for lookup.
"""
from .a5_admission import admit_a5

def admit_canonical_audio(percept, *, consent=False, max_bytes=320):
    if not isinstance(percept, dict) or percept.get("modality") != "audio":
        raise ValueError("A5_AUDIO_REQUIRED")
    source = percept.get("source_ref")
    segments = percept.get("segments")
    if not isinstance(source, dict) or source.get("modality") != "audio":
        raise ValueError("A5_SOURCE_REQUIRED")
    if not isinstance(segments, list) or not 1 <= len(segments) <= 8:
        raise ValueError("A5_SEGMENTS_REQUIRED")
    if not isinstance(source.get("source_id"), str) or not source["source_id"]:
        raise ValueError("A5_SOURCE_ID_REQUIRED")
    if not isinstance(source.get("sha256"), str) or len(source["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in source["sha256"]):
        raise ValueError("A5_SOURCE_HASH_INVALID")
    for segment in segments:
        if not isinstance(segment, dict) or segment.get("action_authority") is not False or segment.get("learning_authority") is not False:
            raise PermissionError("A5_AUTHORITY_DENIED")
        if not isinstance(segment.get("consent_receipt_ref"), str) or not segment["consent_receipt_ref"].strip():
            raise PermissionError("A5_RECEIPT_REQUIRED")
        if segment.get("finality") not in ("FINAL", "PROVISIONAL"):
            raise ValueError("A5_FINALITY_INVALID")
        if type(segment.get("start_ms")) is not int or type(segment.get("end_ms")) is not int or not 0 <= segment["start_ms"] < segment["end_ms"]:
            raise ValueError("A5_TIME_INVALID")
    status = "FINAL" if all(s["finality"] == "FINAL" for s in segments) else "PROVISIONAL"
    # No acoustic values, ASR transcript, source ID or untrusted teacher text
    # enter the JEF/C3 prompt envelope.
    return admit_a5({"schema":"v13.a5.audio/1",
                     "source":{"id":source["source_id"],"authorized":True,"modality":"audio",
                               "sha256":source["sha256"]},
                     "status":status,"action_authority":False,
                     "learning_authority":False}, consent=consent, max_bytes=max_bytes)
