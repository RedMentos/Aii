"""Bounded one-shot C3 speech playback consumer with an injected trusted renderer.

The renderer and receipt verifier MUST be supplied by a separately authorized
Android companion. This module never executes shell commands or grants audio
permissions. A receipt is not trusted merely because it claims success.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .speech_intent import SpeechIntentQueue


class Renderer(Protocol):
    def render(self, intent_id: str, text: str, digest: str) -> object: ...
    def cancel(self, intent_id: str) -> None: ...


class ReceiptVerifier(Protocol):
    def verify(self, intent_id: str, digest: str, receipt: object) -> bool: ...


@dataclass(frozen=True)
class PlaybackResult:
    status: str
    intent_id: str | None = None


class SpeechRendererPump:
    """Explicit operator-driven playback. No implicit background execution.

    Crash-recovered RENDERING entries are INTERRUPTED by SpeechIntentQueue,
    avoiding automatic duplicate speech. Only verified receipts commit.
    """
    def __init__(self, queue: SpeechIntentQueue, *, renderer: Renderer,
                 verifier: ReceiptVerifier, enabled: bool = False):
        if not isinstance(queue, SpeechIntentQueue):
            raise TypeError("SpeechIntentQueue required")
        if not callable(getattr(renderer, "render", None)) or not callable(getattr(renderer, "cancel", None)):
            raise TypeError("renderer requires render/cancel")
        if not callable(getattr(verifier, "verify", None)):
            raise TypeError("receipt verifier required")
        self.queue = queue
        self.renderer = renderer
        self.verifier = verifier
        self.enabled = enabled is True
        self.stopped = False

    def run_one(self) -> PlaybackResult:
        if self.stopped or not self.enabled:
            return PlaybackResult("OFF")
        intent = self.queue.claim()
        if intent is None:
            return PlaybackResult("EMPTY")
        try:
            receipt = self.renderer.render(intent.intent_id, intent.text, intent.digest)
            if self.stopped or not self.enabled:
                return PlaybackResult("INTERRUPTED", intent.intent_id)
            if self.verifier.verify(intent.intent_id, intent.digest, receipt) is not True:
                return PlaybackResult("UNVERIFIED", intent.intent_id)
            if self.stopped or not self.enabled:
                return PlaybackResult("INTERRUPTED", intent.intent_id)
            self.queue.acknowledge(intent.intent_id, digest=intent.digest, rendered=True)
            return PlaybackResult("RENDERED", intent.intent_id)
        except Exception:
            # Playback may have happened despite failure. Never auto-retry.
            return PlaybackResult("FAILED_UNCERTAIN", intent.intent_id)
        finally:
            if self.queue.status(intent.intent_id) == "RENDERING":
                self.queue.interrupt_one(intent.intent_id)
            if self.queue.status(intent.intent_id) != "RENDERED":
                try:
                    self.renderer.cancel(intent.intent_id)
                except Exception:
                    pass

    def stop(self) -> int:
        self.stopped = True
        self.enabled = False
        return self.queue.interrupt()
