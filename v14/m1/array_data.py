"""Bounded-memory NumPy window batches for the V14 M1 forecasting experiment.

The list-based helpers in data.py remain useful for tiny fixtures. Real UCI runs
must use ArrayDataset: it stores one dense value matrix and creates only one
bounded batch of overlapping windows at a time.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Mapping, Sequence

import numpy as np

MAX_WINDOW_BATCH_BYTES = 256 * 1024 * 1024

from .data import (
    DataConfig,
    MinuteRow,
    SplitStats,
    _validate_rows,
    UCI_TIMESTAMP_FORMAT,
    _parse_measurement,
    build_chronological_boundaries,
    data_config_sha256,
    dataset_sha256,
    split_boundaries_sha256,
)


@dataclass(frozen=True)
class InputBundle:
    """The exact information families supplied to every primary comparison model."""
    x: np.ndarray          # [batch, L, channels]
    seasonal: np.ndarray   # [batch, horizon, lags, channels]
    calendar: np.ndarray   # [batch, horizon, 4]

    def flatten(self) -> np.ndarray:
        """Common deterministic adapter; no model-specific information is added."""
        n = self.x.shape[0]
        return np.concatenate(
            (
                self.x.reshape(n, -1),
                self.seasonal.reshape(n, -1),
                self.calendar.reshape(n, -1),
            ),
            axis=1,
        )


@dataclass(frozen=True)
class WindowBatch:
    origin_indices: np.ndarray
    inputs: InputBundle
    target: np.ndarray     # [batch, horizon, channels]


class ArrayDataset:
    """One in-memory numeric matrix plus lazy, bounded window batches.

    Construct from parsed rows once, then release the Python row objects. The
    matrix is float32 with NaN as the internal missing-value marker. A prefix
    count makes whole-window missingness checks O(batch * channels), not O(L).
    Test windows remain inaccessible until open_test_split verifies the exact
    preregistration, config, split and parsed-data hashes.
    """

    def __init__(self, rows: Sequence[MinuteRow], channels: Sequence[str], config: DataConfig):
        _validate_rows(rows, channels)
        self.channels = tuple(channels)
        self.config = config
        self.n_rows = len(rows)
        self.bounds = build_chronological_boundaries(self.n_rows, config)
        self.config_sha256 = data_config_sha256(config)
        self.split_sha256 = split_boundaries_sha256(rows, config)
        self.dataset_sha256 = dataset_sha256(rows, channels)

        raw = np.asarray(
            [[np.nan if value is None else float(value) for value in row.values] for row in rows],
            dtype=np.float32,
        )
        if raw.shape != (self.n_rows, len(self.channels)) or not np.isfinite(raw[~np.isnan(raw)]).all():
            raise ValueError("invalid numeric matrix")
        minute_ids = np.fromiter(
            (
                row.timestamp.toordinal() * 1440 + row.timestamp.hour * 60 + row.timestamp.minute
                for row in rows
            ),
            dtype=np.int64,
            count=self.n_rows,
        )
        month_ids = np.fromiter(
            (row.timestamp.year * 100 + row.timestamp.month for row in rows),
            dtype=np.int32,
            count=self.n_rows,
        )
        self._install(raw, minute_ids, month_ids, self.channels, config, self.dataset_sha256)

    def _install(
        self,
        values: np.ndarray,
        minute_ids: np.ndarray,
        month_ids: np.ndarray,
        channels: Sequence[str],
        config: DataConfig,
        parsed_data_sha256: str,
    ) -> None:
        self.channels = tuple(channels)
        if not self.channels or len(set(self.channels)) != len(self.channels):
            raise ValueError("channel names must be non-empty and unique")
        if config.primary_channel not in self.channels:
            raise ValueError(f"primary channel {config.primary_channel!r} absent")
        if values.ndim != 2 or values.shape[1] != len(self.channels):
            raise ValueError("invalid numeric matrix shape")
        if minute_ids.shape != (values.shape[0],) or month_ids.shape != (values.shape[0],):
            raise ValueError("invalid timestamp/month index arrays")
        if not np.isfinite(values[~np.isnan(values)]).all():
            raise ValueError("non-finite value in numeric matrix")
        self.config = config
        self.n_rows = int(values.shape[0])
        self.bounds = build_chronological_boundaries(self.n_rows, config)
        self.config_sha256 = data_config_sha256(config)
        self.split_sha256 = hashlib.sha256(
            json.dumps(
                {key: list(value) for key, value in self.bounds.items()},
                sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        self.dataset_sha256 = parsed_data_sha256
        self.values = values
        self._missing_prefix = np.concatenate(
            (np.zeros(1, dtype=np.int64), np.isnan(values).sum(axis=1, dtype=np.int64).cumsum())
        )
        self._minute_ids = minute_ids
        self._month_ids = month_ids
        self._test_authorized = False
        self._test_preregistration_sha256: str | None = None

    @classmethod
    def from_uci(cls, path: str | Path, config: DataConfig) -> "ArrayDataset":
        """Two-pass UCI CSV ingestion directly into a dense matrix, without MinuteRow objects."""
        source = Path(path)
        before = source.stat()
        channels: tuple[str, ...] | None = None
        row_count = 0
        previous: datetime | None = None
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            if not reader.fieldnames or "Date" not in reader.fieldnames or "Time" not in reader.fieldnames:
                raise ValueError("Expected UCI Date and Time columns")
            channels = tuple(name for name in reader.fieldnames if name not in {"Date", "Time"})
            if not channels or any(not name.strip() for name in channels) or len(set(channels)) != len(channels):
                raise ValueError("UCI measurement channels must be non-empty and unique")
            for line_no, raw in enumerate(reader, start=2):
                if None in raw or raw.get("Date") is None or raw.get("Time") is None or any(raw.get(channel) is None for channel in channels):
                    raise ValueError(f"truncated or overlong CSV row at line {line_no}")
                stamp = datetime.strptime(
                    f"{(raw.get('Date') or '').strip()} {(raw.get('Time') or '').strip()}",
                    UCI_TIMESTAMP_FORMAT,
                )
                if stamp.second != 0 or stamp.microsecond != 0:
                    raise ValueError(f"timestamp is not aligned to a whole minute at line {line_no}")
                if previous is not None and stamp - previous != timedelta(minutes=1):
                    raise ValueError(f"non-contiguous minute timestamp at line {line_no}")
                previous = stamp
                row_count += 1
        if row_count < 1 or channels is None:
            raise ValueError("UCI file contains no data rows")
        values = np.full((row_count, len(channels)), np.nan, dtype=np.float32)
        minute_ids = np.empty(row_count, dtype=np.int64)
        month_ids = np.empty(row_count, dtype=np.int32)
        digest = hashlib.sha256()
        digest.update(json.dumps(list(channels), separators=(",", ":")).encode("utf-8"))
        index = 0
        previous = None
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            if tuple(name for name in (reader.fieldnames or ()) if name not in {"Date", "Time"}) != channels:
                raise ValueError("UCI header changed between ingestion passes")
            for line_no, raw in enumerate(reader, start=2):
                if index >= row_count:
                    raise ValueError("UCI file gained rows between ingestion passes")
                if None in raw or raw.get("Date") is None or raw.get("Time") is None or any(raw.get(channel) is None for channel in channels):
                    raise ValueError(f"truncated or overlong CSV row at line {line_no}")
                stamp = datetime.strptime(
                    f"{(raw.get('Date') or '').strip()} {(raw.get('Time') or '').strip()}",
                    UCI_TIMESTAMP_FORMAT,
                )
                if stamp.second != 0 or stamp.microsecond != 0:
                    raise ValueError(f"timestamp is not aligned to a whole minute at line {line_no}")
                if previous is not None and stamp - previous != timedelta(minutes=1):
                    raise ValueError(f"non-contiguous minute timestamp at line {line_no}")
                previous = stamp
                parsed: list[float | None] = []
                for column, channel in enumerate(channels):
                    value = _parse_measurement(raw.get(channel), context=f"line {line_no}, channel {channel}")
                    parsed.append(value)
                    if value is not None:
                        values[index, column] = value
                minute_ids[index] = stamp.toordinal() * 1440 + stamp.hour * 60 + stamp.minute
                month_ids[index] = stamp.year * 100 + stamp.month
                record = [stamp.isoformat(), parsed]
                digest.update(json.dumps(record, separators=(",", ":"), allow_nan=False).encode("utf-8"))
                digest.update(b"\\n")
                index += 1
        after = source.stat()
        if index != row_count or (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino
        ):
            raise ValueError("UCI file changed during two-pass ingestion")
        obj = cls.__new__(cls)
        obj._install(values, minute_ids, month_ids, channels, config, digest.hexdigest())
        return obj

    @property
    def input_width(self) -> int:
        c = len(self.channels)
        return (
            self.config.input_length * c
            + self.config.horizon * len(self.config.seasonal_lags) * c
            + (self.config.horizon * 4 if self.config.include_calendar else 0)
        )

    def _candidate_origins(self, split: str) -> range:
        if split not in self.bounds:
            raise ValueError(f"unknown split: {split}")
        if split == "test" and not self._test_authorized:
            raise PermissionError("test split is locked until hash-bound preregistration is verified")
        start, end = self.bounds[split]
        return range(max(self.config.input_length - 1, start), end - self.config.horizon)

    def _valid_mask(self, origins: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        cfg = self.config
        x_start = origins - cfg.input_length + 1
        x_end = origins + 1
        target_end = origins + cfg.horizon + 1
        x_missing = self._missing_prefix[x_end] - self._missing_prefix[x_start]
        target_missing = self._missing_prefix[target_end] - self._missing_prefix[x_end]

        steps = np.arange(1, cfg.horizon + 1, dtype=np.int64)
        lags = np.asarray(cfg.seasonal_lags, dtype=np.int64)
        sources = origins[:, None, None] + steps[None, :, None] - lags[None, None, :]
        invalid_source = (sources < 0) | (sources > origins[:, None, None])
        safe_sources = np.clip(sources, 0, self.n_rows - 1)
        seasonal_missing = np.isnan(self.values[safe_sources]).any(axis=(1, 2, 3))
        valid = (x_missing == 0) & (target_missing == 0) & (~invalid_source.any(axis=(1, 2))) & (~seasonal_missing)
        return valid, sources

    def _calendar(self, forecast_minute_ids: np.ndarray) -> np.ndarray:
        minute_of_day = forecast_minute_ids % 1440
        ordinal = forecast_minute_ids // 1440
        weekday = (ordinal - 1) % 7
        minute_angle = 2.0 * np.pi * minute_of_day / 1440.0
        weekday_angle = 2.0 * np.pi * weekday / 7.0
        return np.stack(
            (
                np.sin(minute_angle),
                np.cos(minute_angle),
                np.sin(weekday_angle),
                np.cos(weekday_angle),
            ),
            axis=-1,
        ).astype(np.float32, copy=False)

    def _make_batch(self, origins: np.ndarray, sources: np.ndarray) -> WindowBatch:
        cfg = self.config
        x_offsets = np.arange(-cfg.input_length + 1, 1, dtype=np.int64)
        target_offsets = np.arange(1, cfg.horizon + 1, dtype=np.int64)
        x = self.values[origins[:, None] + x_offsets[None, :]]
        target = self.values[origins[:, None] + target_offsets[None, :]]
        seasonal = self.values[sources]
        forecast_ids = self._minute_ids[origins[:, None] + target_offsets[None, :]]
        calendar = (
            self._calendar(forecast_ids)
            if cfg.include_calendar
            else np.empty((len(origins), cfg.horizon, 0), dtype=np.float32)
        )
        return WindowBatch(
            origin_indices=origins.copy(),
            inputs=InputBundle(x=x, seasonal=seasonal, calendar=calendar),
            target=target,
        )

    def iter_batches(self, split: str, *, batch_size: int = 256) -> Iterator[WindowBatch]:
        """Yield only valid windows; peak window memory is bounded by batch_size."""
        if type(batch_size) is not int or batch_size < 1 or batch_size > 8192:
            raise ValueError("batch_size must be an integer in [1, 8192]")
        c = len(self.channels)
        elements_per_window = (
            self.config.input_length * c
            + self.config.horizon * len(self.config.seasonal_lags) * c
            + self.config.horizon * c
            + (self.config.horizon * 4 if self.config.include_calendar else 0)
        )
        estimated_bytes = batch_size * elements_per_window * np.dtype(np.float32).itemsize
        if estimated_bytes > MAX_WINDOW_BATCH_BYTES:
            raise ValueError(
                f"window batch would require about {estimated_bytes} bytes; "
                f"limit is {MAX_WINDOW_BATCH_BYTES}"
            )
        origins_range = self._candidate_origins(split)
        for offset in range(origins_range.start, origins_range.stop, batch_size):
            origins = np.arange(offset, min(offset + batch_size, origins_range.stop), dtype=np.int64)
            valid, sources = self._valid_mask(origins)
            if not valid.any():
                continue
            yield self._make_batch(origins[valid], sources[valid])

    def split_stats(self, split: str, *, batch_size: int = 4096) -> SplitStats:
        """Scan candidates without materializing windows; report exact monthly rejection counts."""
        if type(batch_size) is not int or batch_size < 1 or batch_size > 8192:
            raise ValueError("batch_size must be an integer in [1, 8192]")
        c = len(self.channels)
        seasonal_work_bytes = batch_size * self.config.horizon * len(self.config.seasonal_lags) * (
            c * np.dtype(np.float32).itemsize + 2 * np.dtype(np.int64).itemsize
        )
        if seasonal_work_bytes > MAX_WINDOW_BATCH_BYTES:
            raise ValueError(
                f"statistics batch would require about {seasonal_work_bytes} bytes; "
                f"limit is {MAX_WINDOW_BATCH_BYTES}"
            )
        origins_range = self._candidate_origins(split)
        accepted_by_month: dict[str, int] = {}
        rejected_by_month: dict[str, int] = {}
        accepted = rejected = 0
        first_origin = last_origin = None
        for offset in range(origins_range.start, origins_range.stop, batch_size):
            origins = np.arange(offset, min(offset + batch_size, origins_range.stop), dtype=np.int64)
            valid, _ = self._valid_mask(origins)
            months = self._month_ids[origins]
            for month_id in np.unique(months):
                key = f"{int(month_id) // 100:04d}-{int(month_id) % 100:02d}"
                month_mask = months == month_id
                good = int(np.count_nonzero(valid & month_mask))
                bad = int(np.count_nonzero((~valid) & month_mask))
                if good:
                    accepted_by_month[key] = accepted_by_month.get(key, 0) + good
                if bad:
                    rejected_by_month[key] = rejected_by_month.get(key, 0) + bad
            if valid.any():
                valid_origins = origins[valid]
                if first_origin is None:
                    first_origin = self._format_minute(int(valid_origins[0]))
                last_origin = self._format_minute(int(valid_origins[-1]))
            accepted += int(valid.sum())
            rejected += int((~valid).sum())
        candidates = accepted + rejected
        return SplitStats(
            split=split,
            candidate_windows=candidates,
            accepted_windows=accepted,
            rejected_windows=rejected,
            rejection_fraction=(rejected / candidates if candidates else 0.0),
            first_origin=first_origin,
            last_origin=last_origin,
            accepted_by_month=dict(sorted(accepted_by_month.items())),
            rejected_by_month=dict(sorted(rejected_by_month.items())),
        )

    def _format_minute(self, index: int) -> str:
        minute_id = int(self._minute_ids[index])
        ordinal, minute = divmod(minute_id, 1440)
        return datetime.fromordinal(ordinal).replace(
            hour=minute // 60, minute=minute % 60
        ).isoformat()

    def open_test_split(
        self,
        *,
        preregistration_path: str | Path,
        preregistration_sha256: str,
        access_log_path: str | Path,
    ) -> SplitStats:
        """Verify exact preregistration and log opening before test batches can be iterated."""
        path = Path(preregistration_path)
        raw = path.read_bytes()
        actual_hash = hashlib.sha256(raw).hexdigest()
        if actual_hash != preregistration_sha256:
            raise PermissionError("preregistration file hash mismatch")
        prereg = json.loads(raw.decode("utf-8"))
        expected = {
            "data_config_sha256": self.config_sha256,
            "split_boundaries_sha256": self.split_sha256,
            "dataset_sha256": self.dataset_sha256,
        }
        for key, value in expected.items():
            if prereg.get(key) != value:
                raise PermissionError(f"preregistration mismatch: {key}")
        event = {
            "event": "TEST_SPLIT_OPENED",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "preregistration_sha256": actual_hash,
            **expected,
        }
        log_path = Path(access_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        # Authorize only after the audit event is durably written.
        self._test_authorized = True
        self._test_preregistration_sha256 = actual_hash
        return self.split_stats("test")

