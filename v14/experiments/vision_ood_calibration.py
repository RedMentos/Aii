"""Source-disjoint A3 tile-descriptor OOD calibration ablation.

Research-only diagnostic. It uses the existing V13 RAW-EYE 37-D tile
representation and compares:
- the production RMS-z leave-one-source-out threshold;
- diagonal-shrinkage Mahalanobis with the same source-disjoint heuristic;
- source-level split-conformal thresholds for each fixed score.

Conformal calibration uses the maximum tile score per source as the exchangeable
unit. Its finite-sample statement is marginal over source groups, conditional on
the fitted score and under source-group exchangeability; it is not a per-tile
conditional guarantee. No production threshold, model, weight, permission,
Runtime behavior or persistent user data is changed.

Run from the repository root with PYTHONPATH=v13/code:
    python v14/experiments/vision_ood_calibration.py --repeats 30
"""
from __future__ import annotations

import argparse
import json
import math
from collections.abc import Callable, Sequence

import numpy as np
from PIL import Image, ImageDraw

from v13 import vision

ScoreFunction = Callable[[np.ndarray, np.ndarray], np.ndarray]
SHIFT_KINDS = ("black", "checker", "invert", "noise", "posterize")


def make_synthetic_ui(seed: int) -> Image.Image:
    """Generate a small UI-like source with randomized bounded layout/style."""
    rng = np.random.default_rng(seed)
    bg = tuple(int(x) for x in rng.integers(235, 253, 3))
    image = Image.new("RGB", (64, 64), bg)
    draw = ImageDraw.Draw(image)
    header = tuple(int(x) for x in rng.integers([20, 70, 120], [65, 145, 220]))
    draw.rectangle((0, 0, 63, 8), fill=header)
    side = tuple(int(x) for x in rng.integers([210, 215, 220], [245, 250, 255]))
    draw.rectangle((0, 9, 10, 63), fill=side)
    for index in range(3):
        y = 13 + index * 15
        colour = tuple(int(x) for x in rng.integers(60, 190, 3))
        x = int(rng.integers(15, 29))
        width = int(rng.integers(20, 38))
        draw.rounded_rectangle((x, y, min(62, x + width), y + 10), radius=2, fill=colour)
        draw.rectangle((x + 3, y + 3, min(60, x + width - 3), y + 5), fill=(245, 245, 245))
    cx = int(rng.integers(18, 58))
    cy = int(rng.integers(14, 58))
    radius = int(rng.integers(2, 5))
    colour = tuple(int(x) for x in rng.integers(30, 230, 3))
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=colour)
    return image


