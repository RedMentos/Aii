"""Turn-scoped bridge from a signed Android frame to normal A5/B1/B2/C3 consumers.

This module never starts MediaProjection. It only consumes a frame already
captured by the separate companion after explicit OS consent. The outer
UIObservationLease and inner Perception source scope remain live until Runtime
closes its ExitStack after C3 generation. Neither raw frames nor derived
PerceptPackets are persisted by this bridge.
"""
from __future__ import annotations

from contextlib import contextmanager
import re

from .a5_ui_admission_bridge import A5UIRuntimeAdapter


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _source_ref_ok(ref):
    return (
        isinstance(ref, dict)
        and isinstance(ref.get("source_id"), str) and bool(ref["source_id"])
        and isinstance(ref.get("sha256"), str) and bool(_SHA256.fullmatch(ref["sha256"]))
        and isinstance(ref.get("modality"), str)
        and type(ref.get("char_start")) is int
        and type(ref.get("char_end")) is int
        and 0 <= ref["char_start"] <= ref["char_end"]
    )


@contextmanager
def current_turn_context(
    runtime, current_source, *, goal="", token_budget=512,
    context_budget_chars=320, priority=0, cfg=None,
):
    """Yield a transient UI context while the exact turn's signed lease is live."""
    event = getattr(runtime, "turn_event", None)
    if type(event) is not dict or getattr(runtime, "current", None) != "turn":
        yield None
        return
    if type(current_source) is not str or not current_source:
        raise ValueError("current source text is required for UI admission")
    event_id = event.get("event_id")
    generation_id = event.get("brain_generation_id")
    if type(event_id) is not str or type(generation_id) is not str:
        raise ValueError("active Runtime turn has no event/generation binding")

    # Do not instantiate or poll the companion on ordinary chats. It is reached
    # only after the user has explicitly opened the :android operator surface.
    controller = getattr(runtime, "_android_companion_controller", None)
    trust_path = getattr(controller, "trust_path", None) if controller is not None else None
    if controller is None or trust_path is None or not trust_path.exists():
        yield None
        return

    with controller.open_current_turn(runtime) as grant:
        if grant is None:
            yield None
            return
        with grant.consume_scope(
            runtime, current_source=current_source, goal=goal,
            token_budget=token_budget, context_budget_chars=context_budget_chars,
            priority=priority, cfg=cfg,
        ) as result:
            if not isinstance(result, dict):
                raise PermissionError("A5 UI consumer returned no scoped result")
            packet = result.get("packet")
            if not isinstance(packet, dict):
                raise PermissionError("A5 UI consumer returned no PerceptPacket")
            packets = A5UIRuntimeAdapter(runtime).context(event_id, grant.lease)
            if len(packets) != 1 or packets[0] != packet:
                raise PermissionError("A5 UI context is not the exact live leased PerceptPacket")
            if (
                packet.get("event_id") != event_id
                or packet.get("brain_generation_id") != generation_id
                or packet.get("modality") != "ui"
                or packet.get("finality") != "FINAL"
                or packet.get("feature_method") != "HANDCRAFTED_RAW_EYE_V1"
                or packet.get("frame_binding_status") != "PROVIDER_CALLBACK_ACCEPTED"
                or packet.get("capture_method") != "MEDIA_PROJECTION"
                or packet.get("capture_scope") != "FULL_DISPLAY"
                or packet.get("raw_capture_persisted") is not False
                or packet.get("derived_packet_persisted") is not False
                or packet.get("action_authority") is not False
                or packet.get("learning_authority") is not False
                or packet.get("truth_authority") != 0
                or not isinstance(packet.get("frame_sha256"), str)
                or not _SHA256.fullmatch(packet["frame_sha256"])
            ):
                raise PermissionError("A5 UI PerceptPacket authority/provenance contract failed")
            if (
                result.get("raw_capture_persisted") is not False
                or result.get("derived_packet_persisted") is not False
                or result.get("caller_buffer_overwritten") is not True
                or result.get("action_authority") is not False
                or result.get("learning_authority") is not False
                or result.get("truth_authority") != 0
                or result.get("frame_binding_status") != "PROVIDER_CALLBACK_ACCEPTED"
            ):
                raise PermissionError("A5 UI consumer persistence/authority result failed")

            envelope = result.get("context_envelope")
            text = getattr(envelope, "optional_context", None)
            included_ids = getattr(envelope, "included_ids", None)
            omitted_ids = getattr(envelope, "omitted_ids", None)
            if isinstance(envelope, dict):
                text = envelope.get("optional_context", text)
                included_ids = envelope.get("included_ids", included_ids)
                omitted_ids = envelope.get("omitted_ids", omitted_ids)
            if (
                type(text) is not str
                or len(text) > context_budget_chars
                or not isinstance(included_ids, (list, tuple))
                or not isinstance(omitted_ids, (list, tuple))
            ):
                raise PermissionError("A5 UI context envelope is malformed or over budget")

            source_refs = packet.get("provenance")
            source_ref = packet.get("source_ref")
            if (
                type(source_refs) is not list or len(source_refs) != 2
                or not all(_source_ref_ok(ref) for ref in source_refs)
                or not isinstance(source_ref, dict)
                or source_ref != source_refs[0]
            ):
                raise PermissionError("A5 UI source binding is malformed")
            if (
                type(packet.get("capture_session_id")) is not str
                or not packet["capture_session_id"]
                or type(packet.get("consent_receipt_ref")) is not str
                or not packet["consent_receipt_ref"]
                or type(packet.get("feature_revision")) is not str
                or not packet["feature_revision"]
            ):
                raise PermissionError("A5 UI capture/feature identity is missing")

            binding = {
                "schema": "v14.ephemeral-ui-observation-binding/1",
                "event_id": event_id,
                "brain_generation_id": generation_id,
                "source_id": source_ref["source_id"],
                "frame_source_id": source_refs[1]["source_id"],
                "frame_sha256": packet["frame_sha256"],
                "capture_session_id": packet["capture_session_id"],
                "consent_receipt_ref": packet["consent_receipt_ref"],
                "capture_method": packet["capture_method"],
                "capture_scope": packet["capture_scope"],
                "feature_method": packet["feature_method"],
                "feature_revision": packet["feature_revision"],
                "finality": packet["finality"],
                "action_authority": False,
                "learning_authority": False,
                "truth_authority": 0,
                "raw_capture_persisted": False,
                "derived_packet_persisted": False,
                "student_projector_used": bool(packet.get("student_projector_used")),
                "student_estimate_authority": (packet.get("student_estimate") or {}).get("authority", "NONE"),
            }
            audit = dict(binding) | {
                "status": "CONSUMED" if text else "CONSUMED_NO_CONTEXT",
                "context_chars": len(text),
                "context_packet_id": packet.get("packet_id"),
                "included_ids": list(included_ids),
                "omitted_ids": list(omitted_ids),
                "c3_context_attached": False,
            }
            yield {
                "text": text,
                "binding": binding,
                "source_refs": [dict(ref) for ref in source_refs],
                "event_id": event_id,
                "brain_generation_id": generation_id,
                "audit": audit,
            }


