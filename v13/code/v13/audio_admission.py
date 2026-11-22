"""A-plane timed acoustic admission: synthetic/consented metadata, never raw microphone capture.

No ASR authority, Android permission acquisition, or model-weight promotion.
"""
from dataclasses import dataclass
from math import isfinite
import hashlib
import json

@dataclass(frozen=True)
class AcousticFrame:
    start_ms: int
    end_ms: int
    rms: float
    pitch_hz: float | None = None
    voiced: bool = False
    non_speech: str | None = None
    speaker_hint: str | None = None
    provisional: bool = True

def admit_audio(frames, *, consent, source_id, max_frames=32, max_bytes=2048):
    """Create bounded A5 metadata for B/C. Fail closed rather than silently lose evidence."""
    if consent is not True:
        raise PermissionError("audio metadata requires explicit capture/use consent")
    if not isinstance(source_id, str) or not source_id or len(source_id)>128:
        raise ValueError("invalid source reference")
    if type(max_frames) is not int or not 1<=max_frames<=256:
        raise ValueError("invalid frame bound")
    if type(max_bytes) is not int or not 256<=max_bytes<=16384:
        raise ValueError("invalid byte bound")
    sequence=list(frames)
    if len(sequence)>max_frames:
        return {"status":"REJECTED_BUDGET","source_id":source_id,
                "frame_count":len(sequence),"accepted":False}
    previous=-1
    encoded=[]
    for frame in sequence:
        if not isinstance(frame,AcousticFrame):
            raise TypeError("expected AcousticFrame")
        if type(frame.start_ms) is not int or type(frame.end_ms) is not int or frame.start_ms<0 or frame.end_ms<=frame.start_ms or frame.start_ms<previous:
            raise ValueError("non-monotonic audio timestamps")
        previous=frame.end_ms
        if not isfinite(frame.rms) or not 0<=frame.rms<=1:
            raise ValueError("invalid RMS")
        if frame.pitch_hz is not None and (not isfinite(frame.pitch_hz) or not 0<frame.pitch_hz<4000):
            raise ValueError("invalid pitch")
        for value in (frame.non_speech,frame.speaker_hint):
            if value is not None and (not isinstance(value,str) or len(value)>48 or any(ord(c)<32 for c in value)):
                raise ValueError("invalid annotation")
        encoded.append({"t0":frame.start_ms,"t1":frame.end_ms,"rms":round(frame.rms,5),
                        "pitch_hz":frame.pitch_hz,"voiced":bool(frame.voiced),
                        "non_speech":frame.non_speech,"speaker_hint":frame.speaker_hint,
                        "provenance":"PROVISIONAL" if frame.provisional else "FINAL"})
    canonical=json.dumps(encoded,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    if len(canonical)>max_bytes:
        return {"status":"REJECTED_BUDGET","source_id":source_id,
                "frame_count":len(sequence),"accepted":False}
    return {"status":"A5_ACOUSTIC_METADATA","source_id":source_id,"accepted":True,
            "modality":"audio_features","raw_audio_included":False,
            "teacher_asr_authority":False,"frames":encoded,
            "sha256":hashlib.sha256(canonical).hexdigest(),"bytes":len(canonical)}
