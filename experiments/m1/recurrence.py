"""M1b fixed-step shared-weight recurrence ablation (validation only)."""
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

import torch

from .array_data import ArrayDataset
from .baselines import PersistenceBaseline
from .download_uci import DATASET_DOI, DATASET_LICENSE
from .jepa import (
    FrozenContextProbe,
    RecurrentDirectMAEForecaster,
    RecurrentJEPAForecaster,
    make_random_recurrent_context_probe,
    total_parameter_count,
    trainable_parameter_count,
)
from .metrics import evaluate_suite, write_result_atomic
from .provenance import current_git_commit
from .runner import (
    PilotConfig,
    TrainingWindowView,
    _count_train_windows,
    _load_download_manifest,
    _sha256_file,
)
from .training import (
    TorchBatchPredictor,
    build_seeded_model,
    evaluate_jepa,
    save_checkpoint_atomic,
    train_direct_mae,
    train_frozen_probe,
    train_jepa,
)


DEFAULT_STEPS = (1, 2, 4)


def _validate_steps(steps: tuple[int, ...]) -> tuple[int, ...]:
    if not steps or tuple(sorted(set(steps))) != steps:
        raise ValueError("recurrence steps must be a non-empty sorted unique tuple")
    if any(type(step) is not int or step not in DEFAULT_STEPS for step in steps):
        raise ValueError("M1b recurrence steps are restricted to 1, 2 and 4")
    return steps


