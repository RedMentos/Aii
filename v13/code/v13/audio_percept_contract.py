"""Bounded RAW EAR -> canonical A5 PerceptPacket. Not Android microphone authorization."""
import math
import re
from .contracts import packet, validate

_SHA = re.compile(r"[0-9a-f]{64}\Z")

def audio_percept_packet(*, event_id, generation_id, source_id, source_sha256,
                         start_ms, end_ms, rms, zcr, finality="FINAL",
                         consent_receipt=None):
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
    source_ref = {"source_id":source_id,"sha256":source_sha256,
                  "char_start":0,"char_end":0,"modality":"audio"}
    validate("SourceRef", packet("SourceRef", "A_RAW_EAR", event_id, generation_id, **source_ref))
    segment = {"start_ms":start_ms,"end_ms":end_ms,"finality":finality,
               "acoustic":{"rms":float(rms),"zcr":float(zcr)},
               "unmeasured":["pitch","speaker","speech_probability","prosody"],
               "asr_transcript":None,"learning_authority":False,
               "action_authority":False,"consent_receipt_ref":consent_receipt}
    return packet("PerceptPacket", "A5_AUDIO", event_id, generation_id,
                  provenance=[source_ref], source_ref=source_ref,
                  segments=[segment], modality="audio")
