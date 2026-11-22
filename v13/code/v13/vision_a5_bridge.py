"""Source-bound RAW EYE image ingress into A5, A4 and bounded C3 context.

This is a local user-supplied-image adapter. It accepts only an existing IMAGE
SourceRef created by vision.ingest after an explicit local :image add action.
It does not read arbitrary paths, capture the screen/camera, call a teacher/VLM,
use a trained projector, persist derived vectors, train weights or grant action
authority. Static images have no trustworthy monotonic capture timestamp; the
packet marks timing UNKNOWN rather than inventing one.

The returned PerceptPacket and context envelope are ephemeral. The original
image remains in the existing content-addressed Store blob. A normal Runtime
turn must explicitly call this adapter and consume the returned envelope;
this module does not silently modify runtime.py or the default text path.
"""
from __future__ import annotations

import math
import re

from . import attention as attention_module
from . import vision
from .a5_context_envelope import A5Item, admit_a5
from .common import Unavailable
from .contracts import packet as make_packet, validate
from .percept_admission import Percept, admit


REVISION = "v14-a5-raw-eye-ingress-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_REGIONS = 64
_MAX_SUMMARY_CHARS = 512


def _validate_image_ref(ref):
    required = {"source_id", "sha256", "char_start", "char_end", "modality"}
    if type(ref) is not dict or set(ref) != required:
        raise ValueError("image SourceRef must be the exact base IMAGE reference")
    if (type(ref["source_id"]) is not str or not ref["source_id"].strip()
            or len(ref["source_id"]) > 128):
        raise ValueError("image source_id is invalid")
    if type(ref["sha256"]) is not str or not _SHA256.fullmatch(ref["sha256"]):
        raise ValueError("image source SHA256 is invalid")
    if (type(ref["char_start"]) is not int or type(ref["char_end"]) is not int
            or ref["char_start"] != 0 or ref["char_end"] != 0
            or ref["modality"] != "image"):
        raise ValueError("image SourceRef modality/range is invalid")
    return dict(ref)


def _feature_summary(prefix, region_id, box, features, salience=None):
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
        f"{prefix} region={region_id} dominant_channel={dominant}_heuristic "
        f"mean_rgb={rgb[0]:.3f},{rgb[1]:.3f},{rgb[2]:.3f} "
        f"edge_energy={edge_energy:.4f} mean_luminance={luminance:.3f}"
        f"{salience_text} pixel_box={box_text}"
    )[:_MAX_SUMMARY_CHARS]


