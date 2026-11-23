"""M1 forecast metrics and paired temporal-block bootstrap statistics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class MetricReport:
    mae_at_15: float
    mae_at_30: float
    mae_at_60: float
    primary_mae_15_60: float


@dataclass(frozen=True)
class BootstrapReport:
    model_a: str
    model_b: str
    point_difference_a_minus_b: float
    confidence_interval_low: float
    confidence_interval_high: float
    confidence_level: float
    block_length: int
    block_count: int
    bootstrap_replicates: int
    per_seed_differences: tuple[float, ...]
    seed_difference_std: float


def forecast_metrics(target: np.ndarray, prediction: np.ndarray) -> MetricReport:
    """Compute exact lead-time MAE and the preregistered 15–60-minute primary endpoint."""
    y = np.asarray(target, dtype=np.float64)
    p = np.asarray(prediction, dtype=np.float64)
    if y.shape != p.shape or y.ndim != 3 or y.shape[1] < 60:
        raise ValueError("target and prediction must share shape [windows, horizon>=60, channels]")
    if not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError("metrics require finite target and prediction values")
    absolute = np.abs(y - p)
    return MetricReport(
        mae_at_15=float(absolute[:, 14, :].mean()),
        mae_at_30=float(absolute[:, 29, :].mean()),
        mae_at_60=float(absolute[:, 59, :].mean()),
        primary_mae_15_60=float(absolute[:, 14:60, :].mean()),
    )


def per_window_primary_mae(target: np.ndarray, prediction: np.ndarray) -> np.ndarray:
    """One scalar primary-endpoint error per origin for paired block resampling."""
    y = np.asarray(target, dtype=np.float64)
    p = np.asarray(prediction, dtype=np.float64)
    if y.shape != p.shape or y.ndim != 3 or y.shape[1] < 60:
        raise ValueError("target and prediction must share shape [windows, horizon>=60, channels]")
    if not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError("metrics require finite target and prediction values")
    return np.abs(y[:, 14:60, :] - p[:, 14:60, :]).mean(axis=(1, 2))


def paired_block_bootstrap(
    errors_by_model: Mapping[str, np.ndarray],
    origin_indices: np.ndarray,
    model_a: str,
    model_b: str,
    *,
    block_length: int,
    n_bootstrap: int = 2000,
    confidence_level: float = 0.95,
    random_seed: int = 20261123,
) -> BootstrapReport:
    """Paired block bootstrap with identical sampled time blocks for all models/seeds.

    Each model array has shape [seeds, windows] and contains per-window primary
    MAE. Seeds are averaged inside each replicate; they are never treated as
    independent temporal observations. Per-seed paired effects are reported
    separately from the temporal-block confidence interval.
    """
    if model_a not in errors_by_model or model_b not in errors_by_model:
        raise KeyError("both requested model names must be present")
    origins = np.asarray(origin_indices, dtype=np.int64)
    a = np.asarray(errors_by_model[model_a], dtype=np.float64)
    b = np.asarray(errors_by_model[model_b], dtype=np.float64)
    if a.ndim != 2 or b.shape != a.shape or a.shape[1] != origins.size:
        raise ValueError("model errors must share shape [seeds, windows] aligned to origin_indices")
    if origins.size < 1 or block_length < 1 or n_bootstrap < 1:
        raise ValueError("origins, block_length and n_bootstrap must be positive")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be in (0, 1)")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("bootstrap errors must be finite")
    if len(np.unique(origins)) != origins.size:
        raise ValueError("origin_indices must be unique")
    order = np.argsort(origins)
    origins = origins[order]
    a = a[:, order]
    b = b[:, order]

    block_keys = origins // block_length
    unique_blocks = np.unique(block_keys)
    block_indices = [np.flatnonzero(block_keys == key) for key in unique_blocks]
    if not block_indices:
        raise ValueError("no temporal blocks available")

    per_seed = (a.mean(axis=1) - b.mean(axis=1))
    point = float(per_seed.mean())
    rng = np.random.default_rng(random_seed)
    replicate_effects = np.empty(n_bootstrap, dtype=np.float64)
    for replicate in range(n_bootstrap):
        chosen = rng.integers(0, len(block_indices), size=len(block_indices))
        sampled = np.concatenate([block_indices[index] for index in chosen])
        seed_differences = a[:, sampled].mean(axis=1) - b[:, sampled].mean(axis=1)
        replicate_effects[replicate] = seed_differences.mean()

    alpha = (1.0 - confidence_level) / 2.0
    low, high = np.quantile(replicate_effects, [alpha, 1.0 - alpha])
    return BootstrapReport(
        model_a=model_a,
        model_b=model_b,
        point_difference_a_minus_b=point,
        confidence_interval_low=float(low),
        confidence_interval_high=float(high),
        confidence_level=confidence_level,
        block_length=block_length,
        block_count=len(unique_blocks),
        bootstrap_replicates=n_bootstrap,
        per_seed_differences=tuple(float(value) for value in per_seed),
        seed_difference_std=float(np.std(per_seed, ddof=1)) if per_seed.size > 1 else 0.0,
    )
