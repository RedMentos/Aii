import numpy as np
import pytest

from vision_temporal_calibration import calibrate_a3_temporal_change


def synthetic_sequences(seed=5, sources=10, frames=5, tiles=16, dim=12):
    rng = np.random.default_rng(seed)
    rows, labels, source_ids = [], [], []
    for source in range(sources):
        base = rng.normal(size=(tiles, dim))
        base /= np.linalg.norm(base, axis=-1, keepdims=True)
        stable = np.stack([base + rng.normal(0, 0.00005, size=base.shape) for _ in range(frames)])
        changed = np.stack([base.copy() for _ in range(frames)])
        changed[3:, :4] = -base[:4]
        changed += rng.normal(0, 0.00005, size=changed.shape)
        rows.extend([stable, changed])
        labels.extend([[0, 0, 0, 0], [0, 0, 1, 0]])
        source_ids.extend([f"source-{source}", f"source-{source}"])
    return np.asarray(rows), np.asarray(labels), source_ids


def test_source_disjoint_noise_calibration_separates_stable_and_changed_transitions():
    features, labels, sources = synthetic_sequences()
    result = calibrate_a3_temporal_change(
        lambda x: x, features, labels, sources,
        folds=5, seed=11, noise_std=0.005, noise_repeats=4,
    )
    assert result["split"] == "SOURCE_DISJOINT"
    assert result["status"] == "DIAGNOSTIC_ONLY"
    assert result["source_groups"] == 10
    assert result["heldout_change_tpr_mean"] >= 0.9
    assert result["heldout_stable_fpr_mean"] <= 0.1
    assert result["heldout_noise_fpr_mean"] <= 0.1
    assert result["reverse_abs_error_max"] <= 1e-12
    assert all(row["source_overlap_count"] == 0 for row in result["fold_results"])
    assert all(row["train_source_count"] + row["test_source_count"] == 10 for row in result["fold_results"])
    assert result["threshold_persisted"] is False
    assert result["projector_weights_persisted"] is False


def test_noise_and_shuffle_controls_are_deterministic_and_reported():
    features, labels, sources = synthetic_sequences(seed=9)
    kwargs = dict(folds=5, seed=13, noise_std=0.006, noise_repeats=3)
    first = calibrate_a3_temporal_change(lambda x: x, features, labels, sources, **kwargs)
    second = calibrate_a3_temporal_change(lambda x: x, features, labels, sources, **kwargs)
    assert first == second
    assert 0.0 <= first["shuffle_ge_order_fraction_mean"] <= 1.0
    assert first["reverse_abs_error_max"] == 0.0
    assert first["shuffle_ge_order_fraction_mean"] > 0.5


def test_rejects_invalid_shapes_labels_noise_and_zero_projector_embeddings():
    features, labels, sources = synthetic_sequences(sources=5)
    with pytest.raises(ValueError, match="16-tile"):
        calibrate_a3_temporal_change(lambda x: x, features[:, :, :8], labels, sources, folds=5)
    with pytest.raises(ValueError, match="transition_labels"):
        calibrate_a3_temporal_change(lambda x: x, features, labels + 2, sources, folds=5)
    with pytest.raises(ValueError, match="noise_std"):
        calibrate_a3_temporal_change(lambda x: x, features, labels, sources, folds=5, noise_std=0)
    with pytest.raises(ValueError, match="nonzero"):
        calibrate_a3_temporal_change(lambda x: np.zeros_like(x), features, labels, sources, folds=5)


def test_rejects_source_leakage_insufficient_groups_and_missing_class_per_fold():
    features, labels, sources = synthetic_sequences(sources=4)
    with pytest.raises(ValueError, match="not enough distinct"):
        calibrate_a3_temporal_change(lambda x: x, features, labels, sources, folds=5)
    repeated = ["one-source"] * len(sources)
    with pytest.raises(ValueError, match="not enough distinct"):
        calibrate_a3_temporal_change(lambda x: x, features, labels, repeated, folds=2)
