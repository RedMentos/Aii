"""Cross-organ C5→Android fake goal→JEPA→C3 speech intent.

No real microphone, Android UI, speaker or OS permission is exercised.
"""
from v13.android_c5_goal_replay import run_integrated_goal


def test_completed_simulated_goal_emits_off_gated_c3_speech(tmp_path):
    report = run_integrated_goal(tmp_path, count=4, steps=3)
    speech = report["c3_speech_intent"]
    assert speech["queued"] is True
    assert speech["source_turn"] == "synthetic-goal-0"
    assert speech["renderer_status"] == "OFF"
    assert speech["native_audio_executed"] is False
    assert report["c5_native_execution"] is False
    assert report["native_android_executed"] is False
    assert report["replay_weight_checkpoint_reloaded"] is True
