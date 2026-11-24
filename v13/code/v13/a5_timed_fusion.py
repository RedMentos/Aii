"""A5 timed audio/UI correlation: consent-scoped, source-bound, SHADOW only."""
from collections.abc import Mapping
import hashlib
import json
import math

class FusionError(ValueError):
    pass

def fuse_timed_a5(audio: Mapping, ui: Mapping, *, consent: bool = False,
                  max_skew_ms: int = 250, max_bytes: int = 512) -> dict:
    if not consent:
        raise PermissionError("A5_CONSENT_REQUIRED")
    if not isinstance(audio, Mapping) or not isinstance(ui, Mapping):
        raise FusionError("INVALID_PACKET")
    if type(max_skew_ms) is not int or not 0 <= max_skew_ms <= 10000:
        raise FusionError("INVALID_SKEW")
    if type(max_bytes) is not int or not 256 <= max_bytes <= 4096:
        raise FusionError("INVALID_BUDGET")
    def check(packet, modality):
        source = packet.get("source")
        if not isinstance(source, Mapping) or source.get("authorized") is not True or source.get("modality") != modality:
            raise FusionError("UNAUTHORIZED_SOURCE")
        sid = source.get("id")
        if not isinstance(sid, str) or not 1 <= len(sid) <= 128:
            raise FusionError("INVALID_SOURCE_ID")
        if packet.get("action_authority") is not False or packet.get("learning_authority") is not False:
            raise FusionError("AUTHORITY_ESCALATION")
        if packet.get("status") not in ("PROVISIONAL", "FINAL"):
            raise FusionError("INVALID_STATUS")
        if not isinstance(packet.get("schema"), str) or not packet["schema"].startswith("v13.a5."):
            raise FusionError("INVALID_SCHEMA")
        start, end = packet.get("start_ms"), packet.get("end_ms")
        if any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) or x < 0 for x in (start, end)) or start > end:
            raise FusionError("INVALID_TIME")
        try:
            raw = json.dumps(packet, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        except (TypeError, ValueError) as exc:
            raise FusionError("UNSERIALIZABLE") from exc
        if len(raw) > 65536:
            raise FusionError("PACKET_TOO_LARGE")
        return hashlib.sha256(raw).hexdigest(), start, end
    ah, a0, a1 = check(audio, "audio")
    uh, u0, u1 = check(ui, "ui")
    skew = max(0, a0-u1, u0-a1)
    if skew > max_skew_ms:
        raise FusionError("OUTSIDE_TEMPORAL_WINDOW")
    out = {"schema": "v13.a5.timed_fusion/1", "audio_sha256": ah,
           "ui_sha256": uh, "temporal_gap_ms": skew,
           "status": "FINAL" if audio["status"] == ui["status"] == "FINAL" else "PROVISIONAL",
           "requires_source_lookup": True, "action_authority": False,
           "learning_authority": False, "route": "SHADOW"}
    if len(json.dumps(out, separators=(",", ":")).encode()) > max_bytes:
        raise FusionError("ENVELOPE_OVER_BUDGET")
    return out
