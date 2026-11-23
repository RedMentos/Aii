"""M1 baseline model family with common X/S/calendar information parity."""
from __future__ import annotations

import numpy as np
import torch
from torch import Tensor, nn

from .array_data import ArrayDataset, InputBundle
from .base import BaseConfig, SharedTokenEncoder


def flatten_input_bundle(bundle: InputBundle) -> Tensor:
    """Flatten exactly X, S and calendar in a fixed, documented order."""
    x = torch.as_tensor(bundle.x)
    seasonal = torch.as_tensor(bundle.seasonal, device=x.device, dtype=x.dtype)
    calendar = torch.as_tensor(bundle.calendar, device=x.device, dtype=x.dtype)
    batch = x.shape[0]
    return torch.cat(
        (x.reshape(batch, -1), seasonal.reshape(batch, -1), calendar.reshape(batch, -1)),
        dim=1,
    )


class PersistenceBaseline(nn.Module):
    """Repeat the last observed multichannel value across the forecast horizon."""
    def __init__(self, horizon: int):
        super().__init__()
        self.horizon = horizon

    def forward(self, bundle: InputBundle) -> Tensor:
        x = torch.as_tensor(bundle.x)
        return x[:, -1:, :].expand(-1, self.horizon, -1)


class SeasonalPersistenceBaseline(nn.Module):
    """Use one explicitly declared seasonal-lag channel as the forecast."""
    def __init__(self, lag_index: int):
        super().__init__()
        if lag_index < 0:
            raise ValueError("lag_index must be non-negative")
        self.lag_index = lag_index

    def forward(self, bundle: InputBundle) -> Tensor:
        seasonal = torch.as_tensor(bundle.seasonal)
        if self.lag_index >= seasonal.shape[2]:
            raise ValueError("requested seasonal lag is absent from InputBundle")
        return seasonal[:, :, self.lag_index, :]


class TrainConstantBaseline(nn.Module):
    """Training-only channel-wise mean or median repeated at every horizon."""
    def __init__(self, horizon: int, channels: int, statistic: str = "mean"):
        super().__init__()
        if statistic not in {"mean", "median"}:
            raise ValueError("statistic must be mean or median")
        self.horizon = horizon
        self.channels = channels
        self.statistic = statistic
        self.register_buffer("constant", torch.zeros(channels))
        self.register_buffer("_fitted", torch.tensor(False, dtype=torch.bool))

    @property
    def fitted(self) -> bool:
        return bool(self._fitted.item())

    def fit(self, dataset: ArrayDataset) -> "TrainConstantBaseline":
        start, end = dataset.bounds["train"]
        values = dataset.values[start:end]
        if self.statistic == "mean":
            result = np.nanmean(values, axis=0)
        else:
            result = np.nanmedian(values, axis=0)
        if not np.isfinite(result).all():
            raise ValueError("training split has a channel with no finite values")
        self.constant.copy_(torch.as_tensor(result, dtype=self.constant.dtype, device=self.constant.device))
        self._fitted.fill_(True)
        return self

    def forward(self, bundle: InputBundle) -> Tensor:
        if not self.fitted:
            raise RuntimeError("TrainConstantBaseline must be fitted on the training split")
        x = torch.as_tensor(bundle.x, device=self.constant.device, dtype=self.constant.dtype)
        return self.constant.view(1, 1, -1).expand(x.shape[0], self.horizon, -1)


class LinearInputBaseline(nn.Module):
    """Linear map over the identical flattened X/S/calendar information bundle."""
    def __init__(self, input_width: int, horizon: int, channels: int):
        super().__init__()
        self.input_width = input_width
        self.horizon = horizon
        self.channels = channels
        self.linear = nn.Linear(input_width, horizon * channels)

    def forward(self, bundle: InputBundle) -> Tensor:
        features = flatten_input_bundle(bundle).to(
            device=self.linear.weight.device, dtype=self.linear.weight.dtype
        )
        if features.shape[1] != self.input_width:
            raise ValueError("InputBundle width differs from the declared baseline width")
        output = self.linear(features)
        return output.reshape(output.shape[0], self.horizon, self.channels)


class RidgeAR(LinearInputBaseline):
    """Conventional squared-error autoregression with an L2 coefficient penalty."""
    pass


