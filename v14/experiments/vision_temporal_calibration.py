"""Source-disjoint noise/shuffle calibration for the existing A3 temporal score.

This is an offline diagnostic gate for the A3 -> A4 novelty contribution. It
uses the caller's existing A3 projector, never persists frames/features/weights,
and does not modify runtime thresholds or grant learning/action/truth authority.
The noise control perturbs numeric tile features; it is not a pixel-camera model.
"""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np

from vision_counterfactual_probe import project_a3_sequences, source_disjoint_folds


def _validate_sequences(frame_features, transition_labels, source_ids):
    values = np.asarray(frame_features, dtype=np.float64)
    targets = np.asarray(transition_labels)
    groups = tuple(source_ids)
    if values.ndim != 4 or values.shape[0] < 4 or values.shape[1] < 2:
        raise ValueError("frame_features must have shape [clips,frames>=2,16,feature_dim]")
    if values.shape[2] != 16 or values.shape[3] < 1:
        raise ValueError("A3 temporal calibration requires the complete 16-tile grid")
    if not np.isfinite(values).all():
        raise ValueError("frame_features must be finite")
    if targets.shape != (values.shape[0], values.shape[1] - 1) or not np.isin(targets, (0, 1)).all():
        raise ValueError("transition_labels must contain stable=0/changed=1 per adjacent frame pair")
    if len(np.unique(targets)) != 2:
        raise ValueError("both stable and changed transitions are required")
    if len(groups) != values.shape[0] or any(type(g) is not str or not g or len(g) > 256 for g in groups):
        raise ValueError("one bounded nonempty source id is required per clip")
    return values, targets.astype(np.int8), groups


def _project_tiles(projector: Callable, features: np.ndarray) -> np.ndarray:
    clips, frames, tiles, width = features.shape
    projected = project_a3_sequences(projector, features.reshape(clips, frames * tiles, width))
    projected = projected.reshape(clips, frames, tiles, projected.shape[-1])
    norms = np.linalg.norm(projected, axis=-1, keepdims=True)
    if not np.isfinite(projected).all() or np.any(norms <= 1e-8):
        raise ValueError("A3 projector must return finite nonzero tile embeddings")
    return projected / norms


def _tile_score_from_cosines(cosines: np.ndarray) -> np.ndarray:
    """Match runtime A3 pooling: 0.6 * top-four mean + 0.4 * all-tile mean."""
    if cosines.shape[-1] != 16 or not np.isfinite(cosines).all():
        raise ValueError("A3 temporal cosine rows must contain 16 finite tile values")
    delta = np.clip((1.0 - np.clip(cosines, -1.0, 1.0)) * 0.5, 0.0, 1.0)
    ordered = np.sort(delta, axis=-1)[..., ::-1]
    return 0.6 * np.mean(ordered[..., :4], axis=-1) + 0.4 * np.mean(delta, axis=-1)


def _transition_scores(normalized_embeddings: np.ndarray) -> np.ndarray:
    if normalized_embeddings.ndim != 4 or normalized_embeddings.shape[1] < 2:
        raise ValueError("normalized embeddings must have shape [clips,frames>=2,16,dim]")
    adjacent_cosines = np.sum(normalized_embeddings[:, 1:] * normalized_embeddings[:, :-1], axis=-1)
    return _tile_score_from_cosines(adjacent_cosines)


def _paired_frame_noise_scores(original: np.ndarray, perturbed: np.ndarray) -> np.ndarray:
    cosines = np.sum(original * perturbed, axis=-1)
    return _tile_score_from_cosines(cosines)


