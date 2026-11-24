"""Source-disjoint probe for whether an A3 representation exposes temporal change.

This is a diagnostic, not a video encoder, JEPA learner, or runtime authority.
It compares aligned original/transformed token features using the c/d split
from V-JEPA-LM (arXiv:2611.17831). The caller supplies A3 frame features and
may pass the existing v13.vision.Projector as projector. No frames, labels,
features, or fitted probe weights are persisted.

Important: transformed must already be aligned to the original token
positions (for reversal, apply the inverse token permutation first). The
probe reports feature-level change separately from the readout's ability to
recover that change on source-disjoint held-out clips.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np


@dataclass(frozen=True)
class _ValidatedPairs:
    original: np.ndarray
    transformed: np.ndarray
    labels: np.ndarray
    groups: tuple[str, ...]


def _validate_pairs(original, transformed, labels, source_ids) -> _ValidatedPairs:
    x = np.asarray(original, dtype=np.float64)
    xt = np.asarray(transformed, dtype=np.float64)
    y = np.asarray(labels)
    groups = tuple(source_ids)
    if x.ndim != 3 or xt.shape != x.shape:
        raise ValueError("features must be matching [clips,tokens,dimensions] arrays")
    if x.shape[0] < 4 or x.shape[1] < 1 or x.shape[2] < 1:
        raise ValueError("at least four nonempty clip feature pairs are required")
    if not np.isfinite(x).all() or not np.isfinite(xt).all():
        raise ValueError("features must be finite")
    if y.shape != (x.shape[0],) or not np.isin(y, (-1, 1)).all():
        raise ValueError("labels must be one -1/+1 value per clip")
    if len(groups) != x.shape[0] or any(type(g) is not str or not g or len(g) > 256 for g in groups):
        raise ValueError("one bounded nonempty source group is required per clip")
    if len(set(y.tolist())) != 2:
        raise ValueError("both counterfactual answer classes must be present")
    return _ValidatedPairs(x, xt, y.astype(np.float64), groups)


def project_a3_sequences(projector: Callable[[np.ndarray], np.ndarray], frame_features) -> np.ndarray:
    """Apply the existing A3 projector to every frame without changing clip order."""
    values = np.asarray(frame_features, dtype=np.float64)
    if values.ndim != 3 or values.shape[0] < 1 or values.shape[1] < 1 or values.shape[2] < 1:
        raise ValueError("frame_features must have shape [clips,frames,feature_dim]")
    if not np.isfinite(values).all() or not callable(projector):
        raise ValueError("finite frame features and a callable A3 projector are required")
    projected = np.asarray(projector(values.reshape(-1, values.shape[-1])), dtype=np.float64)
    if projected.ndim != 2 or projected.shape[0] != values.shape[0] * values.shape[1]:
        raise ValueError("A3 projector must return one 2-D embedding per input frame")
    if projected.shape[1] < 1 or not np.isfinite(projected).all():
        raise ValueError("A3 projector returned invalid embeddings")
    return projected.reshape(values.shape[0], values.shape[1], projected.shape[1])


def source_disjoint_folds(source_ids: Sequence[str], folds: int = 5, seed: int = 17):
    """Return deterministic row-index folds with no source group crossing folds."""
    groups = tuple(source_ids)
    if type(folds) is not int or not 2 <= folds <= 10:
        raise ValueError("folds must be an integer in [2,10]")
    if len(groups) < 4 or any(type(g) is not str or not g for g in groups):
        raise ValueError("source groups must be nonempty strings")
    unique = np.asarray(sorted(set(groups)), dtype=object)
    if len(unique) < folds:
        raise ValueError("not enough distinct source groups for requested folds")
    rng = np.random.default_rng(seed)
    shuffled = unique[rng.permutation(len(unique))]
    buckets = [set(shuffled[i::folds].tolist()) for i in range(folds)]
    rows = np.asarray(groups, dtype=object)
    result = []
    for bucket in buckets:
        test = np.flatnonzero(np.isin(rows, tuple(bucket)))
        train = np.flatnonzero(~np.isin(rows, tuple(bucket)))
        if not len(train) or not len(test):
            raise ValueError("source-disjoint fold is empty")
        result.append((train, test))
    return tuple(result)


def _fit_ridge(x: np.ndarray, y: np.ndarray, ridge: float) -> np.ndarray:
    design = np.column_stack((x, np.ones(len(x), dtype=np.float64)))
    penalty = np.eye(design.shape[1], dtype=np.float64) * ridge
    penalty[-1, -1] = 0.0
    return np.linalg.solve(design.T @ design + penalty, design.T @ y)


def _predict(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return np.sign(np.column_stack((x, np.ones(len(x), dtype=np.float64))) @ weights)


def measure_counterfactual_change(
    original,
    transformed,
    labels,
    source_ids,
    *,
    folds: int = 5,
    seed: int = 17,
    ridge: float = 1e-2,
    content_rank: int = 8,
    min_shared_change: float = 0.01,
) -> dict:
    """Measure change energy, content overlap, shared direction and held-out readout.

    labels are the answer signs for the original clip; the transformed clip is
    constructed to have the opposite answer. High kappa is only a candidate
    shared change direction, not semantic truth or a calibrated probability.
    """
    data = _validate_pairs(original, transformed, labels, source_ids)
    if type(folds) is not int or not 2 <= folds <= 10:
        raise ValueError("folds must be an integer in [2,10]")
    if type(ridge) not in (int, float) or not np.isfinite(ridge) or ridge <= 0:
        raise ValueError("ridge must be finite and positive")
    if type(content_rank) is not int or content_rank < 1:
        raise ValueError("content_rank must be a positive integer")
    if type(min_shared_change) not in (int, float) or not np.isfinite(min_shared_change) or min_shared_change < 0:
        raise ValueError("min_shared_change must be finite and nonnegative")

    x, xt, y = data.original, data.transformed, data.labels
    common = 0.5 * (x + xt)
    change = 0.5 * (x - xt)
    pooled_common = common.mean(axis=1)
    pooled_change = change.mean(axis=1)

    centered_x = x - x.mean(axis=(0, 1), keepdims=True)
    change_energy = float(np.mean(np.sum(change * change, axis=(1, 2))))
    content_energy = float(np.mean(np.sum(centered_x * centered_x, axis=(1, 2))))
    r_d = change_energy / max(content_energy, 1e-12)
    denominator = float(np.mean(np.sum(pooled_change * pooled_change, axis=1)))
    kappa = float(np.sum(np.mean(y[:, None] * pooled_change, axis=0) ** 2) / max(denominator, 1e-12))

    content = common.reshape(-1, common.shape[-1])
    content = content - content.mean(axis=0, keepdims=True)
    covariance = content.T @ content / max(1, len(content) - 1)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    rank = min(content_rank, x.shape[-1])
    basis = eigenvectors[:, np.argsort(eigenvalues)[-rank:]]
    if denominator <= 1e-12:
        rho = 0.0
    else:
        projected = pooled_change @ basis
        rho = float(np.mean(np.sum(projected * projected, axis=1)) / denominator)

    fold_scores, content_scores, prototype_scores = [], [], []
    for train, test in source_disjoint_folds(data.groups, folds=folds, seed=seed):
        if len(np.unique(y[train])) != 2 or len(np.unique(y[test])) != 2:
            raise ValueError("each source-disjoint fold must contain both answer classes")
        weights = _fit_ridge(pooled_change[train], y[train], float(ridge))
        content_weights = _fit_ridge(pooled_common[train], y[train], float(ridge))
        prototype = np.mean(y[train, None] * pooled_change[train], axis=0)
        fold_scores.append(float(np.mean(_predict(pooled_change[test], weights) == y[test])))
        content_scores.append(float(np.mean(_predict(pooled_common[test], content_weights) == y[test])))
        prototype_scores.append(float(np.mean(np.sign(pooled_change[test] @ prototype) == y[test])))

    if r_d <= 1e-10:
        status = "NO_CHANGE_COMPONENT"
    elif kappa < float(min_shared_change):
        status = "NO_SHARED_CHANGE_CANDIDATE"
    else:
        status = "SHARED_CHANGE_CANDIDATE"
    return {
        "schema": "v14.vision-counterfactual-probe/1",
        "status": status,
        "split": "SOURCE_DISJOINT",
        "authority": "DIAGNOSTIC_ONLY",
        "feature_shape": [int(x.shape[1]), int(x.shape[2])],
        "samples": int(x.shape[0]),
        "source_groups": len(set(data.groups)),
        "folds": int(folds),
        "chance": 0.5,
        "r_d": round(r_d, 8),
        "rho_topk": round(rho, 8),
        "rho_rank": rank,
        "kappa": round(kappa, 8),
        "change_linear_probe_accuracy": round(float(np.mean(fold_scores)), 6),
        "content_linear_probe_accuracy": round(float(np.mean(content_scores)), 6),
        "change_prototype_accuracy": round(float(np.mean(prototype_scores)), 6),
        "fitted_weights_persisted": False,
        "raw_frames_persisted": False,
    }


def audit_a3_projector(
    projector: Callable[[np.ndarray], np.ndarray],
    original_frame_features,
    transformed_frame_features,
    labels,
    source_ids,
    **kwargs,
) -> dict:
    """Compare pre-A3 frame features with the actual A3 projector output."""
    before = measure_counterfactual_change(
        original_frame_features, transformed_frame_features, labels, source_ids, **kwargs,
    )
    original_projected = project_a3_sequences(projector, original_frame_features)
    transformed_projected = project_a3_sequences(projector, transformed_frame_features)
    after = measure_counterfactual_change(
        original_projected, transformed_projected, labels, source_ids, **kwargs,
    )
    before_kappa = float(before["kappa"])
    after_kappa = float(after["kappa"])
    return {
        "schema": "v14.a3-counterfactual-audit/1",
        "authority": "DIAGNOSTIC_ONLY",
        "input_features": before,
        "a3_projector_output": after,
        "kappa_retention_ratio": round(after_kappa / before_kappa, 6) if before_kappa > 1e-12 else None,
        "projector_weights_persisted": False,
    }
