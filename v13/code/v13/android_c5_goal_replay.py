"""Typed C5 action review -> synthetic broker -> durable outcome -> JEPA.

The shadow bridge is never a native approval. The only executor is the
separate synthetic Notes world. Real Android permissions remain OFF.
"""
from __future__ import annotations

from pathlib import Path

from .android_capability_bridge import (
    ActionRequest, AndroidActionBridge, Capability, CapabilityRegistry,
    ExecutionStatus,
)
from .android_goal_learning_demo import run_demo
from .android_goal_replay_retention import run_goal_replay
from .speech_intent import SpeechCoordinator


def run_integrated_goal(home, *, first=0, count=4, seed=17, steps=5):
    """Exercise C5 typed shadow planning and persistent replay in one run."""
    if type(first) is not int or type(count) is not int or not 1 <= count <= 24:
        raise ValueError("invalid integration budget")
    # The replay ablation needs enough distinct x+action cohorts for disjoint
    # old-test / old-train / recent splits. Small demos must use run_demo,
    # never fabricate heldout support or silently weaken the split.
    if count < 18:
        raise ValueError("replay requires at least 18 distinct synthetic note tasks")
    home = Path(home)
    registry = CapabilityRegistry()
    bridge = AndroidActionBridge(registry, clock=lambda: 100.0)
    intent = ActionRequest(
        action_id="synthetic-c5-goal-" + str(first),
        capability=Capability.LAUNCH_APP,
        args={"package": "org.v13.demo.notes"},
        source_event_id="synthetic-goal-" + str(first),
        expires_at=130.0,
    )
    denied = bridge.submit(intent)
    if denied.status is not ExecutionStatus.OFF:
        raise ValueError("typed bridge must default OFF")
    registry.enable_shadow_for_test(Capability.LAUNCH_APP)
    intent = ActionRequest(
        action_id="synthetic-c5-shadow-" + str(first),
        capability=Capability.LAUNCH_APP,
        args={"package": "org.v13.demo.notes"},
        source_event_id="synthetic-goal-" + str(first),
        expires_at=130.0,
    )
    shadow = bridge.submit(intent)
    if shadow.status is not ExecutionStatus.SHADOW:
        raise ValueError("no synthetic shadow planning")
    registry.stop()
    if registry.status(Capability.LAUNCH_APP) is not ExecutionStatus.OFF:
        raise ValueError("stop failed")
    # This fixture invokes only the fake Notes simulator, never the bridge's
    # (nonexistent) native executor. A second call tests persisted replay.
    result = run_goal_replay(home, first=first, count=count, seed=seed, steps=steps)
    replay = result["replay"]
    if (replay["readback"]["replay_trained_model_reloaded"] is not True
            or result["goal"]["native_android_executed"] is not False):
        raise ValueError("learning checkpoint or isolation verification failed")
    # C3 language-to-voice intent is wired to the SAME completed goal receipt.
    # No renderer, microphone, or OS audio privilege exists in this path.
    speech = SpeechCoordinator(max_pending=2, clock=lambda: 101.0)
    utterance = speech.enqueue(
        "The simulated notes task completed.",
        "synthetic-goal-" + str(first),
    )
    speech_status = speech.dispatch_one()
    if speech_status.status != "OFF":
        raise ValueError("unapproved native speech output")
    return {
        "schema": "v13.c5_shadow_android_goal_replay/1",
        "c5_typed_status": shadow.status.value,
        "c3_speech_intent": {
            "id": utterance.id,
            "source_turn": utterance.source_turn,
            "queued": len(speech.receipts()) == 1,
            "renderer_status": speech_status.status,
            "native_audio_executed": False,
        },
        "c5_native_execution": False,
        "t8_redacted_action_outcome": shadow.t8_record(),
        "synthetic_goal": result,
        "native_android_executed": False,
        "b1_b2_c3_weights_modified": False,
        "replay_weight_checkpoint_reloaded": True,
    }
