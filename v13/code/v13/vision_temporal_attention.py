"""Bounded temporal RAW EYE tile-change hints for consent-scoped UI frames.

This is a deterministic feature-delta heuristic, not semantic change detection,
a trained model, confidence, or truth. It stores only a tiny in-process feature
snapshot per live source/session/consent/generation/lease; never pixels or files.
"""
from __future__ import annotations

from collections import OrderedDict
import math
import re
import threading

REGION_IDS = tuple(f"r{row}{column}" for row in range(4) for column in range(4))
FEATURE_DIM = 37
_SHA256 = re.compile(r"[0-9a-f]{64}\\Z")


class TemporalUIAttentionError(ValueError):
    """Malformed or out-of-contract temporal RAW EYE features."""


class TemporalUIAttentionRegistry:
    """Small LRU of consecutive 4x4 RAW EYE tile descriptors per exact lease."""

    METHOD = "RAW_EYE_TILE_FEATURE_DELTA_V1"

    def __init__(
        self,
        *,
        max_streams: int = 8,
        max_gap_ms: int = 2000,
        change_threshold: float = 0.05,
        interrupt_threshold: float = 0.08,
    ) -> None:
        if type(max_streams) is not int or not 1 <= max_streams <= 64:
            raise ValueError("max_streams must be an integer in 1..64")
        if type(max_gap_ms) is not int or not 0 <= max_gap_ms <= 60000:
            raise ValueError("max_gap_ms must be an integer in 0..60000")
        for name, value in (("change_threshold", change_threshold),
                            ("interrupt_threshold", interrupt_threshold)):
            if (type(value) not in (int, float) or not math.isfinite(float(value))
                    or not 0.0 <= float(value) <= 1.0):
                raise ValueError(name + " must be finite and in [0, 1]")
        if float(interrupt_threshold) < float(change_threshold):
            raise ValueError("interrupt_threshold cannot be below change_threshold")
        self.max_streams = max_streams
        self.max_gap_ms = max_gap_ms
        self.change_threshold = float(change_threshold)
        self.interrupt_threshold = float(interrupt_threshold)
        self._states: OrderedDict[tuple, dict] = OrderedDict()
        self._lock = threading.RLock()

    @staticmethod
    def _identity(value, name: str) -> str:
        if type(value) is not str or not value.strip() or len(value) > 128:
            raise TemporalUIAttentionError(name + " is invalid")
        return value

    @staticmethod
    def _features(region_ids, feature_rows) -> tuple[tuple[float, ...], ...]:
        if type(region_ids) not in (list, tuple) or tuple(region_ids) != REGION_IDS:
            raise TemporalUIAttentionError("RAW EYE region order must be the exact 4x4 grid")
        if type(feature_rows) not in (list, tuple) or len(feature_rows) != len(REGION_IDS):
            raise TemporalUIAttentionError("RAW EYE feature rows must contain exactly 16 tiles")
        rows = []
        for row in feature_rows:
            if hasattr(row, "tolist"):
                row = row.tolist()
            if type(row) not in (list, tuple) or len(row) != FEATURE_DIM:
                raise TemporalUIAttentionError("RAW EYE tile feature dimension must be 37")
            values = []
            for value in row:
                if isinstance(value, (bool, str, bytes, bytearray)):
                    raise TemporalUIAttentionError("RAW EYE feature must be numeric")
                try:
                    numeric = float(value)
                except (TypeError, ValueError, OverflowError):
                    raise TemporalUIAttentionError("RAW EYE feature must be numeric") from None
                if not math.isfinite(numeric) or not -1.0e-5 <= numeric <= 1.00001:
                    raise TemporalUIAttentionError("RAW EYE feature must be finite and in [0, 1]")
                values.append(numeric)
            rows.append(tuple(values))
        return tuple(rows)

    def update(
        self,
        *,
        consent_lease,
        source_id: str,
        capture_session_id: str,
        consent_receipt_ref: str,
        generation_id: str,
        start_ms: int,
        end_ms: int,
        frame_sha256: str,
        region_ids,
        feature_rows,
    ) -> dict:
        if consent_lease is None:
            raise PermissionError("a live UI consent lease is required for temporal attention")
        source_id = self._identity(source_id, "source_id")
        capture_session_id = self._identity(capture_session_id, "capture_session_id")
        consent_receipt_ref = self._identity(consent_receipt_ref, "consent_receipt_ref")
        generation_id = self._identity(generation_id, "generation_id")
        if (type(start_ms) is not int or type(end_ms) is not int
                or start_ms < 0 or end_ms <= start_ms or end_ms - start_ms > 5000):
            raise TemporalUIAttentionError("UI frame interval is invalid")
        if type(frame_sha256) is not str or not _SHA256.fullmatch(frame_sha256):
            raise TemporalUIAttentionError("frame_sha256 must be lowercase SHA-256")
        current = self._features(region_ids, feature_rows)
        # Lease identity prevents feature carry-over between separately issued
        # capabilities even if source/session metadata is accidentally reused.
        key = (id(consent_lease), source_id, capture_session_id,
               consent_receipt_ref, generation_id)
        zeros = {region_id: 0.0 for region_id in REGION_IDS}
        with self._lock:
            previous = self._states.get(key)
            status = "WARMUP"
            per_region = zeros
            if previous is not None:
                if start_ms < previous["end_ms"] or end_ms <= previous["end_ms"]:
                    status = "TIME_RESET"
                elif start_ms - previous["end_ms"] > self.max_gap_ms:
                    status = "GAP_RESET"
                elif frame_sha256 == previous["frame_sha256"]:
                    status = "DUPLICATE"
                else:
                    status = "MEASURED"
                    per_region = {
                        region_id: round(
                            math.fsum(abs(a - b) for a, b in zip(old, new)) / FEATURE_DIM,
                            6,
                        )
                        for region_id, old, new in zip(REGION_IDS, previous["features"], current)
                    }
            self._states.pop(key, None)
            self._states[key] = {
                "end_ms": end_ms,
                "frame_sha256": frame_sha256,
                "features": current,
            }
            while len(self._states) > self.max_streams:
                self._states.popitem(last=False)

        maximum = max(per_region.values(), default=0.0)
        mean = math.fsum(per_region.values()) / len(REGION_IDS)
        changed = sorted(
            (region_id for region_id, score in per_region.items()
             if score >= self.change_threshold),
            key=lambda region_id: (-per_region[region_id], region_id),
        )
        return {
            "method": self.METHOD,
            "status": status,
            "per_region_change": per_region,
            "mean_change": round(mean, 6),
            "max_change": round(maximum, 6),
            "changed_regions": changed,
            "change_threshold": self.change_threshold,
            "interrupt_threshold": self.interrupt_threshold,
            "novelty_signal": round(maximum, 6) if status == "MEASURED" else 0.0,
            "interrupt_signal": (
                round(maximum, 6)
                if status == "MEASURED" and maximum >= self.interrupt_threshold else 0.0
            ),
            "authority": "HEURISTIC_RAW_FEATURE_DELTA",
            "calibrated": False,
            "truth_authority": 0,
            "learning_authority": False,
            "action_authority": False,
        }

    def reset(
        self,
        *,
        source_id: str | None = None,
        capture_session_id: str | None = None,
        consent_receipt_ref: str | None = None,
        generation_id: str | None = None,
    ) -> int:
        if source_id is not None:
            source_id = self._identity(source_id, "source_id")
        if capture_session_id is not None:
            capture_session_id = self._identity(capture_session_id, "capture_session_id")
        if consent_receipt_ref is not None:
            consent_receipt_ref = self._identity(consent_receipt_ref, "consent_receipt_ref")
        if generation_id is not None:
            generation_id = self._identity(generation_id, "generation_id")
        with self._lock:
            stale = [
                key for key in self._states
                if (source_id is None or key[1] == source_id)
                and (capture_session_id is None or key[2] == capture_session_id)
                and (consent_receipt_ref is None or key[3] == consent_receipt_ref)
                and (generation_id is None or key[4] == generation_id)
            ]
            for key in stale:
                self._states.pop(key, None)
            return len(stale)

    def stream_count(self) -> int:
        with self._lock:
            return len(self._states)


