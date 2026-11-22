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
import io
import math
import os
import stat
import time
import zipfile
from pathlib import Path

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
MAX_PROJECTOR_BYTES = 16 * 1024 * 1024
MAX_PROJECTOR_UNPACKED_BYTES = 8 * 1024 * 1024
MAX_PROJECTOR_OUTPUT_DIM = 4096


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



def _load_local_tile_projector(runtime, cfg, query_text: str) -> dict:
    """Load only the existing local LAB_SHADOW_ONLY tile projector, without following paths.

    The trained A3 student is optional: a missing, stale, malformed or slow
    projector leaves the handcrafted RAW EYE path intact. This function never
    downloads, trains, promotes or writes model state.
    """
    if not isinstance(query_text, str) or not query_text.strip():
        return {"status": "NO_QUERY"}
    store = getattr(runtime, "store", None)
    home_value = getattr(runtime, "home", None)
    if store is None or home_value is None:
        return {"status": "NO_LOCAL_STORE"}

    try:
        record = vision.load(store).get("tile_projector")
    except Exception:
        return {"status": "STORE_UNAVAILABLE"}
    if type(record) is not dict:
        return {"status": "NO_TILE_PROJECTOR"}
    if record.get("authority") != "LAB_SHADOW_ONLY":
        return {"status": "AUTHORITY_MISMATCH"}

    relative = record.get("path")
    if type(relative) is not str:
        return {"status": "INVALID_PROJECTOR_PATH"}
    rel = Path(relative)
    if (
        rel.is_absolute()
        or len(rel.parts) != 3
        or rel.parts[:2] != ("data", "vision")
        or any(part in ("", ".", "..") for part in rel.parts)
        or not rel.name.startswith("tiles-")
        or not rel.name.endswith(".npz")
    ):
        return {"status": "UNSAFE_PROJECTOR_PATH"}

    expected_sha = record.get("sha256")
    if (
        type(expected_sha) is not str
        or len(expected_sha) != 64
        or any(ch not in "0123456789abcdef" for ch in expected_sha)
    ):
        return {"status": "INVALID_PROJECTOR_HASH"}
    declared_n = record.get("n")
    if type(declared_n) is not int or declared_n < 4:
        return {"status": "INVALID_PROJECTOR_TRAIN_COUNT"}
    encoder_name = record.get("encoder")
    if type(encoder_name) is not str:
        return {"status": "INVALID_PROJECTOR_ENCODER"}

    required_flags = ("O_NOFOLLOW", "O_DIRECTORY")
    if not all(hasattr(os, flag) for flag in required_flags) or os.open not in getattr(os, "supports_dir_fd", set()):
        return {"status": "NO_SECURE_DIRFD_SUPPORT"}

    root_fd = parent_fd = file_fd = None
    raw = bytearray()
    try:
        root = Path(home_value).resolve(strict=True)
        root_fd = os.open(
            str(root),
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0),
        )
        parent_fd = root_fd
        for part in rel.parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=parent_fd,
            )
            if parent_fd != root_fd:
                os.close(parent_fd)
            parent_fd = next_fd

        file_fd = os.open(
            rel.parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            dir_fd=parent_fd,
        )
        info = os.fstat(file_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size <= 0 or info.st_size > MAX_PROJECTOR_BYTES:
            return {"status": "INVALID_PROJECTOR_FILE"}
        while True:
            chunk = os.read(file_fd, min(65536, MAX_PROJECTOR_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > MAX_PROJECTOR_BYTES:
                return {"status": "PROJECTOR_FILE_TOO_LARGE"}
    except (OSError, ValueError, TypeError):
        return {"status": "PROJECTOR_FILE_UNAVAILABLE"}
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if parent_fd is not None and parent_fd != root_fd:
            os.close(parent_fd)
        if root_fd is not None:
            os.close(root_fd)

    try:
        if vision.digest(bytes(raw)) != expected_sha:
            return {"status": "PROJECTOR_HASH_MISMATCH"}
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            archive_names = archive.namelist()
            if len(archive_names) != 4 or set(archive_names) != {"mu.npy", "sd.npy", "W.npy", "meta.npy"}:
                return {"status": "PROJECTOR_ARCHIVE_SHAPE_INVALID"}
            if sum(item.file_size for item in archive.infolist()) > MAX_PROJECTOR_UNPACKED_BYTES:
                return {"status": "PROJECTOR_ARCHIVE_TOO_LARGE"}
            if any(item.file_size > MAX_PROJECTOR_UNPACKED_BYTES for item in archive.infolist()):
                return {"status": "PROJECTOR_ARCHIVE_TOO_LARGE"}

        np = vision._np()
        with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
            mu = np.array(archive["mu"], dtype=np.float64, copy=True)
            sd = np.array(archive["sd"], dtype=np.float64, copy=True)
            weights = np.array(archive["W"], dtype=np.float64, copy=True)
            meta = np.array(archive["meta"], dtype=np.float64, copy=True)
        if (
            mu.shape != (37,)
            or sd.shape != (37,)
            or weights.ndim != 2
            or weights.shape[0] != 38
            or not 1 <= weights.shape[1] <= MAX_PROJECTOR_OUTPUT_DIM
            or meta.shape != (2,)
            or not np.isfinite(mu).all()
            or not np.isfinite(sd).all()
            or not np.isfinite(weights).all()
            or not np.isfinite(meta).all()
            or (sd <= 0).any()
            or not 0.0 < float(meta[0]) <= 1000.0
            or int(meta[1]) != declared_n
            or float(meta[1]) != float(int(meta[1]))
        ):
            return {"status": "PROJECTOR_TENSOR_INVALID"}

        projector = vision.Projector(float(meta[0]))
        projector.mu, projector.sd, projector.W = mu, sd, weights
        projector.n = int(meta[1])

        query_text = query_text.strip()[:512]
        if encoder_name == "hashed_bow":
            vectors = np.stack((
                vision.hashed_embed(query_text, cfg["hash_dim"]),
                vision.hashed_embed(vision.BACKGROUND, cfg["hash_dim"]),
            )).astype(np.float64, copy=False)
        elif encoder_name.startswith("embedding:"):
            try:
                from .semantic_memory import EmbeddingEncoder
                encoder = EmbeddingEncoder(runtime.home, runtime.models, runtime.cfg)
                if not encoder.installed() or "embedding:" + str(encoder.revision()) != encoder_name:
                    return {"status": "TEXT_ENCODER_REVISION_MISMATCH"}
                vectors = np.asarray(
                    encoder([query_text, vision.BACKGROUND], None, time.monotonic() + 2.0),
                    dtype=np.float64,
                )
            except Exception:
                return {"status": "TEXT_ENCODER_UNAVAILABLE"}
        else:
            return {"status": "UNSUPPORTED_TEXT_ENCODER"}

        if vectors.shape != (2, weights.shape[1]) or not np.isfinite(vectors).all():
            return {"status": "TEXT_VECTOR_SHAPE_INVALID"}
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if (norms <= 1e-8).any():
            return {"status": "TEXT_VECTOR_ZERO"}
        vectors = vectors / norms
        return {
            "status": "READY",
            "projector": projector,
            "query": vectors[0],
            "background": vectors[1],
            "encoder": encoder_name,
            "sha256": expected_sha,
        }
    except Exception:
        return {"status": "PROJECTOR_LOAD_FAILED"}


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
        student_query = goal.strip() or current_source[:512].strip()
        student = _load_local_tile_projector(runtime, cfg, student_query)
        student_status = student["status"]
        tile_feature_rows = []
        tile_region_ids = []
        region_records = []
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
                    region_records.append((region, box, features, salience))
                    if region["region_id"].startswith("r"):
                        tile_feature_rows.append(features)
                        tile_region_ids.append(region["region_id"])
                finally:
                    if tile is not image:
                        tile.close()

            student_scores = {}
            if student_status == "READY" and tile_feature_rows:
                try:
                    np = vision._np()
                    projected = student["projector"](np.stack(tile_feature_rows))
                    margins = projected @ student["query"] - projected @ student["background"]
                    if not np.isfinite(margins).all():
                        raise ValueError("student projector returned a non-finite margin")
                    student_scores = {
                        region_id: float(margin)
                        for region_id, margin in zip(tile_region_ids, margins)
                    }
                    student_status = "USED"
                except Exception:
                    student_status = "INFERENCE_FAILED"

            for region, box, features, salience in region_records:
                region_id = region["region_id"]
                margin = student_scores.get(region_id)
                summary = _feature_summary(region_id, box, features, salience)
                if margin is not None:
                    summary = (
                        summary + f" student_goal_margin={margin:.4f} authority=STUDENT_ESTIMATE"
                    )[:MAX_SUMMARY_CHARS]
                region_ref = vision.region_ref(frame_ref, region)
                source_id = f"{frame_source_id}:{region_id}"
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
                if margin is not None:
                    segment["student_goal_margin"] = round(margin, 4)
                    segment["student_estimate_authority"] = "STUDENT_ESTIMATE"
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
            teacher_used=False, student_projector_used=bool(student_scores),
            student_estimate={
                "status": student_status,
                "authority": "STUDENT_ESTIMATE" if student_scores else "NONE",
                "encoder": student.get("encoder") if student_scores else None,
                "projector_sha256": student.get("sha256") if student_scores else None,
                "goal_margin_by_region": {key: round(value, 4) for key, value in student_scores.items()},
            },
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
            "student_projector_used": bool(student_scores),
            "student_projector_status": student_status,
            "student_goal_margins": {key: round(value, 4) for key, value in student_scores.items()},
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