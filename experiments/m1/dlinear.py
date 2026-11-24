"""Matched-information DLinear control for the M1 time-series experiment.

The trend/seasonal decomposition follows the published DLinear method. M1 adds
a small future-known-covariate projection so this control receives the same
X/S/calendar information as JEPA and Direct-MAE.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .jepa import ChannelStandardizer, JEPAConfig


class MovingAverageDecomposition(nn.Module):
    """Replicate-edge moving average and residual decomposition."""

    def __init__(self, kernel_size: int = 25):
        super().__init__()
        if type(kernel_size) is not int or kernel_size < 1 or kernel_size % 2 == 0:
            raise ValueError("kernel_size must be a positive odd integer")
        self.kernel_size = kernel_size
        self.pool = nn.AvgPool1d(kernel_size=kernel_size, stride=1)

    def forward(self, sequence: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if sequence.ndim != 3 or sequence.shape[1] < 1:
            raise ValueError("sequence must have shape [batch, time, channels]")
        pad = (self.kernel_size - 1) // 2
        if pad:
            left = sequence[:, :1, :].expand(-1, pad, -1)
            right = sequence[:, -1:, :].expand(-1, pad, -1)
            padded = torch.cat((left, sequence, right), dim=1)
        else:
            padded = sequence
        trend = self.pool(padded.transpose(1, 2)).transpose(1, 2)
        seasonal = sequence - trend
        return seasonal, trend


class MatchedDLinearForecaster(nn.Module):
    """DLinear-style forecaster with the common M1 X/S/calendar input contract.

    X is decomposed into seasonal and trend components. Each component uses a
    linear map along the look-back axis. Known future seasonal lags and calendar
    features are projected per horizon and added to the time-linear forecast.
    Outputs remain in raw target units; the input scaler is fit on train rows.
    """

    def __init__(
        self,
        config: JEPAConfig,
        *,
        input_length: int,
        kernel_size: int = 25,
        individual: bool = True,
    ):
        super().__init__()
        if type(individual) is not bool:
            raise ValueError("individual must be a boolean")
        if type(input_length) is not int or input_length < 1:
            raise ValueError("input_length must be a positive integer")
        self.config = config
        self.input_length = input_length
        self.individual = individual
        self.decomposition = MovingAverageDecomposition(kernel_size)
        self.scaler = ChannelStandardizer(config.input_channels)

        channels = config.input_channels
        if individual:
            self.seasonal_linear = nn.ModuleList(
                nn.Linear(input_length, config.horizon) for _ in range(channels)
            )
            self.trend_linear = nn.ModuleList(
                nn.Linear(input_length, config.horizon) for _ in range(channels)
            )
        else:
            self.seasonal_linear = nn.Linear(input_length, config.horizon)
            self.trend_linear = nn.Linear(input_length, config.horizon)

        known_width = config.seasonal_lags * channels + config.calendar_features
        self.future_known_projection = nn.Linear(known_width, channels)

    def _time_linear(self, values: torch.Tensor, layers: nn.Module) -> torch.Tensor:
        # values: [B, L, C] -> [B, H, C]
        by_channel = values.transpose(1, 2)
        if self.individual:
            output = torch.stack(
                [layers[channel](by_channel[:, channel, :])
                 for channel in range(by_channel.shape[1])],
                dim=-1,
            )
        else:
            output = layers(by_channel).transpose(1, 2)
        return output

    def forward(
        self,
        x: torch.Tensor,
        seasonal: torch.Tensor,
        calendar: torch.Tensor,
    ) -> torch.Tensor:
        cfg = self.config
        if x.ndim != 3 or x.shape[1:] != (self.input_length, cfg.input_channels):
            raise ValueError("X shape does not match the configured [L, C] contract")
        batch = x.shape[0]
        if seasonal.shape != (
            batch, cfg.horizon, cfg.seasonal_lags, cfg.input_channels
        ):
            raise ValueError("seasonal shape does not match the configured [B, H, K, C] contract")
        if calendar.shape != (batch, cfg.horizon, cfg.calendar_features):
            raise ValueError("calendar shape does not match the configured [B, H, F] contract")
        if not bool(self.scaler.fitted):
            raise RuntimeError("input scaler must be fitted on train rows before prediction")

        x_scaled = self.scaler.transform(x)
        seasonal_scaled = self.scaler.transform(seasonal)
        seasonal_x, trend_x = self.decomposition(x_scaled)
        forecast_x = (
            self._time_linear(seasonal_x, self.seasonal_linear)
            + self._time_linear(trend_x, self.trend_linear)
        )
        known = torch.cat(
            (seasonal_scaled.reshape(batch, cfg.horizon, -1), calendar), dim=-1
        )
        return forecast_x + self.future_known_projection(known)

    def loss(self, prediction: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if prediction.shape != target.shape:
            raise ValueError("DLinear prediction and target shapes differ")
        if not torch.isfinite(prediction).all() or not torch.isfinite(target).all():
            raise FloatingPointError("DLinear loss received non-finite values")
        return F.l1_loss(prediction, target)


class MatchedNLinearForecaster(nn.Module):
    """NLinear-style last-value normalization with the common M1 X/S/calendar contract.

    X is centered by its last observed value and restored after the time-linear
    residual forecast. A train-only scaler standardizes known future S
    covariates; the future-known branch predicts an additive raw-unit residual.
    This is a matched-information adaptation, not an exact reproduction of the
    original X-only NLinear benchmark.
    """

    def __init__(
        self,
        config: JEPAConfig,
        *,
        input_length: int,
        individual: bool = True,
    ):
        super().__init__()
        if type(input_length) is not int or input_length < 1:
            raise ValueError("input_length must be a positive integer")
        if type(individual) is not bool:
            raise ValueError("individual must be a boolean")
        self.config = config
        self.input_length = input_length
        self.individual = individual
        self.scaler = ChannelStandardizer(config.input_channels)

        channels = config.input_channels
        if individual:
            self.linear = nn.ModuleList(
                nn.Linear(input_length, config.horizon) for _ in range(channels)
            )
        else:
            self.linear = nn.Linear(input_length, config.horizon)
        known_width = config.seasonal_lags * channels + config.calendar_features
        self.future_known_projection = nn.Linear(known_width, channels)

    def forward(
        self,
        x: torch.Tensor,
        seasonal: torch.Tensor,
        calendar: torch.Tensor,
    ) -> torch.Tensor:
        cfg = self.config
        if x.ndim != 3 or x.shape[1:] != (self.input_length, cfg.input_channels):
            raise ValueError("X shape does not match the configured [L, C] contract")
        batch = x.shape[0]
        if seasonal.shape != (
            batch, cfg.horizon, cfg.seasonal_lags, cfg.input_channels
        ):
            raise ValueError("seasonal shape does not match the configured [B, H, K, C] contract")
        if calendar.shape != (batch, cfg.horizon, cfg.calendar_features):
            raise ValueError("calendar shape does not match the configured [B, H, F] contract")
        if not bool(self.scaler.fitted):
            raise RuntimeError("input scaler must be fitted on train rows before prediction")

        last = x[:, -1:, :].detach()
        centered = x - last
        by_channel = centered.transpose(1, 2)
        if self.individual:
            residual = torch.stack(
                [self.linear[channel](by_channel[:, channel, :])
                 for channel in range(by_channel.shape[1])],
                dim=-1,
            )
        else:
            residual = self.linear(by_channel).transpose(1, 2)
        forecast = residual + last

        seasonal_scaled = self.scaler.transform(seasonal)
        known = torch.cat(
            (seasonal_scaled.reshape(batch, cfg.horizon, -1), calendar), dim=-1
        )
        return forecast + self.future_known_projection(known)

    def loss(self, prediction: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if prediction.shape != target.shape:
            raise ValueError("NLinear prediction and target shapes differ")
        if not torch.isfinite(prediction).all() or not torch.isfinite(target).all():
            raise FloatingPointError("NLinear loss received non-finite values")
        return F.l1_loss(prediction, target)
