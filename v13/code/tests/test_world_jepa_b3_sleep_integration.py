import importlib.util
from pathlib import Path
from types import SimpleNamespace

from v13 import world_jepa_b3_supervision, world_jepa_planner, world_jepa_runtime


def _postcommit_helpers():
    path = Path(__file__).with_name("test_v14_world_jepa_postcommit_runtime.py")
    spec = importlib.util.spec_from_file_location("_postcommit_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sleep_postcommit_routes_updated_world_jepa_to_both_b3_receivers(
    monkeypatch, tmp_path
):
    helpers = _postcommit_helpers()
    home = tmp_path / "brain-b3-postcommit"
    store, session = helpers._make_store(home)
    try:
        event_id = helpers._add_transitions(store, session, 0, 1)[0]
        sleep = helpers._sleep(store, home)
        cognition = object()
        sleep.r.cognition = cognition
        calls = []

        monkeypatch.setattr(
            world_jepa_runtime,
            "consume_after_commit",
            lambda store_arg, home_arg, **kwargs: {
                "status": "UPDATED_EXPERIMENTAL_WORLD_JEPA",
                "checkpoint_sha256": "a" * 64,
                "metrics": {"fit_steps_after": 1, "ema_target_delta_norm": 0.01},
            },
        )
        monkeypatch.setattr(
            world_jepa_planner,
            "consume_world_planner_shadow",
            lambda store_arg, event_arg, **kwargs: {
                "status": "SHADOW_PLANNER_UNAVAILABLE",
                "checkpoint_sha256": None,
            },
        )

        def train(store_arg, cognition_arg, home_arg, **kwargs):
            calls.append((store_arg, cognition_arg, home_arg, kwargs))
            return {
                "status": "PARTIAL",
                "directions": {
                    "B1_TO_B2": {"status": "NO_PAIRED_TAPS"},
                    "B2_TO_B1": {"status": "NO_PAIRED_TAPS"},
                },
            }

        monkeypatch.setattr(
            world_jepa_b3_supervision,
            "train_l1_shadow_directions_from_t8",
            train,
        )
        result = sleep._run_world_jepa(event_id)
        assert result["status"] == "POSTCOMMIT_PROCESSED"
        assert result["receiver_training"]["status"] == "PARTIAL"
        assert set(result["receiver_training"]["directions"]) == {
            "B1_TO_B2", "B2_TO_B1"
        }
        assert len(calls) == 1
        assert calls[0][0] is store
        assert calls[0][1] is cognition
        assert calls[0][2] == home
        assert calls[0][3]["directions"] == ("B1_TO_B2", "B2_TO_B1")
        assert calls[0][3]["epochs"] == 1
        assert calls[0][3]["seeds"] == (11, 17)
    finally:
        store.close()
