"""Consent-rechecked RAW EAR PCM16 -> canonical A5 PerceptPacket -> A4/C3 bridge.

The caller supplies PCM bytes and a current-consent provider. This module does
not open a microphone, retain PCM, run ASR, infer speaker identity, or grant
learning/action authority. It persists only the bounded acoustic packet.
"""
import math
import re

from . import attention as attctl
from .a5_audio_admission_bridge import audio_to_admission
from .audio_ear import observe_pcm16
from .audio_percept_contract import audio_percept_packet
from .contracts import validate
from .percept_admission import admit

_SHA256 = re.compile(r"[0-9a-f]{64}")


def _require_current_consent(consent_check, source_id, receipt_ref):
    if not callable(consent_check):
        raise TypeError("a current-consent provider is required")
    try:
        active = consent_check(source_id, receipt_ref)
    except Exception:
        raise PermissionError("current audio consent could not be verified") from None
    if active is not True:
        raise PermissionError("current audio consent is not active")


def _validate_packet_shape(audio_packet):
    validate("PerceptPacket", audio_packet)
    if type(audio_packet.get("event_id")) is not str or not audio_packet["event_id"]:
        raise ValueError("missing audio event binding")
    if type(audio_packet.get("brain_generation_id")) is not str or not audio_packet["brain_generation_id"]:
        raise ValueError("missing audio generation binding")
    if audio_packet.get("modality") != "audio":
        raise ValueError("expected audio PerceptPacket")
    source = audio_packet.get("source_ref")
    provenance = audio_packet.get("provenance")
    if (type(source) is not dict or type(provenance) is not list or len(provenance) != 1
            or provenance[0] != source):
        raise ValueError("audio source provenance mismatch")
    source_id = source.get("source_id")
    digest = source.get("sha256")
    if type(source_id) is not str or not source_id or len(source_id) > 128:
        raise ValueError("invalid audio source ID")
    if type(digest) is not str or not _SHA256.fullmatch(digest):
        raise ValueError("invalid audio source digest")
    if (source.get("modality") != "audio" or type(source.get("char_start")) is not int
            or type(source.get("char_end")) is not int
            or source["char_start"] != 0 or source["char_end"] != 0):
        raise ValueError("invalid audio SourceRef")
    segments = audio_packet.get("segments")
    if type(segments) is not list or len(segments) != 1 or type(segments[0]) is not dict:
        raise ValueError("expected one bounded audio segment")
    segment = segments[0]
    start, end = segment.get("start_ms"), segment.get("end_ms")
    if type(start) is not int or type(end) is not int or not 0 <= start < end or end - start > 1000:
        raise ValueError("invalid audio interval")
    if segment.get("finality") not in ("FINAL", "PROVISIONAL"):
        raise ValueError("invalid audio finality")
    receipt = segment.get("consent_receipt_ref")
    if type(receipt) is not str or not receipt.strip() or len(receipt) > 256:
        raise PermissionError("audio consent receipt reference required")
    if segment.get("learning_authority") is not False or segment.get("action_authority") is not False:
        raise PermissionError("RAW EAR cannot grant learning or action authority")
    if segment.get("asr_transcript") is not None:
        raise ValueError("this acoustic-only bridge does not accept transcripts")
    acoustic = segment.get("acoustic")
    if type(acoustic) is not dict:
        raise ValueError("missing acoustic features")
    rms, zcr = acoustic.get("rms"), acoustic.get("zcr")
    if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in (rms, zcr)):
        raise ValueError("invalid normalized acoustic features")
    return source_id, receipt, float(rms), float(zcr), segment


def _validate_runtime_binding(runtime, event_id, audio_packet):
    source_id, receipt, rms, zcr, segment = _validate_packet_shape(audio_packet)
    if type(event_id) is not str or not event_id or audio_packet["event_id"] != event_id:
        raise ValueError("audio packet event binding mismatch")
    if audio_packet["brain_generation_id"] != runtime.store.generation_id:
        raise ValueError("audio packet generation is stale")
    if runtime.store.one("SELECT id FROM events WHERE id=?", (event_id,)) is None:
        raise ValueError("audio packet event is not in the active Store")
    return source_id, receipt, rms, zcr, segment


def consume_audio_packet(runtime, event_id, audio_packet, *, consent_check):
    """Persist a canonical A5 packet and feed real A4 Attention under live consent."""
    source_id, receipt, rms, zcr, segment = _validate_runtime_binding(runtime, event_id, audio_packet)
    _require_current_consent(consent_check, source_id, receipt)
    runtime.store.add_packet("PerceptPacket", audio_packet)
    # Recheck after persistence and immediately before the A4 consumer.
    _require_current_consent(consent_check, source_id, receipt)
    attention = attctl.controller(runtime)
    # BOOT mapping only: RMS can recruit an interrupt; zero-crossing rate is a
    # weak novelty proxy. Neither signal changes truth or permission authority.
    result = attention.modulate(event_id, sal={
        "novelty": min(1.0, zcr),
        "external_interrupt": min(1.0, rms * 0.5),
    })
    return {
        "packet_id": audio_packet["packet_id"],
        "source_id": source_id,
        "finality": segment["finality"],
        "attention": result,
        "learning_authority": False,
        "action_authority": False,
    }


def admit_audio_packet(runtime, event_id, audio_packet, *, consent_check, token_budget):
    """Return a bounded C3 Percept admission; this does not inject it into C3 prompts."""
    source_id, receipt, _, _, _ = _validate_runtime_binding(runtime, event_id, audio_packet)
    _require_current_consent(consent_check, source_id, receipt)
    candidate = audio_to_admission(audio_packet, consent_active=True)
    return admit((candidate,), token_budget)


def consume_pcm16_window(runtime, pcm, *, sample_rate, start_ms, event_id,
                         generation_id, source_id, consent_receipt,
                         consent_check, token_budget=512, finality="FINAL"):
    """Build one <=1s A5 packet, deliver it to A4, then recheck consent for C3."""
    _require_current_consent(consent_check, source_id, consent_receipt)
    raw = observe_pcm16(
        pcm, sample_rate, start_ms, consent=True, source_id=source_id, max_seconds=1
    )
    segment = raw["segments"][0]
    audio_packet = audio_percept_packet(
        event_id=event_id,
        generation_id=generation_id,
        source_id=source_id,
        source_sha256=raw["source_ref"]["sha256"],
        start_ms=segment["start_ms"],
        end_ms=segment["end_ms"],
        rms=segment["acoustic"]["rms"],
        zcr=segment["acoustic"]["zero_crossing_rate"],
        finality=finality,
        consent_receipt=consent_receipt,
    )
    a4 = consume_audio_packet(
        runtime, event_id, audio_packet, consent_check=consent_check
    )
    c3 = admit_audio_packet(
        runtime, event_id, audio_packet,
        consent_check=consent_check, token_budget=token_budget
    )
    return {
        "status": "SYNTHETIC_PCM16_A5_A4_C3_ADMISSION",
        "packet": audio_packet,
        "a4": a4,
        "c3_admission": c3,
        "capture_authority": "CALLER_SUPPLIED_PCM16",
        "learning_authority": False,
        "action_authority": False,
    }
