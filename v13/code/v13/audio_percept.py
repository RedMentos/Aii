"""A-plane timed RAW EAR contract. Source-bound metadata only; no microphone capture.
Audio features are observations, not ASR truth, identity, or learning permission.
"""
import math

def timed_audio_percept(source_ref, frames, *, consent, capture_id, sample_rate_hz, provisional=True, teacher=None):
    if consent is not True:
        raise PermissionError("explicit audio input consent required")
    if not isinstance(source_ref,dict) or not source_ref.get("source_id"):
        raise ValueError("source_ref required")
    if not isinstance(capture_id,str) or not capture_id or len(capture_id)>128:
        raise ValueError("bounded capture_id required")
    if type(sample_rate_hz) is not int or not 8000<=sample_rate_hz<=192000:
        raise ValueError("sample rate out of range")
    if not isinstance(frames,list) or not 1<=len(frames)<=4096:
        raise ValueError("bounded nonempty audio frames required")
    cleaned=[];previous_end=-1
    for frame in frames:
        if not isinstance(frame,dict):
            raise ValueError("invalid frame")
        start,end=frame.get("start_ms"),frame.get("end_ms")
        if any(type(x) is not int for x in (start,end)) or start<0 or end<=start or start<previous_end:
            raise ValueError("nonmonotonic or invalid timestamps")
        if end-start>10000:
            raise ValueError("audio frame exceeds 10s")
        features={}
        for key in ("rms","pitch_hz","voicing","spectral_flux"):
            value=frame.get(key)
            if value is not None:
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                    raise ValueError("invalid acoustic feature")
                if key in ("rms","voicing") and value>1:
                    raise ValueError("normalized feature out of range")
                features[key]=float(value)
        cleaned.append({"start_ms":start,"end_ms":end,"acoustic":features,
                        "non_speech":bool(frame.get("non_speech",False)),
                        "speaker_track":str(frame.get("speaker_track","unknown"))[:64]})
        previous_end=end
    if teacher is not None:
        if not isinstance(teacher,dict) or teacher.get("status") not in ("PROVISIONAL","FINAL") or not isinstance(teacher.get("transcript"),str):
            raise ValueError("teacher must carry provenance/status")
        teacher={"status":teacher["status"],"transcript":teacher["transcript"][:4096],
                 "model_revision":str(teacher.get("model_revision","unknown"))[:128],
                 "authority":"UNTRUSTED_TEACHER_HYPOTHESIS"}
    return {"modality":"audio","source_ref":source_ref,"capture_id":capture_id,
            "sample_rate_hz":sample_rate_hz,"frames":cleaned,
            "provenance_status":"PROVISIONAL" if provisional else "FINAL",
            "teacher_ear":teacher,"raw_audio_embedded":False,
            "learning_authority":0,"native_receiver_authority":0,
            "android_capture_verified":False}
