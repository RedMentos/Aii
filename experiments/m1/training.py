"""Deterministic train/evaluate/checkpoint helpers for M1 torch models."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import torch

from .array_data import ArrayDataset
from .jepa import DirectMAEForecaster, JEPAConfig, JEPAForecaster, jepa_loss




def build_seeded_model(model_factory, config, seed: int, **kwargs):
    """Construct a model with deterministic CPU initialization without leaking RNG state."""
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        return model_factory(config, **kwargs)



def current_git_commit(repo_root: str | Path | None = None) -> str:
    """Resolve the executing repository HEAD; never read the expected hash from preregistration."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("git rev-parse HEAD did not return a full lowercase commit SHA")
    return commit



def _batch_tensors(batch, device):
    return (
        torch.as_tensor(batch.inputs.x, dtype=torch.float32, device=device),
        torch.as_tensor(batch.inputs.seasonal, dtype=torch.float32, device=device),
        torch.as_tensor(batch.inputs.calendar, dtype=torch.float32, device=device),
        torch.as_tensor(batch.target, dtype=torch.float32, device=device),
    )


def _validate_model_dataset(config: JEPAConfig, dataset: ArrayDataset) -> None:
    if config.input_channels != len(dataset.channels):
        raise ValueError("model input_channels does not match dataset channels")
    if config.seasonal_lags != len(dataset.config.seasonal_lags):
        raise ValueError("model seasonal_lags does not match dataset")
    if config.horizon != dataset.config.horizon:
        raise ValueError("model horizon does not match dataset")
    expected_calendar = 4 if dataset.config.include_calendar else 0
    if config.calendar_features != expected_calendar:
        raise ValueError("model calendar_features does not match dataset")


def train_jepa(
    model: JEPAForecaster,
    dataset: ArrayDataset,
    *,
    epochs: int = 5,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    seed: int = 17,
    device: str = "cpu",
    max_grad_norm: float = 1.0,
) -> list[dict[str, float]]:
    """Train a preconstructed model; use build_seeded_model to seed its initialization."""
    if type(epochs) is not int or epochs < 1:
        raise ValueError("epochs must be a positive integer")
    if type(batch_size) is not int or batch_size < 2:
        raise ValueError("batch_size must be an integer >= 2 for anti-collapse training")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if not np.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning_rate must be finite and positive")
    if not np.isfinite(weight_decay) or weight_decay < 0:
        raise ValueError("weight_decay must be finite and non-negative")
    _validate_model_dataset(model.config, dataset)
    torch.manual_seed(seed)
    if torch.cuda.is_available() and str(device).startswith("cuda"):
        torch.cuda.manual_seed_all(seed)
    model.to(device)
    model.scaler.fit(dataset)
    model.train()
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=learning_rate,
        weight_decay=weight_decay,
    )
    planned_steps = [
        sum(1 for _ in dataset.iter_batches(
            "train", batch_size=batch_size, shuffle=True, seed=seed + epoch
        ))
        for epoch in range(epochs)
    ]
    if any(steps < 1 for steps in planned_steps):
        raise ValueError("no accepted train batches")
    total_steps = sum(planned_steps)
    global_step = 0
    history: list[dict[str, float]] = []

    for epoch in range(epochs):
        totals = {"total": 0.0, "latent_mse": 0.0, "variance": 0.0, "covariance": 0.0}
        batches = 0
        windows = 0
        for batch in dataset.iter_batches(
            "train", batch_size=batch_size, shuffle=True, seed=seed + epoch
        ):
            x, seasonal, calendar, target = _batch_tensors(batch, device)
            optimizer.zero_grad(set_to_none=True)
            outputs = model.forward_pretrain(x, seasonal, calendar, target)
            loss, components = jepa_loss(outputs, model.config)
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite JEPA loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                [parameter for parameter in model.parameters() if parameter.requires_grad],
                max_grad_norm,
            )
            optimizer.step()
            global_step += 1
            tau = model.update_target_encoder(global_step, total_steps)
            count = len(batch.origin_indices)
            for key in totals:
                totals[key] += float(components[key]) * count
            windows += count
            batches += 1
        if batches == 0:
            raise ValueError("no accepted train batches in epoch")
        if batches != planned_steps[epoch]:
            raise RuntimeError("train batch stream changed after EMA schedule planning")
        history.append({
            "epoch": float(epoch + 1),
            **{key: value / windows for key, value in totals.items()},
            "ema_tau": float(tau),
            "steps": float(batches),
            "windows": float(windows),
        })
    return history