def run_recurrence_ablation(
    dataset: ArrayDataset,
    config: PilotConfig,
    *,
    output_path: str | Path,
    steps: tuple[int, ...] = DEFAULT_STEPS,
    raw_file_sha256: str | None = None,
    raw_file_size_bytes: int | None = None,
    source_manifest: dict | None = None,
) -> tuple[dict, str]:
    """Run the fixed T=1/2/4 shared-block comparison on train and validation only.

    PilotConfig supplies the shared data, optimizer, seed, batch and metric
    settings. Its M1a model-selection tuple is intentionally ignored: M1b
    always evaluates persistence, JEPA-frozen probes, random recurrent probes
    and recurrent Direct-MAE for every selected recurrence step.
    """
    steps = _validate_steps(tuple(steps))
    if dataset.config != config.data_config():
        raise ValueError("recurrence pilot data config does not match loaded dataset")
    if source_manifest is not None and source_manifest.get("file_sha256") != raw_file_sha256:
        raise ValueError("download sidecar is not bound to the raw file hash")
    if config.batch_size < 2:
        raise ValueError("JEPA anti-collapse training requires batch_size >= 2")
    if config.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")

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

    destination = Path(output_path).resolve()
    if destination.exists():
        raise FileExistsError(f"result already exists; choose a new output path: {destination}")
    checkpoint_dir = destination.parent / f"{destination.stem}.checkpoints"
    if checkpoint_dir.exists():
        raise FileExistsError(f"checkpoint directory already exists: {checkpoint_dir}")

    base_model_config = config.model_config(dataset)
    runs = []
    training_manifest = []
    for seed in config.seeds:
        runs.append((PersistenceBaseline(), seed))
        for recurrence_steps in steps:
            model_config = replace(
                base_model_config,
                encoder_layers=1,
                recurrent_steps=recurrence_steps,
            )
            shared_steps = math.ceil(train_windows_per_epoch / config.batch_size)

            # JEPA pretraining is recorded separately; only its frozen probe
            # enters the raw-unit forecast comparison.
            jepa_model = build_seeded_model(
                RecurrentJEPAForecaster, model_config, seed
            )
            fit_started = time.perf_counter()
            jepa_history = train_jepa(
                jepa_model,
                train_view,
                epochs=config.epochs,
                batch_size=config.batch_size,
                learning_rate=config.learning_rate,
                weight_decay=config.weight_decay,
                seed=seed,
                device=config.device,
            )
            jepa_fit_seconds = time.perf_counter() - fit_started
            collapse = evaluate_jepa(
                jepa_model,
                dataset,
                "validation",
                batch_size=config.eval_batch_size,
                device=config.device,
            )
            jepa_path = checkpoint_dir / f"jepa-recurrent-t{recurrence_steps}-seed-{seed}.pt"
            jepa_hash = save_checkpoint_atomic(
                jepa_model,
                model_config,
                jepa_path,
                code_commit=code_commit,
                metadata={
                    "role": "latent-pretraining",
                    "recurrent_steps": recurrence_steps,
                    "shared_recurrent_block": True,
                    "seed": seed,
                    "train_windows_per_epoch": train_windows_per_epoch,
                },
            )
            training_manifest.append({
                "model": f"jepa_pretrain_t{recurrence_steps}",
                "role": "latent-pretraining-not-ranked-as-forecast",
                "seed": seed,
                "recurrent_steps": recurrence_steps,
                "shared_block_parameter_count": sum(
                    parameter.numel()
                    for parameter in jepa_model.context_encoder.recurrent_block.parameters()
                ),
                "history": jepa_history,
                "validation_collapse": collapse,
                "trainable_parameter_count": trainable_parameter_count(jepa_model),
                "total_parameter_count": total_parameter_count(jepa_model),
                "checkpoint_sha256": jepa_hash,
                "checkpoint_path": str(jepa_path),
                "fit_seconds": jepa_fit_seconds,
                "train_windows_per_epoch": train_windows_per_epoch,
                "train_steps_per_epoch": shared_steps,
                "training_window_cap": config.max_train_windows,
            })

            frozen_probe = FrozenContextProbe(
                jepa_model, model_config, readout_seed=seed
            )
            fit_started = time.perf_counter()
            frozen_history = train_frozen_probe(
                frozen_probe,
                train_view,
                epochs=config.epochs,
                batch_size=config.batch_size,
                learning_rate=config.learning_rate,
                weight_decay=config.weight_decay,
                seed=seed,
                device=config.device,
            )
            frozen_fit_seconds = time.perf_counter() - fit_started
            frozen_path = checkpoint_dir / f"jepa-frozen-probe-t{recurrence_steps}-seed-{seed}.pt"
            frozen_hash = save_checkpoint_atomic(
                frozen_probe,
                model_config,
                frozen_path,
                code_commit=code_commit,
                metadata={
                    "role": "frozen-jepa-probe",
                    "recurrent_steps": recurrence_steps,
                    "seed": seed,
                    "train_windows_per_epoch": train_windows_per_epoch,
                },
            )
            runs.append((
                TorchBatchPredictor(
                    frozen_probe,
                    name=f"jepa_frozen_probe_t{recurrence_steps}",
                    device=config.device,
                ),
                seed,
            ))
            training_manifest.append({
                "model": f"jepa_frozen_probe_t{recurrence_steps}",
                "role": "forecast-readout-over-frozen-jepa-context",
                "seed": seed,
                "recurrent_steps": recurrence_steps,
                "shared_block_parameter_count": sum(
                    parameter.numel()
                    for parameter in frozen_probe.encoder.recurrent_block.parameters()
                ),
                "history": frozen_history,
                "validation_collapse": None,
                "trainable_parameter_count": trainable_parameter_count(frozen_probe),
                "total_parameter_count": total_parameter_count(frozen_probe),
                "checkpoint_sha256": frozen_hash,
                "checkpoint_path": str(frozen_path),
                "fit_seconds": frozen_fit_seconds,
                "train_windows_per_epoch": train_windows_per_epoch,
                "train_steps_per_epoch": shared_steps,
                "training_window_cap": config.max_train_windows,
            })

            random_probe = make_random_recurrent_context_probe(
                model_config, seed
            )
            fit_started = time.perf_counter()
            random_history = train_frozen_probe(
                random_probe,
                train_view,
                epochs=config.epochs,
                batch_size=config.batch_size,
                learning_rate=config.learning_rate,
                weight_decay=config.weight_decay,
                seed=seed,
                device=config.device,
            )
            random_fit_seconds = time.perf_counter() - fit_started
            random_path = checkpoint_dir / f"random-recurrent-probe-t{recurrence_steps}-seed-{seed}.pt"
            random_hash = save_checkpoint_atomic(
                random_probe,
                model_config,
                random_path,
                code_commit=code_commit,
                metadata={
                    "role": "random-recurrent-probe",
                    "recurrent_steps": recurrence_steps,
                    "seed": seed,
                    "train_windows_per_epoch": train_windows_per_epoch,
                },
            )
            runs.append((
                TorchBatchPredictor(
                    random_probe,
                    name=f"random_recurrent_probe_t{recurrence_steps}",
                    device=config.device,
                ),
                seed,
            ))
            training_manifest.append({
                "model": f"random_recurrent_probe_t{recurrence_steps}",
                "role": "forecast-readout-over-random-frozen-recurrent-context",
                "seed": seed,
                "recurrent_steps": recurrence_steps,
                "shared_block_parameter_count": sum(
                    parameter.numel()
                    for parameter in random_probe.encoder.recurrent_block.parameters()
                ),
                "history": random_history,
                "validation_collapse": None,
                "trainable_parameter_count": trainable_parameter_count(random_probe),
                "total_parameter_count": total_parameter_count(random_probe),
                "checkpoint_sha256": random_hash,
                "checkpoint_path": str(random_path),
                "fit_seconds": random_fit_seconds,
                "train_windows_per_epoch": train_windows_per_epoch,
                "train_steps_per_epoch": shared_steps,
                "training_window_cap": config.max_train_windows,
            })

            direct_model = build_seeded_model(
                RecurrentDirectMAEForecaster, model_config, seed
            )
            fit_started = time.perf_counter()
            direct_history = train_direct_mae(
                direct_model,
                train_view,
                epochs=config.epochs,
                batch_size=config.batch_size,
                learning_rate=config.learning_rate,
                weight_decay=config.weight_decay,
                seed=seed,
                device=config.device,
            )
            direct_fit_seconds = time.perf_counter() - fit_started
            direct_path = checkpoint_dir / f"direct-mae-recurrent-t{recurrence_steps}-seed-{seed}.pt"
            direct_hash = save_checkpoint_atomic(
                direct_model,
                model_config,
                direct_path,
                code_commit=code_commit,
                metadata={
                    "role": "direct-mae-control",
                    "recurrent_steps": recurrence_steps,
                    "seed": seed,
                    "train_windows_per_epoch": train_windows_per_epoch,
                },
            )
            runs.append((
                TorchBatchPredictor(
                    direct_model,
                    name=f"recurrent_direct_mae_t{recurrence_steps}",
                    device=config.device,
                ),
                seed,
            ))
            training_manifest.append({
                "model": f"recurrent_direct_mae_t{recurrence_steps}",
                "role": "raw-unit-direct-mae-control",
                "seed": seed,
                "recurrent_steps": recurrence_steps,
                "shared_block_parameter_count": sum(
                    parameter.numel()
                    for parameter in direct_model.context_encoder.recurrent_block.parameters()
                ),
                "history": direct_history,
                "validation_collapse": None,
                "trainable_parameter_count": trainable_parameter_count(direct_model),
                "total_parameter_count": total_parameter_count(direct_model),
                "checkpoint_sha256": direct_hash,
                "checkpoint_path": str(direct_path),
                "fit_seconds": direct_fit_seconds,
                "train_windows_per_epoch": train_windows_per_epoch,
                "train_steps_per_epoch": shared_steps,
                "training_window_cap": config.max_train_windows,
            })

    result = evaluate_suite(
        runs,
        dataset,
        split="validation",
        reference_model="persistence",
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
        "profile": "m1b-shared-weight-recurrence-ablation",
        "status": "VALIDATION_ONLY_NOT_PROMOTED",
        "code_commit": code_commit,
        "started_utc": started_utc.isoformat(),
        "finished_utc": finished_utc.isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "config": asdict(config),
        "recurrence_steps": list(steps),
        "shared_block_parameter_count_constant_across_steps": True,
        "test_split_accessed": False,
        "hyperparameters_locked": False,
        "promotion_status": "NOT_ASSESSED",
        "notes": [
            "M1a's stacked encoder remains unchanged.",
            "M1b reuses one TransformerEncoderLayer T times with deterministic step embeddings.",
            "The M1a PilotConfig.models tuple is not used; M1b always runs the same four-role comparison per seed.",
            "JEPA latent loss and collapse telemetry are not ranked as raw-unit forecast MAE.",
            "The optional training-window cap limits fit batches only; all validation origins are evaluated.",
            "The test split remains locked and is never opened by this runner.",
            "The UCI cohort is one household and does not establish population-level generalization.",
        ],
    }
    result["data_provenance"] = {
        "dataset": "Individual Household Electric Power Consumption",
        "doi": DATASET_DOI,
        "license": DATASET_LICENSE,
        "raw_file_sha256": raw_file_sha256,
        "raw_file_size_bytes": raw_file_size_bytes,
        "download_manifest": source_manifest,
        "parsed_dataset_sha256": dataset.dataset_sha256,
        "data_config_sha256": dataset.config_sha256,
        "split_boundaries_sha256": dataset.split_sha256,
        "channels": list(dataset.channels),
        "n_rows": dataset.n_rows,
        "train": asdict(train_stats),
        "validation": asdict(validation_stats),
    }
    result["training_manifest"] = training_manifest
    digest = write_result_atomic(result, destination)
    return result, digest


