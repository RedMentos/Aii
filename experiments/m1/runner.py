"""Executable validation-only M1 experiment runner.

This runner is deliberately an exploratory pilot: it uses the fixed calendar
train/validation split, never opens the test split, caps only model-fitting
windows when requested, and evaluates every predictor on the same full
validation origins. It writes provenance, parameter counts, checkpoints and
paired temporal-block uncertainty to an atomic JSON result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import numpy as np
import torch

from .array_data import ArrayDataset, InputBundle, WindowBatch
from .baselines import (
    LADARBaseline,
    PersistenceBaseline,
    RidgeARBaseline,
    SeasonalPersistenceBaseline,
    TrainMeanBaseline,
    TrainMedianBaseline,
)
from .data import DataConfig
from .dlinear import MatchedDLinearForecaster, MatchedNLinearForecaster
from .gru import RawGRUForecaster
from .jepa import (
    DirectMAEForecaster,
    FrozenContextProbe,
    JEPAConfig,
    JEPAForecaster,
    make_random_context_probe,
    total_parameter_count,
    trainable_parameter_count,
)
from .metrics import evaluate_suite, write_result_atomic
from .provenance import current_git_commit
from .raw_probes import RawWindowMLP, RawWindowProbe
from .training import (
    TorchBatchPredictor,
    build_seeded_model,
    evaluate_jepa,
    save_checkpoint_atomic,
    train_direct_mae,
    train_frozen_probe,
    train_jepa,
    train_raw_gru,
)


MODEL_NAMES = frozenset({
    "persistence",
    "seasonal_persistence_lag_0",
    "seasonal_persistence_lag_1",
    "train_mean",
    "train_median",
    "ridge_ar_l2",
    "lad_ar_l1_l2penalty",
    "raw_window_probe",
    "raw_window_mlp",
    "matched_dlinear",
    "matched_nlinear",
    "raw_gru",
    "jepa",
    "direct_mae",
    "frozen_context_probe",
    "random_context_probe",
})


@dataclass(frozen=True)
class PilotConfig:
    """Exploratory settings; these defaults are not a preregistration or promotion gate."""

    input_length: int = 1440
    horizon: int = 60
    max_candidate_input_length: int = 10080
    seasonal_lags: tuple[int, ...] = (1440, 10080)
    include_calendar: bool = True
    primary_channel: str = "Global_active_power"
    validation_start: str | None = "2008-12-01T00:00"
    test_start: str | None = "2009-12-01T00:00"
    split_gap: int | None = None

    models: tuple[str, ...] = (
        "persistence",
        "seasonal_persistence_lag_0",
        "seasonal_persistence_lag_1",
        "train_mean",
        "train_median",
        "matched_dlinear",
        "matched_nlinear",
        "jepa",
        "direct_mae",
        "raw_gru",
    )
    seeds: tuple[int, ...] = (17, 23, 29)
    reference_model: str = "persistence"

    batch_size: int = 128
    eval_batch_size: int = 1024
    max_train_windows: int | None = 4096
    epochs: int = 1
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    device: str = "cpu"

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

    dlinear_kernel_size: int = 25
    gru_hidden_size: int = 64
    raw_mlp_hidden_size: int = 64
    ar_lags: tuple[int, ...] = (1, 60, 1440)
    ar_alpha: float = 1.0

    primary_start: int = 15
    primary_end: int = 60
    report_horizons: tuple[int, ...] = (15, 30, 60)
    bootstrap_block_len_minutes: int = 10080
    bootstrap_resamples: int = 2000
    bootstrap_seed: int = 17

    def __post_init__(self) -> None:
        for name in ("input_length", "horizon", "max_candidate_input_length",
                     "batch_size", "eval_batch_size", "epochs", "patch_size",
                     "d_model", "n_heads", "encoder_layers", "predictor_layers",
                     "dlinear_kernel_size", "gru_hidden_size", "raw_mlp_hidden_size",
                     "bootstrap_block_len_minutes", "bootstrap_resamples"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.input_length > self.max_candidate_input_length:
            raise ValueError("input_length exceeds max_candidate_input_length")
        if self.d_model % self.n_heads:
            raise ValueError("d_model must be divisible by n_heads")
        if self.dlinear_kernel_size % 2 == 0:
            raise ValueError("dlinear_kernel_size must be odd")
        if self.batch_size > 8192 or self.eval_batch_size > 8192:
            raise ValueError("batch sizes must not exceed 8192")
        if self.max_train_windows is not None and (
            type(self.max_train_windows) is not int or self.max_train_windows < 1
        ):
            raise ValueError("max_train_windows must be a positive integer or None")
        if not self.seasonal_lags or any(
            type(lag) is not int or lag < self.horizon for lag in self.seasonal_lags
        ):
            raise ValueError("seasonal_lags must be integers >= horizon")
        if len(set(self.seasonal_lags)) != len(self.seasonal_lags):
            raise ValueError("seasonal_lags must be unique")
        if not self.models or any(name not in MODEL_NAMES for name in self.models):
            raise ValueError("models contains an unknown name or is empty")
        if len(set(self.models)) != len(self.models):
            raise ValueError("models must not contain duplicates")
        if self.reference_model not in self.models:
            raise ValueError("reference_model must be included in models")
        if "seasonal_persistence_lag_1" in self.models and len(self.seasonal_lags) < 2:
            raise ValueError("seasonal_persistence_lag_1 requires at least two seasonal lags")
        if "frozen_context_probe" in self.models:
            if "jepa" not in self.models or self.models.index("jepa") > self.models.index("frozen_context_probe"):
                raise ValueError("frozen_context_probe requires jepa earlier in models")
        if not self.seeds or any(type(seed) is not int for seed in self.seeds):
            raise ValueError("seeds must be a non-empty sequence of integers")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("seeds must be unique")
        if not self.ar_lags or any(type(lag) is not int or lag < 1 for lag in self.ar_lags):
            raise ValueError("ar_lags must be positive integers")
        if not 1 <= self.primary_start <= self.primary_end <= self.horizon:
            raise ValueError("primary horizon bounds must lie inside horizon")
        if not self.report_horizons or any(
            type(h) is not int or not 1 <= h <= self.horizon for h in self.report_horizons
        ):
            raise ValueError("report_horizons must be within horizon")
        if tuple(sorted(set(self.report_horizons))) != self.report_horizons:
            raise ValueError("report_horizons must be sorted and unique")
        if not np.isfinite(self.learning_rate) or self.learning_rate <= 0:
            raise ValueError("learning_rate must be finite and positive")
        if not np.isfinite(self.weight_decay) or self.weight_decay < 0:
            raise ValueError("weight_decay must be finite and non-negative")
        if not np.isfinite(self.ar_alpha) or self.ar_alpha <= 0:
            raise ValueError("ar_alpha must be finite and positive")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must lie in [0, 1)")
        if not 0.0 <= self.ema_start <= self.ema_end <= 1.0:
            raise ValueError("EMA rates must satisfy 0 <= start <= end <= 1")
        if self.lambda_variance < 0 or self.lambda_covariance < 0:
            raise ValueError("anti-collapse weights must be non-negative")
        if self.device != "cpu" and not self.device.startswith("cuda"):
            raise ValueError("device must be 'cpu' or a CUDA device string")
        if (self.validation_start is None) != (self.test_start is None):
            raise ValueError("validation_start and test_start must be set together")

    @classmethod
    def from_json(cls, path: str | Path) -> "PilotConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("pilot config JSON must contain an object")
        allowed = {field.name for field in fields(cls)}
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(f"unknown pilot config fields: {sorted(unknown)}")
        for key in ("seasonal_lags", "models", "seeds", "ar_lags", "report_horizons"):
            if key in raw:
                raw[key] = tuple(raw[key])
        return cls(**raw)

    def data_config(self) -> DataConfig:
        return DataConfig(
            input_length=self.input_length,
            horizon=self.horizon,
            max_candidate_input_length=self.max_candidate_input_length,
            primary_channel=self.primary_channel,
            seasonal_lags=self.seasonal_lags,
            include_calendar=self.include_calendar,
            split_gap=self.split_gap,
            validation_start=self.validation_start,
            test_start=self.test_start,
        )

    def model_config(self, dataset: ArrayDataset) -> JEPAConfig:
        return JEPAConfig(
            input_channels=len(dataset.channels),
            seasonal_lags=len(dataset.config.seasonal_lags),
            horizon=dataset.config.horizon,
            calendar_features=4 if dataset.config.include_calendar else 0,
            patch_size=self.patch_size,
            d_model=self.d_model,
            n_heads=self.n_heads,
            encoder_layers=self.encoder_layers,
            predictor_layers=self.predictor_layers,
            dropout=self.dropout,
            ema_start=self.ema_start,
            ema_end=self.ema_end,
            lambda_variance=self.lambda_variance,
            lambda_covariance=self.lambda_covariance,
        )


class TrainingWindowView:
    """Delegate to ArrayDataset while limiting only accepted training windows."""

    def __init__(self, dataset: ArrayDataset, max_train_windows: int | None):
        self._dataset = dataset
        self.max_train_windows = max_train_windows

    def __getattr__(self, name):
        return getattr(self._dataset, name)

    def iter_batches(
        self,
        split: str,
        *,
        batch_size: int = 256,
        shuffle: bool = False,
        seed: int = 17,
    ) -> Iterator[WindowBatch]:
        stream = self._dataset.iter_batches(
            split, batch_size=batch_size, shuffle=shuffle, seed=seed
        )
        if split != "train" or self.max_train_windows is None:
            yield from stream
            return
        remaining = self.max_train_windows
        for batch in stream:
            if remaining <= 0:
                break
            count = min(len(batch.origin_indices), remaining)
            if count == len(batch.origin_indices):
                yield batch
            else:
                yield WindowBatch(
                    origin_indices=batch.origin_indices[:count].copy(),
                    inputs=InputBundle(
                        x=batch.inputs.x[:count],
                        seasonal=batch.inputs.seasonal[:count],
                        calendar=batch.inputs.calendar[:count],
                    ),
                    target=batch.target[:count],
                )
            remaining -= count


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_train_windows(dataset: TrainingWindowView, batch_size: int) -> int:
    return sum(
        len(batch.origin_indices)
        for batch in dataset.iter_batches("train", batch_size=batch_size, shuffle=False)
    )


def _parameter_counts(model_or_predictor) -> tuple[int, int]:
    model = getattr(model_or_predictor, "model", model_or_predictor)
    if isinstance(model, torch.nn.Module):
        return trainable_parameter_count(model), total_parameter_count(model)
    count = int(getattr(model, "parameter_count", 0))
    return count, count


def _fit_one(
    name: str,
    seed: int,
    dataset: ArrayDataset,
    train_view: TrainingWindowView,
    config: PilotConfig,
    model_config: JEPAConfig,
    checkpoint_dir: Path,
    code_commit: str,
    jepa_model: JEPAForecaster | None,
):
    started = time.perf_counter()
    history = []
    collapse = None
    checkpoint_sha256 = None
    checkpoint_path = None
    extra = {}
    model = None

    if name == "persistence":
        predictor = PersistenceBaseline()
    elif name == "seasonal_persistence_lag_0":
        predictor = SeasonalPersistenceBaseline(0)
    elif name == "seasonal_persistence_lag_1":
        predictor = SeasonalPersistenceBaseline(1)
    elif name == "train_mean":
        predictor = TrainMeanBaseline().fit(dataset)
    elif name == "train_median":
        predictor = TrainMedianBaseline().fit(dataset)
    elif name == "ridge_ar_l2":
        predictor = RidgeARBaseline(alpha=config.ar_alpha, ar_lags=config.ar_lags).fit(train_view)
        extra["n_train_windows"] = predictor.n_train_windows
        extra["selected_ar_lags"] = list(predictor.selected_ar_lags)
    elif name == "lad_ar_l1_l2penalty":
        predictor = LADARBaseline(
            alpha=config.ar_alpha,
            ar_lags=config.ar_lags,
            epochs=config.epochs,
            learning_rate=config.learning_rate,
            seed=seed,
        ).fit(train_view)
        history = [{"epoch": float(i + 1), "objective": float(value)}
                   for i, value in enumerate(predictor.epoch_losses)]
        extra["n_train_windows"] = predictor.n_train_windows
        extra["selected_ar_lags"] = list(predictor.selected_ar_lags)
    elif name == "raw_window_probe":
        predictor = RawWindowProbe(
            epochs=config.epochs,
            learning_rate=config.learning_rate,
            weight_decay=config.weight_decay,
            seed=seed,
            batch_size=config.batch_size,
        ).fit(train_view)
        history = [{"epoch": float(i + 1), "mae": float(value)}
                   for i, value in enumerate(predictor.epoch_mae)]
        extra["n_train_windows"] = predictor.n_train_windows
    elif name == "raw_window_mlp":
        predictor = RawWindowMLP(
            hidden_width=config.raw_mlp_hidden_size,
            epochs=config.epochs,
            learning_rate=config.learning_rate,
            weight_decay=config.weight_decay,
            seed=seed,
            batch_size=config.batch_size,
        ).fit(train_view)
        history = [{"epoch": float(i + 1), "mae": float(value)}
                   for i, value in enumerate(predictor.epoch_mae)]
        extra["n_train_windows"] = predictor.n_train_windows
    elif name == "matched_dlinear":
        model = build_seeded_model(
            MatchedDLinearForecaster,
            model_config,
            seed,
            input_length=dataset.config.input_length,
            kernel_size=config.dlinear_kernel_size,
        )
        history = train_direct_mae(
            model, train_view, epochs=config.epochs, batch_size=config.batch_size,
            learning_rate=config.learning_rate, weight_decay=config.weight_decay,
            seed=seed, device=config.device,
        )
    elif name == "matched_nlinear":
        model = build_seeded_model(
            MatchedNLinearForecaster,
            model_config,
            seed,
            input_length=dataset.config.input_length,
        )
        history = train_direct_mae(
            model, train_view, epochs=config.epochs, batch_size=config.batch_size,
            learning_rate=config.learning_rate, weight_decay=config.weight_decay,
            seed=seed, device=config.device,
        )
    elif name == "raw_gru":
        model = build_seeded_model(
            RawGRUForecaster, model_config, seed, hidden_size=config.gru_hidden_size
        )
        history = train_raw_gru(
            model, train_view, epochs=config.epochs, batch_size=config.batch_size,
            learning_rate=config.learning_rate, weight_decay=config.weight_decay,
            seed=seed, device=config.device,
        )
    elif name == "jepa":
        model = build_seeded_model(JEPAForecaster, model_config, seed)
        history = train_jepa(
            model, train_view, epochs=config.epochs, batch_size=config.batch_size,
            learning_rate=config.learning_rate, weight_decay=config.weight_decay,
            seed=seed, device=config.device,
        )
        collapse = evaluate_jepa(
            model, dataset, "validation", batch_size=config.eval_batch_size,
            device=config.device,
        )
    elif name == "direct_mae":
        model = build_seeded_model(DirectMAEForecaster, model_config, seed)
        history = train_direct_mae(
            model, train_view, epochs=config.epochs, batch_size=config.batch_size,
            learning_rate=config.learning_rate, weight_decay=config.weight_decay,
            seed=seed, device=config.device,
        )
    elif name == "frozen_context_probe":
        if jepa_model is None:
            raise ValueError("frozen_context_probe requires the trained JEPA model for this seed")
        model = FrozenContextProbe(jepa_model, model_config, readout_seed=seed)
        history = train_frozen_probe(
            model, train_view, epochs=config.epochs, batch_size=config.batch_size,
            learning_rate=config.learning_rate, weight_decay=config.weight_decay,
            seed=seed, device=config.device,
        )
    elif name == "random_context_probe":
        model = make_random_context_probe(model_config, seed)
        history = train_frozen_probe(
            model, train_view, epochs=config.epochs, batch_size=config.batch_size,
            learning_rate=config.learning_rate, weight_decay=config.weight_decay,
            seed=seed, device=config.device,
        )
    else:
        raise ValueError(f"unsupported model: {name}")

    if model is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint = checkpoint_dir / f"{name}-seed-{seed}.pt"
        checkpoint_sha256 = save_checkpoint_atomic(
            model,
            model_config,
            checkpoint,
            code_commit=code_commit,
            metadata={
                "model": name,
                "seed": seed,
                "input_length": dataset.config.input_length,
                "training_window_cap": config.max_train_windows,
                "epochs": config.epochs,
                "device": config.device,
            },
        )
        checkpoint_path = str(checkpoint)
        predictor = TorchBatchPredictor(model, name=name, device=config.device)

    trainable, total = _parameter_counts(model if model is not None else predictor)
    if name in {"train_mean", "train_median"}:
        extra["n_unique_target_rows"] = predictor.n_unique_target_rows
    if hasattr(predictor, "parameter_count"):
        extra["parameter_count"] = int(predictor.parameter_count)

    manifest = {
        "model": name,
        "seed": seed,
        "history": history,
        "validation_collapse": collapse,
        "trainable_parameter_count": trainable,
        "total_parameter_count": total,
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_path": checkpoint_path,
        "fit_seconds": time.perf_counter() - started,
        "training_window_cap": config.max_train_windows,
        **extra,
    }
    return predictor, manifest, (model if name == "jepa" else None)


def run_validation_experiment(
    dataset: ArrayDataset,
    config: PilotConfig,
    *,
    output_path: str | Path,
    raw_file_sha256: str | None = None,
    raw_file_size_bytes: int | None = None,
) -> tuple[dict, str]:
    """Train selected models on train only and compare them on full validation only."""
    if dataset.config != config.data_config():
        raise ValueError("pilot data config does not match loaded dataset config")
    if config.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    if "jepa" in config.models and config.batch_size < 2:
        raise ValueError("JEPA anti-collapse training requires batch_size >= 2")

    repo_root = Path(__file__).resolve().parents[2]
    code_commit = current_git_commit(repo_root)
    started_utc = datetime.now(timezone.utc)
    started = time.perf_counter()

    train_stats = dataset.split_stats("train", batch_size=8192)
    validation_stats = dataset.split_stats("validation", batch_size=8192)
    if train_stats.accepted_windows < 1 or validation_stats.accepted_windows < 2:
        raise ValueError("train/validation split has too few accepted windows")
    train_view = TrainingWindowView(dataset, config.max_train_windows)
    train_windows_per_epoch = _count_train_windows(train_view, config.batch_size)
    if train_windows_per_epoch < 1:
        raise ValueError("training window cap leaves no accepted training windows")

    model_config = config.model_config(dataset)
    checkpoint_dir = Path(output_path).resolve().parent / "checkpoints"
    runs = []
    manifest = []

    for seed in config.seeds:
        jepa_model = None
        for name in config.models:
            predictor, entry, trained_jepa = _fit_one(
                name, seed, dataset, train_view, config, model_config,
                checkpoint_dir, code_commit, jepa_model,
            )
            if trained_jepa is not None:
                jepa_model = trained_jepa
            runs.append((predictor, seed))
            manifest.append({
                **entry,
                "train_windows_per_epoch": (
                    train_windows_per_epoch
                    if name not in {"persistence", "seasonal_persistence_lag_0",
                                    "seasonal_persistence_lag_1", "train_mean", "train_median"}
                    else 0
                ),
                "train_steps_per_epoch": (
                    math.ceil(train_windows_per_epoch / config.batch_size)
                    if name not in {"persistence", "seasonal_persistence_lag_0",
                                    "seasonal_persistence_lag_1", "train_mean", "train_median"}
                    else 0
                ),
            })

    result = evaluate_suite(
        runs,
        dataset,
        split="validation",
        reference_model=config.reference_model,
        code_commit=code_commit,
        primary_start=config.primary_start,
        primary_end=config.primary_end,
        report_horizons=config.report_horizons,
        block_len_minutes=config.bootstrap_block_len_minutes,
        n_resamples=config.bootstrap_resamples,
        bootstrap_seed=config.bootstrap_seed,
        batch_size=config.eval_batch_size,
    )
    finished_utc = datetime.now(timezone.utc)
    result["experiment"] = {
        "profile": "exploratory-validation-pilot",
        "status": "VALIDATION_ONLY_NOT_PROMOTED",
        "code_commit": code_commit,
        "started_utc": started_utc.isoformat(),
        "finished_utc": finished_utc.isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "config": asdict(config),
        "test_split_accessed": False,
        "hyperparameters_locked": False,
        "promotion_status": "NOT_ASSESSED",
        "notes": [
            "This run is exploratory and does not lock hyperparameters.",
            "The optional training-window cap applies only to model fitting; validation uses every accepted validation origin.",
            "The test split remains locked and is never opened by this runner.",
            "The UCI cohort is one household and does not establish population-level generalization.",
        ],
    }
    result["data_provenance"] = {
        "dataset": "Individual Household Electric Power Consumption",
        "doi": "10.24432/C58K54",
        "license": "CC BY 4.0",
        "citation": "Hebrail, G. & Berard, A. (2006). Individual Household Electric Power Consumption [Dataset]. UCI Machine Learning Repository.",
        "raw_file_sha256": raw_file_sha256,
        "raw_file_size_bytes": raw_file_size_bytes,
        "parsed_dataset_sha256": dataset.dataset_sha256,
        "data_config_sha256": dataset.config_sha256,
        "split_boundaries_sha256": dataset.split_sha256,
        "channels": list(dataset.channels),
        "n_rows": dataset.n_rows,
        "train": asdict(train_stats),
        "validation": asdict(validation_stats),
    }
    result["training_manifest"] = manifest
    digest = write_result_atomic(result, output_path)
    return result, digest


def run_uci_validation(
    data_path: str | Path,
    output_path: str | Path,
    config: PilotConfig,
) -> tuple[dict, str]:
    """Load the official UCI file and run the validation-only pilot."""
    source = Path(data_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    if config.validation_start is None or config.test_start is None:
        raise ValueError("real UCI runs require fixed validation_start and test_start dates")
    before = source.stat()
    dataset = ArrayDataset.from_uci(source, config.data_config())
    raw_hash = _sha256_file(source)
    after = source.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size, after.st_mtime_ns, after.st_ino
    ):
        raise ValueError("UCI file changed while the runner computed provenance")
    return run_validation_experiment(
        dataset,
        config,
        output_path=output_path,
        raw_file_sha256=raw_hash,
        raw_file_size_bytes=after.st_size,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="path to the local UCI household_power_consumption.txt")
    parser.add_argument("--output", default="experiments/results/m1-validation-pilot.json")
    parser.add_argument("--config", help="optional JSON PilotConfig override")
    args = parser.parse_args(argv)
    config = PilotConfig.from_json(args.config) if args.config else PilotConfig()
    result, digest = run_uci_validation(args.data, args.output, config)
    bootstrap = result["paired_block_bootstrap"]["models"]
    print(json.dumps({
        "status": result["experiment"]["status"],
        "code_commit": result["experiment"]["code_commit"],
        "output": str(Path(args.output)),
        "result_sha256": digest,
        "validation_models": {
            name: {
                "mae": metrics["mae"],
                "delta_vs_reference": metrics["delta_vs_reference"],
                "delta_ci": metrics["delta_ci"],
            }
            for name, metrics in bootstrap.items()
        },
        "test_split_accessed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
