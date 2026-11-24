"""Minimal, auditable time-series JEPA and matched direct-MAE forecaster."""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass(frozen=True)
class JEPAConfig:
    input_channels: int
    seasonal_lags: int
    horizon: int = 60
    calendar_features: int = 4
    patch_size: int = 10
    d_model: int = 64
    n_heads: int = 4
    encoder_layers: int = 2
    predictor_layers: int = 1
    dropout: float = 0.0
    ema_start: float = 0.99
    ema_end: float = 0.999
    lambda_variance: float = 1.0
    lambda_covariance: float = 0.04

    def __post_init__(self):
        positive = (
            self.input_channels, self.seasonal_lags, self.horizon,
            self.patch_size, self.d_model, self.n_heads,
            self.encoder_layers, self.predictor_layers,
        )
        if any(type(value) is not int or value < 1 for value in positive):
            raise ValueError("model dimensions and layer counts must be positive integers")
        if self.calendar_features not in (0, 4):
            raise ValueError("calendar_features must be 0 or 4")
        if self.d_model % self.n_heads:
            raise ValueError("d_model must be divisible by n_heads")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must lie in [0, 1)")
        if not 0.0 <= self.ema_start <= self.ema_end <= 1.0:
            raise ValueError("EMA rates must satisfy 0 <= start <= end <= 1")
        if self.lambda_variance < 0 or self.lambda_covariance < 0:
            raise ValueError("anti-collapse weights must be non-negative")

    def to_dict(self) -> dict:
        return asdict(self)


def sinusoidal_positions(length: int, width: int, *, device, dtype) -> torch.Tensor:
    position = torch.arange(length, device=device, dtype=torch.float32).unsqueeze(1)
    div = torch.exp(
        torch.arange(0, width, 2, device=device, dtype=torch.float32)
        * (-math.log(10000.0) / width)
    )
    result = torch.zeros((1, length, width), device=device, dtype=torch.float32)
    result[0, :, 0::2] = torch.sin(position * div)
    if width > 1:
        result[0, :, 1::2] = torch.cos(position * div[:result[0, :, 1::2].shape[-1]])
    return result.to(dtype=dtype)


def patchify(sequence: torch.Tensor, patch_size: int) -> tuple[torch.Tensor, int]:
    """Non-overlapping time patches; pad only the final patch by repeating the last row."""
    if sequence.ndim != 3 or sequence.shape[1] < 1:
        raise ValueError("sequence must have shape [batch, time, features] and non-empty time")
    length = sequence.shape[1]
    pad = (-length) % patch_size
    if pad:
        sequence = torch.cat(
            (sequence, sequence[:, -1:, :].expand(-1, pad, -1)), dim=1
        )
    patches = sequence.unfold(1, patch_size, patch_size)
    patches = patches.permute(0, 1, 3, 2).contiguous()
    return patches.reshape(sequence.shape[0], -1, patch_size * sequence.shape[-1]), length


def unpatchify(patches: torch.Tensor, patch_size: int, channels: int, length: int) -> torch.Tensor:
    batch = patches.shape[0]
    values = patches.reshape(batch, patches.shape[1], patch_size, channels)
    return values.reshape(batch, -1, channels)[:, :length, :]


class PatchTransformerEncoder(nn.Module):
    def __init__(self, config: JEPAConfig):
        super().__init__()
        self.patch_size = config.patch_size
        self.input_projection = nn.Linear(
            config.patch_size * config.input_channels, config.d_model
        )
        layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.n_heads,
            dim_feedforward=4 * config.d_model,
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=config.encoder_layers)
        self.norm = nn.LayerNorm(config.d_model)

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        patches, _ = patchify(sequence, self.patch_size)
        tokens = self.input_projection(patches)
        tokens = tokens + sinusoidal_positions(
            tokens.shape[1], tokens.shape[2], device=tokens.device, dtype=tokens.dtype
        )
        return self.norm(self.encoder(tokens))


