"""Bridge consented RAW EAR voice-onset evidence into the existing duplex controller.

This is an additive adapter, not an audio capture provider. The caller must keep
an AudioConsentLease active while it consumes PCM and dispatches the result. In
default auto mode voice onset is only recorded as an overlap candidate; it
never cancels speech. Cancellation is enabled only by the explicit existing
duplex_mode=interrupt setting. No ASR text, speaker identity, learning
authority or action authority is used.
"""
from __future__ import annotations

import time

from . import duplex
from .audio_voice_cues import AudioConsentLease, consume_pcm16_voice_window

BRIDGE_REVISION = "V14_RAW_EAR_AUDIO_DUPLEX_BRIDGE_V1"
_AUDIO_STATUS = "CALLER_SUPPLIED_PCM16_A5_A4_C3_ADMISSION"
_ACTIVITY_HINTS = {"SILENCE", "VOICED", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN"}


def decide_audio_overlap(activity_hint: str, voice_onset: bool, mode: str = "auto"):
    """Return a duplex decision for a newly observed speech onset, or None.

    The default mode is intentionally non-interrupting: onset is recorded as a
    candidate but does not cancel a running answer. Only the user's explicit
    interrupt mode treats any new voiced onset as a barge-in, matching the
    semantics of the existing text duplex controller.
    """
    if mode not in duplex.MODES:
        raise ValueError("duplex_mode auto|interrupt|off")
    if type(activity_hint) is not str or activity_hint not in _ACTIVITY_HINTS:
        raise ValueError("activity_hint is invalid")
    if type(voice_onset) is not bool:
        raise ValueError("voice_onset must be boolean")
    if mode == "off" or activity_hint != "VOICED" or not voice_onset:
        return None
    if mode == "interrupt":
        return "INTERRUPT", "AUDIO_BARGE_IN"
    return "CONTINUE", "AUDIO_OVERLAP_CANDIDATE"


def _validate_audio_result(runtime, audio_result, consent_lease):
    if not isinstance(consent_lease, AudioConsentLease) or consent_lease.active is not True:
        raise PermissionError("a live AudioConsentLease is required for audio duplex dispatch")
    if type(audio_result) is not dict or audio_result.get("status") != _AUDIO_STATUS:
        raise ValueError("audio result is not the canonical RAW EAR consumer result")
    packet = audio_result.get("packet")
    if type(packet) is not dict or packet.get("modality") != "audio":
        raise ValueError("audio PerceptPacket is missing")
    source_ref = packet.get("source_ref")
    segments = packet.get("segments")
    if type(source_ref) is not dict or type(segments) is not list or len(segments) != 1:
        raise ValueError("audio source/segment binding is invalid")
    segment = segments[0]
    if type(segment) is not dict or segment.get("finality") not in {"FINAL", "PROVISIONAL"}:
        raise ValueError("audio segment finality is invalid")
    source_id = source_ref.get("source_id")
    source_sha256 = source_ref.get("sha256")
    generation_id = packet.get("generation_id") or packet.get("brain_generation_id")
    event_id = packet.get("event_id")
    receipt = segment.get("consent_receipt_ref")
    if (type(source_id) is not str or not source_id
            or type(source_sha256) is not str or len(source_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in source_sha256)
            or type(generation_id) is not str or not generation_id
            or type(event_id) is not str or not event_id
            or type(receipt) is not str or not receipt):
        raise ValueError("audio source identity is invalid")
    if not consent_lease.matches(runtime, source_id, generation_id, receipt):
        raise PermissionError("audio result is outside its active source-bound consent lease")
    event = runtime.store.one(
        "SELECT id, brain_generation_id FROM events WHERE id=?", (event_id,)
    )
    if not event or event["brain_generation_id"] != generation_id:
        raise ValueError("audio event is missing or belongs to another generation")
    a4 = audio_result.get("a4")
    cues = a4.get("voice_cues") if type(a4) is dict else None
    temporal = a4.get("temporal_voice") if type(a4) is dict else None
    if type(cues) is not dict or type(temporal) is not dict:
        raise ValueError("A4 RAW EAR voice/temporal evidence is missing")
    activity_hint = cues.get("activity_hint")
    voice_onset = temporal.get("voice_onset")
    if type(activity_hint) is not str or activity_hint not in _ACTIVITY_HINTS:
        raise ValueError("A4 activity hint is invalid")
    if type(voice_onset) is not bool:
        raise ValueError("A4 voice onset is invalid")
    return event_id, activity_hint, voice_onset


def on_audio_input(runtime, audio_result, consent_lease):
    """Decide/cancel under Runtime.lock, then persist through duplex.record.

    Call from the same thread that owns the live AudioConsentLease. The lock
    order is provider lease -> Runtime.lock; the provider must not acquire its
    revocation lock while holding Runtime.lock. Store I/O occurs after the
    Runtime lock is released, mirroring Runtime.submit's text duplex path.
    """
    event_id, activity_hint, voice_onset = _validate_audio_result(
        runtime, audio_result, consent_lease
    )
    mode = runtime.cfg.get("duplex_mode", "auto")
    outcome = decide_audio_overlap(activity_hint, voice_onset, mode)
    if outcome is None:
        return None
    decision_name, relation = outcome
    with runtime.lock:
        current = runtime.turn_event if runtime.current == "turn" else None
        if type(current) is not dict:
            return None
        from_event = current.get("event_id")
        if type(from_event) is not str or not from_event or from_event == event_id:
            return None
        started = time.monotonic()
        decision = {
            "decision": decision_name,
            "relation": relation,
            "from_event": from_event,
            "to_event": event_id,
            "at": time.time(),
            "started": started,
        }
        if decision_name == "INTERRUPT":
            runtime.cancel_event.set()
    try:
        duplex.record(runtime, decision)
        decision["record_status"] = "RECORDED"
    except Exception as exc:
        runtime.store.log(
            "duplex_unavailable", event_id,
            {"stage": "audio_record", "error": type(exc).__name__},
        )
        decision["record_status"] = "FAILED"
    return decision


def consume_pcm16_voice_window_with_duplex(runtime, pcm, *, consent_lease, **kwargs):
    """Run the existing A5->A4->C3 PCM consumer and duplex bridge under one lease.

    The caller must open audio_consent_lease(...) first and pass the same
    handle, temporal state and VAD stream through this function. No microphone
    is opened here; the only input is caller-supplied PCM already authorized
    by the provider.
    """
    if not isinstance(consent_lease, AudioConsentLease) or consent_lease.active is not True:
        raise PermissionError("a live AudioConsentLease is required")
    result = consume_pcm16_voice_window(
        runtime, pcm, consent_lease=consent_lease, **kwargs
    )
    result["duplex"] = on_audio_input(runtime, result, consent_lease)
    return result
