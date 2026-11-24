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
import threading
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path

from . import attention as attention_module
from . import vision
from .a5_context_envelope import A5Item, admit_a5
from .a5_ui_admission_bridge import (
    A5UIRuntimeAdapter,
    UIObservationLease,
    revoke_ui_observation,
    validate_ui_observation,
    _summary,
)
from .contracts import packet as make_packet, validate
from .percept_admission import Percept, admit
from .vision_temporal_evidence import TemporalVisualEvidenceRegistry

REVISION = "v14-a5-media-projection-raw-eye-v2-temporal"
MAX_FRAME_BYTES = 8 * 1024 * 1024
MAX_FRAME_PIXELS = 4_000_000
GRID = 4
TILE_PX = 32
MAX_REGIONS = 1 + GRID * GRID
MAX_SUMMARY_CHARS = 512
MAX_PROJECTOR_BYTES = 16 * 1024 * 1024
MAX_PROJECTOR_UNPACKED_BYTES = 8 * 1024 * 1024
MAX_PROJECTOR_OUTPUT_DIM = 4096

_FRAME_VERIFIER_ISSUER = object()
_TEMPORAL_REGISTRY_INIT_LOCK = threading.Lock()


def _bounded_vision_config(cfg):
    """Copy only the hash dimension while enforcing fixed frame byte/pixel caps."""
    if cfg is not None and type(cfg) is not dict:
        raise ValueError("RAW EYE vision config must be a dictionary")
    result = dict(vision.DEFAULTS)
    hash_dim = cfg.get("hash_dim", result["hash_dim"]) if cfg is not None else result["hash_dim"]
    if type(hash_dim) is not int or not 1 <= hash_dim <= 4096:
        raise ValueError("RAW EYE hash_dim must be an integer in 1..4096")
    result["hash_dim"] = hash_dim
    result["max_bytes"] = MAX_FRAME_BYTES
    result["max_pixels"] = MAX_FRAME_PIXELS
    result["grid"] = GRID
    result["tile_px"] = TILE_PX
    return result


def _runtime_temporal_visual_registry(runtime):
    """Create the small ephemeral temporal registry once per Runtime."""
    with _TEMPORAL_REGISTRY_INIT_LOCK:
        registry = getattr(runtime, "_a5_temporal_visual_registry", None)
        if registry is None:
            registry = TemporalVisualEvidenceRegistry()
            runtime._a5_temporal_visual_registry = registry
        elif not isinstance(registry, TemporalVisualEvidenceRegistry):
            raise ValueError("Runtime temporal visual evidence state is invalid")
        return registry


def reset_temporal_visual_evidence(runtime, *, capture_session_id: str) -> int:
    """Erase one capture session's luminance and polarity history after revocation/end."""
    registry = getattr(runtime, "_a5_temporal_visual_registry", None)
    if registry is None:
        return 0
    if not isinstance(registry, TemporalVisualEvidenceRegistry):
        raise ValueError("Runtime temporal visual evidence state is invalid")
    return registry.reset(capture_session_id=capture_session_id)


def temporal_visual_revocation_callback(runtime, *, capture_session_id: str):
    """Create a provider post-lock callback that clears one capture session's temporal state.

    This is a SESSION-END callback, not a per-frame callback when multiple frame
    receipts share the same capture session. Pass it only to the provider's
    session-revocation path, or set end_of_stream=True on the final frame.
    It preserves standard A5 source tombstone/cache cleanup while erasing
    frame-derived luminance history when the provider revokes the grant.
    """
    if type(capture_session_id) is not str or not capture_session_id.strip():
        raise ValueError("capture_session_id is invalid")

    def cleanup(source_id):
        reset_error = None
        try:
            reset_temporal_visual_evidence(runtime, capture_session_id=capture_session_id)
        except Exception as exc:
            reset_error = exc
        result = revoke_ui_observation(runtime, source_id)
        if reset_error is not None:
            raise reset_error
        return result

    return cleanup


def _overwrite_caller_buffer(buffer):
    """Best-effort zeroization for mutable compressed frame buffers."""
    if type(buffer) is not bytearray:
        return False
    try:
        buffer[:] = b"\x00" * len(buffer)
    except Exception:
        return False
    return not any(buffer)


