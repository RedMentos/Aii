"""C3-to-speech handoff: typed, inert output intent for an explicit local command.

This is a platform TTS fallback, not a trainable speech decoder or audio learner.
It never records audio and never starts playback automatically.
"""
from __future__ import annotations

import hashlib

SCHEMA = "v13.c3-speech-intent/1"
MAX_CHARS = 8192


def final_text_intent(message_id, event_id, text, status, *, enabled=False, user_command=False):
    """Create a source-bound intent only for a FINAL C3 answer and a local command."""
    if status != "FINAL" or not text or enabled is not True or user_command is not True:
        return None
    if type(message_id) is not int or message_id <= 0:
        raise ValueError("invalid message identity")
    if type(event_id) is not str or not event_id or len(event_id) > 128:
        raise ValueError("invalid event identity")
    if type(text) is not str or not text.strip() or len(text) > MAX_CHARS:
        raise ValueError("invalid C3 text")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
        raise ValueError("control characters in C3 text")
    return {
        "schema": SCHEMA,
        "source_message_id": message_id,
        "source_event_id": event_id,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text_chars": len(text),
        "language": "und",
        "acoustic_decoder": "TERMUX_SYSTEM_TTS_FALLBACK",
        "execution": "EXPLICIT_TTY_COMMAND_ONLY",
        "consent": "LOCAL_OPERATOR_COMMAND",
        "automatic_playback": False,
        "trainable_voice_model": False,
    }


def verify_intent(intent, message_id, event_id, text):
    if type(intent) is not dict:
        return False
    try:
        expected = final_text_intent(
            message_id, event_id, text, "FINAL", enabled=True, user_command=True
        )
    except ValueError:
        return False
    return expected is not None and intent == expected