def train_direct_mae(
    model,
    dataset: ArrayDataset,
    *,
    epochs: int = 5,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    seed: int = 17,
    device: str = "cpu",
    max_grad_norm: float = 1.0,
) -> list[dict[str, float]]:
    if type(epochs) is not int or epochs < 1:
        raise ValueError("epochs must be a positive integer")
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    _validate_model_dataset(model.config, dataset)
    torch.manual_seed(seed)
    model.to(device)
    if not bool(model.scaler.fitted):
        model.scaler.fit(dataset)
    model.train()
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    history = []
    for epoch in range(epochs):
        total = 0.0
        windows = 0
        for batch in dataset.iter_batches(
            "train", batch_size=batch_size, shuffle=True, seed=seed + epoch
        ):
            x, seasonal, calendar, target = _batch_tensors(batch, device)
            optimizer.zero_grad(set_to_none=True)
            prediction = model(x, seasonal, calendar)
            loss = model.loss(prediction, target)
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite direct-MAE loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
            optimizer.step()
            total += float(loss.detach()) * len(batch.origin_indices)
            windows += len(batch.origin_indices)
        if not windows:
            raise ValueError("no accepted train windows")
        history.append({"epoch": float(epoch + 1), "mae": total / windows})
    return history


def train_raw_gru(model, dataset: ArrayDataset, **kwargs) -> list[dict[str, float]]:
    """Train the Raw-GRU control with the same raw-unit MAE loop as Direct-MAE."""
    return train_direct_mae(model, dataset, **kwargs)



def train_frozen_probe(
    model,
    dataset: ArrayDataset,
    *,
    epochs: int = 5,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    seed: int = 17,
    device: str = "cpu",
    max_grad_norm: float = 1.0,
) -> list[dict[str, float]]:
    """Fit only the linear value head; the pretrained/random backbone stays frozen."""
    if type(epochs) is not int or epochs < 1:
        raise ValueError("epochs must be a positive integer")
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    _validate_model_dataset(model.config, dataset)
    if any(parameter.requires_grad for parameter in model.encoder.parameters()):
        raise ValueError("frozen probe encoder unexpectedly has trainable parameters")
    model.scaler.fit(dataset)
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable:
        raise ValueError("frozen probe has no trainable readout parameters")
    torch.manual_seed(seed)
    model.to(device)
    model.train()
    optimizer = torch.optim.AdamW(
        trainable, lr=learning_rate, weight_decay=weight_decay
    )
    history = []
    for epoch in range(epochs):
        total = 0.0
        windows = 0
        for batch in dataset.iter_batches(
            "train", batch_size=batch_size, shuffle=True, seed=seed + epoch
        ):
            x, seasonal, calendar, target = _batch_tensors(batch, device)
            optimizer.zero_grad(set_to_none=True)
            prediction = model(x, seasonal, calendar)
            loss = model.loss(prediction, target)
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite frozen-probe loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, max_grad_norm)
            optimizer.step()
            count = len(batch.origin_indices)
            total += float(loss.detach()) * count
            windows += count
        if not windows:
            raise ValueError("no accepted train windows")
        history.append({"epoch": float(epoch + 1), "mae": total / windows})
    return history



@torch.no_grad()
def evaluate_direct_mae(
    model,
    dataset: ArrayDataset,
    split: str = "validation",
    *,
    batch_size: int = 256,
    device: str = "cpu",
) -> float:
    _validate_model_dataset(model.config, dataset)
    model.to(device)
    if hasattr(model, "scaler") and not bool(model.scaler.fitted):
        raise ValueError("model scaler must be fitted on train before evaluation")
    model.eval()
    absolute_sum = 0.0
    elements = 0
    for batch in dataset.iter_batches(split, batch_size=batch_size):
        x, seasonal, calendar, target = _batch_tensors(batch, device)
        prediction = model(x, seasonal, calendar)
        absolute_sum += float(torch.abs(prediction - target).sum())
        elements += target.numel()
    if elements == 0:
        raise ValueError(f"no accepted windows in split {split}")
    return absolute_sum / elements



def _collapse_moments():
    return {"n": 0, "sum": None, "cross": None}


def _update_collapse_moments(state: dict, latents: torch.Tensor) -> None:
    pooled = latents.detach().mean(dim=1).to(torch.float64).cpu().numpy()
    if state["sum"] is None:
        width = pooled.shape[1]
        state["sum"] = np.zeros(width, dtype=np.float64)
        state["cross"] = np.zeros((width, width), dtype=np.float64)
    state["sum"] += pooled.sum(axis=0)
    state["cross"] += pooled.T @ pooled
    state["n"] += pooled.shape[0]