def _feature_summary(region_id, box, features, salience):
    """Render bounded, content-free RAW EYE numeric features for A5 context."""
    valid_named = {"g", "hl", "hr", "ht", "hb", "qtl", "qtr", "qbl", "qbr"}
    valid_grid = (
        isinstance(region_id, str)
        and len(region_id) == 3
        and region_id[0] == "r"
        and region_id[1] in "0123"
        and region_id[2] in "0123"
    )
    if not isinstance(region_id, str) or (region_id not in valid_named and not valid_grid):
        raise ValueError("invalid RAW EYE region id")
    if (
        type(box) not in (list, tuple)
        or len(box) != 4
        or any(type(value) is not int or value < 0 for value in box)
        or box[0] >= box[2]
        or box[1] >= box[3]
    ):
        raise ValueError("invalid RAW EYE region box")

    try:
        raw_values = tuple(features)
        if any(isinstance(value, (str, bytes, bytearray, bool)) for value in raw_values):
            raise ValueError("non-numeric RAW EYE feature value")
        values = tuple(float(value) for value in raw_values)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid RAW EYE feature vector") from exc
    expected = 6 + vision.HUE_BINS + 3 + vision.ORI_BINS + 16
    if len(values) != expected:
        raise ValueError("RAW EYE feature vector has an unexpected dimension")
    if any(not math.isfinite(value) or value < 0.0 or value > 2.0 for value in values):
        raise ValueError("RAW EYE feature vector is outside its finite bounds")

    if salience is None:
        salience_text = "na"
    else:
        if isinstance(salience, bool):
            raise ValueError("invalid RAW EYE salience")
        try:
            salience_value = float(salience)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("invalid RAW EYE salience") from exc
        if not math.isfinite(salience_value) or not 0.0 <= salience_value <= 1.0:
            raise ValueError("RAW EYE salience is outside [0,1]")
        salience_text = f"{salience_value:.3f}"

    def group(items):
        return ",".join(f"{value:.3f}" for value in items)

    hue_end = 6 + vision.HUE_BINS
    sv_edge_end = hue_end + 3
    orientation_end = sv_edge_end + vision.ORI_BINS
    summary = (
        f"raw_eye_v1 authority=RAW_FEATURE_MEASUREMENT region={region_id} "
        f"box={box[0]},{box[1]},{box[2]},{box[3]} salience={salience_text} "
        f"rgb={group(values[:3])} rgb_sd={group(values[3:6])} "
        f"hue={group(values[6:hue_end])} "
        f"sv_edge={group(values[hue_end:sv_edge_end])} "
        f"orientation={group(values[sv_edge_end:orientation_end])} "
        f"lum4x4={group(values[orientation_end:])}"
    )
    if len(summary) > MAX_SUMMARY_CHARS:
        raise ValueError("RAW EYE feature summary exceeds its fixed bound")
    return summary


class ProviderFrameVerifier:
    """One-shot provider capability bound to one active UIObservationLease.

    The Android companion must construct this only after verifying the
    companion-signed frame receipt and binding its exact frame digest/length.
    If session_consent_receipt_ref is present, the provider verifier must also
    authenticate that stable session receipt as part of the signed observation.
    This Python object is an injection contract, not the hard OS security boundary.
    """
    __slots__ = (
        "_runtime", "_lease", "_generation_id", "_source_id",
        "_capture_session_id", "_receipt", "_session_receipt", "_capture_method",
        "_event_kind", "_verify", "_used",
    )

    def __init__(self, lease, observation, verify_fn, *, _issuer=None):
        if _issuer is not _FRAME_VERIFIER_ISSUER:
            raise PermissionError("ProviderFrameVerifier is issued only by the companion-provider factory")
        if not callable(verify_fn):
            raise TypeError("provider receipt verifier must be callable")
        self._runtime = lease.runtime
        self._lease = lease
        self._generation_id = lease.generation_id
        self._source_id = observation["source_id"]
        self._capture_session_id = observation["capture_session_id"]
        self._receipt = observation["consent_receipt_ref"]
        self._session_receipt = observation.get(
            "session_consent_receipt_ref", observation["consent_receipt_ref"],
        )
        self._capture_method = observation["capture_method"]
        self._event_kind = observation["event_kind"]
        self._verify = verify_fn
        self._used = False

    def verify(self, runtime, lease, observation, frame_sha256, frame_size):
        if self._used:
            return False
        self._used = True
        if (
            runtime is not self._runtime
            or lease is not self._lease
            or not lease.active_for(runtime, self._generation_id)
            or not lease.matches(runtime, observation, self._generation_id)
            or type(observation) is not dict
            or observation.get("source_id") != self._source_id
            or observation.get("capture_session_id") != self._capture_session_id
            or observation.get("consent_receipt_ref") != self._receipt
            or observation.get("session_consent_receipt_ref", observation.get("consent_receipt_ref")) != self._session_receipt
            or observation.get("capture_method") != self._capture_method
            or observation.get("event_kind") != self._event_kind
            or self._capture_method != "MEDIA_PROJECTION"
            or self._event_kind != "SCREEN_FRAME_AVAILABLE"
        ):
            return False
        try:
            return self._verify(observation, frame_sha256, frame_size) is True
        except Exception:
            return False


