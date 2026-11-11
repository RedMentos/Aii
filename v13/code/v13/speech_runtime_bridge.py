"""Explicit C3 response -> persistent speech intent handoff, without playback authority.

The caller must pass the authoritative completed-turn receipt. This adapter does
not listen to arbitrary notifications or turn model proposals into speech.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .speech_intent import SpeechIntentQueue, SpeechIntentError

_EVENT = re.compile(r"evt_[a-f0-9]{28,32}\Z")
_SHA = re.compile(r"[a-f0-9]{64}\Z")


@dataclass(frozen=True)
class C3ResponseReceipt:
    event_id: str
    output_sha256: str
    text: str
    completed: bool
    role: str = "C3_LANGUAGE"


class SpeechRuntimeBridge:
    """Opt-in output sink. Never claims to have rendered audio."""
    def __init__(self, queue: SpeechIntentQueue, *, enabled=False):
        if not isinstance(queue, SpeechIntentQueue):
            raise TypeError("speech queue required")
        self.queue = queue
        self.enabled = enabled is True

    def submit(self, receipt: C3ResponseReceipt):
        if not self.enabled:
            raise SpeechIntentError("speech handoff OFF")
        if not isinstance(receipt, C3ResponseReceipt):
            raise SpeechIntentError("authoritative C3 receipt required")
        if (receipt.completed is not True or receipt.role != "C3_LANGUAGE"
                or not isinstance(receipt.event_id, str)
                or _EVENT.fullmatch(receipt.event_id) is None
                or not isinstance(receipt.output_sha256, str)
                or _SHA.fullmatch(receipt.output_sha256) is None):
            raise SpeechIntentError("invalid completed C3 receipt")
        import hashlib
        if not isinstance(receipt.text, str) or hashlib.sha256(
            receipt.text.encode("utf-8")
        ).hexdigest() != receipt.output_sha256:
            raise SpeechIntentError("output digest mismatch")
        # A replayed completed turn must not enqueue a second spoken message.
        # Serialize the existence check and insertion under the queue lock.
        source_id = "c3:" + receipt.event_id
        with self.queue.lock:
            if self.queue.db.execute(
                "SELECT 1 FROM speech_intents WHERE source_id=? LIMIT 1", (source_id,)
            ).fetchone():
                raise SpeechIntentError("C3 response already queued")
            return self.queue.submit(receipt.text, source_id=source_id)

    def stop(self):
        self.enabled = False
        return self.queue.interrupt()