class FutureQueryEncoder(nn.Module):
    def __init__(self, config: JEPAConfig):
        super().__init__()
        self.patch_size = config.patch_size
        self.expected_features = (
            config.seasonal_lags * config.input_channels + config.calendar_features
        )
        self.projection = nn.Linear(
            config.patch_size * self.expected_features, config.d_model
        )
        self.norm = nn.LayerNorm(config.d_model)

    def forward(self, seasonal: torch.Tensor, calendar: torch.Tensor) -> torch.Tensor:
        if seasonal.ndim != 4:
            raise ValueError("seasonal must have shape [batch, horizon, lags, channels]")
        batch, horizon, lags, channels = seasonal.shape
        if calendar.ndim != 3 or calendar.shape[:2] != (batch, horizon):
            raise ValueError("calendar must align with batch and horizon")
        known = torch.cat((seasonal.reshape(batch, horizon, -1), calendar), dim=-1)
        if known.shape[-1] != self.expected_features:
            raise ValueError(
                f"future covariate width {known.shape[-1]} != configured {self.expected_features}"
            )
        patches, _ = patchify(known, self.patch_size)
        tokens = self.projection(patches)
        tokens = tokens + sinusoidal_positions(
            tokens.shape[1], tokens.shape[2], device=tokens.device, dtype=tokens.dtype
        )
        return self.norm(tokens)


