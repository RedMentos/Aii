"""Composite integration of persistent behavior-head weights and replay JEPA.

Neither learner is a permission broker. Both are synthetic-only evidence.
"""
from v13.android_goal_replay_retention import run_goal_replay
from v13.behavior_governor import TinyBehaviorHead, neutral_signals, review_behavior


def test_behavior_training_restart_then_android_goal_and_replay(tmp_path):
    signal = neutral_signals()
    signal["deception_intent"] = 1.0
    head = TinyBehaviorHead()
    before = head.score(signal)
    head.learn_from_reviewed_label(signal, 1, operator_enabled=True)
    assert head.score(signal) > before
    head.save(tmp_path / "behavior-head.json")
    restarted = TinyBehaviorHead.load(tmp_path / "behavior-head.json")
    assert restarted.steps == 1
    assert restarted.score(signal) > before
    assert review_behavior(neutral_signals(), head=restarted,
                           undisclosed_storage=True).guidance == "REJECT_UNAUTHORIZED_ACTION"
    result = run_goal_replay(tmp_path / "sim", count=18, seed=9, steps=3)
    assert result["goal"]["behavior_review"] == "CONTEXTUAL_ADVISORY_ON_EACH_SYNTHETIC_ACTION"
    assert result["goal"]["restart_state_digest_equal"]
    assert result["replay"]["both_models_changed_numeric_weights"]
    assert result["replay"]["source_ids_disjoint"]
    assert result["native_android_executed"] is False
    assert result["registered_t8_training_corpus_modified"] is False
    assert result["body_weights_modified"] is False
