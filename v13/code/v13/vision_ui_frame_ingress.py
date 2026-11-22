"""Ephemeral RAW EYE features from an already-authorized MediaProjection frame.

The Android companion remains the only capture provider. This adapter accepts
one caller-owned mutable frame buffer while the existing UIObservationLease is
held, computes bounded handcrafted visual features, and returns an ephemeral
PerceptPacket/A4/admission result. It never opens MediaProjection, stores the
frame, persists derived features, performs OCR, or grants action/learning
authority. The caller must keep the same lease open through every downstream
consumer, including C3 generation.
"""
from __future__ import annotations

import hashlib
import math

from . import attention as attention_module
from . import vision
from .a5_context_envelope import A5Item, admit_a5
from .a5_ui_admission_bridge import (
    A5UIRuntimeAdapter,
    UIObservationLease,
    validate_ui_observation,
)
from .contracts import packet as make_packet, validate
from .percept_admission import Percept, admit

REVISION = "v14-a5-media-projection-raw-eye-v1"
MAX_FRAME_BYTES = 8 * 1024 * 1024
MAX_FRAME_PIXELS = 4_000_000
GRID = 4
TILE_PX = 32
MAX_REGIONS = 1 + GRID * GRID
MAX_SUMMARY_CHARS = 512


def _summary(observation: dict) -> str:
    return (
        "ui event=" + observation["event_kind"]
        + " method=" + observation["capture_method"]
        + " scope=" + observation["capture_scope"]
        + " api=" + str(observation["api_level"])
        + " clock=ELAPSED_REALTIME"
        + " interval_ms=" + str(observation["end_ms"] - observation["start_ms"])
    )


def _feature_summary(region_id, box, features, salience=None) -> str:
    if len(features) != 37:
        raise ValueError("RAW EYE tile feature dimension changed")
    rgb = [float(features[i]) for i in range(3)]
    edge_energy = float(features[16])
    luminance = sum(float(x) for x in features[21:37]) / 16.0
    if not all(math.isfinite(x) for x in rgb + [edge_energy, luminance]):
        raise ValueError("RAW EYE feature contains a non-finite value")
    spread = max(rgb) - min(rgb)
    if spread < 0.08:
        dominant = "neutral"
    else:
        dominant = ("red", "green", "blue")[max(range(3), key=lambda i: rgb[i])]
    salience_text = "" if salience is None else f" salience={float(salience):.4f}"
    box_text = ",".join(str(int(x)) for x in box)
    return (
        f"RAW_EYE region={region_id} dominant_channel={dominant}_heuristic "
        f"mean_rgb={rgb[0]:.3f},{rgb[1]:.3f},{rgb[2]:.3f} "
        f"edge_energy={edge_energy:.4f} mean_luminance={luminance:.3f}"
        f"{salience_text} pixel_box={box_text}"
    )[:MAX_SUMMARY_CHARS]


def _overwrite_caller_buffer(buffer: bytearray) -> None:
    # Best-effort overwrite; Python/PIL internal copies cannot be guaranteed erased.
    if type(buffer) is bytearray:
        buffer[:] = b"\x00" * len(buffer)


def _bounded_vision_config(cfg):
    merged = dict(vision.DEFAULTS)
    if cfg is not None:
        if type(cfg) is not dict or set(cfg) - set(merged):
            raise ValueError("unknown RAW EYE frame configuration")
        merged.update(cfg)
    if type(merged.get("grid")) is not int or merged["grid"] != GRID:
        raise ValueError("MediaProjection RAW EYE requires the fixed 4x4 grid")
    if type(merged.get("tile_px")) is not int or merged["tile_px"] != TILE_PX:
        raise ValueError("MediaProjection RAW EYE requires 32px feature tiles")
    for key, cap in (("max_bytes", MAX_FRAME_BYTES), ("max_pixels", MAX_FRAME_PIXELS)):
        value = merged.get(key)
        if type(value) is not int or value < 1:
            raise ValueError("invalid RAW EYE frame size bound")
        merged[key] = min(value, cap)
    return merged


