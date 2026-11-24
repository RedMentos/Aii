import hashlib

import pytest

from v13.attention_policy_head import (
    FEATURE_NAMES, build_features, empty_head, predict, update, rollback,
    report, validate_features, PolicyHeadError, MAX_UPDATE_NORM,
)

GAINS = {"perceptual": .55, "callosum": .40, "workspace": .60, "focal": .65, "action": .55}


def features(priority, *, source_bound=True, source_index=0):
    source_text = f"source-{source_index}"
    ref = {"source_id": f"src-{source_index}", "sha256": hashlib.sha256(source_text.encode()).hexdigest(),
           "modality": "text", "char_start": 0, "char_end": 32} if source_bound else None
    return build_features(requester="A4", target="MEMORY", reason="recall",
                          priority=priority, budget=64, resolution="default",
                          source_ref=ref, refs=[ref] if ref else [], gains=GAINS)


def test_feature_vector_is_fixed_bounded_and_source_aware():
    x = features(.8)
    assert len(x) == len(FEATURE_NAMES) == 35
    assert all(0.0 <= value <= 1.0 for value in x)
    assert x[7] == 1.0
    assert x[8] == 0.0
    assert x[9] == 0.0
    assert x[10] == 32 / 4096
    assert x[11] == .25
    assert features(.8, source_bound=False)[7] == 0.0


def test_head_predicts_only_after_minimum_source_weighted_outcomes():
    head = empty_head()
    x = features(.7)
    assert predict(head, x) is None
    for i in range(3):
        update(head, x, 1.0, modulator_scale=1.0, source_weight=1.0,
               response_packet_id=f"resp-{i}", provenance_sha256=hashlib.sha256(str(i).encode()).hexdigest(),
               source_class="real_deterministic_outcome")
    assert predict(head, x) is None
    update(head, x, 1.0, modulator_scale=1.0, source_weight=1.0,
           response_packet_id="resp-4", provenance_sha256=hashlib.sha256(b"4").hexdigest(),
           source_class="real_deterministic_outcome")
    assert predict(head, x) is not None


def test_online_utility_head_learns_priority_signal_on_held_out_contexts():
    head = empty_head()
    for i in range(160):
        priority = (i % 20) / 19
        x = features(priority, source_index=i)
        target = 1.0 if priority >= .5 else -1.0
        result = update(head, x, target, modulator_scale=1.0, source_weight=.9,
                        response_packet_id=f"train-{i}",
                        provenance_sha256=hashlib.sha256(f"source-{i}".encode()).hexdigest(),
                        source_class="primary_source")
        assert result is not None
        assert result["applied_update_norm"] <= MAX_UPDATE_NORM + 1e-12
    low = predict(head, features(.1, source_index=1001))
    high = predict(head, features(.9, source_index=1002))
    assert low is not None and high is not None
    assert high > low + .2
    assert report(head)["updates"] == 160
    assert report(head)["prediction_ready"] is True


def test_source_weight_zero_and_n10_zero_scale_do_not_update():
    head = empty_head()
    x = features(.9)
    before = list(head["weights"])
    assert update(head, x, 1.0, modulator_scale=1.0, source_weight=0.0,
                  response_packet_id="dream-1", provenance_sha256="d" * 64,
                  source_class="dream") is None
    assert update(head, x, 1.0, modulator_scale=0.0, source_weight=1.0,
                  response_packet_id="veto-1", provenance_sha256="e" * 64,
                  source_class="real_deterministic_outcome") is None
    assert head["weights"] == before
    assert head["n"] == head["updates"] == 0
    assert head["checkpoints"] == []


def test_update_is_bounded_checkpointed_and_human_rollback_restores_exact_parameters():
    head = empty_head()
    x = features(.75)
    before = list(head["weights"])
    update(head, x, 1.0, modulator_scale=1.0, source_weight=1.0,
           response_packet_id="resp-one", provenance_sha256="f" * 64,
           source_class="real_deterministic_outcome")
    after = list(head["weights"])
    assert after != before
    assert len(head["checkpoints"]) == 1
    with pytest.raises(PermissionError, match="explicit human"):
        rollback(head, authority="SYSTEM")
    rollback(head, authority="EXPLICIT_HUMAN")
    assert head["weights"] == before
    assert head["n"] == 0
    assert head["updates"] == 0
    assert head["checkpoints"] == []


def test_head_caps_checkpoint_history_and_rejects_tampered_features():
    head = empty_head()
    x = features(.5)
    for i in range(12):
        update(head, x, (-1.0 if i % 2 else 1.0), modulator_scale=1.0, source_weight=1.0,
               response_packet_id=f"resp-{i}", provenance_sha256=hashlib.sha256(str(i).encode()).hexdigest(),
               source_class="internal_crosscheck")
    assert len(head["checkpoints"]) == 8
    with pytest.raises(PolicyHeadError, match="geometry"):
        validate_features([.1, .2])
    with pytest.raises(PolicyHeadError, match="finite"):
        validate_features([float("nan")] * len(FEATURE_NAMES))


def test_unknown_attention_categories_use_other_bucket_without_breaking_runtime():
    x = build_features(requester="C3", target="ENLIGHTENED_SPACE", reason="repair",
                       priority=.5, budget=32, resolution="default", source_ref=None,
                       refs=[], gains=GAINS)
    assert len(x) == 35
    assert x[19] == 1.0
    assert x[27] == 1.0
    assert x[34] == 1.0
