"""Explicit audio-only ingress for the consent-bound RAW EAR Runtime path.

This adapter never transcribes, stores PCM, opens a microphone, or downloads a model.
A mutable SecurePCMBuffer is transferred only to a Runtime that advertises the
versioned source-bound audio/zeroization contract. Failed submissions are wiped
here; successful submissions transfer ownership to Runtime, which must wipe the
buffer on every terminal path after the complete consent-bound C3 turn.
"""

from __future__ import annotations

import inspect

AUDIO_ONLY_SOURCE_TEXT = (
    "[Audio input; no transcript supplied. Use RAW EAR acoustic evidence only; "
    "do not infer or invent spoken words. If acoustic context is unavailable, say so.]"
)
AUDIO_WINDOW_RUNTIME_CONTRACT = "v14.raw-ear-runtime/1"

_REQUIRED_FIELDS = frozenset({
    "pcm16",
    "sample_rate",
    "start_ms",
    "source_id",
    "consent_receipt",
    "consent_check",
    "consent_guard",
    "consent_revocation_subscribe",
    "finality",
})


class SecurePCMBuffer(bytearray):
    """Ephemeral mutable PCM storage; zeroization is best-effort, not OS erasure."""

    def __init__(self, source=b""):
        super().__init__(source)
        self._zeroized = False

    def zeroize(self):
        length = len(self)
        if length:
            self[:] = b"\\x00" * length
        self._zeroized = True
        return length

    @property
    def zeroized(self):
        return self._zeroized is True

    def __repr__(self):
        return f"SecurePCMBuffer(length={len(self)}, zeroized={self.zeroized})"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("SecurePCMBuffer is ephemeral and cannot be serialized")

    def __copy__(self):
        raise TypeError("SecurePCMBuffer cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("SecurePCMBuffer cannot be copied")

    def __del__(self):
        try:
            self.zeroize()
        except Exception:
            pass


def zeroize_pcm_buffer(pcm):
    """Best-effort overwrite for mutable PCM; immutable bytes cannot be wiped."""
    if isinstance(pcm, SecurePCMBuffer):
        return pcm.zeroize()
    if isinstance(pcm, bytearray):
        length = len(pcm)
        if length:
            pcm[:] = b"\\x00" * length
        return length
    return 0


def submit_audio_only(runtime, audio_window):
    """Queue one mutable PCM16 window; transfer ownership only to a verified Runtime.

    A successful submit transfers the same SecurePCMBuffer object to Runtime.
    Runtime must keep it in memory only, hold the source-bound consent lease
    through A5/A4, B1/B2 and the complete C3 generation, and call zeroize() on
    success, failure, cancellation, restart recovery and shutdown. This adapter
    rejects older Runtime implementations rather than treating a test stub or
    a JSON/placeholder path as real audio integration.
    """
    pcm = audio_window.get("pcm16") if type(audio_window) is dict else None
    transferred = False
    try:
        if type(audio_window) is not dict:
            raise TypeError("audio_window must be a dict")

        missing = _REQUIRED_FIELDS - set(audio_window)
        extra = set(audio_window) - _REQUIRED_FIELDS
        if missing or extra:
            raise ValueError(
                "audio_window fields mismatch; missing="
                + ",".join(sorted(missing))
                + "; extra="
                + ",".join(sorted(extra))
            )

        if not isinstance(pcm, SecurePCMBuffer) or not pcm or len(pcm) % 2:
            raise ValueError(
                "RAW EAR requires a nonempty mutable SecurePCMBuffer containing complete mono PCM16"
            )
        rate = audio_window["sample_rate"]
        start_ms = audio_window["start_ms"]
        source_id = audio_window["source_id"]
        receipt = audio_window["consent_receipt"]
        finality = audio_window["finality"]

        if type(rate) is not int or not 8000 <= rate <= 48000 or len(pcm) > rate * 2:
            raise ValueError("RAW EAR window exceeds the one-second 8kHz..48kHz bound")
        if type(start_ms) is not int or start_ms < 0:
            raise ValueError("RAW EAR start_ms must be a nonnegative integer")
        if type(source_id) is not str or not source_id.strip() or len(source_id) > 128:
            raise ValueError("RAW EAR source_id is invalid")
        if type(receipt) is not str or not receipt.strip() or len(receipt) > 256:
            raise ValueError("RAW EAR consent receipt is required")
        if type(finality) is not str or finality not in ("PROVISIONAL", "FINAL"):
            raise ValueError("RAW EAR finality must be PROVISIONAL or FINAL")
        if not callable(audio_window["consent_check"]):
            raise ValueError("RAW EAR requires a live consent check")
        if not callable(audio_window["consent_guard"]):
            raise ValueError("RAW EAR requires a linearizable consent guard")
        if not callable(audio_window["consent_revocation_subscribe"]):
            raise ValueError("RAW EAR requires two-phase revocation subscription")

        if getattr(runtime, "audio_window_contract_version", None) != AUDIO_WINDOW_RUNTIME_CONTRACT:
            raise RuntimeError(
                "Runtime does not implement the source-bound RAW EAR/PCM-zeroization contract"
            )
        submit = getattr(runtime, "submit", None)
        if not callable(submit):
            raise TypeError("Runtime does not expose submit()")
        try:
            parameters = inspect.signature(submit).parameters
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Runtime audio submit signature cannot be verified") from exc
        if "audio_window" not in parameters:
            raise RuntimeError("Runtime lacks an explicit audio_window submit parameter")

        try:
            authorized = audio_window["consent_check"](source_id, receipt)
        except Exception as exc:
            raise PermissionError("RAW EAR consent preflight failed") from exc
        if authorized is not True:
            raise PermissionError("RAW EAR consent is not active")

        event_id = submit(AUDIO_ONLY_SOURCE_TEXT, audio_window=audio_window)
        transferred = True
        return event_id
    finally:
        if not transferred:
            zeroize_pcm_buffer(pcm)
