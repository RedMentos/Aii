"""Bounded-batch M1 training and validation routines.

These routines only consume train/validation splits. They never request the test
split; test access remains owned by the preregistration gate in ArrayDataset.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import math
import torch
from torch import Tensor, nn
import torch.nn.functional as F

from .array_data import ArrayDataset, InputBundle, WindowBatch
from .base import (
    DirectMAE,
    FrozenRepresentationProbe,
    M1JEPA,
    VICRegControl,
    variance_covariance_regularizer,
    vicreg_loss,
)


@dataclass(frozen=True)
class FitConfig:
    epochs: int = 20
    batch_size: int = 256
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    patience: int = 4
    min_delta: float = 1e-5
    gradient_clip_norm: float = 1.0
    collapse_weight: float = 0.05

    def __post_init__(self) -> None:
        if self.epochs < 1 or self.batch_size < 1 or self.patience < 1:
            raise ValueError("epochs, batch_size and patience must be positive")
        if not math.isfinite(self.learning_rate) or not math.isfinite(self.weight_decay) or self.learning_rate <= 0 or self.weight_decay < 0:
            raise ValueError("invalid optimizer settings")
        if not math.isfinite(self.gradient_clip_norm) or not math.isfinite(self.collapse_weight) or not math.isfinite(self.min_delta) or self.gradient_clip_norm <= 0 or self.collapse_weight < 0 or self.min_delta < 0:
            raise ValueError("invalid gradient or regularizer setting")


@dataclass(frozen=True)
class FitReport:
    best_epoch: int
    epochs_run: int
    best_validation_score: float
    validation_metric: str
    final_training_loss: float
    optimizer_steps: int


def _torch_bundle(batch: WindowBatch, device: torch.device) -> InputBundle:
    return InputBundle(
        x=torch.as_tensor(batch.inputs.x, device=device, dtype=torch.float32),
        seasonal=torch.as_tensor(batch.inputs.seasonal, device=device, dtype=torch.float32),
        calendar=torch.as_tensor(batch.inputs.calendar, device=device, dtype=torch.float32),
    )


def _torch_target(batch: WindowBatch, device: torch.device) -> Tensor:
    return torch.as_tensor(batch.target, device=device, dtype=torch.float32)


@torch.no_grad()
def evaluate_mae(
    model: nn.Module,
    dataset: ArrayDataset,
    *,
    split: str = "validation",
    batch_size: int = 256,
    device: str | torch.device = "cpu",
) -> float:
    target_device = torch.device(device)
    model.to(target_device)
    model.eval()
    absolute_sum = 0.0
    element_count = 0
    for batch in dataset.iter_batches(split, batch_size=batch_size):
        bundle = _torch_bundle(batch, target_device)
        target = _torch_target(batch, target_device)
        prediction = model(bundle)
        absolute_sum += float(torch.abs(prediction - target).sum().item())
        element_count += target.numel()
    if element_count == 0:
        raise ValueError(f"no valid windows available in {split} split")
    return absolute_sum / element_count


def _fit_supervised(
    model: nn.Module,
    dataset: ArrayDataset,
    config: FitConfig,
    *,
    device: str | torch.device,
    probe_only: bool,
    objective: str = "mae",
    l2_penalty: float = 0.0,
) -> FitReport:
    if objective not in {"mae", "mse"} or not math.isfinite(l2_penalty) or l2_penalty < 0:
        raise ValueError("objective must be mae or mse and l2_penalty must be non-negative")
    if l2_penalty and not hasattr(model, "linear"):
        raise ValueError("explicit L2 coefficient penalty requires a linear baseline")
    target_device = torch.device(device)
    model.to(target_device)
    if probe_only:
        model.encoder.requires_grad_(False)
        parameters = [p for p in model.readout.parameters() if p.requires_grad]
    else:
        parameters = [p for p in model.parameters() if p.requires_grad]
    if not parameters:
        raise ValueError("no trainable parameters")
    optimizer = torch.optim.AdamW(
        parameters, lr=config.learning_rate, weight_decay=(0.0 if l2_penalty else config.weight_decay)
    )
    best_state = None
    best_validation = float("inf")
    best_epoch = 0
    stale_epochs = 0
    optimizer_steps = 0
    final_loss = float("nan")
    epochs_run = 0

    for epoch in range(1, config.epochs + 1):
        model.train()
        loss_sum = 0.0
        batches = 0
        for batch in dataset.iter_batches("train", batch_size=config.batch_size):
            bundle = _torch_bundle(batch, target_device)
            target = _torch_target(batch, target_device)
            optimizer.zero_grad(set_to_none=True)
            prediction = model(bundle)
            loss = F.l1_loss(prediction, target) if objective == "mae" else F.mse_loss(prediction, target)
            if l2_penalty:
                loss = loss + l2_penalty * model.linear.weight.square().sum()
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite supervised baseline loss")
            loss.backward()
            nn.utils.clip_grad_norm_(parameters, config.gradient_clip_norm)
            optimizer.step()
            optimizer_steps += 1
            loss_sum += float(loss.detach().item())
            batches += 1
        if not batches:
            raise ValueError("no valid training windows")
        final_loss = loss_sum / batches
        validation = evaluate_mae(
            model, dataset, split="validation",
            batch_size=config.batch_size, device=target_device,
        )
        epochs_run = epoch
        if validation < best_validation - config.min_delta:
            best_validation = validation
            best_epoch = epoch
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= config.patience:
                break

    if best_state is None:
        raise RuntimeError("training did not produce a finite validation checkpoint")
    model.load_state_dict(best_state)
    return FitReport(
        best_epoch=best_epoch,
        epochs_run=epochs_run,
        best_validation_score=best_validation,
        validation_metric="MAE",
        final_training_loss=final_loss,
        optimizer_steps=optimizer_steps,
    )


def fit_supervised_baseline(
    model: nn.Module,
    dataset: ArrayDataset,
    config: FitConfig = FitConfig(),
    *,
    objective: str = "mae",
    l2_penalty: float = 0.0,
    device: str | torch.device = "cpu",
) -> FitReport:
    """Fit a baseline from bounded train batches; select checkpoints by validation MAE.

    Use objective='mse' and explicit L2 for conventional Ridge-AR; use objective='mae'
    plus L2 for LAD/L1-AR. These objectives are intentionally labelled separately.
    """
    return _fit_supervised(
        model, dataset, config, device=device, probe_only=False,
        objective=objective, l2_penalty=l2_penalty,
    )


def fit_direct_mae(
    model: DirectMAE,
    dataset: ArrayDataset,
    config: FitConfig = FitConfig(),
    *,
    device: str | torch.device = "cpu",
) -> FitReport:
    """Train the direct raw-target MAE control using train/validation only."""
    return _fit_supervised(model, dataset, config, device=device, probe_only=False)


def fit_frozen_probe(
    model: FrozenRepresentationProbe,
    dataset: ArrayDataset,
    config: FitConfig = FitConfig(),
    *,
    device: str | torch.device = "cpu",
) -> FitReport:
    """Fit only the MAE readout; the copied JEPA representation remains frozen."""
    return _fit_supervised(model, dataset, config, device=device, probe_only=True)


def fit_jepa(
    model: M1JEPA,
    dataset: ArrayDataset,
    config: FitConfig = FitConfig(),
    *,
    device: str | torch.device = "cpu",
) -> FitReport:
    """Train context encoder + predictor; update target encoder by EMA each step."""
    target_device = torch.device(device)
    model.to(target_device)
    parameters = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(
        parameters, lr=config.learning_rate, weight_decay=config.weight_decay
    )
    best_state = None
    best_validation = float("inf")
    best_epoch = 0
    stale_epochs = 0
    optimizer_steps = 0
    final_loss = float("nan")
    epochs_run = 0

    for epoch in range(1, config.epochs + 1):
        model.train()
        loss_sum = 0.0
        batches = 0
        for batch in dataset.iter_batches("train", batch_size=config.batch_size):
            bundle = _torch_bundle(batch, target_device)
            future = _torch_target(batch, target_device)
            optimizer.zero_grad(set_to_none=True)
            output = model(bundle, future)
            prediction_loss = model.latent_prediction_loss(output)
            anti_collapse = variance_covariance_regularizer(output["context"])
            loss = prediction_loss + config.collapse_weight * anti_collapse
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite JEPA objective")
            loss.backward()
            nn.utils.clip_grad_norm_(parameters, config.gradient_clip_norm)
            optimizer.step()
            model.update_target_encoder()
            optimizer_steps += 1
            loss_sum += float(loss.detach().item())
            batches += 1
        if not batches:
            raise ValueError("no valid training windows")
        final_loss = loss_sum / batches

        # This validation score is latent prediction loss, not forecasting MAE.
        model.eval()
        val_sum = 0.0
        val_batches = 0
        with torch.no_grad():
            for batch in dataset.iter_batches("validation", batch_size=config.batch_size):
                output = model(_torch_bundle(batch, target_device), _torch_target(batch, target_device))
                val_loss = model.latent_prediction_loss(output)
                if not torch.isfinite(val_loss):
                    raise FloatingPointError("non-finite JEPA validation loss")
                val_sum += float(val_loss.item())
                val_batches += 1
        if not val_batches:
            raise ValueError("no valid validation windows")
        validation = val_sum / val_batches
        epochs_run = epoch
        if validation < best_validation - config.min_delta:
            best_validation = validation
            best_epoch = epoch
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= config.patience:
                break

    if best_state is None:
        raise RuntimeError("JEPA training did not produce a finite validation checkpoint")
    model.load_state_dict(best_state)
    return FitReport(
        best_epoch=best_epoch,
        epochs_run=epochs_run,
        best_validation_score=best_validation,
        validation_metric="latent_prediction_L1",
        final_training_loss=final_loss,
        optimizer_steps=optimizer_steps,
    )


def _augment_bundle(
    bundle: InputBundle,
    *,
    generator: torch.Generator,
    noise_std: float,
    channel_drop_probability: float,
) -> InputBundle:
    x = torch.as_tensor(bundle.x)
    seasonal = torch.as_tensor(bundle.seasonal, device=x.device, dtype=x.dtype)
    calendar = torch.as_tensor(bundle.calendar, device=x.device, dtype=x.dtype)
    if not 0.0 <= channel_drop_probability < 1.0 or not math.isfinite(noise_std) or noise_std < 0:
        raise ValueError("invalid VICReg view augmentation settings")
    batch, _, channels = x.shape
    keep = (
        torch.rand((batch, 1, channels), device=x.device, generator=generator)
        >= channel_drop_probability
    ).to(dtype=x.dtype)
    if channel_drop_probability:
        keep = keep / (1.0 - channel_drop_probability)
    x_noise = torch.randn(x.shape, device=x.device, dtype=x.dtype, generator=generator)
    s_noise = torch.randn(seasonal.shape, device=x.device, dtype=x.dtype, generator=generator)
    return InputBundle(
        x=(x + noise_std * x_noise) * keep,
        seasonal=(seasonal + noise_std * s_noise) * keep[:, None, :, :],
        calendar=calendar,
    )


def fit_vicreg_control(
    model: VICRegControl,
    dataset: ArrayDataset,
    config: FitConfig = FitConfig(),
    *,
    noise_std: float = 0.01,
    channel_drop_probability: float = 0.05,
    random_seed: int = 20261123,
    device: str | torch.device = "cpu",
) -> FitReport:
    """Train the explicit VICReg control on two augmented train views; validate separately."""
    if not math.isfinite(noise_std) or noise_std < 0:
        raise ValueError("noise_std must be finite and non-negative")
    if not 0.0 <= channel_drop_probability < 1.0:
        raise ValueError("channel_drop_probability must be in [0, 1)")
    target_device = torch.device(device)
    model.to(target_device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )
    best_state = None
    best_validation = float("inf")
    best_epoch = 0
    stale_epochs = 0
    optimizer_steps = 0
    final_loss = float("nan")
    epochs_run = 0

    for epoch in range(1, config.epochs + 1):
        model.train()
        generator = torch.Generator(device=target_device)
        generator.manual_seed(random_seed + epoch)
        loss_sum = 0.0
        batches = 0
        for batch in dataset.iter_batches("train", batch_size=config.batch_size):
            base = _torch_bundle(batch, target_device)
            first = _augment_bundle(
                base, generator=generator, noise_std=noise_std,
                channel_drop_probability=channel_drop_probability,
            )
            second = _augment_bundle(
                base, generator=generator, noise_std=noise_std,
                channel_drop_probability=channel_drop_probability,
            )
            optimizer.zero_grad(set_to_none=True)
            z1, z2 = model(first, second)
            loss = vicreg_loss(z1, z2)
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite VICReg objective")
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip_norm)
            optimizer.step()
            optimizer_steps += 1
            loss_sum += float(loss.detach().item())
            batches += 1
        if not batches:
            raise ValueError("no valid training windows")
        final_loss = loss_sum / batches

        model.eval()
        val_generator = torch.Generator(device=target_device)
        val_generator.manual_seed(random_seed)
        val_sum = 0.0
        val_batches = 0
        with torch.no_grad():
            for batch in dataset.iter_batches("validation", batch_size=config.batch_size):
                base = _torch_bundle(batch, target_device)
                first = _augment_bundle(
                    base, generator=val_generator, noise_std=noise_std,
                    channel_drop_probability=channel_drop_probability,
                )
                second = _augment_bundle(
                    base, generator=val_generator, noise_std=noise_std,
                    channel_drop_probability=channel_drop_probability,
                )
                z1, z2 = model(first, second)
                score = vicreg_loss(z1, z2)
                if not torch.isfinite(score):
                    raise FloatingPointError("non-finite VICReg validation objective")
                val_sum += float(score.item())
                val_batches += 1
        if not val_batches:
            raise ValueError("no valid validation windows")
        validation = val_sum / val_batches
        epochs_run = epoch
        if validation < best_validation - config.min_delta:
            best_validation = validation
            best_epoch = epoch
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= config.patience:
                break

    if best_state is None:
        raise RuntimeError("VICReg training did not produce a finite validation checkpoint")
    model.load_state_dict(best_state)
    return FitReport(
        best_epoch=best_epoch,
        epochs_run=epochs_run,
        best_validation_score=best_validation,
        validation_metric="VICReg_objective",
        final_training_loss=final_loss,
        optimizer_steps=optimizer_steps,
    )
