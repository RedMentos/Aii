"""C3 -> voice-output intent contract (no microphone, synthesis or OS authority).

A language organ proposes *what to say*. A separate Android audio companion
must decide how/when to synthesize, with its own user consent and stop control.
This module deliberately never executes TTS or interprets text as commands.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import re

MAX_CHARS = 2048
MAX_SEGMENTS = 16
_SENTENCE = re.compile(r"(?<=[.!?])\\s+")


class SpeechIntentError(ValueError):
    pass


@dataclass(frozen=True)
class SpeechSegment:
    index: int
    text: str
    text_sha256: str


@dataclass(frozen=True)
class SpeechIntent:
    schema: str
    source: str
    language: str
    utterance_sha256: str
    segments: tuple[SpeechSegment, ...]
    status: str = "PROPOSED_NOT_SPOKEN"

    def to_dict(self):
        result = asdict(self)
        result["segments"] = [asdict(s) for s in self.segments]
        return result


def from_c3_text(text: str, *, language: str = "und") -> SpeechIntent:
    """Make bounded, deterministic spoken-text intent from a C3 response.

    Never claims acoustics, ASR, prosody, vocal training or playback. Text
    cannot request Android permissions via this conversion.
    """
    if type(text) is not str or not text or len(text) > MAX_CHARS:
        raise SpeechIntentError("C3 text must be nonempty and bounded")
    if any(ord(c) < 32 and c not in "\n\t" for c in text):
        raise SpeechIntentError("control character in C3 text")
    if language not in ("und", "en", "de"):
        raise SpeechIntentError("unsupported language tag")
    normalized = " ".join(text.split())
    if not normalized:
        raise SpeechIntentError("empty spoken text")
    parts = _SENTENCE.split(normalized)
    # Preserve the exact words when segmentation exceeds the bounded queue.
    if len(parts) > MAX_SEGMENTS:
        parts = parts[:MAX_SEGMENTS - 1] + [" ".join(parts[MAX_SEGMENTS - 1:])]
    segments = tuple(SpeechSegment(i, part, hashlib.sha256(part.encode("utf-8")).hexdigest())
                     for i, part in enumerate(parts))
    return SpeechIntent("v13.c3-speech-intent/1", "C3_LANGUAGE", language,
                        hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
                        segments)


def verify_intent(payload: dict) -> bool:
    """Verify an untrusted serialized proposal before a speech adapter queues it."""
    if type(payload) is not dict or set(payload) != {
        "schema", "source", "language", "utterance_sha256", "segments", "status"
    }:
        return False
    if payload["schema"] != "v13.c3-speech-intent/1" or payload["source"] != "C3_LANGUAGE":
        return False
    if payload["status"] != "PROPOSED_NOT_SPOKEN" or payload["language"] not in ("und", "en", "de"):
        return False
    segments = payload["segments"]
    if type(segments) is not list or not 1 <= len(segments) <= MAX_SEGMENTS:
        return False
    try:
        if any(type(s) is not dict or set(s) != {"index", "text", "text_sha256"}
               or type(s["index"]) is not int or s["index"] != i
               or type(s["text"]) is not str or not s["text"]
               or hashlib.sha256(s["text"].encode("utf-8")).hexdigest() != s["text_sha256"]
               for i, s in enumerate(segments)):
            return False
        joined = " ".join(s["text"] for s in segments)
        return (len(joined) <= MAX_CHARS
                and hashlib.sha256(joined.encode("utf-8")).hexdigest() == payload["utterance_sha256"])
    except (TypeError, UnicodeError):
        return False
