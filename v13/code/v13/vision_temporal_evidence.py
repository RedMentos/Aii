"""Ephemeral, consent-lease-scoped temporal RAW EYE feature evidence.

This deterministic diagnostic compares the existing 37-value tile descriptor
(RGB/hue/edge/orientation/4x4 luminance). It is not optical flow, OCR, object
recognition, a calibrated probability, or a learned temporal model. Only the
previous numeric tile descriptors are retained in bounded process memory.
No frame bytes, images, text, or persistent model state are stored.
"""
from __future__ import annotations

from collections import OrderedDict
import copy
import math
import threading

from .vision_temporal_adaptation import (
    compute_attention_novelty,
    decompose_temporal_change,
    decompose_temporal_feature_change,
    weighted_tile_score,
)

TILE_IDS = tuple(f"r{row}{col}" for row in range(4) for col in range(4))
LUMINANCE_VALUES_PER_TILE = 16
LUMINANCE_METHOD = "RAW_EYE_TEMPORAL_LUMINANCE_DELTA_V1"
METHOD = "RAW_EYE_TEMPORAL_MULTICHANNEL_DELTA_V2"
FEATURE_METHOD = "RAW_EYE_TILE_FEATURES_V1"
FEATURE_VALUES_PER_TILE = 37
MAX_A3_TEMPORAL_DIM = 1024
A3_PROJECTED_CHANGE_METHOD = "A3_TILE_COSINE_DELTA_V1"
# BOOT: cap A3 projected change at a small A4 novelty contribution. This is
# an attention-only heuristic, not a learned weight, confidence or truth score.
A3_TEMPORAL_ATTENTION_GAIN = 0.15
A3_UNAVAILABLE_REASONS = {"NO_PROJECTOR", "PROJECTOR_UNAVAILABLE", "INFERENCE_FAILED", "DIMENSION_LIMIT", "ZERO_EMBEDDING"}
MULTICHANNEL_TILE_THRESHOLD = 0.04
DEFAULT_SURFACE_TAU_MS = 30
DEFAULT_SURFACE_WINDOW_MS = 50


class TemporalVisualEvidenceError(ValueError):
    """Malformed, stale, or out-of-order temporal visual evidence."""


def _identity(value, name: str, limit: int = 256) -> str:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise TemporalVisualEvidenceError(f"{name} is invalid")
    return value


def _validate_luminance(value) -> dict[str, tuple[float, ...]]:
    if type(value) is not dict or set(value) != set(TILE_IDS):
        raise TemporalVisualEvidenceError("temporal visual tile set must be the complete 4x4 grid")
    result = {}
    for tile_id in TILE_IDS:
        row = value[tile_id]
        if type(row) not in (list, tuple) or len(row) != LUMINANCE_VALUES_PER_TILE:
            raise TemporalVisualEvidenceError("temporal visual tile luminance must contain 16 values")
        values = []
        for item in row:
            if type(item) not in (int, float) or not math.isfinite(float(item)) or not 0.0 <= float(item) <= 1.0:
                raise TemporalVisualEvidenceError("temporal visual luminance must be finite in [0,1]")
            values.append(float(item))
        result[tile_id] = tuple(values)
    return result


def _validate_features(value, luminance) -> dict[str, tuple[float, ...]] | None:
    if value is None:
        return None
    if type(value) is not dict or set(value) != set(TILE_IDS):
        raise TemporalVisualEvidenceError("temporal visual feature tile set must be the complete 4x4 grid")
    result = {}
    for tile_id in TILE_IDS:
        row = value[tile_id]
        if type(row) not in (list, tuple) or len(row) != FEATURE_VALUES_PER_TILE:
            raise TemporalVisualEvidenceError("temporal visual tile features must contain 37 values")
        values = []
        for item in row:
            if type(item) not in (int, float) or not math.isfinite(float(item)) or not 0.0 <= float(item) <= 2.0:
                raise TemporalVisualEvidenceError("temporal visual features must be finite in [0,2]")
            values.append(float(item))
        if any(abs(values[-LUMINANCE_VALUES_PER_TILE + i] - luminance[tile_id][i]) > 1e-6
               for i in range(LUMINANCE_VALUES_PER_TILE)):
            raise TemporalVisualEvidenceError("temporal visual features must match the bound luminance tile")
        result[tile_id] = tuple(values)
    return result