def _finish_collapse_moments(state: dict) -> dict[str, float]:
    n = state["n"]
    if n < 2:
        raise ValueError("collapse telemetry requires at least two validation windows")
    mean = state["sum"] / n
    covariance = (state["cross"] - n * np.outer(mean, mean)) / (n - 1)
    covariance = 0.5 * (covariance + covariance.T)
    std = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    eigenvalues = np.maximum(np.linalg.eigvalsh(covariance), 0.0)
    total = float(eigenvalues.sum())
    if total <= 0.0:
        effective_rank = 0.0
    else:
        probabilities = eigenvalues[eigenvalues > 0] / total
        effective_rank = float(np.exp(-(probabilities * np.log(probabilities)).sum()))
    return {
        "stdZ": float(std.mean()),
        "std_min": float(std.min()),
        "std_median": float(np.median(std)),
        "std_max": float(std.max()),
        "effective_rank": effective_rank,
    }


@torch.no_grad()
def evaluate_jepa(
    model: JEPAForecaster,
    dataset: ArrayDataset,
    split: str = "validation",
    *,
    batch_size: int = 256,
    device: str = "cpu",
) -> dict:
    """Stream latent loss and context/target collapse telemetry without storing all embeddings."""
    _validate_model_dataset(model.config, dataset)
    model.to(device)
    if not bool(model.scaler.fitted):
        raise ValueError("JEPA scaler must be fitted on train before evaluation")
    model.eval()
    squared_error = 0.0
    elements = 0
    windows = 0
    context_state = _collapse_moments()
    target_state = _collapse_moments()
    for batch in dataset.iter_batches(split, batch_size=batch_size):
        x, seasonal, calendar, target = _batch_tensors(batch, device)
        outputs = model.forward_pretrain(x, seasonal, calendar, target)
        squared_error += float(torch.square(outputs["prediction"] - outputs["target"]).sum())
        elements += outputs["target"].numel()
        windows += len(batch.origin_indices)
        _update_collapse_moments(context_state, outputs["context"])
        _update_collapse_moments(target_state, outputs["target"])
    if not elements:
        raise ValueError(f"no accepted windows in split {split}")
    return {
        "split": split,
        "n_windows": windows,
        "latent_mse": squared_error / elements,
        "context_collapse": _finish_collapse_moments(context_state),
        "target_collapse": _finish_collapse_moments(target_state),
    }


class TorchBatchPredictor:
    """Adapter so trained torch forecasters can use the common NumPy metric suite."""

    def __init__(self, model, *, name: str, device: str = "cpu"):
        self.model = model
        self.name = name
        self.device = device
        self.model.to(device)
        scaler = getattr(model, "scaler", None)
        if scaler is not None and not bool(scaler.fitted):
            raise ValueError("model scaler must be fitted on train before prediction")
        self.model.eval()

    @torch.no_grad()
    def predict(self, batch):
        self.model.eval()
        x, seasonal, calendar, _ = _batch_tensors(batch, self.device)
        return self.model(x, seasonal, calendar).detach().cpu().numpy()



def save_checkpoint_atomic(
    model: torch.nn.Module,
    config: JEPAConfig,
    path: str | Path,
    *,
    code_commit: str,
    metadata: dict | None = None,
) -> str:
    import hashlib
    import re

    if not re.fullmatch(r"[0-9a-f]{40}", code_commit):
        raise ValueError("code_commit must be a 40-character lowercase git SHA")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "m1.clean-room.torch-checkpoint.v1",
        "code_commit": code_commit,
        "config": config.to_dict(),
        "state_dict": model.state_dict(),
        "metadata": metadata or {},
    }
    fd, temporary = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            torch.save(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return digest


def load_checkpoint(
    model: torch.nn.Module,
    config: JEPAConfig,
    path: str | Path,
    *,
    expected_code_commit: str,
    map_location: str = "cpu",
) -> dict:
    import re

    if not re.fullmatch(r"[0-9a-f]{40}", expected_code_commit):
        raise ValueError("expected_code_commit must be a verified git SHA")
    payload = torch.load(path, map_location=map_location, weights_only=True)
    if payload.get("schema") != "m1.clean-room.torch-checkpoint.v1":
        raise ValueError("unsupported checkpoint schema")
    if payload.get("code_commit") != expected_code_commit:
        raise ValueError("checkpoint code_commit does not match executing commit")
    if payload.get("config") != config.to_dict():
        raise ValueError("checkpoint config mismatch")
    model.load_state_dict(payload["state_dict"], strict=True)
    return dict(payload.get("metadata", {}))
