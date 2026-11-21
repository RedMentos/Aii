"""Bounded RAW EAR -> canonical A5 PerceptPacket. Not Android microphone authorization."""
import math
import re
from .contracts import packet, validate

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ACTIVITY_HINTS = {"SILENCE", "VOICED", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN"}


def validate_voice_cues(voice_cues):
    """Validate heuristic acoustic cues; these are not speaker identity or calibrated VAD."""
    if voice_cues is None:
        return None
    if type(voice_cues) is not dict:
        raise ValueError("voice cues must be an object")
    required = {
        "method", "frame_ms", "hop_ms", "frame_count", "voiced_fraction",
        "voicing_confidence", "f0_median_hz", "f0_range_hz",
        "energy_range_db", "activity_hint", "activity_score",
    }
    if set(voice_cues) != required:
        raise ValueError("voice cue fields incomplete or unsupported")
    if voice_cues["method"] != "RAW_EAR_AUTOCORR_V1":
        raise ValueError("unsupported voice cue method")
    if voice_cues["frame_ms"] != 40 or voice_cues["hop_ms"] != 20:
        raise ValueError("unsupported voice cue timing")
    count = voice_cues["frame_count"]
    if type(count) is not int or not 0 <= count <= 50:
        raise ValueError("invalid voice cue frame count")
    for key in ("voiced_fraction", "voicing_confidence", "activity_score"):
        value = voice_cues[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("invalid voice cue score")
    for key, lower, upper in (("f0_median_hz", 65, 400), ("f0_range_hz", 0, 335),
                              ("energy_range_db", 0, 120)):
        value = voice_cues[key]
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper):
            raise ValueError("invalid voice cue range: " + key)
    if type(voice_cues["activity_hint"]) is not str or voice_cues["activity_hint"] not in _ACTIVITY_HINTS:
        raise ValueError("invalid voice activity hint")
    if count == 0 and (voice_cues["f0_median_hz"] is not None or voice_cues["f0_range_hz"] is not None
                        or voice_cues["voiced_fraction"] != 0 or voice_cues["voicing_confidence"] != 0):
        raise ValueError("voice cues cannot claim pitch or voicing without analysis frames")
    if voice_cues["f0_median_hz"] is None and voice_cues["f0_range_hz"] is not None:
        raise ValueError("pitch range requires a median pitch")
    return dict(voice_cues)


def audio_percept_packet(*, event_id, generation_id, source_id, source_sha256,
                         start_ms, end_ms, rms, zcr, finality="FINAL",
                         consent_receipt=None, voice_cues=None):
    """Build a non-authoritative acoustic packet; caller must verify OS permission.

    Consent receipt is an opaque local reference, not proof of OS permission.
    Recheck source revocation when a downstream consumer reads this packet.
    """
    if not all(isinstance(x, str) and x for x in (event_id, generation_id, source_id)):
        raise ValueError("missing event/generation/source identity")
    if not isinstance(source_sha256, str) or not _SHA.fullmatch(source_sha256):
        raise ValueError("invalid source hash")
    if not isinstance(consent_receipt, str) or not consent_receipt.strip():
        raise PermissionError("local authorized input receipt required")
    if finality not in ("FINAL", "PROVISIONAL"):
        raise ValueError("invalid finality")
    if any(type(x) is not int for x in (start_ms, end_ms)) or not 0 <= start_ms < end_ms or end_ms-start_ms > 1000:
        raise ValueError("invalid bounded audio interval")
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in (rms, zcr)):
        raise ValueError("nonfinite acoustic feature")
    if not 0 <= rms <= 1 or not 0 <= zcr <= 1:
        raise ValueError("feature outside normalized range")
    voice_cues = validate_voice_cues(voice_cues)
    source_ref = {"source_id":source_id,"sha256":source_sha256,
                  "char_start":0,"char_end":0,"modality":"audio"}
    validate("SourceRef", packet("SourceRef", "A_RAW_EAR", event_id, generation_id, **source_ref))
    acoustic = {"rms":float(rms),"zcr":float(zcr)}
    if voice_cues is not None:
        acoustic["voice_cues"] = voice_cues
    unmeasured = (["speaker_identity", "speaker_timbre", "calibrated_speech_probability", "ASR"]
                  if voice_cues is not None else ["pitch", "speaker", "speech_probability", "prosody"])
    segment = {"start_ms":start_ms,"end_ms":end_ms,"finality":finality,
               "acoustic":acoustic,"unmeasured":unmeasured,
               "asr_transcript":None,"learning_authority":False,
               "action_authority":False,"consent_receipt_ref":consent_receipt}
    return packet("PerceptPacket", "A5_AUDIO", event_id, generation_id,
                  provenance=[source_ref], source_ref=source_ref,
                  segments=[segment], modality="audio")
