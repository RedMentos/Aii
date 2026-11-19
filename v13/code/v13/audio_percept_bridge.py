"""A5 RAW EAR acoustic metadata -> bounded C3 admission. No microphone, ASR or training."""
import math
from .percept_admission import Percept, admit

def acoustic_percept(packet):
    if not isinstance(packet, dict) or packet.get("schema") != "v13.a5.raw_ear/1":
        raise ValueError("invalid RAW EAR schema")
    ref, f = packet.get("source_ref"), packet.get("acoustic_features")
    if not isinstance(ref, dict) or not isinstance(f, dict):
        raise ValueError("missing source/features")
    source, consent, digest = (ref.get(k) for k in ("source_id", "consent_id", "sha256"))
    if not all(isinstance(x, str) and x and len(x) <= 128 for x in (source, consent, digest)):
        raise PermissionError("source, consent and digest required")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid source hash")
    start, end = ref.get("start_ms"), ref.get("end_ms")
    if any(type(x) is not int for x in (start, end)) or start < 0 or end <= start:
        raise ValueError("invalid timing")
    if packet.get("provenance") != "RAW_PCM_OBSERVATION" or packet.get("learning_eligible") is not False:
        raise ValueError("untrusted provenance or learning authority")
    if packet.get("status") not in ("FINAL", "PROVISIONAL"):
        raise ValueError("invalid finality")
    if packet.get("teacher_asr") is not None or packet.get("speaker_identity") is not None:
        raise ValueError("teacher/speaker assertions require separate verified contract")
    values = []
    for key in ("rms", "peak", "zero_crossing_rate"):
        value = f.get(key)
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("invalid acoustic feature")
        values.append(value)
    for key in ("silence_candidate", "clipped"):
        if type(f.get(key)) is not bool:
            raise ValueError("invalid acoustic flag")
    summary = "acoustic rms={:.4f} peak={:.4f} zcr={:.4f} silence={} clipped={}".format(
        *values, f["silence_candidate"], f["clipped"])
    return Percept(source_id=source + ":" + digest[:12], modality="audio",
                   start_ms=start, end_ms=end, summary=summary,
                   consent=True, final=packet["status"] == "FINAL")

def admit_acoustic_packets(packets, token_budget, *, max_items=12):
    """C3-facing A5 summary; native tokenizer must still enforce final budget."""
    return admit((acoustic_percept(p) for p in packets), token_budget, max_items=max_items)
