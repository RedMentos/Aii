"""M1 shared-weight JEPA base architecture.

The context and target views use the same token encoder shape. Context consumes
X, seasonal values and forecast-calendar tokens; the target view consumes only
the future observed channel sequence. The target encoder is an EMA copy of the
context encoder, not a permanently frozen teacher.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
import math

import torch
from torch import Tensor, nn
import torch.nn.functional as F

from .array_data import InputBundle


@dataclass(frozen=True)
class BaseConfig:
    channels: int
    horizon: int
    latent_dim: int = 128
    hidden_dim: int = 256
    predictor_steps: int = 1
    predictor_kind: str = "shared"
    ema_decay: float = 0.996

    def __post_init__(self) -> None:
        if min(self.channels, self.horizon, self.latent_dim, self.hidden_dim) < 1:
            raise ValueError("channel, horizon and model dimensions must be positive")
        if self.predictor_steps not in (1, 2, 4):
            raise ValueError("predictor_steps must be one of the preregistered values 1, 2, 4")
        if self.predictor_kind not in {"shared", "unshared"}:
            raise ValueError("predictor_kind must be shared or unshared")
        if not 0.0 <= self.ema_decay < 1.0:
            raise ValueError("ema_decay must be in [0, 1)")


def _position_encoding(length: int, width: int, *, device: torch.device, dtype: torch.dtype) -> Tensor:
    """Sinusoidal position features; O(length * width), no learned max-length table."""
    position = torch.arange(length, device=device, dtype=torch.float32).unsqueeze(1)
    div = torch.exp(
        torch.arange(0, width, 2, device=device, dtype=torch.float32)
        * (-math.log(10000.0) / width)
    )
    encoding = torch.zeros((length, width), device=device, dtype=torch.float32)
    encoding[:, 0::2] = torch.sin(position * div)
    if width > 1:
        encoding[:, 1::2] = torch.cos(position * div[: encoding[:, 1::2].shape[1]])
    return encoding.to(dtype=dtype).unsqueeze(0)


class SharedTokenEncoder(nn.Module):
    """Linear-time token pooling shared by context and future-target views.

    No quadratic self-attention over the 10k-minute input window: token
    projections and learned pooling are O(number_of_tokens * latent_dim).
    """

    TYPE_X = 0
    TYPE_SEASONAL = 1
    TYPE_CALENDAR = 2
    TYPE_TARGET = 3

    def __init__(self, channels: int, latent_dim: int):
        super().__init__()
        self.channel_projection = nn.Linear(channels, latent_dim)
        self.calendar_projection = nn.Linear(4, latent_dim)
        self.type_embedding = nn.Embedding(4, latent_dim)
        self.pool_score = nn.Linear(latent_dim, 1, bias=False)
        self.output_norm = nn.LayerNorm(latent_dim)

    def _pool(self, values: Tensor, type_id: int) -> Tensor:
        if values.ndim != 3:
            raise ValueError("token values must have shape [batch, sequence, features]")
        length = values.shape[1]
        tokens = self.channel_projection(values)
        tokens = tokens + self.type_embedding.weight[type_id].view(1, 1, -1)
        tokens = tokens + _position_encoding(
            length, tokens.shape[-1], device=tokens.device, dtype=tokens.dtype
        )
        weights = torch.softmax(self.pool_score(torch.tanh(tokens)).squeeze(-1), dim=1)
        return torch.sum(tokens * weights.unsqueeze(-1), dim=1)

    def encode_context(self, bundle: InputBundle) -> Tensor:
        device = self.channel_projection.weight.device
        dtype = self.channel_projection.weight.dtype
        x = torch.as_tensor(bundle.x, device=device, dtype=dtype)
        seasonal = torch.as_tensor(bundle.seasonal, device=device, dtype=dtype)
        calendar = torch.as_tensor(bundle.calendar, device=device, dtype=dtype)
        if x.ndim != 3 or x.shape[-1] != self.channel_projection.in_features:
            raise ValueError("X must be [batch, input_length, channels]")
        if seasonal.ndim != 4 or seasonal.shape[0] != x.shape[0] or seasonal.shape[-1] != x.shape[-1]:
            raise ValueError("seasonal values must be [batch, horizon, lags, channels]")
        if calendar.ndim != 3 or calendar.shape[:2] != seasonal.shape[:2] or calendar.shape[-1] not in (0, 4):
            raise ValueError("calendar must be [batch, horizon, 4] or zero-width when disabled")
        x_pool = self._pool(x, self.TYPE_X)
        seasonal_tokens = seasonal.reshape(seasonal.shape[0], -1, seasonal.shape[-1])
        seasonal_pool = self._pool(seasonal_tokens, self.TYPE_SEASONAL)
        if calendar.shape[-1] == 4:
            cal = self.calendar_projection(calendar)
            cal = cal + self.type_embedding.weight[self.TYPE_CALENDAR].view(1, 1, -1)
            cal = cal + _position_encoding(
                cal.shape[1], cal.shape[-1], device=cal.device, dtype=cal.dtype
            )
            cal_weights = torch.softmax(self.pool_score(torch.tanh(cal)).squeeze(-1), dim=1)
            calendar_pool = torch.sum(cal * cal_weights.unsqueeze(-1), dim=1)
            combined = (x_pool + seasonal_pool + calendar_pool) / math.sqrt(3.0)
        else:
            combined = (x_pool + seasonal_pool) / math.sqrt(2.0)
        return self.output_norm(combined)

    def encode_target(self, target: Tensor) -> Tensor:
        target = torch.as_tensor(
            target, device=self.channel_projection.weight.device,
            dtype=self.channel_projection.weight.dtype,
        )
        if target.ndim != 3 or target.shape[-1] != self.channel_projection.in_features:
            raise ValueError("target must be [batch, horizon, channels]")
        return self.output_norm(self._pool(target, self.TYPE_TARGET))


class PredictorF(nn.Module):
    """One latent-to-latent block; hidden-to-hidden layer makes width scaling explicit."""
    def __init__(self, latent_dim: int, hidden_dim: int):
        super().__init__()
        self.norm = nn.LayerNorm(latent_dim)
        self.network = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, latent_dim),
        )

    def forward(self, state: Tensor) -> Tensor:
        return state + self.network(self.norm(state))


class PredictorG(nn.Module):
    """Final projection G applied once after the recurrent F block(s)."""
    def __init__(self, latent_dim: int, hidden_dim: int):
        super().__init__()
        self.network = nn.Sequential(
            nn.LayerNorm(latent_dim),
            nn.Linear(latent_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, latent_dim),
        )

    def forward(self, state: Tensor) -> Tensor:
        return self.network(state)


class SharedWeightPredictor(nn.Module):
    """Predictor is G(F^T(z)); one F parameter set is reused T times."""
    def __init__(self, latent_dim: int, hidden_dim: int, steps: int):
        super().__init__()
        if steps not in (1, 2, 4):
            raise ValueError("predictor steps must be 1, 2 or 4")
        self.steps = steps
        self.F = PredictorF(latent_dim, hidden_dim)
        self.G = PredictorG(latent_dim, hidden_dim)

    def forward(self, context_latent: Tensor, *, steps: int | None = None) -> Tensor:
        count = self.steps if steps is None else steps
        if count not in (1, 2, 4):
            raise ValueError("predictor steps must be 1, 2 or 4")
        state = context_latent
        for _ in range(count):
            state = self.F(state)
        return self.G(state)


class UnsharedWeightPredictor(nn.Module):
    """Depth-T control with independent F blocks and the same final G head."""
    def __init__(self, latent_dim: int, hidden_dim: int, steps: int):
        super().__init__()
        if steps not in (1, 2, 4):
            raise ValueError("predictor steps must be 1, 2 or 4")
        self.steps = steps
        self.blocks = nn.ModuleList(
            PredictorF(latent_dim, hidden_dim) for _ in range(steps)
        )
        self.G = PredictorG(latent_dim, hidden_dim)

    def forward(self, context_latent: Tensor) -> Tensor:
        state = context_latent
        for block in self.blocks:
            state = block(state)
        return self.G(state)


def make_predictor(config: BaseConfig) -> nn.Module:
    predictor_type = SharedWeightPredictor if config.predictor_kind == "shared" else UnsharedWeightPredictor
    return predictor_type(config.latent_dim, config.hidden_dim, config.predictor_steps)


def predictor_parameter_count(predictor: nn.Module) -> int:
    return sum(parameter.numel() for parameter in predictor.parameters() if parameter.requires_grad)


def predictor_macs_per_example(latent_dim: int, hidden_dim: int, steps: int) -> int:
    """Analytic Linear-layer MAC estimate for this explicit predictor graph."""
    if min(latent_dim, hidden_dim) < 1 or steps not in (1, 2, 4):
        raise ValueError("invalid predictor dimensions or recurrence depth")
    f_macs = 2 * latent_dim * hidden_dim + hidden_dim * hidden_dim
    g_macs = 2 * latent_dim * hidden_dim
    return steps * f_macs + g_macs


def matched_predictor_width_estimates(hidden_dim: int, steps: int) -> dict[str, int]:
    """Protocol starting estimates; actual graph parameters/MACs must still be measured."""
    if hidden_dim < 1 or steps not in (1, 2, 4):
        raise ValueError("invalid width or recurrence depth")
    root = math.sqrt(steps)
    return {
        "compute_matched_wide_t1": max(1, round(hidden_dim * root)),
        "parameter_matched_unshared": max(1, round(hidden_dim / root)),
    }


class M1JEPA(nn.Module):
    """Two-view JEPA with EMA target encoder and a shared-weight recurrent predictor."""

    def __init__(self, config: BaseConfig):
        super().__init__()
        self.config = config
        self.context_encoder = SharedTokenEncoder(config.channels, config.latent_dim)
        self.target_encoder = copy.deepcopy(self.context_encoder)
        self.target_encoder.requires_grad_(False)
        self.predictor = make_predictor(config)

    def forward(self, bundle: InputBundle, future_target: Tensor) -> dict[str, Tensor]:
        context = self.context_encoder.encode_context(bundle)
        with torch.no_grad():
            target = self.target_encoder.encode_target(future_target)
        prediction = self.predictor(context)
        return {"context": context, "prediction": prediction, "target": target}

    @torch.no_grad()
    def update_target_encoder(self, decay: float | None = None) -> None:
        """EMA update after an optimizer step; target weights are never gradient-trained."""
        rate = self.config.ema_decay if decay is None else decay
        if not 0.0 <= rate < 1.0:
            raise ValueError("EMA decay must be in [0, 1)")
        for target_param, online_param in zip(
            self.target_encoder.parameters(), self.context_encoder.parameters(), strict=True
        ):
            target_param.mul_(rate).add_(online_param, alpha=1.0 - rate)

    @staticmethod
    def latent_prediction_loss(output: dict[str, Tensor]) -> Tensor:
        return F.l1_loss(output["prediction"], output["target"])


class DirectMAE(nn.Module):
    """Raw-target control using the same context encoder family and predictor depth."""

    def __init__(self, config: BaseConfig):
        super().__init__()
        self.config = config
        self.encoder = SharedTokenEncoder(config.channels, config.latent_dim)
        self.predictor = SharedWeightPredictor(
            config.latent_dim, config.hidden_dim, config.predictor_steps
        )
        self.readout = nn.Sequential(
            nn.LayerNorm(config.latent_dim),
            nn.Linear(config.latent_dim, config.hidden_dim),
            nn.GELU(),
            nn.Linear(config.hidden_dim, config.horizon * config.channels),
        )

    def forward(self, bundle: InputBundle) -> Tensor:
        latent = self.encoder.encode_context(bundle)
        predicted = self.predictor(latent)
        return self.readout(predicted).reshape(
            predicted.shape[0], self.config.horizon, self.config.channels
        )


class FrozenRepresentationProbe(nn.Module):
    """A capacity-declared MAE readout over a trained, frozen JEPA context encoder."""

    def __init__(self, encoder: SharedTokenEncoder, config: BaseConfig):
        super().__init__()
        self.encoder = copy.deepcopy(encoder)
        self.encoder.requires_grad_(False)
        self.config = config
        self.readout = nn.Sequential(
            nn.LayerNorm(config.latent_dim),
            nn.Linear(config.latent_dim, config.hidden_dim),
            nn.GELU(),
            nn.Linear(config.hidden_dim, config.horizon * config.channels),
        )

    def forward(self, bundle: InputBundle) -> Tensor:
        with torch.no_grad():
            latent = self.encoder.encode_context(bundle)
        return self.readout(latent).reshape(
            latent.shape[0], self.config.horizon, self.config.channels
        )


def variance_covariance_regularizer(representations: Tensor, *, variance_target: float = 1.0) -> Tensor:
    """VICReg-style anti-collapse diagnostic/control term, separate from JEPA loss."""
    if representations.ndim != 2 or representations.shape[0] < 2:
        raise ValueError("representations must be [batch>=2, latent_dim]")
    centered = representations - representations.mean(dim=0, keepdim=True)
    std = torch.sqrt(centered.var(dim=0, unbiased=False) + 1e-4)
    variance = torch.relu(variance_target - std).mean()
    covariance = centered.T @ centered / (representations.shape[0] - 1)
    off_diagonal = covariance - torch.diag(torch.diagonal(covariance))
    covariance_penalty = off_diagonal.square().sum() / representations.shape[1]
    return variance + covariance_penalty
