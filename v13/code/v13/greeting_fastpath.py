"""Exact, text-only greeting reflex; never a general-purpose answer path."""
from __future__ import annotations

import hashlib
import re
import unicodedata

RULE_ID = "BUILTIN_GREETING_ACK_V1"
SCOPE = "EXACT_WHOLE_TEXT_GREETING_ONLY"
MAX_INPUT_CHARS = 48
MAX_INPUT_BYTES = 128

_GREETINGS = {
    "hi": ("en", "Hi."),
    "hi there": ("en", "Hi."),
    "hello": ("en", "Hello."),
    "hello there": ("en", "Hello."),
    "hey": ("en", "Hey."),
    "hey there": ("en", "Hey."),
    "yo": ("en", "Yo."),
    "good morning": ("en", "Good morning."),
    "good afternoon": ("en", "Good afternoon."),
    "good evening": ("en", "Good evening."),
    "hallo": ("de", "Hallo."),
    "hallo zusammen": ("de", "Hallo."),
    "moin": ("de", "Moin."),
    "moin moin": ("de", "Moin."),
    "servus": ("de", "Servus."),
    "tach": ("de", "Tach."),
    "guten morgen": ("de", "Guten Morgen."),
    "guten tag": ("de", "Guten Tag."),
    "guten abend": ("de", "Guten Abend."),
}


def match(text: str, event: dict | None = None) -> dict | None:
    """Return a minimal deterministic acknowledgement only for an exact greeting.

    A caller-provided event must bind the input to a text SourceRef. Audio,
    image, video, mixed-modality and longer conversational messages fall
    through to the normal multi-organ path.
    """
    if type(text) is not str or not text or len(text) > MAX_INPUT_CHARS:
        return None
    try:
        encoded = text.encode("utf-8")
    except UnicodeError:
        return None
    if len(encoded) > MAX_INPUT_BYTES or any(ord(ch) < 32 for ch in text):
        return None

    if event is not None:
        if type(event) is not dict:
            return None
        source_ref = event.get("source_ref")
        if type(source_ref) is not dict or source_ref.get("modality") != "text":
            return None
        if any(event.get(key) is not None for key in (
            "audio_consent_lease", "raw_audio", "image_ref", "video_ref",
        )):
            return None
        modalities = event.get("modalities")
        if isinstance(modalities, (list, tuple, set)) and any(x != "text" for x in modalities):
            return None

    normalized = unicodedata.normalize("NFKC", text).casefold().strip()
    normalized = re.sub(r"[.!]+$", "", normalized).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    found = _GREETINGS.get(normalized)
    if found is None:
        return None

    language, reply = found
    return {
        "rule_id": RULE_ID,
        "language": language,
        "reply": reply,
        "input_sha256": hashlib.sha256(encoded).hexdigest(),
        "response_sha256": hashlib.sha256(reply.encode("utf-8")).hexdigest(),
        "scope": SCOPE,
        "authority": "BUILTIN_REFLEX",
        "model_generated": False,
        "native_models_invoked": False,
    }