def _validate_frame_source_ref(value) -> dict:
    if type(value) is not dict or set(value) != {"source_id", "sha256", "char_start", "char_end", "modality"}:
        raise TemporalVisualEvidenceError("A3 temporal frame source reference is invalid")
    source_id, sha256 = value.get("source_id"), value.get("sha256")
    if (type(source_id) is not str or not source_id or len(source_id) > 256
            or type(sha256) is not str or len(sha256) != 64
            or any(char not in "0123456789abcdef" for char in sha256)
            or type(value.get("char_start")) is not int or value["char_start"] != 0
            or type(value.get("char_end")) is not int or value["char_end"] != 0
            or value.get("modality") != "image"):
        raise TemporalVisualEvidenceError("A3 temporal frame source reference is malformed")
    return dict(value)


def _validate_a3_tile_embeddings(value) -> tuple[dict[str, tuple[float, ...]], int]:
    if type(value) is not dict or set(value) != set(TILE_IDS):
        raise TemporalVisualEvidenceError("A3 temporal embeddings require the complete 4x4 tile grid")
    result = {}
    dimension = None
    for tile_id in TILE_IDS:
        row = value[tile_id]
        if type(row) not in (list, tuple) or not 1 <= len(row) <= MAX_A3_TEMPORAL_DIM:
            raise TemporalVisualEvidenceError("A3 temporal embedding dimension is outside the bounded range")
        if dimension is None:
            dimension = len(row)
        elif len(row) != dimension:
            raise TemporalVisualEvidenceError("A3 temporal embedding dimensions must match across tiles")
        vector = []
        for item in row:
            if type(item) not in (int, float) or not math.isfinite(float(item)):
                raise TemporalVisualEvidenceError("A3 temporal embeddings must be finite numeric values")
            vector.append(float(item))
        norm = math.sqrt(sum(item * item for item in vector))
        if norm <= 1e-8:
            raise TemporalVisualEvidenceError("A3 temporal embedding cannot be a zero vector")
        result[tile_id] = tuple(item / norm for item in vector)
    return result, int(dimension)