def calibrate_a3_temporal_change(
    projector: Callable[[np.ndarray], np.ndarray],
    frame_features,
    transition_labels,
    source_ids: Sequence[str],
    *,
    folds: int = 5,
    seed: int = 17,
    noise_std: float = 0.005,
    noise_repeats: int = 5,
    target_false_positive_rate: float = 0.05,
) -> dict:
    """Calibrate a per-transition threshold on train-source feature-noise controls.

    Each label belongs to exactly one adjacent frame pair. Thresholds are fitted
    only from feature-noise pairs belonging to training source groups; held-out
    stable and changed transitions are never used to set their own threshold.
    Random frame permutation and exact reversal are diagnostic controls, not
    semantic motion labels.
    """
    values, targets, groups = _validate_sequences(frame_features, transition_labels, source_ids)
    if not callable(projector):
        raise ValueError("projector must be callable")
    if type(folds) is not int or not 2 <= folds <= 10:
        raise ValueError("folds must be an integer in [2,10]")
    if type(noise_std) not in (int, float) or not np.isfinite(noise_std) or not 0.0 < noise_std <= 0.25:
        raise ValueError("noise_std must be finite in (0,0.25]")
    if type(noise_repeats) is not int or not 1 <= noise_repeats <= 32:
        raise ValueError("noise_repeats must be an integer in [1,32]")
    if (type(target_false_positive_rate) not in (int, float)
            or not np.isfinite(target_false_positive_rate)
            or not 0.001 <= target_false_positive_rate <= 0.25):
        raise ValueError("target_false_positive_rate must be in [0.001,0.25]")

    projected = _project_tiles(projector, values)
    ordered_scores = _transition_scores(projected)
    reversed_scores = _transition_scores(projected[:, ::-1])[:, ::-1]
    reverse_abs_error = np.abs(ordered_scores - reversed_scores)

    rng = np.random.default_rng(seed)
    rms = np.maximum(np.sqrt(np.mean(values * values, axis=-1, keepdims=True)), 1e-6)
    noise_scores = np.empty((values.shape[0], values.shape[1], noise_repeats), dtype=np.float64)
    for repeat in range(noise_repeats):
        perturbation = rng.normal(0.0, 1.0, size=values.shape)
        noisy = values + float(noise_std) * rms * perturbation
        noisy_projected = _project_tiles(projector, noisy)
        noise_scores[:, :, repeat] = _paired_frame_noise_scores(projected, noisy_projected)

    shuffle_rng = np.random.default_rng(seed + 104729)
    shuffled = np.empty_like(projected)
    for clip_index in range(projected.shape[0]):
        order = shuffle_rng.permutation(projected.shape[1])
        if np.array_equal(order, np.arange(projected.shape[1])):
            order = np.roll(order, 1)
        shuffled[clip_index] = projected[clip_index, order]
    shuffled_scores = _transition_scores(shuffled)

    fold_results = []
    for train, test in source_disjoint_folds(groups, folds=folds, seed=seed):
        train_labels = targets[train].reshape(-1)
        test_labels = targets[test].reshape(-1)
        if len(np.unique(train_labels)) != 2 or len(np.unique(test_labels)) != 2:
            raise ValueError("each source-disjoint fold must contain stable and changed transitions")
        train_noise = noise_scores[train].reshape(-1)
        threshold = float(np.quantile(
            train_noise, 1.0 - float(target_false_positive_rate), method="higher",
        ))
        test_noise = noise_scores[test].reshape(-1)
        test_scores = ordered_scores[test].reshape(-1)
        test_shuffle = shuffled_scores[test].reshape(-1)
        fold_results.append({
            "threshold": round(threshold, 8),
            "train_source_count": len({groups[index] for index in train}),
            "test_source_count": len({groups[index] for index in test}),
            "source_overlap_count": len(
                {groups[index] for index in train} & {groups[index] for index in test}
            ),
            "heldout_noise_fpr": round(float(np.mean(test_noise > threshold)), 6),
            "heldout_stable_fpr": round(float(np.mean(test_scores[test_labels == 0] > threshold)), 6),
            "heldout_change_tpr": round(float(np.mean(test_scores[test_labels == 1] > threshold)), 6),
            "shuffle_ge_order_fraction": round(float(np.mean(test_shuffle >= test_scores)), 6),
            "shuffle_score_median": round(float(np.median(test_shuffle)), 8),
            "ordered_score_median": round(float(np.median(test_scores)), 8),
            "reverse_abs_error_max": round(float(np.max(reverse_abs_error[test])), 12),
        })

    thresholds = np.asarray([row["threshold"] for row in fold_results], dtype=np.float64)
    return {
        "schema": "v14.a3-temporal-calibration/1",
        "status": "DIAGNOSTIC_ONLY",
        "split": "SOURCE_DISJOINT",
        "projector_used": True,
        "clips": int(values.shape[0]),
        "frames_per_clip": int(values.shape[1]),
        "transitions": int(targets.size),
        "tiles_per_frame": int(values.shape[2]),
        "embedding_dim": int(projected.shape[-1]),
        "source_groups": len(set(groups)),
        "folds": int(folds),
        "noise_std": float(noise_std),
        "noise_repeats": int(noise_repeats),
        "threshold_source": "TRAIN_SOURCE_FEATURE_NOISE_ONLY",
        "target_false_positive_rate": float(target_false_positive_rate),
        "threshold_median": round(float(np.median(thresholds)), 8),
        "heldout_noise_fpr_mean": round(float(np.mean([r["heldout_noise_fpr"] for r in fold_results])), 6),
        "heldout_stable_fpr_mean": round(float(np.mean([r["heldout_stable_fpr"] for r in fold_results])), 6),
        "heldout_change_tpr_mean": round(float(np.mean([r["heldout_change_tpr"] for r in fold_results])), 6),
        "shuffle_ge_order_fraction_mean": round(float(np.mean([r["shuffle_ge_order_fraction"] for r in fold_results])), 6),
        "reverse_abs_error_max": round(float(np.max(reverse_abs_error)), 12),
        "fold_results": fold_results,
        "threshold_persisted": False,
        "projector_weights_persisted": False,
        "raw_frames_persisted": False,
        "truth_authority": 0,
        "learning_authority": False,
        "action_authority": False,
        "limits": [
            "feature-space Gaussian noise is not pixel/camera/codec noise",
            "frame permutation tests order sensitivity, not semantic understanding",
            "synthetic or caller-supplied source labels do not establish Redmi utility",
            "threshold is diagnostic and is not consumed by Runtime",
        ],
    }
