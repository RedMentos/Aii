"""C3-to-voice handoff: typed, inert output intent, not synthesized audio.

The voice decoder/vocoder and RAW EAR learning are separate organs. A final
C3 text response may be referenced by a future consented speech transport;
this contract neither starts recording nor plays audio.
"""
from __future__ import annotations

import hashlib

SCHEMA = "v13.c3-speech-intent/1"
MAX_CHARS = 8192


def final_text_intent(message_id, text, status, *, enabled=False):
    """Return an inert source-bound speech request or None.

    No audio permissions are implied by enabled: the Android companion must
    separately check local consent and OS capability at execution time.
    """
    if status != "FINAL" or not text or enabled is not True:
        return None
    if type(message_id) is not int or message_id <= 0:
        raise ValueError("invalid message identity")
    if type(text) is not str or len(text) > MAX_CHARS:
        raise ValueError("invalid C3 text")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
        raise ValueError("control characters in C3 text")
    return {
        "schema": SCHEMA,
        "source_message_id": message_id,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text_chars": len(text),
        "language": "und",
        "acoustic_decoder": "UNAVAILABLE",
        "execution": "OFF",
        "consent": "NOT_GRANTED",
    }


def verify_intent(intent, message_id, text):
    """Verify immutable text identity before a future authorized decoder reads it."""
    if type(intent) is not dict or type(message_id) is not int or type(text) is not str:
        return False
    expected = final_text_intent(message_id, text, "FINAL", enabled=True)
    return expected is not None and intent == expected
