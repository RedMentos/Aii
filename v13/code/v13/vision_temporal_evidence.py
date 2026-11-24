"""Ephemeral, consent-lease-scoped temporal RAW EYE feature evidence.

This deterministic diagnostic compares the existing 37-value tile descriptor
(RGB/hue/edge/orientation/4x4 luminance). It is not optical flow, OCR, object
recognition, a calibrated probability, or a learned temporal model. Only the
previous numeric tile descriptors are retained in bounded process memory.
No frame bytes, images, text, or persistent model state are stored.
"""
from __future__ import annotations

from collections import OrderedDict
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
        self._last_end_ms = None
        self._previous = None
        self._previous_features = None
        self._on_surface = {tile: 0.0 for tile in TILE_IDS}
        self._off_surface = {tile: 0.0 for tile in TILE_IDS}
        self._local_surface = {tile: 0.0 for tile in TILE_IDS}
        self._last_activity_ms = None

    def reset(self) -> None:
        self._last_end_ms = None
        self._previous = None
        self._previous_features = None
        self._on_surface = {tile: 0.0 for tile in TILE_IDS}
        self._off_surface = {tile: 0.0 for tile in TILE_IDS}
        self._local_surface = {tile: 0.0 for tile in TILE_IDS}
        self._last_activity_ms = None

    def update(self, *, start_ms: int, end_ms: int, tile_luminance: dict,
               tile_features: dict | None = None) -> dict:
        if type(start_ms) is not int or type(end_ms) is not int or start_ms < 0 or end_ms <= start_ms:
            raise TemporalVisualEvidenceError("temporal visual interval must be positive monotonic milliseconds")
        current = _validate_luminance(tile_luminance)
        current_features = _validate_features(tile_features, current)
        reset_reason = None
        gap_ms = 0
        if self._last_end_ms is not None:
            if end_ms <= self._last_end_ms:
                raise TemporalVisualEvidenceError("temporal visual frames must advance monotonically")
            gap_ms = max(0, start_ms - self._last_end_ms)
            if gap_ms > self.reset_gap_ms:
                self.reset()
                reset_reason = "STREAM_GAP"

        if self._previous is None:
            self._previous = current
            self._previous_features = current_features
            self._last_end_ms = end_ms
            return {
                "method": METHOD if current_features is not None else LUMINANCE_METHOD,
                "feature_method": FEATURE_METHOD if current_features is not None else None,
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
        attention_novelty = round(max(
            base_attention_novelty,
            multichannel_change_score,
            0.15 * global_appearance_shift,
            0.15 * global_structure_shift,
        ), 6)
        on_activity = sum(self._on_surface.values()) / len(TILE_IDS)
        off_activity = sum(self._off_surface.values()) / len(TILE_IDS)
        changed = [tile for tile in TILE_IDS if tile_delta[tile] >= self.changed_tile_threshold]
        self._previous, self._last_end_ms = current, end_ms
        self._previous_features = current_features
        return {
            "method": METHOD if current_features is not None else LUMINANCE_METHOD,
            "feature_method": FEATURE_METHOD if current_features is not None else None,
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
            "attention_novelty": attention_novelty,
            "on_activity": round(on_activity, 6), "off_activity": round(off_activity, 6),
            "surface_expired": surface_expired, "tau_ms": self.tau_ms, "window_ms": self.window_ms,
            "gap_ms": gap_ms, "state_reset": reset_reason is not None, "reset_reason": reset_reason,
            "truth_authority": 0, "learning_authority": False, "action_authority": False,
        }


class TemporalVisualEvidenceRegistry:
    """Bounded process-local streams isolated by capture session, generation and receipt."""

    def __init__(self, *, max_streams: int = 8, **state_options) -> None:
        if type(max_streams) is not int or not 1 <= max_streams <= 64:
            raise ValueError("max_streams must be an integer in [1, 64]")
        self.max_streams = max_streams
        self._state_options = dict(state_options)
        self._states = OrderedDict()
        self._lock = threading.RLock()

    def update(self, *, capture_session_id: str, generation_id: str,
               consent_receipt_ref: str, start_ms: int, end_ms: int,
               tile_luminance: dict, tile_features: dict | None = None,
               session_consent_receipt_ref: str | None = None) -> dict:
        session = _identity(capture_session_id, "capture_session_id")
        generation = _identity(generation_id, "generation_id")
        receipt = _identity(consent_receipt_ref, "consent_receipt_ref")
        session_receipt = _identity(
            session_consent_receipt_ref if session_consent_receipt_ref is not None else receipt,
            "session_consent_receipt_ref",
        )
        key = (session, generation, session_receipt)
        with self._lock:
            # A session must not carry history into a new generation or
            # session-level consent lineage, even when the opaque session ID is reused.
            # Per-frame receipts may rotate inside one verified session lineage.
            for old_key in tuple(self._states):
                if old_key[0] == session and old_key != key:
                    del self._states[old_key]
            state = self._states.get(key)
            if state is None:
                state = TemporalVisualEvidence(**self._state_options)
            result = state.update(
                start_ms=start_ms, end_ms=end_ms, tile_luminance=tile_luminance,
                tile_features=tile_features,
            )
            self._states.pop(key, None)
            self._states[key] = state
            while len(self._states) > self.max_streams:
                self._states.popitem(last=False)
            return result

    def reset(self, *, capture_session_id: str) -> int:
        capture_session_id = _identity(capture_session_id, "capture_session_id")
        with self._lock:
            keys = [key for key in self._states if key[0] == capture_session_id]
            for key in keys:
                del self._states[key]
            return len(keys)

    def __len__(self) -> int:
        with self._lock:
            return len(self._states)
