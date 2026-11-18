"""RAW EAR acoustic enrichment, without ASR replacing the canonical A5 packet.

This adapter consumes an authorized A5 packet and adds measured acoustic cues.
It never captures audio, infers speaker identity, or authorizes an Android action.
"""
import copy
import math

def enrich_audio_percept(percept, *, pitch_hz=None, voiced_probability=None,
                         teacher_text=None, teacher_source=None):
    if not isinstance(percept, dict) or percept.get("modality") != "audio":
        raise ValueError("canonical audio percept required")
    segments = percept.get("segments")
    if not isinstance(segments, list) or len(segments) != 1:
        raise ValueError("single bounded acoustic segment required")
    segment = segments[0]
    if not segment.get("consent_receipt_ref") or segment.get("action_authority") is not False:
        raise PermissionError("authorized observation-only input required")
    for name, value, maximum in (("pitch_hz", pitch_hz, 2000), ("voiced_probability", voiced_probability, 1)):
        if value is not None and (type(value) not in (int, float) or
                                  not math.isfinite(value) or not 0 <= value <= maximum):
            raise ValueError("invalid " + name)
    if teacher_text is not None:
        if not isinstance(teacher_text, str) or len(teacher_text) > 2048:
            raise ValueError("teacher text invalid")
        if not isinstance(teacher_source, str) or not teacher_source.strip() or len(teacher_source) > 128:
            raise ValueError("teacher source required")
    result = copy.deepcopy(percept)
    target = result["segments"][0]
    if pitch_hz is not None:
        target["acoustic"]["pitch_hz"] = float(pitch_hz)
    if voiced_probability is not None:
        target["acoustic"]["voiced_probability"] = float(voiced_probability)
    target["unmeasured"] = [name for name in target.get("unmeasured", [])
                            if not ((name == "pitch" and pitch_hz is not None) or
                                    (name == "speech_probability" and voiced_probability is not None))]
    if teacher_text is not None:
        target["teacher_asr"] = {"text": teacher_text, "source": teacher_source,
                                 "trusted": False, "learning_authority": False}
    return result
