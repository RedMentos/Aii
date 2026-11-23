"""Narrow, source-only acknowledgement for exact standalone text greetings.

The matcher never handles a greeting plus a request. The event guard excludes
audio-backed and non-text sources so RAW EAR/voice processing is not bypassed.
"""
from __future__ import annotations

import re
import unicodedata


_REPLIES = {
    "hi": "Hi.",
    "hey": "Hey.",
    "hello": "Hello.",
    "hallo": "Hallo.",
    "moin": "Moin.",
    "guten morgen": "Guten Morgen.",
    "good morning": "Good morning.",
    "good evening": "Good evening.",
    "good night": "Good night.",
}


def is_text_only_event(event: object) -> bool:
    """Accept only a plain text SourceRef with no non-null audio window."""
    if not isinstance(event, dict):
        return False
    source_ref = event.get("source_ref")
    return (
        isinstance(source_ref, dict)
        and source_ref.get("modality") == "text"
        and event.get("_audio_window") is None
    )


def match(text: object) -> dict | None:
    """Return a fixed acknowledgement only for an exact standalone greeting."""
    if type(text) is not str or not text or len(text) > 64:
        return None
    normalized = unicodedata.normalize("NFKC", text).strip().casefold()
    normalized = re.sub(r"[.!?…]+$", "", normalized).strip()
    reply = _REPLIES.get(normalized)
    if reply is None:
        return None
    return {
        "normalized": normalized,
        "reply": reply,
        "rule_id": "BUILTIN_GREETING_ACK_V1",
    }


def match_unclaimed(
    text: object, *, policy_match_ok: bool, fixed_policy: object
) -> dict | None:
    """Match only after policy validation succeeded and claimed no exact rule."""
    if policy_match_ok is not True or fixed_policy is not None:
        return None
    return match(text)
