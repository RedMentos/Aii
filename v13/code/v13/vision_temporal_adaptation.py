"""Low-cost global/local decomposition for bounded temporal RAW EYE features.

This is a diagnostic heuristic, not camera-motion compensation or semantic
motion detection. It separates a robust common luminance shift from tile-local
residuals so A4 can weight localized changes more strongly while retaining a
small global-transition signal.
"""
from __future__ import annotations

import math

GLOBAL_CHANGE_ATTENTION_WEIGHT = 0.15


def decompose_temporal_change(previous, current, tile_ids, values_per_tile):
    """Return median signed common-mode luminance shift and per-tile residual.

    A median over all bounded sub-tile samples is robust when fewer than half
    the samples contain a localized change. It is not robust to camera motion
    or a scene transition affecting most of the frame; those remain explicit
    limitations and are surfaced as global_change_score.
    """
    signed_by_tile = {}
    flattened = []
    for tile in tile_ids:
        before = previous[tile]
        after = current[tile]
        if len(before) != values_per_tile or len(after) != values_per_tile:
            raise ValueError("temporal adaptation tile width mismatch")
        deltas = tuple(float(a) - float(b) for b, a in zip(before, after))
        if any(not math.isfinite(value) for value in deltas):
            raise ValueError("temporal adaptation delta must be finite")
        signed_by_tile[tile] = deltas
        flattened.extend(deltas)
    if not flattened:
        raise ValueError("temporal adaptation requires at least one sample")
    ordered = sorted(flattened)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        common_mode = ordered[middle]
    else:
        common_mode = (ordered[middle - 1] + ordered[middle]) * 0.5
    local_delta = {
        tile: sum(abs(value - common_mode) for value in signed_by_tile[tile]) / values_per_tile
        for tile in tile_ids
    }
    return common_mode, local_delta


def weighted_tile_score(values):
    """Same top-four/mean pooling used by the RAW EYE temporal baseline."""
    ordered = sorted((max(0.0, float(value)) for value in values), reverse=True)
    if not ordered:
        return 0.0
    divisor = min(4, len(ordered))
    top4 = sum(ordered[:4]) / divisor
    mean = sum(ordered) / len(ordered)
    return min(1.0, max(0.0, 0.6 * top4 + 0.4 * mean))


def compute_attention_novelty(local_change_score, local_activity_score, global_change_score):
    """Prefer local temporal change; keep global-only transitions weakly visible."""
    values = (local_change_score, local_activity_score, global_change_score)
    if any(not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0 for value in values):
        raise ValueError("temporal attention scores must be finite in [0,1]")
    return round(max(
        float(local_change_score),
        float(local_activity_score),
        GLOBAL_CHANGE_ATTENTION_WEIGHT * float(global_change_score),
    ), 6)
