"""Paired temporal-block bootstrap for M1 primary MAE comparisons."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .array_data import ArrayDataset, WindowBatch
from .baselines import Predictor


@dataclass(frozen=True)
class WindowErrorSeries:
    model: str
    seed: int
    origin_minute_ids: np.ndarray
    primary_mae: np.ndarray


def collect_window_errors(
    predictor: Predictor,
    dataset: ArrayDataset,
    split: str,
    *,
    seed: int,
    primary_start: int = 15,
    primary_end: int = 60,
    batch_size: int = 256,
) -> WindowErrorSeries:
    """Collect one primary MAE value per accepted forecast origin.

    The primary metric averages forecast steps [primary_start, primary_end]
    inclusive and all selected channels. The caller must explicitly duplicate
    deterministic baselines under each seed ID to enable per-seed paired deltas.
    """
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if type(primary_start) is not int or type(primary_end) is not int:
        raise ValueError("primary horizon bounds must be integers")
    if not 1 <= primary_start <= primary_end <= dataset.config.horizon:
        raise ValueError("primary horizon bounds must lie inside the configured horizon")
    origins: list[np.ndarray] = []
    values: list[np.ndarray] = []
    for batch in dataset.iter_batches(split, batch_size=batch_size):
        prediction = np.asarray(predictor.predict(batch), dtype=np.float64)
        target = batch.target.astype(np.float64)
        if prediction.shape != target.shape or not np.isfinite(prediction).all():
            raise ValueError("prediction shape/non-finite mismatch")
        error = np.abs(prediction - target)
        selected = error[:, primary_start - 1:primary_end, :]
        origins.append(dataset._minute_ids[batch.origin_indices].copy())
        values.append(selected.mean(axis=(1, 2)))
    if not origins:
        raise ValueError(f"no accepted windows in split {split}")
    return WindowErrorSeries(
        model=str(predictor.name),
        seed=seed,
        origin_minute_ids=np.concatenate(origins),
        primary_mae=np.concatenate(values),
    )


def paired_block_bootstrap(
    series: Sequence[WindowErrorSeries],
    *,
    reference_model: str,
    block_days: int = 7,
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = 17,
) -> dict:
    """Paired block bootstrap; resample the same temporal blocks for all models/seeds.

    For each replicate, calculate each model-reference difference per seed,
    then average those differences over seeds. Confidence intervals are taken
    over replicate-level averages, never over overlapping windows as if
    independent observations.
    """
    if not series:
        raise ValueError("at least one model series is required")
    if type(block_days) is not int or block_days < 1:
        raise ValueError("block_days must be a positive integer")
    if type(n_resamples) is not int or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if not np.isfinite(confidence) or not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie between zero and one")

    models = sorted({item.model for item in series})
    if reference_model not in models:
        raise ValueError("reference model is missing")
    seed_ids = sorted({item.seed for item in series})
    expected = {(model, run_seed) for model in models for run_seed in seed_ids}
    observed = {(item.model, item.seed) for item in series}
    if observed != expected or len(observed) != len(series):
        raise ValueError("every model must have exactly one series for every seed")

    reference_origins: np.ndarray | None = None
    block_ids: np.ndarray | None = None
    block_matrix = np.empty((len(models), len(seed_ids), 0), dtype=np.float64)
    for model_index, model in enumerate(models):
        for seed_index, run_seed in enumerate(seed_ids):
            item = next(x for x in series if x.model == model and x.seed == run_seed)
            origins = np.asarray(item.origin_minute_ids, dtype=np.int64)
            errors = np.asarray(item.primary_mae, dtype=np.float64)
            if origins.ndim != 1 or errors.shape != origins.shape or origins.size == 0:
                raise ValueError("origin and error arrays must be non-empty one-dimensional arrays")
            if not np.isfinite(errors).all() or np.any(np.diff(origins) <= 0):
                raise ValueError("errors must be finite and origins strictly increasing")
            if reference_origins is None:
                reference_origins = origins
                day_ids = origins // 1440
                block_ids = day_ids // block_days
                unique_blocks = np.unique(block_ids)
                block_matrix = np.empty((len(models), len(seed_ids), len(unique_blocks)), dtype=np.float64)
            elif not np.array_equal(origins, reference_origins):
                raise ValueError("all models and seeds must use identical forecast origins")
            assert block_ids is not None
            assert unique_blocks is not None
            for block_index, block in enumerate(unique_blocks):
                mask = block_ids == block
                if not np.any(mask):
                    raise AssertionError("empty temporal block")
                block_matrix[model_index, seed_index, block_index] = errors[mask].mean()

    assert block_ids is not None
    assert unique_blocks is not None
    reference_index = models.index(reference_model)
    full_seed_mae = block_matrix.mean(axis=2)
    rng = np.random.default_rng(seed)
    replicate_deltas = np.empty((n_resamples, len(models)), dtype=np.float64)
    for replicate in range(n_resamples):
        sampled = rng.integers(0, len(unique_blocks), size=len(unique_blocks))
        sampled_mae = block_matrix[:, :, sampled].mean(axis=2)
        per_seed_delta = sampled_mae - sampled_mae[reference_index:reference_index + 1, :]
        replicate_deltas[replicate] = per_seed_delta.mean(axis=1)

    alpha = (1.0 - confidence) / 2.0
    results = {}
    for model_index, model in enumerate(models):
        deltas = replicate_deltas[:, model_index]
        seed_mae = full_seed_mae[model_index]
        results[model] = {
            "mae": float(seed_mae.mean()),
            "seed_mae": {str(run_seed): float(value) for run_seed, value in zip(seed_ids, seed_mae)},
            "seed_variance": float(seed_mae.var(ddof=1)) if len(seed_ids) > 1 else None,
            "delta_vs_reference": float((seed_mae - full_seed_mae[reference_index]).mean()),
            "delta_ci": [
                float(np.quantile(deltas, alpha)),
                float(np.quantile(deltas, 1.0 - alpha)),
            ],
        }
    return {
        "reference_model": reference_model,
        "block_days": block_days,
        "n_blocks": int(len(unique_blocks)),
        "n_resamples": n_resamples,
        "confidence": confidence,
        "seed_ids": seed_ids,
        "models": results,
    }