def _consume_visual_source_locked(
    runtime,
    image_source_ref,
    *,
    consent: bool,
    current_source: str,
    goal: str = "",
    token_budget: int = 512,
    context_budget_chars: int = 320,
    priority: int = 0,
    cfg=None,
):
    """Create an ephemeral A5 packet and bounded A4/C3 candidate from a stored image.

    consent must be the explicit local operator approval for this exact
    user-supplied image. Android screen/camera capture requires a separate OS
    grant/provider and is intentionally not accepted by this API.
    """
    if consent is not True:
        raise PermissionError("explicit local image-processing consent is required")
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

    event = getattr(runtime, "turn_event", None)
    if (type(event) is not dict or type(event.get("event_id")) is not str
            or type(event.get("brain_generation_id")) is not str):
        raise ValueError("visual ingress requires an active Runtime turn event")

    ref = _validate_image_ref(image_source_ref)
    state = vision.load(runtime.store)
    if state.get("revision") != vision.REVISION:
        raise ValueError("vision Store revision is incompatible")
    record = state.get("images", {}).get(ref["source_id"])
    if not isinstance(record, dict) or record.get("ref") != ref:
        raise ValueError("image source is missing, forgotten or no longer matches its SourceRef")

    cfg = cfg or vision.DEFAULTS
    try:
        image = vision.read_image(runtime.store, ref, cfg)
        background = vision.background(image)
        global_features = vision.tile_features(image, cfg["tile_px"])
        regions = [
            region for region in record.get("regions", [])
            if isinstance(region, dict) and isinstance(region.get("region_id"), str)
            and region["region_id"].startswith("r")
        ]
        if not regions or len(regions) > _MAX_REGIONS:
            raise ValueError("stored image has no bounded RAW EYE tile grid")
        width, height = image.size
        tile_rows = []
        for region in sorted(regions, key=lambda x: x["region_id"]):
            box = region.get("box")
            if (type(box) not in (list, tuple) or len(box) != 4
                    or any(type(v) is not int for v in box)):
                raise ValueError("stored image tile box is malformed")
            x0, y0, x1, y1 = box
            if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
                raise ValueError("stored image tile lies outside the source image")
            tile = image.crop(tuple(box))
            features = vision.tile_features(tile, cfg["tile_px"])
            salience = float(vision.saliency(image, box, background))
            if not math.isfinite(salience) or not 0.0 <= salience <= 1.0:
                raise ValueError("RAW EYE salience is outside [0,1]")
            region_ref = vision.region_ref(ref, region)
            summary = _feature_summary("RAW_EYE", region["region_id"], box, features, salience)
            tile_rows.append({
                "region_id": region["region_id"],
                "source_ref": region_ref,
                "summary": summary,
                "salience": salience,
                "priority": priority * 1000 + int(round(salience * 100)),
            })
    except ImportError as exc:
        raise Unavailable("Pillow/NumPy vision dependencies are unavailable") from exc

    global_box = [0, 0, int(width), int(height)]
    global_summary = _feature_summary("RAW_EYE_GLOBAL", "g", global_box, global_features)
    global_priority = priority * 1000 + 101
    segments = [{
        "text": global_summary,
        "source_ref": ref,
        "start_ms": 0,
        "end_ms": 0,
        "time_basis": "STATIC_IMAGE_UNTIMED",
        "finality": "FINAL",
        "authority": "RAW_FEATURE_MEASUREMENT",
        "learning_authority": False,
        "action_authority": False,
    }]
    percepts = [Percept(
        source_id=f"{ref['source_id']}:g",
        modality="visual",
        start_ms=0,
        end_ms=0,
        summary=global_summary,
        consent=True,
        final=True,
        priority=global_priority,
    )]
    for row in tile_rows:
        segments.append({
            "text": row["summary"],
            "source_ref": row["source_ref"],
            "start_ms": 0,
            "end_ms": 0,
            "time_basis": "STATIC_IMAGE_UNTIMED",
            "finality": "FINAL",
            "authority": "RAW_FEATURE_MEASUREMENT",
            "learning_authority": False,
            "action_authority": False,
        })
        percepts.append(Percept(
            source_id=f"{ref['source_id']}:{row['region_id']}",
            modality="visual",
            start_ms=0,
            end_ms=0,
            summary=row["summary"],
            consent=True,
            final=True,
            priority=row["priority"],
        ))

    percept_packet = make_packet(
        "PerceptPacket",
        "A5_RAW_EYE",
        event["event_id"],
        event["brain_generation_id"],
        [ref],
        source_ref=ref,
        segments=segments,
        modality="visual",
        feature_method="HANDCRAFTED_RAW_EYE_V1",
        feature_revision=REVISION,
        temporal_status="STATIC_UNTIMED",
        capture_time_status="UNKNOWN",
        teacher_used=False,
        student_projector_used=False,
        raw_image_source_persisted=True,
        derived_packet_persisted=False,
        learning_authority=False,
        action_authority=False,
        truth_authority=0,
    )
    validate("PerceptPacket", percept_packet)

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
    return {
        "status": "WIRED_SOURCE_BOUND",
        "revision": REVISION,
        "event_id": event["event_id"],
        "brain_generation_id": event["brain_generation_id"],
        "source_ref": ref,
        "packet": percept_packet,
        "a4": a4,
        "admission": admission,
        "context_envelope": envelope,
        "omitted_percept_ids": list(admission.omitted),
        "omitted_context_ids": list(envelope.omitted_ids),
        "raw_image_source_persisted": True,
        "derived_packet_persisted": False,
        "teacher_used": False,
        "student_projector_used": False,
        "learning_authority": False,
        "action_authority": False,
        "truth_authority": 0,
        "context_budget_kind": "CHARACTER_PREFILTER_NOT_NATIVE_TOKENIZER",
    }


def consume_visual_source(
    runtime,
    image_source_ref,
    *,
    consent: bool,
    current_source: str,
    goal: str = "",
    token_budget: int = 512,
    context_budget_chars: int = 320,
    priority: int = 0,
    cfg=None,
):
    """Serialize image-derived A5/A4/C3 context against concurrent source forget.

    Store.mutex is an RLock, so nested Store operations and vision.read_image
    remain safe. A forget either completes before this call starts (and the
    SourceRef is rejected) or after the ephemeral context has been built.
    """
    with runtime.store.mutex:
        return _consume_visual_source_locked(
            runtime,
            image_source_ref,
            consent=consent,
            current_source=current_source,
            goal=goal,
            token_budget=token_budget,
            context_budget_chars=context_budget_chars,
            priority=priority,
            cfg=cfg,
        )


__all__ = ["REVISION", "consume_visual_source"]
