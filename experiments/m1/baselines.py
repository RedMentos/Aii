"""M1 BASE baselines with common X/S/calendar inputs and batch-only training.

RidgeAR is conventional squared-error Ridge (secondary). LADAR minimizes
absolute error plus an L2 coefficient penalty. Train Mean/Median use unique
accepted training target rows. No class reads validation or test data during fit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np

from .array_data import ArrayDataset, WindowBatch

DEFAULT_AR_LAGS = (1, 2, 3, 6, 12, 24, 48, 60, 120, 240, 480, 720, 1440, 2880, 4320, 10080)


class Predictor(Protocol):
    name: str

    def predict(self, batch: WindowBatch) -> np.ndarray: ...


def _constant_predictions(values: np.ndarray, batch: WindowBatch) -> np.ndarray:
    return np.broadcast_to(
        values.reshape(1, 1, -1),
        (len(batch.origin_indices), batch.target.shape[1], len(values)),
    ).copy()


class PersistenceBaseline:
    name = "persistence"

    def predict(self, batch: WindowBatch) -> np.ndarray:
        last = batch.inputs.x[:, -1:, :]
        return np.repeat(last, batch.target.shape[1], axis=1)


@dataclass
class SeasonalPersistenceBaseline:
    lag_index: int = 0

    @property
    def name(self) -> str:
        return f"seasonal_persistence_lag_{self.lag_index}"

    def predict(self, batch: WindowBatch) -> np.ndarray:
        if type(self.lag_index) is not int or not 0 <= self.lag_index < batch.inputs.seasonal.shape[2]:
            raise ValueError("seasonal lag index is not present in this InputBundle")
        return batch.inputs.seasonal[:, :, self.lag_index, :].copy()


class TrainConstantBaseline:
    """Train Mean/Median computed over unique accepted training target timestamps."""

    def __init__(self, statistic: str):
        if statistic not in {"mean", "median"}:
            raise ValueError("statistic must be mean or median")
        self.statistic = statistic
        self.name = f"train_{statistic}"
        self.values: np.ndarray | None = None
        self.n_unique_target_rows = 0

    def fit(self, dataset: ArrayDataset, *, batch_size: int = 256) -> "TrainConstantBaseline":
        target_rows = np.zeros(dataset.n_rows, dtype=bool)
        steps = np.arange(1, dataset.config.horizon + 1, dtype=np.int64)
        for batch in dataset.iter_batches("train", batch_size=batch_size):
            target_rows[batch.origin_indices[:, None] + steps[None, :]] = True
        train_start, train_end = dataset.bounds["train"]
        selected = dataset.train_values()[target_rows[train_start:train_end]]
        if selected.size == 0 or not np.isfinite(selected).all():
            raise ValueError("no finite accepted training target rows")
        self.n_unique_target_rows = int(target_rows[train_start:train_end].sum())
        if self.statistic == "mean":
            self.values = selected.astype(np.float64).mean(axis=0)
        else:
            self.values = np.median(selected.astype(np.float64), axis=0)
        return self

    def predict(self, batch: WindowBatch) -> np.ndarray:
        if self.values is None:
            raise RuntimeError("baseline must be fitted on train before prediction")
        return _constant_predictions(self.values, batch)


class TrainMeanBaseline(TrainConstantBaseline):
    def __init__(self):
        super().__init__("mean")


class TrainMedianBaseline(TrainConstantBaseline):
    def __init__(self):
        super().__init__("median")


def _ar_features(batch: WindowBatch, lags: Sequence[int]) -> np.ndarray:
    x = batch.inputs.x
    selected = tuple(lag for lag in lags if lag <= x.shape[1])
    if not selected:
        raise ValueError("no configured AR lag fits inside X_t")
    taps = np.concatenate([x[:, -lag, :] for lag in selected], axis=1)
    parts = [
        taps,
        batch.inputs.seasonal.reshape(len(x), -1),
        batch.inputs.calendar.reshape(len(x), -1),
    ]
    features = np.concatenate(parts, axis=1).astype(np.float64, copy=False)
    if not np.isfinite(features).all():
        raise ValueError("non-finite value reached BASE feature adapter")
    return features


class _LinearARBase:
    def __init__(self, *, alpha: float = 1.0, ar_lags: Sequence[int] | None = None):
        if not np.isfinite(alpha) or alpha <= 0:
            raise ValueError("alpha must be finite and positive")
        self.alpha = float(alpha)
        self.ar_lags = tuple(DEFAULT_AR_LAGS if ar_lags is None else ar_lags)
        if not self.ar_lags or any(type(lag) is not int or lag < 1 for lag in self.ar_lags):
            raise ValueError("AR lags must be positive integers")
        self.feature_mean: np.ndarray | None = None
        self.feature_scale: np.ndarray | None = None
        self.weights: np.ndarray | None = None
        self.n_train_windows = 0
        self.selected_ar_lags: tuple[int, ...] = ()

    def _raw_features(self, batch: WindowBatch) -> np.ndarray:
        self.selected_ar_lags = tuple(lag for lag in self.ar_lags if lag <= batch.inputs.x.shape[1])
        return _ar_features(batch, self.ar_lags)

    def _fit_scaler(self, dataset: ArrayDataset, batch_size: int) -> None:
        total = total_sq = None
        count = 0
        for batch in dataset.iter_batches("train", batch_size=batch_size):
            x = self._raw_features(batch)
            if total is None:
                total = np.zeros(x.shape[1], dtype=np.float64)
                total_sq = np.zeros(x.shape[1], dtype=np.float64)
            total += x.sum(axis=0)
            total_sq += np.square(x).sum(axis=0)
            count += len(x)
        if count == 0 or total is None or total_sq is None:
            raise ValueError("no accepted training windows for AR baseline")
        mean = total / count
        variance = np.maximum(total_sq / count - np.square(mean), 1e-12)
        scale = np.sqrt(variance)
        self.feature_mean = mean
        self.feature_scale = scale
        self.n_train_windows = count

    def _design(self, batch: WindowBatch) -> np.ndarray:
        if self.feature_mean is None or self.feature_scale is None:
            raise RuntimeError("AR baseline must be fitted before prediction")
        raw = self._raw_features(batch)
        standardized = (raw - self.feature_mean) / self.feature_scale
        return np.concatenate(
            (np.ones((len(raw), 1), dtype=np.float64), standardized),
            axis=1,
        )

    def predict(self, batch: WindowBatch) -> np.ndarray:
        if self.weights is None:
            raise RuntimeError("AR baseline must be fitted before prediction")
        prediction = self._design(batch) @ self.weights
        return prediction.reshape(len(batch.origin_indices), batch.target.shape[1], batch.target.shape[2])


class RidgeARBaseline(_LinearARBase):
    """Conventional squared-error Ridge AR; report as a secondary baseline."""

    name = "ridge_ar_l2"

    def fit(self, dataset: ArrayDataset, *, batch_size: int = 256) -> "RidgeARBaseline":
        self._fit_scaler(dataset, batch_size)
        gram = cross = None
        for batch in dataset.iter_batches("train", batch_size=batch_size):
            design = self._design(batch)
            target = batch.target.reshape(len(design), -1).astype(np.float64)
            if gram is None:
                gram = np.zeros((design.shape[1], design.shape[1]), dtype=np.float64)
                cross = np.zeros((design.shape[1], target.shape[1]), dtype=np.float64)
            gram += design.T @ design
            cross += design.T @ target
        if gram is None or cross is None:
            raise ValueError("no accepted training windows for Ridge AR")
        penalty = np.eye(gram.shape[0], dtype=np.float64) * self.alpha
        penalty[0, 0] = 0.0
        self.weights = np.linalg.solve(gram + penalty, cross)
        return self


class LADARBaseline(_LinearARBase):
    """L1 absolute-error AR fit with L2 coefficient penalty (not ordinary Ridge)."""

    name = "lad_ar_l1_l2penalty"

    def __init__(
        self,
        *,
        alpha: float = 1.0,
        ar_lags: Sequence[int] | None = None,
        epochs: int = 5,
        learning_rate: float = 0.02,
        seed: int = 17,
    ):
        super().__init__(alpha=alpha, ar_lags=ar_lags)
        if type(epochs) is not int or epochs < 1 or epochs > 100:
            raise ValueError("epochs must be an integer in [1, 100]")
        if not np.isfinite(learning_rate) or learning_rate <= 0:
            raise ValueError("learning_rate must be finite and positive")
        if type(seed) is not int:
            raise ValueError("seed must be an integer")
        self.epochs = epochs
        self.learning_rate = float(learning_rate)
        self.seed = seed
        self.epoch_losses: list[float] = []

    def fit(self, dataset: ArrayDataset, *, batch_size: int = 256) -> "LADARBaseline":
        self.epoch_losses = []
        self._fit_scaler(dataset, batch_size)
        weights = None
        first_moment = second_moment = None
        step = 0
        for epoch in range(self.epochs):
            absolute_sum = 0.0
            element_count = 0
            for batch in dataset.iter_batches(
                "train", batch_size=batch_size, shuffle=True, seed=self.seed + epoch
            ):
                design = self._design(batch)
                target = batch.target.reshape(len(design), -1).astype(np.float64)
                if weights is None:
                    weights = np.zeros((design.shape[1], target.shape[1]), dtype=np.float64)
                    first_moment = np.zeros_like(weights)
                    second_moment = np.zeros_like(weights)
                residual = design @ weights - target
                gradient = design.T @ np.sign(residual) / residual.size
                gradient[1:] += self.alpha * weights[1:]
                step += 1
                first_moment = 0.9 * first_moment + 0.1 * gradient
                second_moment = 0.999 * second_moment + 0.001 * np.square(gradient)
                corrected_m = first_moment / (1.0 - 0.9 ** step)
                corrected_v = second_moment / (1.0 - 0.999 ** step)
                weights -= self.learning_rate * corrected_m / (np.sqrt(corrected_v) + 1e-8)
                absolute_sum += float(np.abs(residual).sum())
                element_count += int(residual.size)
            if weights is None or element_count == 0:
                raise ValueError("no accepted training windows for LAD AR")
            penalty_value = 0.5 * self.alpha * float(np.square(weights[1:]).sum())
            self.epoch_losses.append(absolute_sum / element_count + penalty_value)
        self.weights = weights
        return self


def evaluate_mae(
    predictor: Predictor,
    dataset: ArrayDataset,
    split: str,
    *,
    batch_size: int = 256,
) -> dict:
    """Evaluate without retaining predictions; test split remains subject to dataset gate."""
    total_abs = 0.0
    total_elements = 0
    horizon_abs: np.ndarray | None = None
    channel_abs: np.ndarray | None = None
    n_windows = 0
    for batch in dataset.iter_batches(split, batch_size=batch_size):
        prediction = np.asarray(predictor.predict(batch), dtype=np.float64)
        target = batch.target.astype(np.float64)
        if prediction.shape != target.shape or not np.isfinite(prediction).all():
            raise ValueError("baseline prediction shape/non-finite mismatch")
        error = np.abs(prediction - target)
        if horizon_abs is None:
            horizon_abs = np.zeros(target.shape[1], dtype=np.float64)
            channel_abs = np.zeros(target.shape[2], dtype=np.float64)
        horizon_abs += error.sum(axis=(0, 2))
        channel_abs += error.sum(axis=(0, 1))
        total_abs += float(error.sum())
        total_elements += int(error.size)
        n_windows += len(batch.origin_indices)
    if not n_windows or horizon_abs is None or channel_abs is None:
        raise ValueError(f"no accepted windows in split {split}")
    return {
        "name": predictor.name,
        "split": split,
        "n_windows": n_windows,
        "mae": total_abs / total_elements,
        "per_horizon_mae": (horizon_abs / (n_windows * len(dataset.channels))).tolist(),
        "per_channel_mae": (channel_abs / (n_windows * dataset.config.horizon)).tolist(),
    }
