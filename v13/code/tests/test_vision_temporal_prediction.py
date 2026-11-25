import copy
import math

import pytest

from v13.vision_temporal_prediction import A3TemporalPredictor, A3TemporalPredictorError
from v13.vision_temporal_evidence import (
    TILE_IDS, TemporalVisualEvidence, _a3_predictive_attention_novelty,
)


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
    assert all(_a3_predictive_attention_novelty(row) == 0.0 for row in measured)


def test_zero_context_bias_learns_a_nonzero_transition_without_touching_nonzero_contexts():
    predictor = A3TemporalPredictor(warmup_updates=2)
    zero = [0.0] * 16
    event = [0.8] + [0.0] * 15
    predictor.update(zero)
    transition = predictor.update(event)
    assert transition["parameter_delta_l2"] > 0.0
    assert any(abs(value) > 0.0 for value in predictor._weights[-1])
    bias_before = list(predictor._weights[-1])
    other_a = [0.0] * 16
    other_b = [0.0] * 16
    other_a[8], other_b[9] = 0.7, 0.7
    for index in range(100):
        predictor.update(other_a if index % 2 == 0 else other_b)
    assert predictor._weights[-1] == bias_before
    assert len(predictor._weights) == 17
    assert all(len(row) == 16 for row in predictor._weights)


def test_unexpected_delta_sequence_emits_bounded_attention_novelty():
    masks = [
        0x0000, 0x0001, 0x0003, 0x0007, 0x000F, 0x0005, 0x00A5, 0x0B4F,
        0x1E37, 0x0000, 0xFFFF, 0x1234, 0xABCD, 0x0F0F, 0xF0F0, 0x3333,
        0xAAAA, 0x5555, 0x9696, 0x6969,
    ]
    predictor = A3TemporalPredictor(warmup_updates=4)
    previous = None
    measured = []
    for mask in masks:
        delta = [0.0] * 16 if previous is None else [
            0.5 if ((previous >> index) & 1) != ((mask >> index) & 1) else 0.0
            for index in range(16)
        ]
        result = predictor.update(delta)
        if result["status"] == "SHADOW_MEASURED":
            measured.append(result)
        previous = mask
    assert any(row["shadow_surprise"] > 0.0 for row in measured)
    assert all(
        0.0 <= _a3_predictive_attention_novelty(row) <= 0.15
        for row in measured
    )


def test_predictive_attention_novelty_requires_measured_finite_error_and_is_capped():
    assert _a3_predictive_attention_novelty({
        "status": "SHADOW_MEASURED", "shadow_surprise": 0.4,
    }) == pytest.approx(0.06)
    assert _a3_predictive_attention_novelty({
        "status": "SHADOW_MEASURED", "shadow_surprise": 2.0,
    }) == pytest.approx(0.15)
    assert _a3_predictive_attention_novelty({
        "status": "SHADOW_MEASURED", "shadow_surprise": -1.0,
    }) == 0.0
    assert _a3_predictive_attention_novelty({
        "status": "WARMUP", "shadow_surprise": 0.4,
    }) == 0.0
    assert _a3_predictive_attention_novelty({
        "status": "SHADOW_MEASURED", "shadow_surprise": float("nan"),
    }) == 0.0


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
    bias_before = list(predictor._weights[-1])
    for index in range(100):
        predictor.update(c if index % 2 == 0 else d)
    assert predictor._weights[-1] == bias_before
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
        assert result["gradient_l2"] <= math.sqrt(17 * 16) + 1e-8
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