class L1AR(LinearInputBaseline):
    """Absolute-error autoregression with an L2 coefficient penalty (not Ridge)."""
    pass


class RawWindowProbe(LinearInputBaseline):
    """Linear probe on the full raw X/S/calendar information bundle."""
    pass


class TrainMean(TrainConstantBaseline):
    def __init__(self, horizon: int, channels: int):
        super().__init__(horizon, channels, "mean")


class TrainMedian(TrainConstantBaseline):
    def __init__(self, horizon: int, channels: int):
        super().__init__(horizon, channels, "median")


class RawWindowMLP(nn.Module):
    """Nonlinear raw-input control; receives X, S and calendar, not X alone."""
    def __init__(self, input_width: int, horizon: int, channels: int, hidden_dim: int = 256):
        super().__init__()
        self.input_width = input_width
        self.horizon = horizon
        self.channels = channels
        self.network = nn.Sequential(
            nn.Linear(input_width, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, horizon * channels),
        )

    def forward(self, bundle: InputBundle) -> Tensor:
        features = flatten_input_bundle(bundle).to(
            device=next(self.parameters()).device, dtype=next(self.parameters()).dtype
        )
        if features.shape[1] != self.input_width:
            raise ValueError("InputBundle width differs from the declared MLP width")
        output = self.network(features)
        return output.reshape(output.shape[0], self.horizon, self.channels)


class RawGRU(nn.Module):
    """Sequence control with X history followed by horizon-aligned S/calendar tokens."""
    def __init__(
        self, channels: int, seasonal_lags: int, horizon: int,
        hidden_dim: int = 128, num_layers: int = 1,
    ):
        super().__init__()
        if min(channels, seasonal_lags, horizon, hidden_dim, num_layers) < 1:
            raise ValueError("RawGRU dimensions must be positive")
        self.channels = channels
        self.seasonal_lags = seasonal_lags
        self.horizon = horizon
        self.x_projection = nn.Linear(channels, hidden_dim)
        self.side_projection = nn.Linear(seasonal_lags * channels + 4, hidden_dim)
        self.gru = nn.GRU(
            hidden_dim, hidden_dim, num_layers=num_layers, batch_first=True
        )
        self.readout = nn.Linear(hidden_dim, horizon * channels)

    def forward(self, bundle: InputBundle) -> Tensor:
        device = self.x_projection.weight.device
        dtype = self.x_projection.weight.dtype
        x = torch.as_tensor(bundle.x, device=device, dtype=dtype)
        seasonal = torch.as_tensor(bundle.seasonal, device=device, dtype=dtype)
        calendar = torch.as_tensor(bundle.calendar, device=device, dtype=dtype)
        if x.shape[-1] != self.channels or seasonal.shape[2:] != (self.seasonal_lags, self.channels):
            raise ValueError("RawGRU channel or seasonal-lag shape mismatch")
        if calendar.shape[-1] == 0:
            calendar = torch.zeros(
                (x.shape[0], self.horizon, 4), device=device, dtype=dtype
            )
        if calendar.shape != (x.shape[0], self.horizon, 4):
            raise ValueError("RawGRU calendar shape mismatch")
        side = torch.cat(
            (seasonal.reshape(x.shape[0], self.horizon, -1), calendar), dim=-1
        )
        tokens = torch.cat((self.x_projection(x), self.side_projection(side)), dim=1)
        sequence, _ = self.gru(tokens)
        prediction = self.readout(sequence[:, -1, :])
        return prediction.reshape(x.shape[0], self.horizon, self.channels)


class RandomEncoderProbe(nn.Module):
    """Frozen random shared-token encoder plus a trained MAE readout."""
    def __init__(self, config: BaseConfig):
        super().__init__()
        self.config = config
        self.encoder = SharedTokenEncoder(config.channels, config.latent_dim)
        self.encoder.requires_grad_(False)
        self.readout = nn.Sequential(
            nn.LayerNorm(config.latent_dim),
            nn.Linear(config.latent_dim, config.hidden_dim),
            nn.GELU(),
            nn.Linear(config.hidden_dim, config.horizon * config.channels),
        )

    def forward(self, bundle: InputBundle) -> Tensor:
        with torch.no_grad():
            latent = self.encoder.encode_context(bundle)
        output = self.readout(latent)
        return output.reshape(output.shape[0], self.config.horizon, self.config.channels)
