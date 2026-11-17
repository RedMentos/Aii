"""A-plane timed RAW EAR observation contract; no microphone access or ASR-only collapse.

A consented Android capture adapter must supply source refs and acoustic measurements.
This module neither captures nor persists raw recordings and never grants model truth.
"""
import math

FEATURES=("rms","peak","pitch_hz","voicing","speech_probability","noise_probability","energy_delta")
def audio_observation(source_ref, *, start_ms, end_ms, features, consent, finality="PROVISIONAL", teacher=None):
    if not isinstance(source_ref,dict) or source_ref.get("modality")!="audio":
        raise ValueError("audio source reference required")
    if consent is not True:raise PermissionError("explicit audio capture consent required")
    if finality not in ("PROVISIONAL","FINAL"):raise ValueError("invalid finality")
    if any(isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) for t in (start_ms,end_ms)):
        raise ValueError("invalid timestamp")
    if not 0<=start_ms<end_ms:raise ValueError("invalid time window")
    if not isinstance(features,dict) or not features:raise ValueError("acoustic features required")
    if any(k not in FEATURES for k in features):raise ValueError("unsupported acoustic feature")
    for k,v in features.items():
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
            raise ValueError("nonfinite acoustic feature")
        if k in ("rms","peak","voicing","speech_probability","noise_probability") and not 0<=v<=1:
            raise ValueError("normalized feature out of range")
        if k=="pitch_hz" and not 0<=v<=2000:raise ValueError("pitch out of range")
    if teacher is not None:
        if not isinstance(teacher,dict) or teacher.get("kind")!="ASR" or not isinstance(teacher.get("text"),str):
            raise ValueError("invalid optional teacher")
        if teacher.get("source_ref")!=source_ref:raise ValueError("teacher provenance mismatch")
    return {"source_ref":source_ref,"modality":"audio","start_ms":start_ms,"end_ms":end_ms,
            "acoustic_features":dict(features),"finality":finality,"teacher":teacher,
            "speaker_identity":"UNKNOWN","capture_consent":True,
            "truth_authority":0,"native_receiver_authority":0,"learning_authority":0}

def persist_audio_percept(store,event,source_ref,**kwargs):
    """A5 packet usable by existing packet store and downstream C/B packet readers."""
    from .contracts import packet
    obs=audio_observation(source_ref,**kwargs)
    if source_ref.get("source_id")!=event["source_ref"].get("source_id"):
        raise ValueError("source belongs to another event")
    p=packet("PerceptPacket","A5_PERCEPT",event["event_id"],event["brain_generation_id"],
             [source_ref],segments=[],**obs)
    return store.add_packet("PerceptPacket",p)