class TemporalVisualEvidence:
    """One-stream, one-frame-history temporal delta accumulator."""

    def __init__(self, *, reset_gap_ms: int = 1500, changed_tile_threshold: float = 0.08,
                 tau_ms: int = DEFAULT_SURFACE_TAU_MS,
                 window_ms: int = DEFAULT_SURFACE_WINDOW_MS) -> None:
        if type(reset_gap_ms) is not int or not 100 <= reset_gap_ms <= 10000:
            raise ValueError("reset_gap_ms must be an integer in [100, 10000]")
        if type(changed_tile_threshold) not in (int, float) or not math.isfinite(float(changed_tile_threshold)) or not 0.0 < float(changed_tile_threshold) <= 1.0:
            raise ValueError("changed_tile_threshold must be finite in (0,1]")
        if type(tau_ms) is not int or not 1 <= tau_ms <= 1000:
            raise ValueError("tau_ms must be an integer in [1, 1000]")
        if type(window_ms) is not int or not 10 <= window_ms <= 1000:
            raise ValueError("window_ms must be an integer in [10, 1000]")
        self.reset_gap_ms = reset_gap_ms
        self.changed_tile_threshold = float(changed_tile_threshold)
        self.tau_ms = tau_ms
        self.window_ms = window_ms
        self._last_start_ms = None
        self._last_end_ms = None
        self._previous = None
        self._previous_features = None
        self._on_surface = {tile: 0.0 for tile in TILE_IDS}
        self._off_surface = {tile: 0.0 for tile in TILE_IDS}
        self._local_surface = {tile: 0.0 for tile in TILE_IDS}
        self._last_activity_ms = None
        self._previous_a3_embeddings = None
        self._previous_a3_projector_sha256 = None
        self._previous_a3_source_ref = None

    def reset(self) -> None:
        self._last_start_ms = None
        self._last_end_ms = None
        self._previous = None
        self._previous_features = None
        self._on_surface = {tile: 0.0 for tile in TILE_IDS}
        self._off_surface = {tile: 0.0 for tile in TILE_IDS}
        self._local_surface = {tile: 0.0 for tile in TILE_IDS}
        self._last_activity_ms = None
        self._previous_a3_embeddings = None
        self._previous_a3_projector_sha256 = None
        self._previous_a3_source_ref = None

    def _update_a3_projected_change(self, *, tile_embeddings, projector_sha256,
                                    frame_source_ref, unavailable_reason):
        source_ref = _validate_frame_source_ref(frame_source_ref) if frame_source_ref is not None else None
        if tile_embeddings is None:
            if projector_sha256 is not None:
                raise TemporalVisualEvidenceError("A3 projector hash cannot be supplied without embeddings")
            reason = unavailable_reason or "NO_PROJECTOR"
            if reason not in A3_UNAVAILABLE_REASONS:
                raise TemporalVisualEvidenceError("A3 temporal unavailable reason is invalid")
            self._previous_a3_embeddings = None
            self._previous_a3_projector_sha256 = None
            self._previous_a3_source_ref = None
            return {
                "schema": "v14.a3-projected-temporal-change/1",
                "status": reason,
                "method": A3_PROJECTED_CHANGE_METHOD,
                "projector_sha256": None,
                "embedding_dim": None,
                "change_score": 0.0,
                "tile_delta": {},
                "changed_tile_ids": [],
                "previous_source_ref": None,
                "source_ref": source_ref,
                "authority": "DIAGNOSTIC_ONLY",
                "truth_authority": 0,
                "learning_authority": False,
                "action_authority": False,
            }
        if unavailable_reason is not None:
            raise TemporalVisualEvidenceError("A3 temporal embeddings conflict with unavailable status")
        if (type(projector_sha256) is not str or len(projector_sha256) != 64
                or any(char not in "0123456789abcdef" for char in projector_sha256)):
            raise TemporalVisualEvidenceError("A3 temporal projector SHA-256 is invalid")
        if source_ref is None:
            raise TemporalVisualEvidenceError("A3 temporal embeddings require the exact frame SourceRef")
        current, dimension = _validate_a3_tile_embeddings(tile_embeddings)
        previous_ref = self._previous_a3_source_ref
        status = "WARMUP"
        tile_delta = {}
        change_score = 0.0
        if self._previous_a3_embeddings is not None:
            if self._previous_a3_projector_sha256 != projector_sha256:
                status = "PROJECTOR_CHANGED"
            elif len(next(iter(self._previous_a3_embeddings.values()))) != dimension:
                status = "DIMENSION_CHANGED"
            else:
                status = "MEASURED"
                for tile_id in TILE_IDS:
                    cosine = sum(a * b for a, b in zip(self._previous_a3_embeddings[tile_id], current[tile_id]))
                    cosine = max(-1.0, min(1.0, cosine))
                    tile_delta[tile_id] = round(max(0.0, min(1.0, (1.0 - cosine) * 0.5)), 6)
                ordered = sorted(tile_delta.values(), reverse=True)
                mean_change = sum(ordered) / len(ordered)
                top4_change = sum(ordered[:4]) / 4.0
                change_score = round(0.6 * top4_change + 0.4 * mean_change, 6)
        self._previous_a3_embeddings = current
        self._previous_a3_projector_sha256 = projector_sha256
        self._previous_a3_source_ref = source_ref
        return {
            "schema": "v14.a3-projected-temporal-change/1",
            "status": status,
            "method": A3_PROJECTED_CHANGE_METHOD,
            "projector_sha256": projector_sha256,
            "embedding_dim": dimension,
            "change_score": change_score,
            "tile_delta": tile_delta,
            "changed_tile_ids": [tile for tile in TILE_IDS if tile_delta.get(tile, 0.0) > 1e-6],
            "previous_source_ref": previous_ref,
            "source_ref": source_ref,
            "authority": "DIAGNOSTIC_ONLY",
            "truth_authority": 0,
            "learning_authority": False,
            "action_authority": False,
        }

    def update(self, *, start_ms: int, end_ms: int, tile_luminance: dict,
               tile_features: dict | None = None,
               a3_tile_embeddings: dict | None = None,
               a3_projector_sha256: str | None = None,
               frame_source_ref: dict | None = None,
               a3_unavailable_reason: str | None = None) -> dict:
        if type(start_ms) is not int or type(end_ms) is not int or start_ms < 0 or end_ms <= start_ms:
            raise TemporalVisualEvidenceError("temporal visual interval must be positive monotonic milliseconds")
        current = _validate_luminance(tile_luminance)
        current_features = _validate_features(tile_features, current)
        reset_reason = None
        gap_ms = 0
        if self._last_end_ms is not None:
            if self._last_start_ms is not None and start_ms < self._last_start_ms:
                raise TemporalVisualEvidenceError("temporal visual frame starts must be monotonic")
            if end_ms <= self._last_end_ms:
                raise TemporalVisualEvidenceError("temporal visual frames must advance monotonically")
            gap_ms = max(0, start_ms - self._last_end_ms)
            if gap_ms > self.reset_gap_ms:
                self.reset()
                reset_reason = "STREAM_GAP"

        a3_projected_change = self._update_a3_projected_change(
            tile_embeddings=a3_tile_embeddings,
            projector_sha256=a3_projector_sha256,
            frame_source_ref=frame_source_ref,
            unavailable_reason=a3_unavailable_reason,
        )

        if self._previous is None:
            self._previous = current
            self._previous_features = current_features
            self._last_start_ms = start_ms
            self._last_end_ms = end_ms
            return {
                "method": METHOD if current_features is not None else LUMINANCE_METHOD,
                "feature_method": FEATURE_METHOD if current_features is not None else None,
                "a3_projected_change": a3_projected_change,
                "status": "WARMUP",
                "multichannel_status": "WARMUP" if current_features is not None else "UNAVAILABLE",
                "multichannel_tile_delta": {}, "multichannel_changed_tile_ids": [],
                "multichannel_change_score": 0.0, "global_appearance_shift": 0.0,
                "global_structure_shift": 0.0, "local_appearance_change_score": 0.0,
                "local_structure_change_score": 0.0,
                "multichannel_threshold": min(self.changed_tile_threshold, MULTICHANNEL_TILE_THRESHOLD),
                "change_score": 0.0,
                "mean_change": 0.0, "peak_change": 0.0, "changed_tile_ids": [],
                "tile_delta": {}, "polarity_delta_by_tile": {}, "polarity_activity_by_tile": {},
                "temporal_activity_score": 0.0, "on_activity": 0.0, "off_activity": 0.0,
                "global_luminance_shift": 0.0, "global_change_score": 0.0,
                "local_tile_delta": {}, "local_change_score": 0.0,
                "local_temporal_activity_score": 0.0, "locally_changed_tile_ids": [],
                "a3_attention_novelty": 0.0,
                "attention_novelty": 0.0,
                "surface_expired": False, "tau_ms": self.tau_ms, "window_ms": self.window_ms,
                "gap_ms": gap_ms, "state_reset": reset_reason is not None,
                "reset_reason": reset_reason, "truth_authority": 0,
                "learning_authority": False, "action_authority": False,
            }

        elapsed_ms = max(1, end_ms - self._last_end_ms)
        surface_expired = self._last_activity_ms is not None and end_ms - self._last_activity_ms > self.window_ms
        if surface_expired:
            self._on_surface = {tile: 0.0 for tile in TILE_IDS}
            self._off_surface = {tile: 0.0 for tile in TILE_IDS}
            self._local_surface = {tile: 0.0 for tile in TILE_IDS}
        else:
            decay = math.exp(-elapsed_ms / self.tau_ms)
            self._on_surface = {tile: value * decay for tile, value in self._on_surface.items()}
            self._off_surface = {tile: value * decay for tile, value in self._off_surface.items()}
            self._local_surface = {tile: value * decay for tile, value in self._local_surface.items()}

        common_mode_delta, local_tile_delta = decompose_temporal_change(
            self._previous, current, TILE_IDS, LUMINANCE_VALUES_PER_TILE,
        )
        tile_delta, polarity_delta = {}, {}
        for tile_id in TILE_IDS:
            before, after = self._previous[tile_id], current[tile_id]
            on_delta = sum(max(0.0, a - b) for a, b in zip(after, before)) / LUMINANCE_VALUES_PER_TILE
            off_delta = sum(max(0.0, b - a) for a, b in zip(after, before)) / LUMINANCE_VALUES_PER_TILE
            tile_delta[tile_id] = on_delta + off_delta
            polarity_delta[tile_id] = {"on": on_delta, "off": off_delta}
            self._on_surface[tile_id] = min(1.0, self._on_surface[tile_id] + on_delta)
            self._off_surface[tile_id] = min(1.0, self._off_surface[tile_id] + off_delta)
            self._local_surface[tile_id] = min(
                1.0, self._local_surface[tile_id] + local_tile_delta[tile_id],
            )
        if any(value > 0.0 for value in tile_delta.values()):
            self._last_activity_ms = end_ms

        ordered = sorted(tile_delta.values(), reverse=True)
        mean_change = sum(ordered) / len(ordered)
        top4_change = sum(ordered[:4]) / 4.0
        change_score = min(1.0, max(0.0, 0.6 * top4_change + 0.4 * mean_change))
        activity = sorted((self._on_surface[t] + self._off_surface[t] for t in TILE_IDS), reverse=True)
        temporal_activity_score = min(1.0, max(0.0, 0.6 * sum(activity[:4]) / 4.0 + 0.4 * sum(activity) / len(activity)))
        local_change_score = weighted_tile_score(local_tile_delta.values())
        local_temporal_activity_score = weighted_tile_score(self._local_surface.values())
        global_change_score = min(1.0, abs(common_mode_delta))

        multichannel_threshold = min(self.changed_tile_threshold, MULTICHANNEL_TILE_THRESHOLD)
        multichannel_status = "UNAVAILABLE"
        multichannel_tile_delta = {}
        multichannel_changed_tile_ids = []
        multichannel_change_score = 0.0
        global_appearance_shift = 0.0
        global_structure_shift = 0.0
        local_appearance_change_score = 0.0
        local_structure_change_score = 0.0
        if current_features is not None and self._previous_features is not None:
            feature_global, feature_local = decompose_temporal_feature_change(
                self._previous_features, current_features, TILE_IDS, FEATURE_VALUES_PER_TILE,
            )
            appearance_by_tile = feature_local["appearance"]
            structure_by_tile = feature_local["structure"]
            luminance_by_tile = feature_local["luminance"]
            multichannel_tile_delta = {
                tile: max(appearance_by_tile[tile], structure_by_tile[tile], luminance_by_tile[tile])
                for tile in TILE_IDS
            }
            multichannel_changed_tile_ids = [
                tile for tile in TILE_IDS if multichannel_tile_delta[tile] >= multichannel_threshold
            ]
            multichannel_change_score = weighted_tile_score(
                multichannel_tile_delta[tile] for tile in multichannel_changed_tile_ids
            )
            local_appearance_change_score = weighted_tile_score(
                value for value in appearance_by_tile.values() if value >= multichannel_threshold
            )
            local_structure_change_score = weighted_tile_score(
                value for value in structure_by_tile.values() if value >= multichannel_threshold
            )
            global_appearance_shift = feature_global["appearance"]
            global_structure_shift = feature_global["structure"]
            multichannel_status = "MEASURED"
        elif current_features is not None:
            multichannel_status = "WARMUP"

        base_attention_novelty = compute_attention_novelty(
            local_change_score, local_temporal_activity_score, global_change_score,
        )
        a3_change_score = (
            a3_projected_change["change_score"]
            if a3_projected_change["status"] == "MEASURED" else 0.0
        )
        a3_attention_novelty = round(min(
            A3_TEMPORAL_ATTENTION_GAIN,
            A3_TEMPORAL_ATTENTION_GAIN * a3_change_score,
        ), 6)
        attention_novelty = round(max(
            base_attention_novelty,
            multichannel_change_score,
            0.15 * global_appearance_shift,
            0.15 * global_structure_shift,
            a3_attention_novelty,
        ), 6)
        on_activity = sum(self._on_surface.values()) / len(TILE_IDS)
        off_activity = sum(self._off_surface.values()) / len(TILE_IDS)
        changed = [tile for tile in TILE_IDS if tile_delta[tile] >= self.changed_tile_threshold]
        self._previous, self._last_start_ms, self._last_end_ms = current, start_ms, end_ms
        self._previous_features = current_features
        return {
            "method": METHOD if current_features is not None else LUMINANCE_METHOD,
            "feature_method": FEATURE_METHOD if current_features is not None else None,
            "a3_projected_change": a3_projected_change,
            "multichannel_status": multichannel_status,
            "multichannel_tile_delta": {k: round(v, 6) for k, v in multichannel_tile_delta.items()},
            "multichannel_changed_tile_ids": multichannel_changed_tile_ids,
            "multichannel_change_score": round(multichannel_change_score, 6),
            "global_appearance_shift": round(global_appearance_shift, 6),
            "global_structure_shift": round(global_structure_shift, 6),
            "local_appearance_change_score": round(local_appearance_change_score, 6),
            "local_structure_change_score": round(local_structure_change_score, 6),
            "multichannel_threshold": round(multichannel_threshold, 6),
            "status": "MEASURED",
            "change_score": round(change_score, 6), "mean_change": round(mean_change, 6),
            "peak_change": round(max(ordered), 6), "changed_tile_ids": changed,
            "tile_delta": {k: round(v, 6) for k, v in tile_delta.items()},
            "polarity_delta_by_tile": {k: {p: round(v, 6) for p, v in row.items()} for k, row in polarity_delta.items()},
            "polarity_activity_by_tile": {t: {"on": round(self._on_surface[t], 6), "off": round(self._off_surface[t], 6)} for t in TILE_IDS},
            "temporal_activity_score": round(temporal_activity_score, 6),
            "global_luminance_shift": round(common_mode_delta, 6),
            "global_change_score": round(global_change_score, 6),
            "local_tile_delta": {k: round(v, 6) for k, v in local_tile_delta.items()},
            "local_change_score": round(local_change_score, 6),
            "local_temporal_activity_score": round(local_temporal_activity_score, 6),
            "locally_changed_tile_ids": [tile for tile in TILE_IDS if local_tile_delta[tile] >= self.changed_tile_threshold],
            "a3_attention_novelty": a3_attention_novelty,
            "attention_novelty": attention_novelty,
            "on_activity": round(on_activity, 6), "off_activity": round(off_activity, 6),
            "surface_expired": surface_expired, "tau_ms": self.tau_ms, "window_ms": self.window_ms,
            "gap_ms": gap_ms, "state_reset": reset_reason is not None, "reset_reason": reset_reason,
            "truth_authority": 0, "learning_authority": False, "action_authority": False,
        }


