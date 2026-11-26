"""Exact, text-only greeting reflex; never a general-purpose answer path."""
from __future__ import annotations

import hashlib
import re
import unicodedata

RULE_ID = "BUILTIN_GREETING_ACK_V1"
GREETING_SCOPE = "EXACT_WHOLE_TEXT_GREETING_ONLY"
ACKNOWLEDGMENT_SCOPE = "EXACT_WHOLE_TEXT_ACKNOWLEDGMENT_ONLY"
SCOPE = GREETING_SCOPE
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

# Deliberately excludes bare yes/no/ok and action-approval phrases: those can
# carry turn-specific intent and must remain on the normal multi-organ path.
_ACKNOWLEDGMENTS = {
    "thanks": ("en", "You're welcome."),
    "thank you": ("en", "You're welcome."),
    "thank you very much": ("en", "You're welcome."),
    "thx": ("en", "You're welcome."),
    "appreciate it": ("en", "You're welcome."),
    "danke": ("de", "Gern."),
    "danke dir": ("de", "Gern."),
    "vielen dank": ("de", "Gern."),
    "dankeschön": ("de", "Gern."),
    "danke schön": ("de", "Gern."),
    "understood": ("en", "Okay."),
    "got it": ("en", "Okay."),
    "noted": ("en", "Okay."),
    "verstanden": ("de", "Alles klar."),
    "alles klar": ("de", "Alles klar."),
}

_MULTIMODAL_FIELDS = (
    "audio_consent_lease", "raw_audio", "image_ref", "video_ref",
    "_audio_window", "audio_window", "audio_source_ref",
    "image_source_ref", "video_source_ref", "raw_ear", "raw_eye",
)


def _event_is_exact_text_source(text: str, encoded: bytes, event: object) -> bool:
    if type(event) is not dict:
        return False
    source_ref = event.get("source_ref")
    if type(source_ref) is not dict or source_ref.get("modality") != "text":
        return False
    source_id = source_ref.get("source_id")
    source_hash = source_ref.get("sha256")
    char_start = source_ref.get("char_start")
    char_end = source_ref.get("char_end")
    if (type(source_id) is not str or not source_id
            or type(source_hash) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", source_hash)
            or type(char_start) is not int or char_start != 0
            or type(char_end) is not int or char_end != len(text)
            or source_hash != hashlib.sha256(encoded).hexdigest()):
        return False

    if any(event.get(key) is not None for key in _MULTIMODAL_FIELDS):
        return False
    if "modalities" in event:
        modalities = event["modalities"]
        if (not isinstance(modalities, (list, tuple, set)) or not modalities
                or any(value != "text" for value in modalities)):
            return False
    return True


def match(text: str, event: dict | None = None) -> dict | None:
    """Return a minimal deterministic acknowledgement only for an exact greeting.

    A caller-provided event must bind the entire input to a matching text
    SourceRef. Audio, image, video, mixed-modality, malformed and longer
    conversational messages fall through to the normal multi-organ path.
    """
    if type(text) is not str or not text or len(text) > MAX_INPUT_CHARS:
        return None
    try:
        encoded = text.encode("utf-8")
    except UnicodeError:
        return None
    if len(encoded) > MAX_INPUT_BYTES or any(ord(ch) < 32 for ch in text):
        return None

    if event is not None and not _event_is_exact_text_source(text, encoded, event):
        return None

    normalized = unicodedata.normalize("NFKC", text).casefold().strip()
    normalized = re.sub(r"[.!]+$", "", normalized).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    found = _GREETINGS.get(normalized)
    scope = GREETING_SCOPE
    if found is None:
        found = _ACKNOWLEDGMENTS.get(normalized)
        scope = ACKNOWLEDGMENT_SCOPE
    if found is None:
        return None

    language, reply = found
    return {
        "rule_id": RULE_ID,
        "language": language,
        "reply": reply,
        "input_sha256": hashlib.sha256(encoded).hexdigest(),
        "response_sha256": hashlib.sha256(reply.encode("utf-8")).hexdigest(),
        "scope": scope,
        "authority": "BUILTIN_REFLEX",
        "model_generated": False,
        "native_models_invoked": False,
    }