def _issue_provider_frame_verifier(lease, observation, verify_fn):
    """Internal companion-provider API; call only after signed-receipt verification."""
    validated = validate_ui_observation(observation)
    if (
        not isinstance(lease, UIObservationLease)
        or not lease.matches(lease.runtime, validated, lease.generation_id)
    ):
        raise PermissionError("provider frame verifier requires the exact active UI lease")
    return ProviderFrameVerifier(
        lease, validated, verify_fn, _issuer=_FRAME_VERIFIER_ISSUER,
    )


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
        state = vision.load(store)
        record = state.get("tile_projector")
    except Exception:
        return {"status": "STORE_UNAVAILABLE"}
    if type(record) is not dict:
        return {"status": "NO_TILE_PROJECTOR"}
    if record.get("authority") != "LAB_SHADOW_ONLY":
        return {"status": "AUTHORITY_MISMATCH"}

    # A3 projector bytes are usable only while every exact training source is
    # still live in both the vision index and the canonical source registry.
    # This independent consumer check keeps stale/legacy projectors out of the
    # UI path even if a composed source-forget overlay is missing or stale.
    lineage = record.get("training_sources")
    images = state.get("images") if isinstance(state, dict) else None
    if type(lineage) is not list or not lineage or len(lineage) > 256 or type(images) is not dict:
        return {"status": "PROJECTOR_LINEAGE_UNKNOWN"}
    seen_sources = set()
    for item in lineage:
        if type(item) is not dict or set(item) != {"source_id", "sha256"}:
            return {"status": "PROJECTOR_LINEAGE_INVALID"}
        source_id, source_sha = item.get("source_id"), item.get("sha256")
        if (
            type(source_id) is not str or not source_id or len(source_id) > 256
            or type(source_sha) is not str or len(source_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in source_sha)
            or source_id in seen_sources
        ):
            return {"status": "PROJECTOR_LINEAGE_INVALID"}
        seen_sources.add(source_id)
        image_record = images.get(source_id)
        image_ref = image_record.get("ref") if type(image_record) is dict else None
        if (
            type(image_ref) is not dict
            or image_ref.get("source_id") != source_id
            or image_ref.get("sha256") != source_sha
            or image_ref.get("modality") != "image"
        ):
            return {"status": "PROJECTOR_SOURCE_LINEAGE_STALE"}
        try:
            source_row = store.one("SELECT * FROM sources WHERE id=?", (source_id,))
        except Exception:
            return {"status": "PROJECTOR_SOURCE_REGISTRY_UNAVAILABLE"}
        try:
            if (
                not source_row or source_row["deleted"]
                or source_row["kind"] != "IMAGE" or source_row["hash"] != source_sha
            ):
                return {"status": "PROJECTOR_SOURCE_LINEAGE_STALE"}
        except (KeyError, IndexError, TypeError):
            return {"status": "PROJECTOR_SOURCE_REGISTRY_UNAVAILABLE"}

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

        # O_NONBLOCK makes a malicious FIFO fail at fstat instead of blocking open().
        file_fd = os.open(
            rel.parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0),
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
    frame_verifier: ProviderFrameVerifier = None,
    current_source: str,
    goal: str = "",
    token_budget: int = 512,
    context_budget_chars: int = 320,
    priority: int = 0,
    cfg=None,
):
    """Consume one MediaProjection frame under the exact active UI grant.

    frame_buffer must be a mutable bytearray so this function can overwrite
    the caller-owned compressed bytes after decoding. frame_verifier must be
    a one-shot ProviderFrameVerifier issued by the trusted companion only after
    verifying the signed receipt and exact frame digest/length. Raw callbacks
    are not accepted. The decoded RGB image is closed before return.
    No raw frame or derived packet is written to Store. Python/PIL internal
    copies are not guaranteed to be securely erased.
    """
    if type(frame_buffer) is not bytearray:
        raise TypeError("frame_buffer must be a mutable bytearray")
    image = None
    frame_snapshot = None
    generation_id = None
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
        # Freeze the exact bytes that are hashed and decoded. The provider-owned
        # bytearray remains mutable, so another thread must not be able to swap
        # pixels after receipt verification but before image decoding.
        frame_snapshot = bytearray(frame_buffer)
        frame_sha256 = hashlib.sha256(frame_snapshot).hexdigest()
        if type(frame_verifier) is not ProviderFrameVerifier:
            raise PermissionError("provider-owned frame verifier capability is required")
        if not frame_verifier.verify(runtime, consent_lease, observation, frame_sha256, len(frame_snapshot)):
            raise PermissionError("MediaProjection frame digest is not bound to the active provider receipt")
        image = vision.decode(frame_snapshot, cfg)
        _overwrite_caller_buffer(frame_snapshot)
        frame_snapshot = None
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

        tile_luminance = {
            region["region_id"]: tuple(float(value) for value in features[-16:])
            for region, _box, features, _salience in region_records
            if region["region_id"].startswith("r")
        }
        tile_features = {
            region["region_id"]: tuple(float(value) for value in features)
            for region, _box, features, _salience in region_records
            if region["region_id"].startswith("r")
        }
        session_consent_receipt_ref = observation.get(
            "session_consent_receipt_ref", observation["consent_receipt_ref"],
        )
        temporal_visual = _runtime_temporal_visual_registry(runtime).update(
            capture_session_id=observation["capture_session_id"],
            generation_id=generation_id,
            consent_receipt_ref=observation["consent_receipt_ref"],
            session_consent_receipt_ref=session_consent_receipt_ref,
            start_ms=observation["start_ms"],
            end_ms=observation["end_ms"],
            tile_luminance=tile_luminance,
            tile_features=tile_features,
        )
        attention_novelty = float(temporal_visual["attention_novelty"])
        temporal_visual_packet = dict(temporal_visual)
        temporal_visual_packet["attention_novelty"] = round(attention_novelty, 6)
        temporal_visual_packet.update({
            "source_ref": dict(frame_ref),
            "capture_session_id": observation["capture_session_id"],
            "consent_receipt_ref": observation["consent_receipt_ref"],
            "session_consent_receipt_ref": session_consent_receipt_ref,
            "clock": observation["clock"],
            "start_ms": observation["start_ms"],
            "end_ms": observation["end_ms"],
        })
        # Add only numeric, source-bound tile deltas to the existing A5
        # PerceptPacket. These are diagnostics, never OCR/object/action facts.
        for segment in segments[2:]:
            source_ref = segment.get("source_ref")
            region_id = source_ref.get("region_id") if isinstance(source_ref, dict) else None
            delta = temporal_visual.get("tile_delta", {}).get(region_id)
            if delta is None:
                continue
            suffix = f" temporal_delta={delta:.4f} authority=DIAGNOSTIC_ONLY"
            text_value = segment.get("text", "")
            segment["text"] = text_value[:max(0, MAX_SUMMARY_CHARS - len(suffix))] + suffix
            segment["temporal_change"] = delta
            segment["temporal_change_method"] = temporal_visual["method"]
            multichannel_delta = temporal_visual.get("multichannel_tile_delta", {}).get(region_id)
            if multichannel_delta is not None:
                segment["temporal_multichannel_change"] = multichannel_delta
                segment["temporal_multichannel_method"] = temporal_visual["method"]

        attention = attention_module.controller(runtime)
        temporal_modulation = None
        if temporal_visual["status"] == "MEASURED" and attention_novelty > 0.0:
            temporal_modulation = attention.modulate(
                event["event_id"], sal={"novelty": attention_novelty},
            )
        a4 = attention.perceive(
            event["event_id"], segments, goal=goal, file_requests=False
        )
        a4["temporal_visual_evidence"] = {
            "status": temporal_visual["status"],
            "change_score": temporal_visual["change_score"],
            "temporal_activity_score": temporal_visual.get("temporal_activity_score", 0.0),
            "global_luminance_shift": temporal_visual.get("global_luminance_shift", 0.0),
            "global_change_score": temporal_visual.get("global_change_score", 0.0),
            "multichannel_status": temporal_visual.get("multichannel_status", "UNAVAILABLE"),
            "multichannel_change_score": temporal_visual.get("multichannel_change_score", 0.0),
            "global_appearance_shift": temporal_visual.get("global_appearance_shift", 0.0),
            "global_structure_shift": temporal_visual.get("global_structure_shift", 0.0),
            "local_appearance_change_score": temporal_visual.get("local_appearance_change_score", 0.0),
            "local_structure_change_score": temporal_visual.get("local_structure_change_score", 0.0),
            "multichannel_changed_tile_ids": list(temporal_visual.get("multichannel_changed_tile_ids", [])),
            "local_change_score": temporal_visual.get("local_change_score", 0.0),
            "local_temporal_activity_score": temporal_visual.get("local_temporal_activity_score", 0.0),
            "attention_novelty": round(attention_novelty, 6),
            "changed_tile_ids": list(temporal_visual["changed_tile_ids"]),
            "locally_changed_tile_ids": list(temporal_visual.get("locally_changed_tile_ids", [])),
            "source_ref": dict(frame_ref),
            "truth_authority": 0,
        }
        a4["temporal_visual_modulation"] = temporal_modulation
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
            session_consent_receipt_ref=session_consent_receipt_ref,
            capture_method=observation["capture_method"],
            capture_scope=observation["capture_scope"], clock=observation["clock"],
            finality=observation["finality"], frame_sha256=frame_sha256,
            frame_size=[width, height],
            feature_method="HANDCRAFTED_RAW_EYE_V1", feature_revision=REVISION,
            temporal_visual_evidence=temporal_visual_packet,
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
            "temporal_visual_evidence": temporal_visual_packet,
            "temporal_visual_modulation": temporal_modulation,
            "learning_authority": False,
            "action_authority": False,
            "truth_authority": 0,
            "context_budget_kind": "UTF8_BYTE_UPPER_BOUND_AND_CHAR_PREFILTER_NOT_NATIVE_TOKENIZER",
        }
    finally:
        if image is not None:
            image.close()
        if frame_snapshot is not None:
            _overwrite_caller_buffer(frame_snapshot)
        _overwrite_caller_buffer(frame_buffer)
        if generation_id is not None and isinstance(consent_lease, UIObservationLease):
            try:
                if not consent_lease.active_for(runtime, generation_id):
                    reset_temporal_visual_evidence(
                        runtime, capture_session_id=consent_lease.capture_session_id,
                    )
            except Exception:
                # Cleanup must not mask the original cancellation/provider error.
                pass