def body_ui_query(ui_context, event_id, generation_id):
    """Return model-only visual context plus content-free ephemeral provenance."""
    if ui_context is None:
        return {}, None, []
    if not isinstance(ui_context, dict):
        raise ValueError("UI context must be a dictionary")
    binding = ui_context.get("binding")
    text = ui_context.get("text")
    refs = ui_context.get("source_refs")
    if (
        not isinstance(binding, dict)
        or binding.get("schema") != "v14.ephemeral-ui-observation-binding/1"
        or binding.get("event_id") != event_id
        or binding.get("brain_generation_id") != generation_id
        or type(text) is not str or len(text) > 320
        or type(refs) is not list or len(refs) != 2
        or not all(_source_ref_ok(ref) for ref in refs)
        or binding.get("action_authority") is not False
        or binding.get("learning_authority") is not False
        or binding.get("truth_authority") != 0
        or binding.get("raw_capture_persisted") is not False
        or binding.get("derived_packet_persisted") is not False
    ):
        raise ValueError("UI context binding is invalid or belongs to another turn")
    if not text:
        return {}, dict(binding), [dict(ref) for ref in refs]
    prompt_binding = {
        key: binding[key]
        for key in (
            "source_id", "frame_source_id", "frame_sha256",
            "capture_session_id", "capture_method", "capture_scope",
            "feature_method", "feature_revision", "finality",
        )
    }
    return {
        "current_ui_observation": {
            "summary": text,
            "source_binding": prompt_binding,
            "authority": "TRANSIENT_LOW_LEVEL_FEATURES_ONLY",
            "not_ocr_or_object_recognition": True,
            "can_quote_as_source_text": False,
            "action_authority": False,
            "learning_authority": False,
            "truth_authority": 0,
        }
    }, dict(binding), [dict(ref) for ref in refs]


def append_c3_ui_context(messages, ui_context, event_id, generation_id):
    """Add the live UI summary only to the in-memory C3 prompt after context save."""
    query, _, _ = body_ui_query(ui_context, event_id, generation_id)
    if not query:
        return messages
    if type(messages) is not list or not messages or messages[0].get("role") != "system":
        raise ValueError("C3 messages require a leading system message")
    result = [dict(message) for message in messages]
    if type(result[0].get("content")) is not str:
        raise ValueError("C3 system message content must be text")
    summary = query["current_ui_observation"]["summary"]
    result[0]["content"] += (
        "\n\nCURRENT TURN — USER-APPROVED TRANSIENT SCREEN OBSERVATION\n"
        "This is low-level RAW-EYE feature context, not OCR or object recognition. "
        "Treat it as uncertain; do not quote it as source text. It grants no action "
        "or learning authority.\n" + summary
    )
    return result