def run_uci_recurrence_ablation(
    data_path: str | Path,
    output_path: str | Path,
    config: PilotConfig,
    *,
    steps: tuple[int, ...] = DEFAULT_STEPS,
) -> tuple[dict, str]:
    """Load the local official UCI file and run the M1b validation-only sweep."""
    source = Path(data_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == Path(output_path).resolve():
        raise ValueError("result output must not overwrite the UCI source file")
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
    source_manifest = _load_download_manifest(source, raw_hash)
    return run_recurrence_ablation(
        dataset,
        config,
        output_path=output_path,
        steps=steps,
        raw_file_sha256=raw_hash,
        raw_file_size_bytes=after.st_size,
        source_manifest=source_manifest,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="path to local household_power_consumption.txt")
    parser.add_argument("--output", default="experiments/results/m1b-recurrence.json")
    parser.add_argument("--config", help="optional JSON PilotConfig override")
    parser.add_argument("--steps", default="1,2,4", help="fixed shared-recurrence steps, e.g. 1,2,4")
    args = parser.parse_args(argv)
    config = PilotConfig.from_json(args.config) if args.config else PilotConfig()
    steps = tuple(int(part.strip()) for part in args.steps.split(",") if part.strip())
    result, digest = run_uci_recurrence_ablation(
        args.data, args.output, config, steps=steps
    )
    models = result["paired_block_bootstrap"]["models"]
    print(json.dumps({
        "status": result["experiment"]["status"],
        "code_commit": result["experiment"]["code_commit"],
        "output": str(Path(args.output)),
        "result_sha256": digest,
        "recurrence_steps": result["experiment"]["recurrence_steps"],
        "validation_models": {
            name: {
                "mae": metrics["mae"],
                "delta_vs_reference": metrics["delta_vs_reference"],
                "delta_ci": metrics["delta_ci"],
            }
            for name, metrics in models.items()
        },
        "test_split_accessed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