class CrossAttentionPredictor(nn.Module):
    def __init__(self, config: JEPAConfig):
        super().__init__()
        layer = nn.TransformerDecoderLayer(
            d_model=config.d_model,
            nhead=config.n_heads,
            dim_feedforward=4 * config.d_model,
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.decoder = nn.TransformerDecoder(layer, num_layers=config.predictor_layers)
        self.norm = nn.LayerNorm(config.d_model)

    def forward(self, future_queries: torch.Tensor, context: torch.Tensor) -> torch.Tensor:
        # Future self-attention is allowed: all query covariates are known at origin.
        return self.norm(self.decoder(tgt=future_queries, memory=context))


class JEPAForecaster(nn.Module):
    """Context -> predictor -> future latents; EMA target encoder sees Y only."""

    def __init__(self, config: JEPAConfig):
        super().__init__()
        self.config = config
        self.context_encoder = PatchTransformerEncoder(config)
        self.target_encoder = copy.deepcopy(self.context_encoder)
        self.target_encoder.requires_grad_(False)
        self.target_encoder.eval()
        self.future_query_encoder = FutureQueryEncoder(config)
        self.predictor = CrossAttentionPredictor(config)

    def train(self, mode: bool = True):
        super().train(mode)
        self.target_encoder.eval()
        return self

    def predict_latents(
        self, x: torch.Tensor, seasonal: torch.Tensor, calendar: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        context = self.context_encoder(x)
        queries = self.future_query_encoder(seasonal, calendar)
        prediction = self.predictor(queries, context)
        return prediction, context

    @torch.no_grad()
    def encode_target(self, target: torch.Tensor) -> torch.Tensor:
        self.target_encoder.eval()
        return self.target_encoder(target)

    def forward_pretrain(
        self,
        x: torch.Tensor,
        seasonal: torch.Tensor,
        calendar: torch.Tensor,
        target: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        prediction, context = self.predict_latents(x, seasonal, calendar)
        target_latents = self.encode_target(target)
        if prediction.shape != target_latents.shape:
            raise ValueError(
                f"predicted/target latent shapes differ: {prediction.shape} vs {target_latents.shape}"
            )
        return {
            "prediction": prediction,
            "target": target_latents,
            "context": context,
        }

    @torch.no_grad()
    def update_target_encoder(self, step: int, total_steps: int) -> float:
        if total_steps < 1 or step < 0:
            raise ValueError("step and total_steps are invalid")
        progress = min(step / total_steps, 1.0)
        tau = self.config.ema_end - (
            self.config.ema_end - self.config.ema_start
        ) * (math.cos(math.pi * progress) + 1.0) / 2.0
        for target_param, online_param in zip(
            self.target_encoder.parameters(), self.context_encoder.parameters()
        ):
            target_param.mul_(tau).add_(online_param, alpha=1.0 - tau)
        for target_buffer, online_buffer in zip(
            self.target_encoder.buffers(), self.context_encoder.buffers()
        ):
            target_buffer.copy_(online_buffer)
        return float(tau)


def _vicreg_terms(latents: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    # Pool temporal patches per window; variance is measured across independent windows.
    pooled = latents.mean(dim=1)
    if pooled.shape[0] < 2:
        zero = pooled.new_zeros(())
        return zero, zero
    centered = pooled - pooled.mean(dim=0, keepdim=True)
    std = torch.sqrt(centered.var(dim=0, unbiased=False) + 1e-4)
    variance_loss = F.relu(1.0 - std).mean()
    covariance = centered.T @ centered / max(pooled.shape[0] - 1, 1)
    off_diagonal = covariance - torch.diag(torch.diag(covariance))
    covariance_loss = off_diagonal.square().sum() / pooled.shape[1]
    return variance_loss, covariance_loss


def jepa_loss(
    outputs: dict[str, torch.Tensor], config: JEPAConfig
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    latent = F.mse_loss(outputs["prediction"], outputs["target"].detach())
    ctx_var, ctx_cov = _vicreg_terms(outputs["context"])
    pred_var, pred_cov = _vicreg_terms(outputs["prediction"])
    variance = 0.5 * (ctx_var + pred_var)
    covariance = 0.5 * (ctx_cov + pred_cov)
    total = latent + config.lambda_variance * variance + config.lambda_covariance * covariance
    return total, {
        "total": total.detach(),
        "latent_mse": latent.detach(),
        "variance": variance.detach(),
        "covariance": covariance.detach(),
    }


@torch.no_grad()
def collapse_metrics(latents: torch.Tensor) -> dict[str, float]:
    pooled = latents.detach().mean(dim=1).to(torch.float64)
    if pooled.shape[0] < 2:
        raise ValueError("collapse metrics require at least two windows")
    centered = pooled - pooled.mean(dim=0, keepdim=True)
    std = centered.std(dim=0, unbiased=False)
    covariance = centered.T @ centered / max(pooled.shape[0] - 1, 1)
    eigenvalues = torch.linalg.eigvalsh(covariance).clamp_min(0.0)
    total = eigenvalues.sum()
    if float(total) <= 0.0:
        effective_rank = 0.0
    else:
        probabilities = eigenvalues / total
        positive = probabilities > 0
        entropy = -(probabilities[positive] * probabilities[positive].log()).sum()
        effective_rank = float(torch.exp(entropy))
    return {
        "stdZ": float(std.mean()),
        "std_min": float(std.min()),
        "std_median": float(std.median()),
        "std_max": float(std.max()),
        "effective_rank": effective_rank,
    }


class DirectMAEForecaster(nn.Module):
    """Matched context/query geometry with direct value-space L1 supervision."""

    def __init__(self, config: JEPAConfig):
        super().__init__()
        self.config = config
        self.context_encoder = PatchTransformerEncoder(config)
        self.future_query_encoder = FutureQueryEncoder(config)
        self.predictor = CrossAttentionPredictor(config)
        self.value_head = nn.Linear(
            config.d_model, config.patch_size * config.input_channels
        )

    def forward(
        self, x: torch.Tensor, seasonal: torch.Tensor, calendar: torch.Tensor
    ) -> torch.Tensor:
        context = self.context_encoder(x)
        queries = self.future_query_encoder(seasonal, calendar)
        predicted_latents = self.predictor(queries, context)
        patches = self.value_head(predicted_latents)
        return unpatchify(
            patches, self.config.patch_size, self.config.input_channels,
            seasonal.shape[1],
        )

    def loss(
        self, prediction: torch.Tensor, target: torch.Tensor
    ) -> torch.Tensor:
        if prediction.shape != target.shape:
            raise ValueError("direct-MAE prediction and target shapes differ")
        return F.l1_loss(prediction, target)



class FrozenContextProbe(nn.Module):
    """Shared linear forecast readout over a frozen context representation and known covariates."""

    def __init__(self, backbone: JEPAForecaster, config: JEPAConfig):
        super().__init__()
        if backbone.config != config:
            raise ValueError("probe config must match frozen backbone config")
        self.config = config
        self.backbone = backbone
        self.backbone.requires_grad_(False)
        self.backbone.eval()
        feature_width = (
            config.d_model
            + config.seasonal_lags * config.input_channels
            + config.calendar_features
            + 4
        )
        self.readout = nn.Linear(feature_width, config.input_channels)

    def train(self, mode: bool = True):
        super().train(mode)
        self.backbone.eval()
        return self

    def forward(
        self, x: torch.Tensor, seasonal: torch.Tensor, calendar: torch.Tensor
    ) -> torch.Tensor:
        batch, horizon = seasonal.shape[:2]
        with torch.no_grad():
            context = self.backbone.context_encoder(x)[:, -1, :]
        context = context.unsqueeze(1).expand(-1, horizon, -1)
        known = torch.cat((seasonal.reshape(batch, horizon, -1), calendar), dim=-1)
        step = torch.arange(horizon, device=x.device, dtype=x.dtype) / max(horizon, 1)
        angle = 2.0 * math.pi * step
        position = torch.stack(
            (torch.sin(angle), torch.cos(angle), torch.sin(2 * angle), torch.cos(2 * angle)),
            dim=-1,
        ).unsqueeze(0).expand(batch, -1, -1)
        return self.readout(torch.cat((context, known, position), dim=-1))

    def loss(self, prediction: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if prediction.shape != target.shape:
            raise ValueError("frozen-context probe prediction and target shapes differ")
        return F.l1_loss(prediction, target)


def trainable_parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def total_parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())
