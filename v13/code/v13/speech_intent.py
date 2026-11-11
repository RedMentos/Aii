"""C3/JEF speech intent scheduling, separate from acoustic generation.

Pure local orchestration. This module never accesses microphones, speakers,
Android services or a network. A renderer must be explicitly attached by a
trusted Android operator; otherwise output stays OFF.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from threading import RLock
from typing import Protocol
import time
import uuid


@dataclass(frozen=True)
class SpeechIntent:
    id: str
    text: str
    created_at: float
    source_turn: str
    interruptible: bool = True


@dataclass(frozen=True)
class SpeechReceipt:
    intent_id: str
    status: str
    at: float


class SpeechRenderer(Protocol):
    def render(self, intent: SpeechIntent) -> bool: ...
    def cancel(self, intent_id: str) -> None: ...


class SpeechCoordinator:
    """Bounded speech queue; no synthetic audio claims.

    Renderer invocation is synchronous. No queue item is dispatched until the
    operator enables output and supplies a renderer. Interruptions invalidate
    pending speech and signal cancellation of an active render.
    """
    def __init__(self, *, max_pending: int = 8, clock=None):
        if type(max_pending) is not int or not 1 <= max_pending <= 32:
            raise ValueError("invalid queue capacity")
        self._clock = clock or time.time
        self._max_pending = max_pending
        self._lock = RLock()
        self._pending = deque()
        self._renderer: SpeechRenderer | None = None
        self._enabled = False
        self._active: SpeechIntent | None = None
        self._receipts: list[SpeechReceipt] = []

    def configure(self, renderer: SpeechRenderer | None, *, operator_enabled: bool = False):
        with self._lock:
            self.stop()
            self._renderer = renderer
            self._enabled = operator_enabled is True and renderer is not None

    def enqueue(self, text: str, source_turn: str, *, interruptible: bool = True) -> SpeechIntent:
        if not isinstance(text, str) or not text.strip() or len(text) > 2048:
            raise ValueError("invalid speech text")
        if not isinstance(source_turn, str) or not source_turn or len(source_turn) > 128:
            raise ValueError("invalid source turn")
        if type(interruptible) is not bool:
            raise ValueError("invalid interruptibility")
        with self._lock:
            if len(self._pending) >= self._max_pending:
                raise OverflowError("speech queue full")
            intent = SpeechIntent(uuid.uuid4().hex, text, self._clock(), source_turn, interruptible)
            self._pending.append(intent)
            self._receipts.append(SpeechReceipt(intent.id, "QUEUED", self._clock()))
            return intent

    def dispatch_one(self) -> SpeechReceipt:
        with self._lock:
            if not self._enabled or self._renderer is None:
                return SpeechReceipt("", "OFF", self._clock())
            if self._active is not None:
                return SpeechReceipt(self._active.id, "BUSY", self._clock())
            if not self._pending:
                return SpeechReceipt("", "EMPTY", self._clock())
            intent = self._pending.popleft()
            self._active = intent
        try:
            success = self._renderer.render(intent)
            status = "RENDERED" if success is True else "FAILED"
        except Exception:
            status = "FAILED"
        with self._lock:
            if self._active is not intent:
                status = "CANCELLED"
            else:
                self._active = None
            receipt = SpeechReceipt(intent.id, status, self._clock())
            self._receipts.append(receipt)
            return receipt

    def barge_in(self) -> int:
        """Stop queued speech; cancel active speech only when interruptible."""
        with self._lock:
            n = len(self._pending)
            while self._pending:
                item = self._pending.popleft()
                self._receipts.append(SpeechReceipt(item.id, "CANCELLED", self._clock()))
            if self._active is not None and self._active.interruptible:
                active = self._active
                self._active = None
                try:
                    if self._renderer is not None:
                        self._renderer.cancel(active.id)
                finally:
                    self._receipts.append(SpeechReceipt(active.id, "CANCELLED", self._clock()))
                n += 1
            return n

    def stop(self):
        with self._lock:
            self._enabled = False
            self.barge_in()

    def receipts(self) -> tuple[SpeechReceipt, ...]:
        with self._lock:
            return tuple(self._receipts)