def apply_synthetic_shift(image: Image.Image, kind: str, seed: int) -> Image.Image:
    """Apply controlled pixel shifts; these are stressors, not real OOD labels."""
    array = np.asarray(image, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    if kind == "black":
        shifted = np.zeros_like(array)
    elif kind == "checker":
        yy, xx = np.indices(array.shape[:2])
        mask = ((xx + yy) % 2) * 255
        shifted = np.repeat(mask[..., None].astype(np.uint8), 3, axis=2)
    elif kind == "invert":
        shifted = 255 - array
    elif kind == "noise":
        shifted = rng.integers(0, 256, array.shape, dtype=np.uint8)
    elif kind == "posterize":
        shifted = (array // 64) * 64
    else:
        raise ValueError(f"unknown synthetic shift: {kind}")
    return Image.fromarray(shifted, "RGB")


def tile_matrix(
    images: Sequence[Image.Image], source_prefix: str, cfg: dict | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract production 37-D tile features and preserve source/tile grouping."""
    cfg = cfg or vision.DEFAULTS
    rows: list[np.ndarray] = []
    groups: list[str] = []
    keys: list[str] = []
    for image_index, image in enumerate(images):
        source_id = f"{source_prefix}-{image_index:03d}"
        for region in vision.boxes(image.width, image.height, cfg["grid"]):
            if not region["region_id"].startswith("r"):
                continue
            tile = image.crop(tuple(region["box"]))
            try:
                feature = vision.tile_features(tile, cfg["tile_px"])
            finally:
                tile.close()
            rows.append(np.asarray(feature, dtype=np.float64))
            groups.append(source_id)
            keys.append(f"{source_id}:{region['region_id']}")
    if not rows:
        return np.empty((0, 37), dtype=np.float64), np.empty((0,), dtype=str), []
    return np.stack(rows), np.asarray(groups), keys


def rms_z_scores(train: np.ndarray, rows: np.ndarray) -> np.ndarray:
    """Existing diagonal RMS-z nonconformity score; larger means less ID-like."""
    train = np.asarray(train, dtype=np.float64)
    rows = np.asarray(rows, dtype=np.float64)
    if (
        train.ndim != 2 or rows.ndim != 2 or train.shape[1] != rows.shape[1]
        or len(train) < 2 or not np.isfinite(train).all() or not np.isfinite(rows).all()
    ):
        raise ValueError("RMS-z feature geometry is invalid")
    mean = train.mean(axis=0)
    std = train.std(axis=0) + 1e-6
    score = np.sqrt(np.mean(((rows - mean) / std) ** 2, axis=1))
    if not np.isfinite(score).all():
        raise ValueError("RMS-z score is non-finite")
    return score


def shrinkage_mahalanobis_scores(
    train: np.ndarray, rows: np.ndarray, shrinkage: float = 0.25,
) -> np.ndarray:
    """Mahalanobis score with covariance shrunk toward its diagonal; NumPy only."""
    train = np.asarray(train, dtype=np.float64)
    rows = np.asarray(rows, dtype=np.float64)
    if (
        train.ndim != 2 or rows.ndim != 2 or train.shape[1] != rows.shape[1]
        or len(train) < 2 or isinstance(shrinkage, bool)
        or not 0.0 <= shrinkage <= 1.0
        or not np.isfinite(train).all() or not np.isfinite(rows).all()
    ):
        raise ValueError("shrinkage Mahalanobis input is invalid")
    mean = train.mean(axis=0)
    centered = train - mean
    covariance = centered.T @ centered / max(1, len(train) - 1)
    diagonal = np.diag(np.diag(covariance))
    covariance = (1.0 - shrinkage) * covariance + shrinkage * diagonal
    scale = max(1e-8, float(np.trace(covariance) / covariance.shape[0]))
    covariance = covariance + np.eye(covariance.shape[0]) * (scale * 1e-5)
    delta = rows - mean
    solved = np.linalg.solve(covariance, delta.T).T
    squared = np.einsum("ij,ij->i", delta, solved) / train.shape[1]
    score = np.sqrt(np.maximum(squared, 0.0))
    if not np.isfinite(score).all():
        raise ValueError("shrinkage Mahalanobis score is non-finite")
    return score


def source_max_scores(scores: np.ndarray, groups: np.ndarray) -> tuple[np.ndarray, list[str]]:
    scores = np.asarray(scores, dtype=np.float64)
    groups = np.asarray(groups)
    if (
        scores.ndim != 1 or groups.ndim != 1 or len(scores) != len(groups)
        or not np.isfinite(scores).all()
    ):
        raise ValueError("source score grouping is invalid")
    names = sorted(set(str(value) for value in groups))
    maxima = np.asarray([np.max(scores[groups == name]) for name in names], dtype=np.float64)
    return maxima, names


def conformal_source_threshold(source_scores: np.ndarray, alpha: float = 0.1) -> float:
    """Split-conformal upper threshold on source maxima; inf if resolution is insufficient."""
    scores = np.asarray(source_scores, dtype=np.float64)
    if (
        scores.ndim != 1 or len(scores) == 0 or not np.isfinite(scores).all()
        or not 0.0 < alpha < 1.0
    ):
        raise ValueError("conformal calibration input is invalid")
    rank = int(math.ceil((len(scores) + 1) * (1.0 - alpha)))
    if rank > len(scores):
        return float("inf")
    return float(np.sort(scores)[rank - 1])


def source_disjoint_heuristic_threshold(
    features: np.ndarray, groups: np.ndarray, keys: list[str], score_fn: ScoreFunction,
    multiplier: float = 1.25, max_folds: int = 8,
) -> float | None:
    """Leave-one-source-out q95-of-q95 heuristic used for cross-score comparison."""
    if score_fn is rms_z_scores:
        return vision.tile_descriptor_threshold(features, keys, max_folds=max_folds)
    features = np.asarray(features, dtype=np.float64)
    groups = np.asarray(groups)
    names = sorted(set(str(value) for value in groups))
    if len(names) > max_folds:
        picks = np.linspace(0, len(names) - 1, max_folds).round().astype(int)
        names = [names[int(index)] for index in picks]
    group_q95: list[float] = []
    for held_out in names:
        held_mask = groups == held_out
        train_mask = ~held_mask
        if int(held_mask.sum()) < 4 or int(train_mask.sum()) < 4:
            continue
        score = score_fn(features[train_mask], features[held_mask])
        group_q95.append(float(np.quantile(score, 0.95)))
    if len(group_q95) < 2:
        return None
    threshold = float(np.quantile(np.asarray(group_q95), 0.95)) * multiplier
    if not math.isfinite(threshold) or threshold <= 0.0:
        return None
    return min(threshold, 1000.0)


def gate_metrics(scores: np.ndarray, groups: np.ndarray, threshold: float) -> dict:
    source_max, _ = source_max_scores(scores, groups)
    return {
        "tile_rejection_rate": float(np.mean(scores > threshold)),
        "source_rejection_rate": float(np.mean(source_max > threshold)),
        "sources": int(len(source_max)),
        "tiles": int(len(scores)),
    }


def run_once(
    seed: int, fit_sources: int = 24, calibration_sources: int = 20,
    test_sources: int = 20, alpha: float = 0.1,
) -> dict:
    if min(fit_sources, calibration_sources, test_sources) < 2:
        raise ValueError("at least two independent source groups are required per split")
    rng = np.random.default_rng(seed)
    source_seeds = rng.choice(
        2**31 - 1, size=fit_sources + calibration_sources + test_sources, replace=False,
    )
    fit_images = [make_synthetic_ui(int(value)) for value in source_seeds[:fit_sources]]
    cal_start = fit_sources
    test_start = fit_sources + calibration_sources
    cal_images = [make_synthetic_ui(int(value)) for value in source_seeds[cal_start:test_start]]
    test_images = [make_synthetic_ui(int(value)) for value in source_seeds[test_start:]]
    x_fit, g_fit, k_fit = tile_matrix(fit_images, "fit")
    x_cal, g_cal, k_cal = tile_matrix(cal_images, "cal")
    x_test, g_test, _ = tile_matrix(test_images, "test")
    shifts: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for kind in SHIFT_KINDS:
        shifted = [
            apply_synthetic_shift(image, kind, seed + 300 + index)
            for index, image in enumerate(test_images)
        ]
        x_shift, g_shift, _ = tile_matrix(shifted, kind)
        shifts[kind] = (x_shift, g_shift)
    heuristic_features = np.vstack((x_fit, x_cal))
    heuristic_groups = np.concatenate((g_fit, g_cal))
    heuristic_keys = k_fit + k_cal
    detector_specs = (
        ("rms_z", rms_z_scores),
        ("shrinkage_mahalanobis", shrinkage_mahalanobis_scores),
    )
    output: dict[str, dict] = {}
    for name, score_fn in detector_specs:
        calibration_scores = score_fn(x_fit, x_cal)
        test_scores = score_fn(x_fit, x_test)
        calibration_max, _ = source_max_scores(calibration_scores, g_cal)
        conformal_threshold = conformal_source_threshold(calibration_max, alpha)
        heuristic_threshold = source_disjoint_heuristic_threshold(
            heuristic_features, heuristic_groups, heuristic_keys, score_fn,
        )
        if heuristic_threshold is None:
            raise RuntimeError(f"source-disjoint heuristic unavailable for {name}")
        result = {
            "calibration": {
                "source_count": int(len(calibration_max)),
                "alpha": alpha,
                "conformal_source_threshold": conformal_threshold,
                "heuristic_source_threshold": heuristic_threshold,
            },
            "test_id": {
                "conformal": gate_metrics(test_scores, g_test, conformal_threshold),
                "heuristic": gate_metrics(test_scores, g_test, heuristic_threshold),
            },
            "ood": {},
        }
        for kind, (x_shift, g_shift) in shifts.items():
            shift_scores = score_fn(x_fit, x_shift)
            result["ood"][kind] = {
                "conformal": gate_metrics(shift_scores, g_shift, conformal_threshold),
                "heuristic": gate_metrics(shift_scores, g_shift, heuristic_threshold),
            }
        output[name] = result
    output["split"] = {
        "fit_sources": sorted(set(g_fit.tolist())),
        "calibration_sources": sorted(set(g_cal.tolist())),
        "test_sources": sorted(set(g_test.tolist())),
    }
    return output


def run_experiment(repeats: int = 30, seed: int = 20261127, alpha: float = 0.1) -> dict:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    runs = [run_once(seed + index * 997, alpha=alpha) for index in range(repeats)]
    summary: dict[str, dict] = {}
    for detector in ("rms_z", "shrinkage_mahalanobis"):
        summary[detector] = {}
        for gate in ("conformal", "heuristic"):
            summary[detector][gate] = {
                "id_source_rejection_rate": float(np.mean([
                    run[detector]["test_id"][gate]["source_rejection_rate"] for run in runs
                ])),
                "id_tile_rejection_rate": float(np.mean([
                    run[detector]["test_id"][gate]["tile_rejection_rate"] for run in runs
                ])),
                "ood": {},
            }
            for kind in SHIFT_KINDS:
                summary[detector][gate]["ood"][kind] = {
                    "source_rejection_rate": float(np.mean([
                        run[detector]["ood"][kind][gate]["source_rejection_rate"] for run in runs
                    ])),
                    "tile_rejection_rate": float(np.mean([
                        run[detector]["ood"][kind][gate]["tile_rejection_rate"] for run in runs
                    ])),
                }
    return {
        "schema": "v14.vision_ood_calibration/1",
        "seed": seed,
        "repeats": repeats,
        "fit_sources_per_repeat": 24,
        "calibration_sources_per_repeat": 20,
        "test_sources_per_repeat": 20,
        "tiles_per_source": 16,
        "feature_dim": 37,
        "alpha": alpha,
        "source_exchangeability_unit": "maximum tile score per independent image source",
        "summary": summary,
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261127)
    parser.add_argument("--alpha", type=float, default=0.1)
    args = parser.parse_args()
    print(json.dumps(run_experiment(args.repeats, args.seed, args.alpha), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
