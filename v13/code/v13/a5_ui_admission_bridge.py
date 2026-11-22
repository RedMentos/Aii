"""Consent-revalidated A5 UI event -> bounded percept admission; SHADOW only."""
import re
from .percept_admission import Percept, admit

HEX = re.compile(r"[0-9a-f]{64}\Z")

def ui_to_admission(packet, *, consent_active: bool, priority: int = 0):
    if type(consent_active) is not bool or not consent_active:
        raise PermissionError("current Android UI observation consent required")
    if type(priority) is not int or not -100 <= priority <= 100:
        raise ValueError("invalid priority")
    if not isinstance(packet, dict) or packet.get("modality") != "ui":
        raise ValueError("expected UI packet")
    source, segments = packet.get("source_ref"), packet.get("segments")
    if not isinstance(source, dict) or not isinstance(segments, list) or len(segments) != 1:
        raise ValueError("invalid source/segments")
    sid, digest = source.get("source_id"), source.get("sha256")
    if not isinstance(sid, str) or not 0 < len(sid) <= 128 or not isinstance(digest, str) or not HEX.fullmatch(digest):
        raise ValueError("invalid source identity")
    seg = segments[0]
    if not isinstance(seg, dict):
        raise ValueError("invalid segment")
    if not isinstance(seg.get("consent_receipt_ref"), str) or not seg["consent_receipt_ref"].strip():
        raise PermissionError("missing receipt reference")
    if seg.get("learning_authority") is not False or seg.get("action_authority") is not False:
        raise PermissionError("observation cannot grant authority")
    start, end = seg.get("start_ms"), seg.get("end_ms")
    if type(start) is not int or type(end) is not int or not 0 <= start <= end or end-start > 1000:
        raise ValueError("invalid interval")
    if seg.get("finality") not in ("FINAL", "PROVISIONAL"):
        raise ValueError("invalid finality")
    kind = seg.get("event_kind")
    if kind not in ("window_changed", "view_changed", "notification_changed", "screen_changed"):
        raise ValueError("invalid event kind")
    return Percept(sid, "ui", start, end, f"ui event={kind} interval_ms={end-start}", True, seg["finality"] == "FINAL", priority)

def admit_ui(packet, *, consent_active: bool, token_budget: int):
    return admit((ui_to_admission(packet, consent_active=consent_active),), token_budget)
