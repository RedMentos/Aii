"""Explicit audio-only ingress for the consent-bound RAW EAR Runtime path.

This adapter never transcribes, stores PCM, opens a microphone, or downloads a model.
The supplied Runtime remains responsible for its source-bound A5/A4/C3 processing,
linearizable consent lease, revocation, and bounded persistence.
"""

from __future__ import annotations

AUDIO_ONLY_SOURCE_TEXT = (
    "[Audio input; no transcript supplied. Use RAW EAR acoustic evidence only; "
    "do not infer or invent spoken words. If acoustic context is unavailable, say so.]"
)

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


def submit_audio_only(runtime, audio_window):
    """Queue one caller-supplied PCM16 window without requiring or fabricating text.

    A successful preflight is not the lease: Runtime.submit's staged audio path
    still acquires the provider's linearizable guard and subscribes to both
    revocation phases before it processes the window.
    """
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

    pcm = audio_window["pcm16"]
    rate = audio_window["sample_rate"]
    start_ms = audio_window["start_ms"]
    source_id = audio_window["source_id"]
    receipt = audio_window["consent_receipt"]
    finality = audio_window["finality"]

    if type(pcm) is not bytes or not pcm or len(pcm) % 2:
        raise ValueError("RAW EAR requires complete mono PCM16 bytes")
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

    try:
        authorized = audio_window["consent_check"](source_id, receipt)
    except Exception as exc:
        raise PermissionError("RAW EAR consent preflight failed") from exc
    if authorized is not True:
        raise PermissionError("RAW EAR consent is not active")

    submit = getattr(runtime, "submit", None)
    if not callable(submit):
        raise TypeError("Runtime does not expose submit()")

    try:
        return submit(AUDIO_ONLY_SOURCE_TEXT, audio_window=audio_window)
    except TypeError as exc:
        message = str(exc)
        if "audio_window" in message and "keyword" in message:
            raise RuntimeError(
                "Runtime lacks the staged RAW EAR audio_window submit path"
            ) from exc
        raise
