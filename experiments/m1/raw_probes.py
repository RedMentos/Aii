"""Raw-window controls for M1, trained on the common X/S/calendar InputBundle.

These controls deliberately do not use a learned encoder. RawWindowProbe is a
linear MAE readout; RawWindowMLP adds one nonlinear hidden layer. Both fit only
on train windows and expose validation evaluation through evaluate_mae().
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .array_data import ArrayDataset, WindowBatch
from .baselines import evaluate_mae


@dataclass
class _AdamState:
    first: list[np.ndarray]
    second: list[np.ndarray]
    step: int = 0


class _RawWindowModel:
    def __init__(
        self,
        *,
        hidden_width: int | None,
        epochs: int = 5,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        seed: int = 17,
        batch_size: int = 32,
    ) -> None:
        if hidden_width is not None and (type(hidden_width) is not int or hidden_width < 1):
            raise ValueError("hidden_width must be a positive integer or None")
        if type(epochs) is not int or not 1 <= epochs <= 100:
            raise ValueError("epochs must be an integer in [1, 100]")
        if not np.isfinite(learning_rate) or learning_rate <= 0:
            raise ValueError("learning_rate must be finite and positive")
        if not np.isfinite(weight_decay) or weight_decay < 0:
            raise ValueError("weight_decay must be finite and non-negative")
        if type(seed) is not int:
            raise ValueError("seed must be an integer")
        if type(batch_size) is not int or not 1 <= batch_size <= 8192:
            raise ValueError("batch_size must be an integer in [1, 8192]")
        self.hidden_width = hidden_width
        self.epochs = epochs
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.seed = seed
        self.batch_size = batch_size
        self.name = "raw_window_probe" if hidden_width is None else "raw_window_mlp"
        self.feature_mean: np.ndarray | None = None
        self.feature_scale: np.ndarray | None = None
        self.weights: list[np.ndarray] = []
        self.biases: list[np.ndarray] = []
        self.epoch_mae: list[float] = []
        self.n_train_windows = 0
        self.n_scaler_windows = 0
        self._input_width: int | None = None
        self._output_shape: tuple[int, int] | None = None

    @property
    def parameter_count(self) -> int:
        return int(sum(w.size for w in self.weights) + sum(b.size for b in self.biases))

    def _fit_scaler(self, dataset: ArrayDataset) -> None:
        total = total_sq = None
        count = 0
        full_batch_iterator = getattr(dataset, "iter_full_batches", dataset.iter_batches)
        for batch in full_batch_iterator("train", batch_size=self.batch_size):
            x = batch.inputs.flatten().astype(np.float64, copy=False)
            if not np.isfinite(x).all():
                raise ValueError("non-finite raw input reached probe")
            if total is None:
                total = np.zeros(x.shape[1], dtype=np.float64)
                total_sq = np.zeros(x.shape[1], dtype=np.float64)
            total += x.sum(axis=0)
            total_sq += np.square(x).sum(axis=0)
            count += len(x)
        if count == 0 or total is None or total_sq is None:
            raise ValueError("no accepted train windows for raw-window model")
        mean = total / count
        variance = np.maximum(total_sq / count - np.square(mean), 1e-8)
        self.feature_mean = mean.astype(np.float32)
        self.feature_scale = np.sqrt(variance).astype(np.float32)
        self.n_scaler_windows = count
        self._input_width = int(total.size)

    def _initialize(self, input_width: int, output_width: int) -> None:
        rng = np.random.default_rng(self.seed)
        dims = [input_width]
        if self.hidden_width is not None:
            dims.append(self.hidden_width)
        dims.append(output_width)
        self.weights = []
        self.biases = []
        for fan_in, fan_out in zip(dims[:-1], dims[1:]):
            scale = np.sqrt(2.0 / fan_in) if self.hidden_width is not None and fan_in == input_width else np.sqrt(2.0 / (fan_in + fan_out))
            self.weights.append((rng.standard_normal((fan_in, fan_out)) * scale).astype(np.float32))
            self.biases.append(np.zeros(fan_out, dtype=np.float32))

    def _forward(self, x: np.ndarray) -> tuple[np.ndarray, list[np.ndarray], list[np.ndarray]]:
        activations = [x]
        preactivations: list[np.ndarray] = []
        for index, (weight, bias) in enumerate(zip(self.weights, self.biases)):
            z = activations[-1] @ weight + bias
            preactivations.append(z)
            if index < len(self.weights) - 1:
                activations.append(np.maximum(z, 0.0))
            else:
                activations.append(z)
        return activations[-1], activations, preactivations

    def _step(self, gradients_w: list[np.ndarray], gradients_b: list[np.ndarray], state: _AdamState) -> None:
        state.step += 1
        for i in range(len(self.weights)):
            gradients_w[i] = gradients_w[i] + self.weight_decay * self.weights[i]
            state.first[i] *= 0.9
            state.first[i] += 0.1 * gradients_w[i]
            state.second[i] *= 0.999
            state.second[i] += 0.001 * np.square(gradients_w[i])
            m = state.first[i] / (1.0 - 0.9 ** state.step)
            v = state.second[i] / (1.0 - 0.999 ** state.step)
            self.weights[i] -= self.learning_rate * m / (np.sqrt(v) + 1e-8)

            state.first[len(self.weights) + i] *= 0.9
            state.first[len(self.weights) + i] += 0.1 * gradients_b[i]
            state.second[len(self.weights) + i] *= 0.999
            state.second[len(self.weights) + i] += 0.001 * np.square(gradients_b[i])
            mb = state.first[len(self.weights) + i] / (1.0 - 0.9 ** state.step)
            vb = state.second[len(self.weights) + i] / (1.0 - 0.999 ** state.step)
            self.biases[i] -= self.learning_rate * mb / (np.sqrt(vb) + 1e-8)

    def fit(self, dataset: ArrayDataset) -> "_RawWindowModel":
        self._fit_scaler(dataset)
        output_shape = (dataset.config.horizon, len(dataset.channels))
        output_width = output_shape[0] * output_shape[1]
        assert self._input_width is not None
        self._output_shape = output_shape
        self._initialize(self._input_width, output_width)
        state = _AdamState(
            first=[np.zeros_like(p) for p in self.weights + self.biases],
            second=[np.zeros_like(p) for p in self.weights + self.biases],
        )

        self.n_train_windows = 0
        for _epoch in range(self.epochs):
            abs_sum = 0.0
            element_count = 0
            fit_windows = 0
            for batch in dataset.iter_batches("train", batch_size=self.batch_size, shuffle=True, seed=self.seed + _epoch):
                fit_windows += len(batch.origin_indices)
                raw = batch.inputs.flatten().astype(np.float32, copy=False)
                x = (raw - self.feature_mean) / self.feature_scale
                prediction, activations, preactivations = self._forward(x)
                target = batch.target.reshape(len(batch.origin_indices), -1).astype(np.float32, copy=False)
                if prediction.shape != target.shape or not np.isfinite(prediction).all():
                    raise ValueError("raw-window prediction shape/non-finite mismatch")
                abs_sum += float(np.abs(prediction - target).sum())
                element_count += int(target.size)
                grad = np.sign(prediction - target) / target.size
                gradients_w = [np.empty_like(w) for w in self.weights]
                gradients_b = [np.empty_like(b) for b in self.biases]
                for layer in range(len(self.weights) - 1, -1, -1):
                    gradients_w[layer] = activations[layer].T @ grad
                    gradients_b[layer] = grad.sum(axis=0)
                    if layer > 0:
                        grad = grad @ self.weights[layer].T
                        grad *= (preactivations[layer - 1] > 0.0)
                self._step(gradients_w, gradients_b, state)
            if element_count == 0:
                raise ValueError("no train windows available during raw-window fit")
            self.n_train_windows = fit_windows
            self.epoch_mae.append(abs_sum / element_count)
        return self

    def predict(self, batch: WindowBatch) -> np.ndarray:
        if not self.weights or self.feature_mean is None or self.feature_scale is None or self._output_shape is None:
            raise RuntimeError("raw-window model must be fitted before prediction")
        raw = batch.inputs.flatten().astype(np.float32, copy=False)
        if raw.shape[1] != self._input_width:
            raise ValueError("raw input width differs from fitted model")
        x = (raw - self.feature_mean) / self.feature_scale
        prediction, _, _ = self._forward(x)
        result = prediction.reshape((len(batch.origin_indices),) + self._output_shape)
        if not np.isfinite(result).all():
            raise ValueError("raw-window model produced non-finite predictions")
        return result

    def evaluate(self, dataset: ArrayDataset, split: str = "validation") -> dict:
        return evaluate_mae(self, dataset, split, batch_size=self.batch_size)


class RawWindowProbe(_RawWindowModel):
    """Linear raw-input probe; isolates what the readout can learn without an encoder."""

    def __init__(self, **kwargs) -> None:
        kwargs.pop("hidden_width", None)
        super().__init__(hidden_width=None, **kwargs)


class RawWindowMLP(_RawWindowModel):
    """One-hidden-layer nonlinear raw-input control with the same input information."""

    def __init__(self, *, hidden_width: int = 64, **kwargs) -> None:
        super().__init__(hidden_width=hidden_width, **kwargs)
