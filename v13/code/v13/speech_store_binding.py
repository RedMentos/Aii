"""Read completed C3 output from the authoritative Runtime Store before speech handoff.

This is a local opt-in data bridge, not a native Android permission boundary.
No caller-supplied C3ResponseReceipt is trusted here.
"""
from __future__ import annotations

import hashlib
import json

from .speech_runtime_bridge import C3ResponseReceipt, SpeechRuntimeBridge
from .speech_intent import SpeechIntentError

def enqueue_committed_c3(store, event_id: str, bridge: SpeechRuntimeBridge):
    """Enqueue only a committed FINAL C3-generated assistant message.

    Reads the authoritative message row and its metadata at call time. The
    event ID is a lookup key, never proof of completion or organ identity.
    """
    if not isinstance(event_id, str) or not event_id.startswith("evt_"):
        raise SpeechIntentError("invalid event id")
    if not isinstance(bridge, SpeechRuntimeBridge):
        raise SpeechIntentError("speech bridge required")
    row = store.one(
        "SELECT text,status,metadata FROM messages "
        "WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",
        (event_id,),
    )
    if not row or row["status"] != "FINAL":
        raise SpeechIntentError("no completed assistant message")
    try:
        metadata = json.loads(row["metadata"])
    except (TypeError, ValueError):
        raise SpeechIntentError("invalid committed metadata") from None
    if not isinstance(metadata, dict) or metadata.get("model_generated") is not True:
        raise SpeechIntentError("not a generated C3 output")
    if metadata.get("speech_source_role") != "C3_LANGUAGE":
        raise SpeechIntentError("output not produced by C3")
    text = row["text"]
    if not isinstance(text, str) or not text:
        raise SpeechIntentError("missing committed output")
    return bridge.submit(C3ResponseReceipt(
        event_id=event_id,
        output_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        text=text,
        completed=True,
        role="C3_LANGUAGE",
    ))