def test_error_gated_lms_reduces_updates_on_static_stream_without_losing_predictive_signal():
    zero = [0.0] * 16
    a, b = patterns()
    c, d = [0.0] * 16, [0.0] * 16
    c[8], d[9] = 0.7, 0.7
    stream = (
        [zero] * 500
        + [a if i % 2 == 0 else b for i in range(100)]
        + [zero] * 1000
        + [c if i % 2 == 0 else d for i in range(100)]
        + [zero] * 500
        + [a if i % 2 == 0 else b for i in range(100)]
    )
    always = A3TemporalPredictor(learning_rate=0.3, warmup_updates=4)
    gated = A3TemporalPredictor(
        learning_rate=0.3, warmup_updates=4, update_policy="ERROR_GATED",
    )
    gated_errors, gated_baselines = [], []
    for sample in stream:
        always.update(sample)
        row = gated.update(sample)
        if row["status"] == "SHADOW_MEASURED":
            gated_errors.append(row["prediction_error_mae"])
            gated_baselines.append(row["persistence_baseline_mae"])
    assert gated._updates < always._updates * 0.5
    assert gated._parameter_l2() > 0.0
    assert sum(gated_errors) / len(gated_errors) < sum(gated_baselines) / len(gated_baselines)
    assert sum(gated_errors[-100:]) / 100 < sum(gated_baselines[-100:]) / 100


def test_temporal_visual_consumer_runs_error_gated_shadow_without_a4_authority():
    state = TemporalVisualEvidence()
    luminance = {tile: [0.0] * 16 for tile in TILE_IDS}
    projector_sha = "a" * 64
    result = None
    for index in range(8):
        changed = TILE_IDS[index % len(TILE_IDS)] if index % 2 else None
        embeddings = {
            tile: ((0.0, 1.0) if tile == changed else (1.0, 0.0))
            for tile in TILE_IDS
        }
        source_ref = {
            "source_id": f"frame-{index}",
            "sha256": f"{index + 1:064x}",
            "char_start": 0,
            "char_end": 0,
            "modality": "image",
        }
        result = state.update(
            start_ms=index * 10,
            end_ms=(index + 1) * 10,
            tile_luminance=luminance,
            a3_tile_embeddings=embeddings,
            a3_projector_sha256=projector_sha,
            frame_source_ref=source_ref,
        )
    prediction = result["a3_temporal_prediction"]
    shadow = prediction["error_gated_shadow"]
    assert prediction["update_policy"] == "ALWAYS"
    assert shadow["update_policy"] == "ERROR_GATED"
    assert shadow["authority"] == "SHADOW_ONLY"
    assert shadow["persistent_weights"] is False
    assert shadow["truth_authority"] == 0
    assert shadow["learning_authority"] is False
    assert shadow["action_authority"] is False
    original = _a3_predictive_attention_novelty(prediction)
    changed_shadow = dict(prediction)
    changed_shadow["error_gated_shadow"] = dict(shadow, shadow_surprise=1.0)
    assert _a3_predictive_attention_novelty(changed_shadow) == original


def test_temporal_visual_reset_clears_error_gated_shadow_weights():
    state = TemporalVisualEvidence()
    zero = [0.0] * 16
    for index in range(40):
        state._a3_error_gated_predictor.update(zero if index % 2 else [0.8] + [0.0] * 15)
    assert state._a3_error_gated_predictor._observations > 0
    state.reset()
    assert state._a3_error_gated_predictor._observations == 0
    assert state._a3_error_gated_predictor._updates == 0
    assert state._a3_error_gated_predictor._parameter_l2() == 0.0


def test_error_gate_rule_is_explicit_and_invalid_policy_fails_closed():
    predictor = A3TemporalPredictor(update_policy="ERROR_GATED")
    zero = [0.0] * 16
    for _ in range(5):
        result = predictor.update(zero)
    assert result["update_gate"] == "ERROR_GATE_CLOSED"
    assert result["prediction_error_exceeds_gate"] is False
    assert result["update_gate_rule"] == "MODEL_MAE_GT_MAX_EPSILON_OR_0.25_PERSISTENCE_MAE"
    with pytest.raises(ValueError, match="update_policy"):
        A3TemporalPredictor(update_policy="UNBOUNDED")
