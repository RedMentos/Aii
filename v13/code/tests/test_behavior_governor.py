"""Behavior head unit regression: training is real; security authority stays external."""
import json
import pytest
from v13.behavior_governor import (
    CORE_PRINCIPLES, TinyBehaviorHead, BehaviorReviewError,
    neutral_signals, review_behavior,
)


def test_neutral_synthetic_does_not_force_censorship():
    v = review_behavior(neutral_signals())
    assert v.guidance == "NO_OBJECTION_IN_ADVISORY_REVIEW"
    assert not v.can_grant_permissions and not v.can_edit_sandbox_rules
    assert len(CORE_PRINCIPLES) == 8


def test_contextual_moral_behavior_not_keyword_filter():
    s = neutral_signals()
    s["fiction_or_satire"] = 1.0
    assert review_behavior(s).risk < review_behavior(neutral_signals()).risk
    s = neutral_signals()
    s["likelihood_of_harm"] = 1.0
    s["third_party_effect"] = 1.0
    risky = review_behavior(s)
    assert risky.guidance == "ASK_FOR_CONTEXT_OR_APPROVAL"
    assert "likelihood_of_harm" in risky.concerns
    s = neutral_signals()
    s["self_harm_encouragement"] = 1.0
    assert review_behavior(s).guidance == "ASK_FOR_CONTEXT_OR_APPROVAL"


def test_unapproved_technical_actions_stay_rejected_despite_training():
    model = TinyBehaviorHead()
    s = neutral_signals()
    for _ in range(30):
        model.learn_from_reviewed_label(s, 0, operator_enabled=True)
    for key in ("unapproved_egress", "undisclosed_storage", "sandbox_escape"):
        verdict = review_behavior(s, head=model, **{key: True})
        assert verdict.guidance == "REJECT_UNAUTHORIZED_ACTION"
        assert verdict.needs_external_capability_check
    assert review_behavior(s, has_external_effect=True, head=model).guidance == "ASK_FOR_CONTEXT_OR_APPROVAL"


def test_tiny_head_trains_actual_persistent_weights_and_roundtrips(tmp_path):
    model = TinyBehaviorHead()
    s = neutral_signals()
    s["deception_intent"] = 1.0
    before = model.score(s)
    old = model.weights
    for _ in range(12):
        model.learn_from_reviewed_label(s, 1, operator_enabled=True)
    assert model.score(s) > before
    assert model.weights != old
    assert model.steps == 12
    checkpoint = tmp_path / "head.json"
    model.save(checkpoint)
    restarted = TinyBehaviorHead.load(checkpoint)
    assert restarted.snapshot() == model.snapshot()
    assert restarted.score(s) == model.score(s)
    assert checkpoint.stat().st_mode & 0o777 == 0o600
    with pytest.raises(BehaviorReviewError):
        model.learn_from_reviewed_label(s, 0)


def test_weights_can_change_but_cannot_grant_sandbox_rights():
    s = neutral_signals()
    model = TinyBehaviorHead(weights=[-6.0] * 10, bias=-6.0)
    verdict = review_behavior(s, sandbox_escape=True, head=model)
    assert verdict.guidance == "REJECT_UNAUTHORIZED_ACTION"
    assert verdict.can_grant_permissions is False
    assert verdict.can_edit_sandbox_rules is False


def test_bad_inputs_and_tampered_checkpoint_fail_closed(tmp_path):
    s = neutral_signals()
    s.pop("deception_intent")
    with pytest.raises(BehaviorReviewError):
        review_behavior(s)
    s = neutral_signals()
    s["uncertainty"] = float("nan")
    with pytest.raises(BehaviorReviewError):
        review_behavior(s)
    s = neutral_signals()
    with pytest.raises(BehaviorReviewError):
        review_behavior(s, has_external_effect=1)
    model = TinyBehaviorHead()
    with pytest.raises(BehaviorReviewError):
        model.learn_from_reviewed_label(s, 2, operator_enabled=True)
    altered = model.snapshot()
    altered["weights"][0] = 999.0
    with pytest.raises(BehaviorReviewError):
        TinyBehaviorHead.restore(altered)
    checkpoint = tmp_path / "model.json"
    model.save(checkpoint)
    checkpoint.write_text(json.dumps(altered))
    with pytest.raises(BehaviorReviewError):
        TinyBehaviorHead.load(checkpoint)
