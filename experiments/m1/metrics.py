"""Common M1 forecast metrics and paired validation-suite evaluation."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Sequence

import numpy as np

from .array_data import ArrayDataset
from .baselines import Predictor
from .bootstrap import WindowErrorSeries, paired_block_bootstrap

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def evaluate_predictor(
    predictor: Predictor,
    dataset: ArrayDataset,
    split: str,
    *,
    seed: int,
    primary_start: int = 15,
    primary_end: int = 60,
    report_horizons: Sequence[int] = (15, 30, 60),
    batch_size: int = 256,
) -> tuple[dict, WindowErrorSeries]:
    """One-pass evaluation; primary score is per-origin MAE over steps 15..60."""
    horizon = dataset.config.horizon
    channels = len(dataset.channels)
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if type(primary_start) is not int or type(primary_end) is not int:
        raise ValueError("primary horizon bounds must be integers")
    if not 1 <= primary_start <= primary_end <= horizon:
        raise ValueError("primary horizon bounds must lie inside configured horizon")
    horizons = tuple(report_horizons)
    if not horizons or any(type(h) is not int or not 1 <= h <= horizon for h in horizons):
        raise ValueError("report_horizons must be non-empty integer horizons within the configured horizon")
    if tuple(sorted(set(horizons))) != horizons:
        raise ValueError("report_horizons must be strictly increasing and unique")

    horizon_abs = np.zeros(horizon, dtype=np.float64)
    channel_abs = np.zeros(channels, dtype=np.float64)
    horizon_channel_abs = np.zeros((horizon, channels), dtype=np.float64)
    primary_errors: list[np.ndarray] = []
    origin_ids: list[np.ndarray] = []
    n_windows = 0

    for batch in dataset.iter_batches(split, batch_size=batch_size):
        prediction = np.asarray(predictor.predict(batch), dtype=np.float64)
        target = batch.target.astype(np.float64)
        if prediction.shape != target.shape or not np.isfinite(prediction).all():
            raise ValueError("prediction shape/non-finite mismatch")
        error = np.abs(prediction - target)
        horizon_abs += error.sum(axis=(0, 2))
        channel_abs += error.sum(axis=(0, 1))
        horizon_channel_abs += error.sum(axis=0)
        primary = error[:, primary_start - 1:primary_end, :]
        primary_errors.append(primary.mean(axis=(1, 2)))
        origin_ids.append(dataset._minute_ids[batch.origin_indices].copy())
        n_windows += len(batch.origin_indices)

    if not n_windows:
        raise ValueError(f"no accepted windows in split {split}")
    per_horizon = horizon_abs / (n_windows * channels)
    per_channel = channel_abs / (n_windows * horizon)
    metrics = {
        "model": str(predictor.name),
        "seed": seed,
        "split": split,
        "n_windows": n_windows,
        "mae_at_horizons": {
            str(h): float(horizon_abs[:h].sum() / (n_windows * h * channels))
            for h in horizons
        },
        "primary_horizon": [primary_start, primary_end],
        "primary_mae": float(np.concatenate(primary_errors).mean()),
        "per_horizon_mae": per_horizon.tolist(),
        "per_channel_mae": per_channel.tolist(),
        "per_horizon_channel_mae": (
            horizon_channel_abs / n_windows
        ).tolist(),
    }
    series = WindowErrorSeries(
        model=str(predictor.name),
        seed=seed,
        origin_minute_ids=np.concatenate(origin_ids),
        primary_mae=np.concatenate(primary_errors),
    )
    return metrics, series


def evaluate_suite(
    runs: Sequence[tuple[Predictor, int]],
    dataset: ArrayDataset,
    *,
    split: str = "validation",
    reference_model: str,
    code_commit: str,
    primary_start: int = 15,
    primary_end: int = 60,
    report_horizons: Sequence[int] = (15, 30, 60),
    block_len_minutes: int = 10080,
    n_resamples: int = 2000,
    bootstrap_seed: int = 17,
    batch_size: int = 256,
) -> dict:
    """Evaluate all model/seed pairs on identical windows and compute paired block CIs."""
    if not runs:
        raise ValueError("at least one predictor/seed run is required")
    if not _COMMIT_RE.fullmatch(code_commit):
        raise ValueError("code_commit must be a verified 40-character lowercase git SHA")
    metrics_rows: list[dict] = []
    error_series: list[WindowErrorSeries] = []
    for predictor, run_seed in runs:
        metrics, errors = evaluate_predictor(
            predictor, dataset, split, seed=run_seed,
            primary_start=primary_start, primary_end=primary_end,
            report_horizons=report_horizons, batch_size=batch_size,
        )
        metrics_rows.append(metrics)
        error_series.append(errors)
    bootstrap = paired_block_bootstrap(
        error_series, reference_model=reference_model,
        block_len_minutes=block_len_minutes, n_resamples=n_resamples, seed=bootstrap_seed,
    )
    return {
        "schema": "m1.clean-room.experiment-result.v1",
        "code_commit": code_commit,
        "split": split,
        "dataset_sha256": dataset.dataset_sha256,
        "data_config_sha256": dataset.config_sha256,
        "split_boundaries_sha256": dataset.split_sha256,
        "metric_definition": {
            "primary": f"mean absolute error over forecast steps {primary_start}..{primary_end}, all channels, per origin",
            "reported_prefix_horizons": list(report_horizons),
            "bootstrap": "paired non-overlapping temporal blocks; block sums/counts preserve the per-window mean; paired deltas averaged across seeds",
        },
        "runs": metrics_rows,
        "paired_block_bootstrap": bootstrap,
    }


def write_result_atomic(result: dict, path: str | Path) -> str:
    """Persist canonical JSON atomically; return SHA-256 of the exact written bytes."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8") + b"\n"
    digest = hashlib.sha256(payload).hexdigest()
    fd, temporary = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        dir_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return digest