def consume_projected_frame_from_provider(
    runtime, observation, frame_buffer, *, consent_lease, verify_fn, **kwargs,
):
    """Issue the one-shot provider verifier and consume the frame under one lease.

    The caller still owns the mutable bytearray until this entry point returns.
    Always overwrite it even when verifier issuance fails before the consumer's
    own cleanup scope can begin.
    """
    try:
        verifier = _issue_provider_frame_verifier(
            consent_lease, observation, verify_fn,
        )
        return consume_projected_frame(
            runtime, observation, frame_buffer,
            consent_lease=consent_lease, frame_verifier=verifier, **kwargs,
        )
    finally:
        _overwrite_caller_buffer(frame_buffer)


@contextmanager
def consume_projected_frame_scope(runtime, observation, frame_buffer, *, end_of_stream=False, **kwargs):
    """Scope one UI frame through downstream consumers, then revoke its cache/source.

    Keep the outer UIObservationLease open while C3 reads the returned packet.
    Set end_of_stream=True on the final frame to erase this session's temporal
    luminance history; provider revocation should also call the reset helper.
    """
    if type(end_of_stream) is not bool:
        raise ValueError("end_of_stream must be boolean")
    validated = validate_ui_observation(observation)
    try:
        result = consume_projected_frame(runtime, validated, frame_buffer, **kwargs)
        yield result
    finally:
        try:
            revoke_ui_observation(runtime, validated["source_id"])
        finally:
            if end_of_stream:
                reset_temporal_visual_evidence(
                    runtime, capture_session_id=validated["capture_session_id"],
                )


__all__ = [
    "REVISION",
    "consume_projected_frame",
    "consume_projected_frame_from_provider",
    "consume_projected_frame_scope",
    "reset_temporal_visual_evidence",
    "temporal_visual_revocation_callback",
]