class _PreparedTemporalVisualUpdate:
    """Private speculative state; only its issuing registry may commit it."""

    __slots__ = ("owner", "session", "key", "epoch", "version", "state", "result")

    def __init__(self, owner, session, key, epoch, version, state, result):
        self.owner = owner
        self.session = session
        self.key = key
        self.epoch = epoch
        self.version = version
        self.state = state
        self.result = result


class TemporalVisualEvidenceRegistry:
    """Bounded process-local streams isolated by capture session, generation and receipt.

    prepare_update() computes against a private copy. The caller commits only
    after the resulting PerceptPacket has passed validation and the active A5
    context consumer has accepted it. Concurrent/stale tickets fail closed.
    """

    def __init__(self, *, max_streams: int = 8, **state_options) -> None:
        if type(max_streams) is not int or not 1 <= max_streams <= 64:
            raise ValueError("max_streams must be an integer in [1, 64]")
        self.max_streams = max_streams
        self._state_options = dict(state_options)
        self._states = OrderedDict()
        self._session_versions = {}
        self._epoch = 0
        self._lock = threading.RLock()

    def prepare_update(self, *, capture_session_id: str, generation_id: str,
                       consent_receipt_ref: str, start_ms: int, end_ms: int,
                       tile_luminance: dict, tile_features: dict | None = None,
                       session_consent_receipt_ref: str | None = None,
                       a3_tile_embeddings: dict | None = None,
                       a3_projector_sha256: str | None = None,
                       frame_source_ref: dict | None = None,
                       a3_unavailable_reason: str | None = None):
        session = _identity(capture_session_id, "capture_session_id")
        generation = _identity(generation_id, "generation_id")
        receipt = _identity(consent_receipt_ref, "consent_receipt_ref")
        session_receipt = _identity(
            session_consent_receipt_ref if session_consent_receipt_ref is not None else receipt,
            "session_consent_receipt_ref",
        )
        key = (session, generation, session_receipt)
        with self._lock:
            epoch = self._epoch
            version = self._session_versions.get(session, 0)
            current = self._states.get(key)
            state = copy.deepcopy(current) if current is not None else TemporalVisualEvidence(**self._state_options)
        result = state.update(
            start_ms=start_ms, end_ms=end_ms, tile_luminance=tile_luminance,
            tile_features=tile_features, a3_tile_embeddings=a3_tile_embeddings,
            a3_projector_sha256=a3_projector_sha256, frame_source_ref=frame_source_ref,
            a3_unavailable_reason=a3_unavailable_reason,
        )
        return _PreparedTemporalVisualUpdate(
            self, session, key, epoch, version, state, result,
        )

    def commit_update(self, ticket) -> bool:
        if not isinstance(ticket, _PreparedTemporalVisualUpdate) or ticket.owner is not self:
            raise ValueError("temporal visual update ticket belongs to another registry")
        with self._lock:
            if (ticket.epoch != self._epoch
                    or ticket.version != self._session_versions.get(ticket.session, 0)):
                return False
            # A reused session ID with a new generation or session-consent
            # receipt starts from a fresh stream and invalidates the old one.
            for old_key in tuple(self._states):
                if old_key[0] == ticket.session and old_key != ticket.key:
                    del self._states[old_key]
            self._states.pop(ticket.key, None)
            self._states[ticket.key] = ticket.state
            self._session_versions[ticket.session] = ticket.version + 1
            while len(self._states) > self.max_streams:
                evicted_key, _ = self._states.popitem(last=False)
                self._session_versions.pop(evicted_key[0], None)
                # Invalidate speculative tickets that may have been prepared
                # before the LRU eviction removed their baseline.
                self._epoch += 1
            return True

    def update(self, *, capture_session_id: str, generation_id: str,
               consent_receipt_ref: str, start_ms: int, end_ms: int,
               tile_luminance: dict, tile_features: dict | None = None,
               session_consent_receipt_ref: str | None = None,
               a3_tile_embeddings: dict | None = None,
               a3_projector_sha256: str | None = None,
               frame_source_ref: dict | None = None,
               a3_unavailable_reason: str | None = None) -> dict:
        ticket = self.prepare_update(
            capture_session_id=capture_session_id, generation_id=generation_id,
            consent_receipt_ref=consent_receipt_ref, start_ms=start_ms, end_ms=end_ms,
            tile_luminance=tile_luminance, tile_features=tile_features,
            session_consent_receipt_ref=session_consent_receipt_ref,
            a3_tile_embeddings=a3_tile_embeddings, a3_projector_sha256=a3_projector_sha256,
            frame_source_ref=frame_source_ref, a3_unavailable_reason=a3_unavailable_reason,
        )
        if not self.commit_update(ticket):
            raise TemporalVisualEvidenceError("concurrent temporal update; retry the frame")
        return ticket.result

    def reset(self, *, capture_session_id: str) -> int:
        capture_session_id = _identity(capture_session_id, "capture_session_id")
        with self._lock:
            keys = [key for key in self._states if key[0] == capture_session_id]
            for key in keys:
                del self._states[key]
            self._session_versions.pop(capture_session_id, None)
            # Revocation also invalidates a prepared first frame for which no
            # committed stream exists yet.
            self._epoch += 1
            return len(keys)

    def __len__(self) -> int:
        with self._lock:
            return len(self._states)
