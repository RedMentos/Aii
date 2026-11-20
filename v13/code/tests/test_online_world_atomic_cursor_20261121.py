"""Exactly-once persistence regressions for the real OnlineWorld consumer."""
import json
import multiprocessing as mp
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from v13 import world_model
from v13.continuous_predictor import OnlinePredictor
from v13.online_world import OnlineWorld


def transition(i):
    return {
        "action_id": f"action-{i}",
        "s": [.1 + i * .01, 0., 0., 1.],
        "a": "simple" if i % 2 == 0 else "detail",
        "y": [.2 + i * .005, 1., .3],
    }


def runtime(home):
    return SimpleNamespace(home=home, store=object())


def test_model_parameters_and_processed_ids_share_one_checkpoint(tmp_path):
    rows = [transition(1)]
    with patch("v13.online_world.world_model.transitions", return_value=rows):
        world = OnlineWorld(runtime(tmp_path))
        assert world.update()["learned"] == 1
        assert world.model.metadata["processed_ids"] == ["action-1"]
        with np.load(world.model.path, allow_pickle=False) as data:
            assert json.loads(str(data["metadata"]))["processed_ids"] == ["action-1"]
        assert not world.cursor.exists()
        restarted = OnlineWorld(runtime(tmp_path))
        assert restarted.update()["learned"] == 0
        assert restarted.model.seen == 1


def test_stale_instance_reloads_checkpoint_inside_shared_lock(tmp_path):
    rows = [transition(2)]
    with patch("v13.online_world.world_model.transitions", return_value=rows):
        first = OnlineWorld(runtime(tmp_path))
        stale = OnlineWorld(runtime(tmp_path))
        assert first.update()["learned"] == 1
        assert stale.update()["learned"] == 0
        assert OnlineWorld(runtime(tmp_path)).model.seen == 1


def test_failure_before_replace_restores_uncommitted_gradient(tmp_path):
    rows = [transition(3)]
    with patch("v13.online_world.world_model.transitions", return_value=rows):
        world = OnlineWorld(runtime(tmp_path))
        before = world.model.path.read_bytes()
        with patch.object(world.model, "checkpoint", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                world.update()
        assert world.model.seen == 0
        assert world.processed == []
        assert world.model.path.read_bytes() == before
        assert OnlineWorld(runtime(tmp_path)).update()["learned"] == 1
        assert OnlineWorld(runtime(tmp_path)).model.seen == 1


def test_exception_after_replace_is_reconciled_as_committed(tmp_path):
    rows = [transition(4)]
    with patch("v13.online_world.world_model.transitions", return_value=rows):
        world = OnlineWorld(runtime(tmp_path))
        original = world.model.checkpoint
        calls = [0]

        def commit_then_interrupt(metadata=None):
            original(metadata=metadata)
            calls[0] += 1
            if calls[0] == 1:
                raise OSError("simulated interruption after atomic replace")

        with patch.object(world.model, "checkpoint", side_effect=commit_then_interrupt):
            assert world.update()["learned"] == 1
        assert world.model.seen == 1
        assert world.processed == ["action-4"]
        assert OnlineWorld(runtime(tmp_path)).update()["learned"] == 0


def test_legacy_cursor_is_migrated_into_checkpoint_metadata(tmp_path):
    home = tmp_path / "online_world"
    home.mkdir()
    legacy_model = OnlinePredictor(7, len(world_model.ACTIONS), home)
    legacy_model.checkpoint(metadata={})
    (home / "cursor.json").write_text(json.dumps({
        "revision": "v13-online-world-v1",
        "processed": ["action-5"],
    }))
    rows = [transition(5), transition(6)]
    with patch("v13.online_world.world_model.transitions", return_value=rows):
        world = OnlineWorld(runtime(tmp_path))
        assert world.processed == ["action-5"]
        assert world.update()["learned"] == 1
        assert world.processed == ["action-5", "action-6"]


def test_corrupt_legacy_cursor_fails_closed(tmp_path):
    home = tmp_path / "online_world"
    home.mkdir()
    (home / "cursor.json").write_text("{bad")
    with pytest.raises(json.JSONDecodeError):
        OnlineWorld(runtime(tmp_path))


def test_old_predictor_checkpoint_without_metadata_remains_readable(tmp_path):
    home = tmp_path / "online_world"
    home.mkdir()
    path = home / "online_predictor.npz"
    rng = np.random.default_rng(0)
    np.savez_compressed(
        path,
        revision=np.array("v13-online-predictor-v1"),
        dimensions=np.array([7, len(world_model.ACTIONS), 128]),
        W=np.eye(7),
        U=np.zeros((len(world_model.ACTIONS), 7)),
        bias=np.zeros(7),
        x=np.zeros((0, 7)),
        act=np.zeros(0, dtype=np.int64),
        y=np.zeros((0, 7)),
        counters=np.array([0, 0]),
        rng_state=np.array(json.dumps(rng.bit_generator.state)),
    )
    model = OnlinePredictor(7, len(world_model.ACTIONS), home)
    assert model.metadata == {}
    assert model.seen == 0


def _concurrent_worker(home, barrier, result_queue):
    from types import SimpleNamespace
    from v13 import world_model
    from v13.online_world import OnlineWorld

    world_model.transitions = lambda store, limit: [transition(77)]
    barrier.wait()
    result = OnlineWorld(SimpleNamespace(home=Path(home), store=object())).update()
    result_queue.put(result["learned"])


def test_two_processes_cannot_apply_same_action_twice(tmp_path):
    if "fork" not in mp.get_all_start_methods():
        pytest.skip("requires POSIX fork for the shared local filesystem regression")
    context = mp.get_context("fork")
    barrier = context.Barrier(2)
    result_queue = context.Queue()
    processes = [
        context.Process(target=_concurrent_worker, args=(str(tmp_path), barrier, result_queue))
        for _ in range(2)
    ]
    try:
        for process in processes:
            process.start()
        values = sorted(result_queue.get(timeout=15) for _ in processes)
        for process in processes:
            process.join(15)
        assert all(process.exitcode == 0 for process in processes)
        assert values == [0, 1]
        final = OnlineWorld(runtime(tmp_path))
        assert final.model.seen == 1
        assert final.processed == ["action-77"]
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(5)
