"""Ephemeral, consent-lease-scoped temporal RAW EYE luminance evidence.

This is a deterministic frame-difference diagnostic, not optical flow, OCR,
object recognition, a calibrated probability, or a learned temporal model.
Only 4x4 luminance summaries per tile are retained in bounded process memory;
no frame bytes, images, text, or persistent model state are stored.
"""
from __future__ import annotations

from collections import OrderedDict
import math
import threading

TILE_IDS = tuple(f"r{row}{col}" for row in range(4) for col in range(4))
LUMINANCE_VALUES_PER_TILE = 16
METHOD = "RAW_EYE_TEMPORAL_LUMINANCE_DELTA_V1"


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


class TemporalVisualEvidence:
    """One-stream, one-frame-history temporal delta accumulator."""

    def __init__(self, *, reset_gap_ms: int = 1500, changed_tile_threshold: float = 0.08) -> None:
        if type(reset_gap_ms) is not int or not 100 <= reset_gap_ms <= 10000:
            raise ValueError("reset_gap_ms must be an integer in [100, 10000]")
        if type(changed_tile_threshold) not in (int, float) or not math.isfinite(float(changed_tile_threshold)) or not 0.0 < float(changed_tile_threshold) <= 1.0:
            raise ValueError("changed_tile_threshold must be finite in (0,1]")
        self.reset_gap_ms = reset_gap_ms
        self.changed_tile_threshold = float(changed_tile_threshold)
        self._last_end_ms = None
        self._previous = None

    def reset(self) -> None:
        self._last_end_ms = None
        self._previous = None

    def update(self, *, start_ms: int, end_ms: int, tile_luminance: dict) -> dict:
        if type(start_ms) is not int or type(end_ms) is not int or start_ms < 0 or end_ms <= start_ms:
            raise TemporalVisualEvidenceError("temporal visual interval must be positive monotonic milliseconds")
        current = _validate_luminance(tile_luminance)
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
            self._last_end_ms = end_ms
            return {
                "method": METHOD,
                "status": "WARMUP",
                "change_score": 0.0,
                "mean_change": 0.0,
                "peak_change": 0.0,
                "changed_tile_ids": [],
                "tile_delta": {},
                "gap_ms": gap_ms,
                "state_reset": reset_reason is not None,
                "reset_reason": reset_reason,
                "truth_authority": 0,
                "learning_authority": False,
                "action_authority": False,
            }

        tile_delta = {
            tile_id: sum(abs(a - b) for a, b in zip(current[tile_id], self._previous[tile_id])) / LUMINANCE_VALUES_PER_TILE
            for tile_id in TILE_IDS
        }
        ordered = sorted(tile_delta.values(), reverse=True)
        mean_change = sum(ordered) / len(ordered)
        top4_change = sum(ordered[:4]) / 4.0
        # Top-four pooling keeps a small changed UI region visible without
        # letting one noisy pixel dominate the entire frame score.
        change_score = min(1.0, max(0.0, 0.6 * top4_change + 0.4 * mean_change))
        changed = [tile_id for tile_id in TILE_IDS if tile_delta[tile_id] >= self.changed_tile_threshold]
        self._previous = current
        self._last_end_ms = end_ms
        return {
            "method": METHOD,
            "status": "MEASURED",
            "change_score": round(change_score, 6),
            "mean_change": round(mean_change, 6),
            "peak_change": round(max(ordered), 6),
            "changed_tile_ids": changed,
            "tile_delta": {key: round(value, 6) for key, value in tile_delta.items()},
            "gap_ms": gap_ms,
            "state_reset": reset_reason is not None,
            "reset_reason": reset_reason,
            "truth_authority": 0,
            "learning_authority": False,
            "action_authority": False,
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
               tile_luminance: dict) -> dict:
        session = _identity(capture_session_id, "capture_session_id")
        generation = _identity(generation_id, "generation_id")
        receipt = _identity(consent_receipt_ref, "consent_receipt_ref")
        key = (session, generation, receipt)
        with self._lock:
            # A session must not carry history into a new generation or
            # consent receipt, even when the opaque session ID is reused.
            for old_key in tuple(self._states):
                if old_key[0] == session and old_key != key:
                    del self._states[old_key]
            state = self._states.get(key)
            if state is None:
                state = TemporalVisualEvidence(**self._state_options)
            result = state.update(start_ms=start_ms, end_ms=end_ms, tile_luminance=tile_luminance)
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