def consume_projected_frame(
    runtime,
    observation,
    frame_buffer,
    *,
    consent_lease: UIObservationLease,
    frame_binding_check,
    current_source: str,
    goal: str = "",
    token_budget: int = 512,
    context_budget_chars: int = 320,
    priority: int = 0,
    cfg=None,
):
    """Consume one MediaProjection frame under the exact active UI grant.

    frame_buffer must be a mutable bytearray so this function can overwrite
    the caller-owned compressed bytes after decoding. frame_binding_check must
    be a provider-owned verifier for the current signed frame receipt, exact
    digest, and capture session. The decoded RGB image is closed before return.
    No raw frame or derived packet is written to Store. Python/PIL internal
    copies are not guaranteed to be securely erased.
    """
    if type(frame_buffer) is not bytearray:
        raise TypeError("frame_buffer must be a mutable bytearray")
    image = None
    try:
        if not frame_buffer:
            raise ValueError("empty MediaProjection frame")
        if len(frame_buffer) > MAX_FRAME_BYTES:
            raise ValueError("MediaProjection frame exceeds 8 MiB")

        observation = validate_ui_observation(observation)
        if (observation["capture_method"] != "MEDIA_PROJECTION"
                or observation["event_kind"] != "SCREEN_FRAME_AVAILABLE"):
            raise PermissionError("RAW EYE frame ingress requires a MediaProjection frame event")
        event = getattr(runtime, "turn_event", None)
        if (type(event) is not dict or type(event.get("event_id")) is not str
                or type(event.get("brain_generation_id")) is not str):
            raise ValueError("visual ingress requires an active Runtime turn event")
        generation_id = event["brain_generation_id"]
        if (not isinstance(consent_lease, UIObservationLease)
                or not consent_lease.matches(runtime, observation, generation_id)):
            raise PermissionError("a live source/session/receipt-bound UI lease is required")
        if not isinstance(current_source, str) or not current_source:
            raise ValueError("current_source must preserve the nonempty user prompt")
        if not isinstance(goal, str):
            raise ValueError("goal must be text")
        if type(token_budget) is not int or not 0 <= token_budget <= 8192:
            raise ValueError("token_budget must be an integer in 0..8192")
        if type(context_budget_chars) is not int or not 0 <= context_budget_chars <= 4096:
            raise ValueError("context_budget_chars must be an integer in 0..4096")
        if type(priority) is not int or not -100 <= priority <= 100:
            raise ValueError("priority must be an integer in -100..100")

        cfg = _bounded_vision_config(cfg)
        frame_sha256 = hashlib.sha256(frame_buffer).hexdigest()
        if not callable(frame_binding_check):
            raise PermissionError("provider frame-receipt verifier is required")
        try:
            frame_bound = frame_binding_check(observation, frame_sha256, len(frame_buffer))
        except Exception:
            frame_bound = False
        if frame_bound is not True:
            raise PermissionError("MediaProjection frame digest is not bound to the active provider receipt")
        image = vision.decode(frame_buffer, cfg)
        _overwrite_caller_buffer(frame_buffer)
        if not consent_lease.active_for(runtime, generation_id):
            raise PermissionError("UI observation was cancelled or revoked during frame decode")

        width, height = image.size
        if width < 1 or height < 1 or width * height > MAX_FRAME_PIXELS:
            raise ValueError("decoded MediaProjection dimensions exceed the 4 MP bound")
        background = vision.background(image)
        regions = [
            region for region in vision.boxes(width, height, GRID)
            if region.get("region_id") == "g"
            or (isinstance(region.get("region_id"), str)
                and region["region_id"].startswith("r"))
        ]
        if len(regions) != MAX_REGIONS:
            raise ValueError("RAW EYE frame grid is incomplete")

        frame_seed = "\0".join((
            observation["source_id"], observation["capture_session_id"],
            str(observation["start_ms"]), str(observation["end_ms"]), frame_sha256,
        )).encode("utf-8")
        frame_source_id = "ui_frame_" + hashlib.sha256(frame_seed).hexdigest()[:32]
        frame_ref = {
            "source_id": frame_source_id,
            "sha256": frame_sha256,
            "char_start": 0,
            "char_end": 0,
            "modality": "image",
        }
        ui_summary = _summary(observation)
        ui_ref = {
            "source_id": observation["source_id"],
            "sha256": hashlib.sha256(ui_summary.encode("utf-8")).hexdigest(),
            "char_start": 0,
            "char_end": len(ui_summary),
            "modality": "ui",
        }

        segments = [{
            "text": ui_summary,
            "source_ref": ui_ref,
            "start_ms": observation["start_ms"],
            "end_ms": observation["end_ms"],
            "clock": observation["clock"],
            "finality": observation["finality"],
            "event_kind": observation["event_kind"],
            "capture_method": observation["capture_method"],
            "capture_scope": observation["capture_scope"],
            "consent_receipt_ref": observation["consent_receipt_ref"],
            "raw_capture_persisted": False,
            "learning_authority": False,
            "action_authority": False,
        }]
        percepts = [Percept(
            observation["source_id"], "ui", observation["start_ms"], observation["end_ms"],
            ui_summary, True, observation["finality"] == "FINAL", priority,
        )]
        try:
            for region in regions:
                box = region["box"]
                if region["region_id"] == "g":
                    tile = image
                    salience = None
                else:
                    tile = image.crop(tuple(box))
                    salience = float(vision.saliency(image, box, background))
                    if not math.isfinite(salience) or not 0.0 <= salience <= 1.0:
                        raise ValueError("RAW EYE salience is outside [0,1]")
                try:
                    features = vision.tile_features(tile, TILE_PX)
                    summary = _feature_summary(region["region_id"], box, features, salience)
                finally:
                    if tile is not image:
                        tile.close()
                region_ref = vision.region_ref(frame_ref, region)
                source_id = f"{frame_source_id}:{region['region_id']}"
                segment = {
                    "text": summary,
                    "source_ref": region_ref,
                    "start_ms": observation["start_ms"],
                    "end_ms": observation["end_ms"],
                    "clock": observation["clock"],
                    "time_basis": "ELAPSED_REALTIME",
                    "finality": observation["finality"],
                    "authority": "RAW_FEATURE_MEASUREMENT",
                    "raw_capture_persisted": False,
                    "learning_authority": False,
                    "action_authority": False,
                }
                segments.append(segment)
                tile_priority = priority * 1000 + (101 if salience is None else int(round(salience * 100)))
                percepts.append(Percept(
                    source_id, "ui", observation["start_ms"], observation["end_ms"],
                    summary, True, observation["finality"] == "FINAL", tile_priority,
                ))
        finally:
            image.close()
            image = None

        if not consent_lease.active_for(runtime, generation_id):
            raise PermissionError("UI observation was cancelled or revoked before A4 admission")

        a4 = attention_module.controller(runtime).perceive(
            event["event_id"], segments, goal=goal, file_requests=False
        )
        admission = admit(percepts, token_budget, max_items=12)
        context_items = [
            A5Item(
                source_id=item.source_id,
                summary=item.summary,
                consent=item.consent,
                final=item.final,
                priority=item.priority,
            )
            for item in admission.selected
        ]
        envelope = admit_a5(
            current_source,
            context_items,
            budget_chars=context_budget_chars,
        )
        percept_packet = make_packet(
            "PerceptPacket", "A5_RAW_EYE_UI", event["event_id"], generation_id,
            [ui_ref, frame_ref], source_ref=ui_ref, segments=segments, modality="ui",
            capture_session_id=observation["capture_session_id"],
            consent_receipt_ref=observation["consent_receipt_ref"],
            capture_method=observation["capture_method"],
            capture_scope=observation["capture_scope"], clock=observation["clock"],
            finality=observation["finality"], frame_sha256=frame_sha256,
            frame_size=[width, height],
            feature_method="HANDCRAFTED_RAW_EYE_V1", feature_revision=REVISION,
            frame_binding_status="PROVIDER_CALLBACK_ACCEPTED",
            raw_capture_persisted=False, derived_packet_persisted=False,
            teacher_used=False, student_projector_used=False,
            learning_authority=False, action_authority=False, truth_authority=0,
        )
        validate("PerceptPacket", percept_packet)
        if not consent_lease.active_for(runtime, generation_id):
            raise PermissionError("UI observation was cancelled or revoked before context caching")

        adapter = A5UIRuntimeAdapter(runtime)
        cache = runtime._a5_ui_context_cache
        cache[observation["source_id"]] = percept_packet
        while len(cache) > 64:
            cache.pop(next(iter(cache)))
        context_packets = adapter.context(event["event_id"], consent_lease)
        if observation["finality"] == "FINAL" and percept_packet not in context_packets:
            cache.pop(observation["source_id"], None)
            raise RuntimeError("final RAW EYE packet did not reach the active UI context consumer")

        return {
            "status": "WIRED_SYNTHETIC",
            "revision": REVISION,
            "packet": percept_packet,
            "source_ref": ui_ref,
            "frame_source_ref": frame_ref,
            "a4": a4,
            "admission": admission,
            "context_envelope": envelope,
            "context_packet_count": len(context_packets),
            "omitted_percept_ids": list(admission.omitted),
            "omitted_context_ids": list(envelope.omitted_ids),
            "raw_capture_persisted": False,
            "derived_packet_persisted": False,
            "caller_buffer_overwritten": not any(frame_buffer),
            "frame_binding_status": "PROVIDER_CALLBACK_ACCEPTED",
            "teacher_used": False,
            "student_projector_used": False,
            "learning_authority": False,
            "action_authority": False,
            "truth_authority": 0,
            "context_budget_kind": "UTF8_BYTE_UPPER_BOUND_AND_CHAR_PREFILTER_NOT_NATIVE_TOKENIZER",
        }
    finally:
        if image is not None:
            image.close()
        _overwrite_caller_buffer(frame_buffer)


__all__ = ["REVISION", "consume_projected_frame"]