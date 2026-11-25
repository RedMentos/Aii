import copy
import math

import pytest

from v13.vision_temporal_prediction import A3TemporalPredictor, A3TemporalPredictorError


def patterns():
    a = [0.0] * 16
    b = [0.0] * 16
    a[0] = 0.8
    b[1] = 0.8
    return a, b


def test_online_lms_changes_parameters_and_beats_persistence_on_repeating_pattern():
    predictor = A3TemporalPredictor(learning_rate=0.3, warmup_updates=4)
    a, b = patterns()
    errors = []
    baselines = []
    delta_norms = []
    for index in range(120):
        result = predictor.update(a if index % 2 == 0 else b)
        delta_norms.append(result["parameter_delta_l2"])
        if result["status"] == "SHADOW_MEASURED":
            errors.append(result["prediction_error_mae"])
            baselines.append(result["persistence_baseline_mae"])
    assert predictor._updates == 119
    assert predictor._parameter_l2() > 0.1
    assert max(delta_norms) > 0.0
    assert sum(errors[-20:]) / 20 < sum(baselines[-20:]) / 20
    assert errors[-1] < baselines[-1]


def test_warmup_hides_prediction_score_but_still_updates_weights():
    predictor = A3TemporalPredictor(warmup_updates=2)
    a, b = patterns()
    assert predictor.update(a)["status"] == "WARMUP"
    second = predictor.update(b)
    third = predictor.update(a)
    assert second["prediction_error_mae"] is None
    assert third["prediction_error_mae"] is None
    assert third["parameter_delta_l2"] > 0.0
    fourth = predictor.update(b)
    assert fourth["status"] == "SHADOW_MEASURED"
    assert fourth["prediction_error_mae"] is not None


def test_static_zero_change_has_no_false_prediction_surprise():
    predictor = A3TemporalPredictor(warmup_updates=2)
    zero = [0.0] * 16
    results = [predictor.update(zero) for _ in range(12)]
    measured = [row for row in results if row["status"] == "SHADOW_MEASURED"]
    assert measured
    assert all(row["prediction_error_mae"] == 0.0 for row in measured)
    assert all(row["shadow_surprise"] == 0.0 for row in measured)


def test_reset_erases_all_session_weights_and_history():
    predictor = A3TemporalPredictor()
    a, b = patterns()
    for index in range(40):
        predictor.update(a if index % 2 == 0 else b)
    assert predictor._parameter_l2() > 0.0
    predictor.reset()
    assert predictor._updates == 0
    assert predictor._previous is None
    assert predictor._parameter_l2() == 0.0
    assert predictor.update(a)["status"] == "WARMUP"


def test_old_pattern_retention_survives_disjoint_second_pattern():
    predictor = A3TemporalPredictor(learning_rate=0.3, warmup_updates=2)
    a, b = patterns()
    c = [0.0] * 16
    d = [0.0] * 16
    c[8] = 0.7
    d[9] = 0.7
    for index in range(100):
        predictor.update(a if index % 2 == 0 else b)
    old_error_before = []
    probe = copy.deepcopy(predictor)
    for index in range(20):
        row = probe.update(a if index % 2 == 0 else b)
        if row["status"] == "SHADOW_MEASURED":
            old_error_before.append(row["prediction_error_mae"])
    for index in range(100):
        predictor.update(c if index % 2 == 0 else d)
    retained = copy.deepcopy(predictor)
    old_error_after = []
    for index in range(20):
        row = retained.update(a if index % 2 == 0 else b)
        if row["status"] == "SHADOW_MEASURED":
            old_error_after.append(row["prediction_error_mae"])
    assert sum(old_error_after) / len(old_error_after) <= sum(old_error_before) / len(old_error_before) + 0.02


def test_invalid_shapes_types_ranges_and_nonfinite_values_fail_closed():
    predictor = A3TemporalPredictor()
    with pytest.raises(A3TemporalPredictorError, match="exactly 16"):
        predictor.update([0.0] * 15)
    with pytest.raises(A3TemporalPredictorError, match="finite"):
        predictor.update([float("nan")] + [0.0] * 15)
    with pytest.raises(A3TemporalPredictorError, match="finite"):
        predictor.update([True] + [0.0] * 15)
    with pytest.raises(A3TemporalPredictorError, match=r"\[0,1\]"):
        predictor.update([1.01] + [0.0] * 15)
    with pytest.raises(ValueError, match="learning_rate"):
        A3TemporalPredictor(learning_rate=0)
    with pytest.raises(ValueError, match="warmup_updates"):
        A3TemporalPredictor(warmup_updates=0)


def test_weight_and_gradient_norms_remain_bounded():
    predictor = A3TemporalPredictor(learning_rate=1.0, max_gradient_norm=0.1)
    a = [1.0] * 16
    b = [0.0] * 16
    predictor.update(a)
    for _ in range(100):
        result = predictor.update(b)
        assert result["gradient_l2"] <= math.sqrt(16 * 16) + 1e-8
        assert result["parameter_l2"] < 10.0
        assert all(abs(weight) <= 2.0 for row in predictor._weights for weight in row)


def test_output_is_shadow_only_and_never_claims_persistent_authority():
    predictor = A3TemporalPredictor(warmup_updates=1)
    a, b = patterns()
    predictor.update(a)
    predictor.update(b)
    result = predictor.update(a)
    assert result["status"] == "SHADOW_MEASURED"
    assert result["persistent_weights"] is False
    assert result["weight_scope"] == "EPHEMERAL_SESSION_SHADOW"
    assert result["authority"] == "SHADOW_ONLY"
    assert result["truth_authority"] == 0
    assert result["learning_authority"] is False
    assert result["action_authority"] is False
