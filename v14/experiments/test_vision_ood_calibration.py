import math

import numpy as np
import pytest
from PIL import Image

from v14.experiments import vision_ood_calibration as experiment


def test_conformal_source_threshold_uses_finite_sample_order_statistic():
    assert experiment.conformal_source_threshold(np.arange(1, 21), alpha=0.1) == 19.0
    assert math.isinf(experiment.conformal_source_threshold(np.arange(1, 9), alpha=0.1))


@pytest.mark.parametrize("scores,alpha", [([], 0.1), ([1.0, float("nan")], 0.1), ([1.0], 0.0), ([1.0], 1.0)])
def test_conformal_source_threshold_rejects_invalid_calibration(scores, alpha):
    with pytest.raises(ValueError):
        experiment.conformal_source_threshold(np.asarray(scores), alpha)


def test_source_max_scores_aggregates_tiles_by_source():
    maxima, names = experiment.source_max_scores(
        np.asarray([0.2, 0.8, 0.4]), np.asarray(["a", "a", "b"]),
    )
    assert names == ["a", "b"]
    assert np.array_equal(maxima, np.asarray([0.8, 0.4]))


def test_shrinkage_mahalanobis_is_finite_for_collinear_features():
    rng = np.random.default_rng(17)
    base = rng.normal(size=(32, 8))
    train = np.hstack((base, base[:, :1], base[:, :1], base[:, 2:3]))
    test = train[:5] + 0.01
    scores = experiment.shrinkage_mahalanobis_scores(train, test, shrinkage=0.25)
    assert scores.shape == (5,)
    assert np.isfinite(scores).all()
    assert (scores >= 0.0).all()


def test_tile_matrix_uses_production_37_dimensional_raw_eye_features():
    image = Image.new("RGB", (64, 64), "white")
    features, groups, keys = experiment.tile_matrix([image], "fixture")
    image.close()
    assert features.shape == (16, 37)
    assert set(groups) == {"fixture-000"}
    assert len(keys) == 16


def test_rms_heuristic_is_the_existing_production_threshold():
    rng = np.random.default_rng(9)
    features = rng.normal(size=(6 * 16, 37))
    groups = np.repeat([f"src-{i}" for i in range(6)], 16)
    keys = [
        f"{source}:r{index // 4}{index % 4}"
        for source in sorted(set(groups)) for index in range(16)
    ]
    expected = experiment.vision.tile_descriptor_threshold(features, keys)
    actual = experiment.source_disjoint_heuristic_threshold(
        features, groups, keys, experiment.rms_z_scores,
    )
    assert actual == expected


def test_run_once_keeps_fit_calibration_and_test_sources_disjoint():
    result = experiment.run_once(seed=12345, fit_sources=8, calibration_sources=10, test_sources=8)
    split = result["split"]
    assert not set(split["fit_sources"]) & set(split["calibration_sources"])
    assert not set(split["fit_sources"]) & set(split["test_sources"])
    assert not set(split["calibration_sources"]) & set(split["test_sources"])
    for detector in ("rms_z", "shrinkage_mahalanobis"):
        assert set(result[detector]["ood"]) == set(experiment.SHIFT_KINDS)
        assert result[detector]["calibration"]["source_count"] == 10
        assert np.isfinite(result[detector]["test_id"]["conformal"]["source_rejection_rate"])


def test_rms_z_rejects_nonfinite_feature_rows():
    train = np.zeros((4, 3), dtype=np.float64)
    rows = np.zeros((2, 3), dtype=np.float64)
    rows[1, 0] = np.nan
    with pytest.raises(ValueError, match="RMS-z"):
        experiment.rms_z_scores(train, rows)


def test_shrinkage_mahalanobis_rejects_invalid_shrinkage_and_nonfinite_rows():
    train = np.zeros((4, 3), dtype=np.float64)
    rows = np.zeros((2, 3), dtype=np.float64)
    with pytest.raises(ValueError, match="shrinkage"):
        experiment.shrinkage_mahalanobis_scores(train, rows, shrinkage=1.5)
    rows[0, 0] = np.inf
    with pytest.raises(ValueError, match="shrinkage"):
        experiment.shrinkage_mahalanobis_scores(train, rows)
