"""M1 DATA pipeline: strict, chronological, parameterized window construction.

This module deliberately uses only the Python standard library. It does not download
UCI data. Callers provide the extracted UCI .txt/.csv path or an iterable of rows.
All timestamps are minute-resolution and all numeric channels are parsed strictly.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

UCI_TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M:%S"
UCI_MISSING = {"", "?", "nan", "NaN", "NA", "null", "None"}
DEFAULT_SEASONAL_LAGS = (1440, 10080)


@dataclass(frozen=True)
class DataConfig:
    input_length: int
    horizon: int = 60
    # Upper bound fixed before the pilot; changing L within this range cannot move splits.
    max_candidate_input_length: int = 10080
    primary_channel: str = "Global_active_power"
    seasonal_lags: tuple[int, ...] = DEFAULT_SEASONAL_LAGS
    include_calendar: bool = True
    train_fraction: float = 0.70
    validation_fraction: float = 0.15
    # Fixed before any pilot. This is not tuned using test performance.
    split_gap: int | None = None

    def __post_init__(self) -> None:
        if self.input_length < 1 or self.horizon < 1 or self.max_candidate_input_length < 1:
            raise ValueError("input_length, horizon and max_candidate_input_length must be positive")
        if self.input_length > self.max_candidate_input_length:
            raise ValueError("input_length exceeds preregistered max_candidate_input_length")
        if not 0 < self.train_fraction < 1:
            raise ValueError("train_fraction must be in (0, 1)")
        if not 0 < self.validation_fraction < 1:
            raise ValueError("validation_fraction must be in (0, 1)")
        if self.train_fraction + self.validation_fraction >= 1:
            raise ValueError("train + validation fractions must be below 1")
        if any(x < 1 for x in self.seasonal_lags):
            raise ValueError("seasonal lags must be positive")
        if self.split_gap is not None and self.split_gap < 0:
            raise ValueError("split_gap cannot be negative")

    @property
    def required_gap(self) -> int:
        # The split is fixed independently of L. The pilot may vary L, but may
        # not silently shrink the predeclared gap. A caller should choose a
        # conservative gap using the maximum candidate L and seasonal lookback.
        minimum = max(self.max_candidate_input_length, self.horizon, max(self.seasonal_lags, default=0))
        return minimum + self.horizon

    @property
    def effective_gap(self) -> int:
        gap = self.required_gap if self.split_gap is None else self.split_gap
        if gap < self.required_gap:
            raise ValueError(
                f"split_gap={gap} is below required minimum {self.required_gap}"
            )
        return gap


@dataclass(frozen=True)
class MinuteRow:
    timestamp: datetime
    values: tuple[float | None, ...]


@dataclass(frozen=True)
class Window:
    origin_index: int
    origin_time: str
    x: tuple[tuple[float, ...], ...]
    seasonal: tuple[tuple[float, ...], ...]
    calendar: tuple[tuple[float, ...], ...]
    target: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class SplitStats:
    split: str
    candidate_windows: int
    accepted_windows: int
    rejected_windows: int
    rejection_fraction: float
    first_origin: str | None
    last_origin: str | None
    accepted_by_month: Mapping[str, int]
    rejected_by_month: Mapping[str, int]


def parse_uci(path: str | Path) -> tuple[tuple[str, ...], list[MinuteRow]]:
    """Read the official semicolon-delimited UCI file (decimal comma)."""
    rows: list[MinuteRow] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if not reader.fieldnames or "Date" not in reader.fieldnames or "Time" not in reader.fieldnames:
            raise ValueError("Expected UCI Date and Time columns")
        channels = tuple(name for name in reader.fieldnames if name not in {"Date", "Time"})
        if not channels:
            raise ValueError("No measurement channels found")
        previous: datetime | None = None
        for line_no, raw in enumerate(reader, start=2):
            timestamp = datetime.strptime(
                f"{raw['Date'].strip()} {raw['Time'].strip()}",
                UCI_TIMESTAMP_FORMAT,
            )
            if previous is not None and timestamp - previous != timedelta(minutes=1):
                raise ValueError(f"non-contiguous minute timestamp at line {line_no}")
            previous = timestamp
            values: list[float | None] = []
            for channel in channels:
                token = (raw.get(channel) or "").strip()
                if token in UCI_MISSING:
                    values.append(None)
                else:
                    values.append(float(token.replace(",", ".")))
            rows.append(MinuteRow(timestamp, tuple(values)))
    if not rows:
        raise ValueError("UCI file contains no data rows")
    return channels, rows


def rows_from_records(
    records: Iterable[tuple[datetime | str, Mapping[str, float | int | str | None]]],
    channels: Sequence[str],
) -> list[MinuteRow]:
    """Synthetic/test and alternate-ingestion adapter."""
    out: list[MinuteRow] = []
    previous: datetime | None = None
    for timestamp, record in records:
        stamp = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
        if previous is not None and stamp - previous != timedelta(minutes=1):
            raise ValueError("timestamps must be contiguous at one-minute resolution")
        previous = stamp
        values: list[float | None] = []
        for channel in channels:
            value = record.get(channel)
            if value is None or str(value).strip() in UCI_MISSING:
                values.append(None)
            else:
                values.append(float(str(value).replace(",", ".")))
        out.append(MinuteRow(stamp, tuple(values)))
    return out


def _calendar(timestamp: datetime) -> tuple[float, ...]:
    minute = timestamp.hour * 60 + timestamp.minute
    weekday = timestamp.weekday()
    import math
    return (
        math.sin(2 * math.pi * minute / 1440),
        math.cos(2 * math.pi * minute / 1440),
        math.sin(2 * math.pi * weekday / 7),
        math.cos(2 * math.pi * weekday / 7),
    )


def _month(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m")


def build_chronological_boundaries(n_rows: int, config: DataConfig) -> dict[str, tuple[int, int]]:
    """Return raw-index ranges; validation/test begin after a predeclared gap."""
    if n_rows <= 0:
        raise ValueError("n_rows must be positive")
    gap = config.effective_gap
    train_end = int(n_rows * config.train_fraction)
    validation_end = int(n_rows * (config.train_fraction + config.validation_fraction))
    train = (0, train_end)
    validation = (min(n_rows, train_end + gap), validation_end)
    test = (min(n_rows, validation_end + gap), n_rows)
    if not (train[0] < train[1] <= validation[0] < validation[1] <= test[0] < test[1]):
        raise ValueError(
            "Dataset too short for requested fractions and split gap; "
            f"n={n_rows}, gap={gap}, ranges={train, validation, test}"
        )
    return {"train": train, "validation": validation, "test": test}


def _window_indices(origin: int, config: DataConfig) -> tuple[range, range, range]:
    x_idx = range(origin - config.input_length + 1, origin + 1)
    target_idx = range(origin + 1, origin + config.horizon + 1)
    # For each forecast minute j, retrieve the corresponding known historical
    # value at t+j-lag. These are all <= t because lag >= horizon is not
    # guaranteed, so validate this explicitly below.
    seasonal_idx = range(1, config.horizon + 1)
    return x_idx, target_idx, seasonal_idx


def make_split(
    rows: Sequence[MinuteRow],
    channels: Sequence[str],
    config: DataConfig,
    split: str,
    bounds: tuple[int, int],
) -> tuple[list[Window], SplitStats]:
    if split not in {"train", "validation", "test"}:
        raise ValueError(f"unknown split: {split}")
    if config.primary_channel not in channels:
        raise ValueError(f"primary channel {config.primary_channel!r} absent")
    channel_count = len(channels)
    start, end = bounds
    channel_index = {name: i for i, name in enumerate(channels)}
    windows: list[Window] = []
    rejected_by_month: dict[str, int] = {}
    accepted_by_month: dict[str, int] = {}
    candidates = 0
    first_origin: str | None = None
    last_origin: str | None = None

    # Split membership is defined by the complete target interval. No target
    # may cross a split boundary; historical covariates may use earlier rows.
    for origin in range(max(config.input_length - 1, start), end - config.horizon):
        target_end = origin + config.horizon + 1
        if target_end > end:
            continue
        candidates += 1
        month = _month(rows[origin].timestamp)
        x_idx, target_idx, js = _window_indices(origin, config)
        required_values: list[float | None] = []
        for idx in x_idx:
            required_values.extend(rows[idx].values)
        for idx in target_idx:
            required_values.extend(rows[idx].values)
        seasonal_rows: list[tuple[float, ...]] = []
        valid_seasonal = True
        for j in js:
            vals: list[float] = []
            for lag in config.seasonal_lags:
                source_idx = origin + j - lag
                if source_idx < 0 or source_idx > origin:
                    valid_seasonal = False
                    break
                row_values = rows[source_idx].values
                if any(v is None for v in row_values):
                    valid_seasonal = False
                    break
                vals.extend(float(v) for v in row_values if v is not None)
            if not valid_seasonal:
                break
            seasonal_rows.append(tuple(vals))
        valid = valid_seasonal and all(v is not None for v in required_values)
        if not valid:
            rejected_by_month[month] = rejected_by_month.get(month, 0) + 1
            continue
        x = tuple(tuple(float(v) for v in rows[idx].values if v is not None) for idx in x_idx)
        target = tuple(tuple(float(v) for v in rows[idx].values if v is not None) for idx in target_idx)
        calendar = tuple(
            _calendar(rows[origin + j].timestamp) if config.include_calendar else ()
            for j in range(1, config.horizon + 1)
        )
        window = Window(
            origin_index=origin,
            origin_time=rows[origin].timestamp.isoformat(),
            x=x,
            seasonal=tuple(seasonal_rows),
            calendar=calendar,
            target=target,
        )
        windows.append(window)
        accepted_by_month[month] = accepted_by_month.get(month, 0) + 1
        first_origin = first_origin or window.origin_time
        last_origin = window.origin_time

    rejected = candidates - len(windows)
    stats = SplitStats(
        split=split,
        candidate_windows=candidates,
        accepted_windows=len(windows),
        rejected_windows=rejected,
        rejection_fraction=(rejected / candidates if candidates else 0.0),
        first_origin=first_origin,
        last_origin=last_origin,
        accepted_by_month=dict(sorted(accepted_by_month.items())),
        rejected_by_month=dict(sorted(rejected_by_month.items())),
    )
    return windows, stats


def build_dataset(
    rows: Sequence[MinuteRow],
    channels: Sequence[str],
    config: DataConfig,
) -> tuple[dict[str, list[Window]], dict[str, SplitStats], dict[str, object]]:
    if any(len(row.values) != len(channels) for row in rows):
        raise ValueError("row channel count does not match channel names")
    if any(rows[i + 1].timestamp - rows[i].timestamp != timedelta(minutes=1) for i in range(len(rows) - 1)):
        raise ValueError("timestamps must be contiguous at one-minute resolution")
    bounds = build_chronological_boundaries(len(rows), config)
    datasets: dict[str, list[Window]] = {}
    stats: dict[str, SplitStats] = {}
    # Test data is intentionally not materialized here. It has a separate
    # preregistration-gated entry point below.
    for name in ("train", "validation"):
        datasets[name], stats[name] = make_split(rows, channels, config, name, bounds[name])
    manifest: dict[str, object] = {
        "schema": "v14.m1.data-manifest.v1",
        "channels": list(channels),
        "row_count": len(rows),
        "first_timestamp": rows[0].timestamp.isoformat(),
        "last_timestamp": rows[-1].timestamp.isoformat(),
        "config": asdict(config),
        "effective_gap": config.effective_gap,
        "split_boundaries": {k: list(v) for k, v in bounds.items()},
        "split_stats": {k: asdict(v) for k, v in stats.items()},
        "test_access": "LOCKED_REQUIRES_HASH_BOUND_PREREGISTRATION",
    }
    return datasets, stats, manifest


def write_manifest(manifest: Mapping[str, object], path: str | Path) -> str:
    """Write canonical JSON and return SHA-256 of the exact bytes."""
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    Path(path).write_bytes(payload + b"\n")
    return digest



def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def data_config_sha256(config: DataConfig) -> str:
    """Hash all split/window-affecting settings, including the preregistered L ceiling."""
    return _canonical_sha256(asdict(config))


def split_boundaries_sha256(rows: Sequence[MinuteRow], config: DataConfig) -> str:
    bounds = {k: list(v) for k, v in build_chronological_boundaries(len(rows), config).items()}
    return _canonical_sha256(bounds)


def dataset_sha256(rows: Sequence[MinuteRow], channels: Sequence[str]) -> str:
    """Stable fingerprint of parsed timestamps and values; missing values remain null."""
    digest = hashlib.sha256()
    digest.update(json.dumps(list(channels), separators=(",", ":")).encode("utf-8"))
    for row in rows:
        record = [row.timestamp.isoformat(), list(row.values)]
        digest.update(json.dumps(record, separators=(",", ":"), allow_nan=False).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def load_test_split(
    rows: Sequence[MinuteRow],
    channels: Sequence[str],
    config: DataConfig,
    *,
    preregistration_path: str | Path,
    preregistration_sha256: str,
    access_log_path: str | Path,
) -> tuple[list[Window], SplitStats]:
    """Open test windows only after exact preregistration/config/data hash checks.

    Preregistration JSON must contain:
      data_config_sha256, split_boundaries_sha256, dataset_sha256.
    The supplied preregistration hash is checked against the exact file bytes.
    """
    path = Path(preregistration_path)
    raw = path.read_bytes()
    actual_prereg_hash = hashlib.sha256(raw).hexdigest()
    if actual_prereg_hash != preregistration_sha256:
        raise PermissionError("preregistration file hash mismatch")
    prereg = json.loads(raw.decode("utf-8"))
    expected = {
        "data_config_sha256": data_config_sha256(config),
        "split_boundaries_sha256": split_boundaries_sha256(rows, config),
        "dataset_sha256": dataset_sha256(rows, channels),
    }
    for key, value in expected.items():
        if prereg.get(key) != value:
            raise PermissionError(f"preregistration mismatch: {key}")
    bounds = build_chronological_boundaries(len(rows), config)
    windows, stats = make_split(rows, channels, config, "test", bounds["test"])
    event = {
        "event": "TEST_SPLIT_OPENED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration_sha256": actual_prereg_hash,
        **expected,
        "accepted_windows": stats.accepted_windows,
        "rejected_windows": stats.rejected_windows,
    }
    log_path = Path(access_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    return windows, stats
