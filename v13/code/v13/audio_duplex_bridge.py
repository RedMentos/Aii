"""Bridge consented RAW EAR voice-onset evidence into the existing duplex controller.

This is an additive adapter, not an audio capture provider. The caller must keep
an AudioConsentLease active while it consumes PCM and dispatches the result. In
default auto mode voice onset is only recorded as an overlap candidate; it
never cancels speech. Cancellation is enabled only by the explicit existing
duplex_mode=interrupt setting. No ASR text, speaker identity, learning
authority or action authority is used.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid

from . import duplex
from .audio_voice_cues import AudioConsentLease, consume_pcm16_voice_window
from .common import dumps

BRIDGE_REVISION = "V14_RAW_EAR_AUDIO_DUPLEX_BRIDGE_V3"
_AUDIO_STATUS = "CALLER_SUPPLIED_PCM16_A5_A4_C3_ADMISSION"
_TEMPORAL_RECEIPT_REVISION = "RAW_EAR_TEMPORAL_VOICE_RECEIPT_V1"
_TEMPORAL_RECEIPT_PROCESS_EPOCH = uuid.uuid4().hex
_REPLAY_STATE_KEY = "RAW_EAR_AUDIO_DUPLEX_REPLAY_V1"
_REPLAY_TTL_NS = 300_000_000_000
_REPLAY_MAX_ENTRIES = 4096
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
        "SELECT id, generation_id FROM events WHERE id=?", (event_id,)
    )
    if not event or event["generation_id"] != generation_id:
        raise ValueError("audio event is missing or belongs to another generation")
    packet_id = packet.get("packet_id")
    if type(packet_id) is not str or not packet_id:
        raise ValueError("audio PerceptPacket id is missing")
    stored_packet = runtime.store.one(
        "SELECT id, event_id, generation_id, payload FROM packets "
        "WHERE id=? AND kind='PerceptPacket'",
        (packet_id,),
    )
    if (not stored_packet or stored_packet["event_id"] != event_id
            or stored_packet["generation_id"] != generation_id):
        raise ValueError("audio PerceptPacket is not persisted for this event/generation")
    try:
        persisted_packet = json.loads(stored_packet["payload"])
    except (TypeError, ValueError) as exc:
        raise ValueError("persisted audio PerceptPacket is unreadable") from exc
    if persisted_packet != packet:
        raise ValueError("audio PerceptPacket differs from its persisted source-bound bytes")
    a4 = audio_result.get("a4")
    acoustic = segment.get("acoustic")
    if type(a4) is not dict or type(acoustic) is not dict:
        raise ValueError("A4 or persisted audio acoustic evidence is missing")
    packet_cues = acoustic.get("voice_cues")
    cues = a4.get("voice_cues")
    temporal = a4.get("temporal_voice")
    temporal_receipt = acoustic.get("temporal_voice_receipt")
    if type(packet_cues) is not dict or type(cues) is not dict:
        raise ValueError("persisted RAW EAR voice cues are missing")
    if cues != packet_cues:
        raise ValueError("A4 voice cues differ from persisted PerceptPacket")
    if type(temporal_receipt) is not dict:
        raise ValueError("persisted RAW EAR temporal receipt is missing")
    receipt_id = temporal_receipt.get("receipt_id")
    receipt_body = {key: value for key, value in temporal_receipt.items() if key != "receipt_id"}
    if (type(receipt_id) is not str or len(receipt_id) != 64
            or any(char not in "0123456789abcdef" for char in receipt_id)
            or hashlib.sha256(dumps(receipt_body).encode("utf-8")).hexdigest() != receipt_id):
        raise ValueError("persisted RAW EAR temporal receipt hash is invalid")
    if temporal_receipt.get("revision") != _TEMPORAL_RECEIPT_REVISION:
        raise ValueError("persisted RAW EAR temporal receipt revision is invalid")
    if temporal_receipt.get("process_epoch") != _TEMPORAL_RECEIPT_PROCESS_EPOCH:
        raise ValueError("persisted RAW EAR temporal receipt belongs to another Runtime process")
    if (temporal_receipt.get("packet_id") != packet_id
            or temporal_receipt.get("event_id") != event_id
            or temporal_receipt.get("generation_id") != generation_id
            or temporal_receipt.get("source_id") != source_id
            or temporal_receipt.get("source_sha256") != source_sha256
            or temporal_receipt.get("consent_receipt_ref") != receipt
            or temporal_receipt.get("start_ms") != segment.get("start_ms")
            or temporal_receipt.get("end_ms") != segment.get("end_ms")):
        raise ValueError("temporal receipt is not bound to this audio packet/source/lease")
    evidence = temporal_receipt.get("evidence")
    if type(evidence) is not dict or temporal != evidence:
        raise ValueError("A4 temporal voice result differs from persisted temporal receipt")
    if (a4.get("temporal_receipt_id") != receipt_id
            or audio_result.get("temporal_receipt_id") != receipt_id):
        raise ValueError("A4 temporal receipt id differs from persisted PerceptPacket")
    if (a4.get("packet_id") != packet_id or a4.get("source_id") != source_id
            or a4.get("finality") != segment.get("finality")):
        raise ValueError("A4 receipt metadata differs from persisted PerceptPacket")
    activity_hint = packet_cues.get("activity_hint")
    voice_onset = evidence.get("voice_onset")
    if type(activity_hint) is not str or activity_hint not in _ACTIVITY_HINTS:
        raise ValueError("persisted A4 activity hint is invalid")
    if type(voice_onset) is not bool or type(evidence.get("voice_active")) is not bool:
        raise ValueError("persisted temporal voice state is invalid")
    created_ns = packet.get("created_monotonic_ns")
    now_ns = time.monotonic_ns()
    if (type(created_ns) is not int or created_ns <= 0
            or created_ns > now_ns or now_ns - created_ns > _REPLAY_TTL_NS):
        raise ValueError("audio temporal receipt is stale or from another monotonic epoch")
    return (
        event_id, packet_id, receipt_id, source_id, generation_id,
        receipt, activity_hint, voice_onset,
    )


def _persist_temporal_voice_receipt(runtime, audio_result, consent_lease):
    """Bind the temporal A4 output to the already-persisted PerceptPacket before dispatch."""
    if not isinstance(consent_lease, AudioConsentLease) or consent_lease.active is not True:
        raise PermissionError("a live AudioConsentLease is required for temporal receipt persistence")
    if type(audio_result) is not dict or audio_result.get("status") != _AUDIO_STATUS:
        raise ValueError("audio result is not the canonical RAW EAR consumer result")
    packet = audio_result.get("packet")
    a4 = audio_result.get("a4")
    if type(packet) is not dict or type(a4) is not dict:
        raise ValueError("audio packet/A4 result is missing")
    source_ref = packet.get("source_ref")
    segments = packet.get("segments")
    if type(source_ref) is not dict or type(segments) is not list or len(segments) != 1:
        raise ValueError("audio source/segment binding is invalid")
    segment = segments[0]
    acoustic = segment.get("acoustic") if type(segment) is dict else None
    temporal = a4.get("temporal_voice")
    if type(acoustic) is not dict or type(temporal) is not dict:
        raise ValueError("A4 temporal evidence is missing")
    source_id = source_ref.get("source_id")
    generation_id = packet.get("generation_id") or packet.get("brain_generation_id")
    event_id = packet.get("event_id")
    packet_id = packet.get("packet_id")
    consent_receipt = segment.get("consent_receipt_ref")
    if (type(source_id) is not str or not source_id
            or type(generation_id) is not str or not generation_id
            or type(event_id) is not str or not event_id
            or type(packet_id) is not str or not packet_id
            or type(consent_receipt) is not str or not consent_receipt):
        raise ValueError("audio temporal receipt identity is invalid")
    if not consent_lease.matches(runtime, source_id, generation_id, consent_receipt):
        raise PermissionError("audio temporal receipt is outside its active consent lease")
    if "temporal_voice_receipt" in acoustic:
        raise ValueError("audio packet already has a temporal voice receipt")
    cues = acoustic.get("voice_cues")
    if type(cues) is not dict or a4.get("voice_cues") != cues:
        raise ValueError("A4 voice cues do not match the persisted packet")
    if (a4.get("packet_id") != packet_id or a4.get("source_id") != source_id
            or a4.get("finality") != segment.get("finality")):
        raise ValueError("A4 metadata does not match the persisted packet")
    expected_payload = dumps(packet)
    receipt_body = {
        "revision": _TEMPORAL_RECEIPT_REVISION,
        "process_epoch": _TEMPORAL_RECEIPT_PROCESS_EPOCH,
        "packet_id": packet_id,
        "event_id": event_id,
        "generation_id": generation_id,
        "source_id": source_id,
        "source_sha256": source_ref.get("sha256"),
        "consent_receipt_ref": consent_receipt,
        "start_ms": segment.get("start_ms"),
        "end_ms": segment.get("end_ms"),
        "evidence": dict(temporal),
    }
    receipt = dict(receipt_body)
    receipt["receipt_id"] = hashlib.sha256(dumps(receipt_body).encode("utf-8")).hexdigest()
    acoustic["temporal_voice_receipt"] = receipt
    updated_payload = dumps(packet)
    with runtime.store.tx() as connection:
        changed = connection.execute(
            "UPDATE packets SET payload=? WHERE id=? AND kind='PerceptPacket' "
            "AND event_id=? AND generation_id=? AND payload=?",
            (updated_payload, packet_id, event_id, generation_id, expected_payload),
        ).rowcount
    if changed != 1:
        acoustic.pop("temporal_voice_receipt", None)
        raise ValueError("persisted PerceptPacket changed before temporal receipt binding")
    a4["temporal_receipt_id"] = receipt["receipt_id"]
    audio_result["temporal_receipt_id"] = receipt["receipt_id"]
    return receipt


def _claim_one_use_audio_receipt(runtime, event_id, packet_id, temporal_receipt_id):
    """Durably claim one audio event/packet receipt, including non-cancelling CONTINUE."""
    receipt_key = hashlib.sha256(dumps({
        "event_id": event_id,
        "packet_id": packet_id,
        "temporal_receipt_id": temporal_receipt_id,
    }).encode("utf-8")).hexdigest()
    now_ns = time.monotonic_ns()
    for _ in range(8):
        state, version = runtime.store.state(
            _REPLAY_STATE_KEY, {"revision": 1, "entries": []},
        )
        if (type(state) is not dict or state.get("revision") != 1
                or type(state.get("entries")) is not list):
            raise ValueError("audio duplex replay guard state is corrupt")
        active = []
        for entry in state["entries"]:
            if (type(entry) is not dict
                    or type(entry.get("receipt_key")) is not str
                    or len(entry["receipt_key"]) != 64
                    or type(entry.get("process_epoch")) is not str
                    or type(entry.get("expires_monotonic_ns")) is not int):
                raise ValueError("audio duplex replay guard entry is corrupt")
            if (entry["process_epoch"] == _TEMPORAL_RECEIPT_PROCESS_EPOCH
                    and entry["expires_monotonic_ns"] > now_ns):
                active.append(entry)
        if any(entry["receipt_key"] == receipt_key for entry in active):
            raise ValueError("audio event/packet temporal receipt was already consumed")
        if len(active) >= _REPLAY_MAX_ENTRIES:
            raise RuntimeError("audio duplex replay guard is full; refusing dispatch")
        active.append({
            "receipt_key": receipt_key,
            "process_epoch": _TEMPORAL_RECEIPT_PROCESS_EPOCH,
            "expires_monotonic_ns": now_ns + _REPLAY_TTL_NS,
        })
        try:
            runtime.store.set_state(
                _REPLAY_STATE_KEY, {"revision": 1, "entries": active},
                expected=version,
            )
            return receipt_key
        except ValueError:
            # Another dispatcher won the Store CAS; reread and detect its claim.
            continue
    raise RuntimeError("audio duplex replay guard could not claim receipt atomically")


def on_audio_input(runtime, audio_result, consent_lease):
    """Decide/cancel under Runtime.lock, then persist through duplex.record.

    Call from the same thread that owns the live AudioConsentLease. The lock
    order is provider lease -> Runtime.lock; the provider must not acquire its
    revocation lock while holding Runtime.lock. Store I/O occurs after the
    Runtime lock is released, mirroring Runtime.submit's text duplex path.
    """
    (
        event_id, packet_id, temporal_receipt_id, _source_id, _generation_id,
        _consent_receipt, activity_hint, voice_onset,
    ) = _validate_audio_result(runtime, audio_result, consent_lease)
    mode = runtime.cfg.get("duplex_mode", "auto")
    outcome = decide_audio_overlap(activity_hint, voice_onset, mode)
    # Claim every receipt, even when the decision is CONTINUE or mode=off.
    # The Store CAS is durable and happens before Runtime.lock/cancellation.
    _claim_one_use_audio_receipt(runtime, event_id, packet_id, temporal_receipt_id)
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
    decision["bridge_revision"] = BRIDGE_REVISION
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
    _persist_temporal_voice_receipt(runtime, result, consent_lease)
    result["duplex"] = on_audio_input(runtime, result, consent_lease)
    return result