_RUNTIME_INIT_LOCK = threading.Lock()


def runtime_registry(runtime) -> TemporalUIAttentionRegistry:
    registry = getattr(runtime, "_v14_ui_temporal_attention", None)
    if registry is None:
        with _RUNTIME_INIT_LOCK:
            registry = getattr(runtime, "_v14_ui_temporal_attention", None)
            if registry is None:
                registry = TemporalUIAttentionRegistry()
                runtime._v14_ui_temporal_attention = registry
    if not isinstance(registry, TemporalUIAttentionRegistry):
        raise RuntimeError("Runtime temporal UI attention registry is already occupied")
    return registry


def update_runtime_ui_temporal_attention(runtime, **kwargs) -> dict:
    return runtime_registry(runtime).update(**kwargs)


def reset_runtime_ui_temporal_attention(runtime, source_id: str | None = None) -> int:
    registry = getattr(runtime, "_v14_ui_temporal_attention", None)
    if registry is None:
        return 0
    if not isinstance(registry, TemporalUIAttentionRegistry):
        raise RuntimeError("Runtime temporal UI attention registry is already occupied")
    return registry.reset(source_id=source_id)


__all__ = [
    "REGION_IDS", "FEATURE_DIM", "TemporalUIAttentionError",
    "TemporalUIAttentionRegistry", "runtime_registry",
    "update_runtime_ui_temporal_attention", "reset_runtime_ui_temporal_attention",
]
