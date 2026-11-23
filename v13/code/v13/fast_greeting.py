"""Narrow, non-model greeting fast path.

Only a standalone allow-listed greeting is eligible. Any added question,
request, context or other text falls through to the full multi-organ turn.
The response is a source-only acknowledgement, never a learned transition.
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


def match(text: object) -> dict | None:
    """Return a tiny acknowledgement only for an exact standalone greeting."""
    if type(text) is not str or not text or len(text) > 64:
        return None
    normalized = unicodedata.normalize("NFKC", text).strip().casefold()
    normalized = re.sub(r"[.!?…]+$", "", normalized).strip()
    reply = _REPLIES.get(normalized)
    if reply is None:
        return None
    return {"normalized": normalized, "reply": reply, "rule_id": "BUILTIN_GREETING_ACK_V1"}



def match_unclaimed(text: object, *, policy_match_ok: bool, fixed_policy: object) -> dict | None:
    """Match only when the normal user-policy lookup succeeded and claimed no rule."""
    if policy_match_ok is not True or fixed_policy is not None:
        return None
    return match(text)
