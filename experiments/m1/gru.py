"""Supervised raw-input GRU control using the same X/S/calendar contract."""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .jepa import ChannelStandardizer, JEPAConfig, sinusoidal_positions


class RawGRUForecaster(nn.Module):
    def __init__(
        self,
        config: JEPAConfig,
        *,
        hidden_size: int = 64,
        num_layers: int = 1,
        dropout: float = 0.0,
    ):
        super().__init__()
        if type(hidden_size) is not int or hidden_size < 1:
            raise ValueError("hidden_size must be a positive integer")
        if type(num_layers) is not int or num_layers < 1:
            raise ValueError("num_layers must be a positive integer")
        if not 0.0 <= dropout < 1.0:
            raise ValueError("dropout must lie in [0, 1)")
        self.config = config
        self.hidden_size = hidden_size
        self.scaler = ChannelStandardizer(config.input_channels)
        recurrent_dropout = dropout if num_layers > 1 else 0.0
        self.context_gru = nn.GRU(
            input_size=config.input_channels,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=recurrent_dropout,
        )
        future_width = config.seasonal_lags * config.input_channels + config.calendar_features
        self.future_projection = nn.Sequential(
            nn.Linear(future_width, hidden_size),
            nn.GELU(),
            nn.Linear(hidden_size, hidden_size),
        )
        self.decoder_gru = nn.GRU(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=recurrent_dropout,
        )
        self.value_head = nn.Linear(hidden_size, config.input_channels)

    def forward(
        self,
        x: torch.Tensor,
        seasonal: torch.Tensor,
        calendar: torch.Tensor,
    ) -> torch.Tensor:
        x_scaled = self.scaler.transform(x)
        seasonal_scaled = self.scaler.transform(seasonal)
        _, context_state = self.context_gru(x_scaled)
        batch, horizon = seasonal.shape[:2]
        known = torch.cat(
            (seasonal_scaled.reshape(batch, horizon, -1), calendar), dim=-1
        )
        queries = self.future_projection(known)
        queries = queries + sinusoidal_positions(
            horizon, self.hidden_size, device=queries.device, dtype=queries.dtype
        )
        decoded, _ = self.decoder_gru(queries, context_state)
        return self.value_head(decoded)

    def loss(self, prediction: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if prediction.shape != target.shape:
            raise ValueError("Raw-GRU prediction and target shapes differ")
        return F.l1_loss(prediction, target)
