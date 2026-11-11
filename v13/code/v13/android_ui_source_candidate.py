"""Android-first, opt-in *textual* UI observation -> A0/A5 source candidate.

This module does NOT capture Android screens or operate the phone. An approved
Android Accessibility/MediaProjection adapter must supply a redacted snapshot.
No implicit permission, model/tool authority, or UI action is granted.
"""
import json
import re

MAX_NODES = 128
MAX_TEXT = 8192
MAX_FIELD = 240
_ALLOWED = frozenset(("text", "content_description", "class_name"))


def _valid_id(value):
    return type(value) is str and bool(re.fullmatch(r"[A-Za-z0-9._:-]{1,96}", value))


def ui_snapshot_text(snapshot):
    """Validate a bounded, already-redacted observation, without persisting it."""
    if type(snapshot) is not dict:
        raise ValueError("UI snapshot must be an object")
    if snapshot.get("schema") != "v13.android.ui_observation/1":
        raise ValueError("UI observation schema mismatch")
    if snapshot.get("capture_authorized") is not True or snapshot.get("redacted") is not True:
        raise ValueError("explicit capture authorization and redaction required")
    if snapshot.get("source") != "ACCESSIBILITY_APPROVED":
        raise ValueError("untrusted Android observation source")
    if not _valid_id(snapshot.get("consent_receipt_id")) or not _valid_id(snapshot.get("observation_id")):
        raise ValueError("missing consent/observation provenance")
    nodes = snapshot.get("nodes")
    if type(nodes) is not list or len(nodes) > MAX_NODES:
        raise ValueError("invalid UI node count")
    lines = []
    for i, node in enumerate(nodes):
        if type(node) is not dict or not node.keys() <= _ALLOWED:
            raise ValueError("unexpected UI node fields")
        fields = []
        for name in ("class_name", "text", "content_description"):
            value = node.get(name, "")
            if type(value) is not str or len(value) > MAX_FIELD:
                raise ValueError("invalid UI field")
            if any(ord(c) < 32 and c not in (chr(9), chr(10)) for c in value):
                raise ValueError("control character in UI field")
            if value:
                fields.append(name + "=" + json.dumps(value, ensure_ascii=False))
        if fields:
            lines.append(str(i) + " " + " ".join(fields))
    text = chr(10).join(lines)
    if not text or len(text.encode("utf-8")) > MAX_TEXT:
        raise ValueError("empty or oversized UI observation")
    return text


def persist_ui_shadow_source(store, snapshot):
    """Store a bounded redacted A0 text source; no EventEnvelope or action."""
    text = ui_snapshot_text(snapshot)  # validate before any persistence
    ref = store.source(text, kind="ANDROID_UI_SHADOW")
    return {
        "schema": "v13.android.ui_source_candidate/1",
        "source_ref": ref,
        "observation_id": snapshot["observation_id"],
        "consent_receipt_id": snapshot["consent_receipt_id"],
        "input_modality": "android_accessibility_text",
        "stored_modality": "text",
        "percept_packet_created": False,
        "runtime_activated": False,
        "action_authority": 0,
        "capture_implemented": False,
        "native_android_verified": False,
    }
