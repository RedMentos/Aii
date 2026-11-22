import hashlib
import numpy as np
import pytest

from v13.latent_bridge_native import (
    LowRankAdapter,
    adapter_directory,
    adapter_status,
    pairs_from_packets,
    resample_rows,
)


def synthetic_pairs(seed=17, count=40, input_dim=32, output_dim=24, rank=8, slots=4):
    rng = np.random.default_rng(seed)
    true_a = rng.normal(0.0, 1.0 / np.sqrt(input_dim), (rank, input_dim)).astype(np.float32)
    true_b = rng.normal(0.0, 0.25 / np.sqrt(rank), (output_dim, rank)).astype(np.float32)
    pairs = []
    for index in range(count):
        sender = rng.normal(size=(slots, input_dim)).astype(np.float32)
        receiver = np.tanh(sender @ true_a.T) @ true_b.T
        pairs.append({
            "source_id": f"source-{index}",
            "event_id": f"event-{index}",
            "generation_id": "generation-1",
            "sender_role": "B1_DETAIL",
            "receiver_role": "B2_GIST",
            "sender_model_revision": "b1-rev-1",
            "receiver_model_revision": "b2-rev-1",
            "sender_tap_id": "b1.tap.v1",
            "receiver_tap_id": "b2.tap.v1",
            "sender_vectors": sender,
            "receiver_vectors": receiver,
            "committed": True,
        })
    return pairs


def train_candidate():
    pairs = synthetic_pairs()
    adapter = LowRankAdapter(
        "B1_DETAIL", "B2_GIST", "b1-rev-1", "b2-rev-1",
        32, 24, rank=8, seed=17,
    )
    metrics = adapter.fit(
        pairs, admitted=True, committed=True, epochs=30,
        batch_size=8, max_steps=200, slots=4,
    )
    return adapter, metrics, pairs


def test_source_disjoint_low_rank_training_improves_holdout_and_negative_control():
    adapter, metrics, pairs = train_candidate()
    assert metrics["status"] == "SHADOW_CANDIDATE"
    assert metrics["heldout_improved"] is True
    assert metrics["negative_control_passed"] is True
    assert metrics["holdout_mse_after"] < metrics["holdout_mse_before"]
    assert metrics["holdout_cosine_after"] > metrics["holdout_cosine_before"]
    assert set(metrics["train_source_ids"]).isdisjoint(metrics["holdout_source_ids"])
    assert metrics["source_pairs"] == 40
    projected = adapter.project(
        pairs[-1]["sender_vectors"], source_id=pairs[-1]["source_id"],
        generation_id=pairs[-1]["generation_id"],
        sender_revision="b1-rev-1", receiver_revision="b2-rev-1",
    )
    assert projected.shape == (4, 24)
    assert np.isfinite(projected).all()


def test_realistic_native_dimensions_are_supported_without_dense_square_matrix():
    adapter = LowRankAdapter(
        "B1_DETAIL", "B2_GIST", "b1", "b2", 2048, 1024, rank=16,
    )
    assert adapter.a.shape == (16, 2048)
    assert adapter.b.shape == (1024, 16)
    assert adapter.a.nbytes + adapter.b.nbytes < 250_000


def test_fit_requires_admission_committed_unique_source_pairs_and_matching_revisions():
    pairs = synthetic_pairs(count=8)
    adapter = LowRankAdapter("B1_DETAIL", "B2_GIST", "b1-rev-1", "b2-rev-1", 32, 24, rank=8)
    with pytest.raises(PermissionError):
        adapter.fit(pairs, admitted=False, committed=True)
    with pytest.raises(PermissionError):
        adapter.fit([{**pairs[0], "committed": False}, *pairs[1:]], admitted=True, committed=True)
    with pytest.raises(ValueError, match="unique"):
        adapter.fit([*pairs[:-1], dict(pairs[0])], admitted=True, committed=True)
    with pytest.raises(ValueError, match="revision"):
        adapter.fit([*pairs[:-1], {**pairs[-1], "receiver_model_revision": "stale"}],
                    admitted=True, committed=True)


def test_rejected_or_stale_adapter_cannot_project():
    pairs = synthetic_pairs()
    adapter = LowRankAdapter("B1_DETAIL", "B2_GIST", "b1-rev-1", "b2-rev-1", 32, 24, rank=8)
    adapter.fit(pairs, admitted=True, committed=True, epochs=30, batch_size=8, max_steps=200, slots=4)
    with pytest.raises(PermissionError, match="revisions"):
        adapter.project(pairs[0]["sender_vectors"], source_id="s", generation_id="g",
                        sender_revision="wrong", receiver_revision="b2-rev-1")
    adapter.status = "REJECTED"
    with pytest.raises(PermissionError, match="SHADOW_CANDIDATE"):
        adapter.project(pairs[0]["sender_vectors"], source_id="s", generation_id="g",
                        sender_revision="b1-rev-1", receiver_revision="b2-rev-1")


def test_atomic_checkpoint_readback_and_rollback(tmp_path):
    adapter, metrics, pairs = train_candidate()
    directory = adapter_directory(tmp_path, "B1_DETAIL", "B2_GIST", "b1-rev-1", "b2-rev-1")
    first = adapter.save(directory)
    loaded, readback = LowRankAdapter.load_current(
        directory, expected_sender_revision="b1-rev-1", expected_receiver_revision="b2-rev-1",
    )
    assert readback == first
    assert loaded.revision() == adapter.revision()
    assert np.allclose(
        loaded.project(pairs[0]["sender_vectors"], source_id="source-0", generation_id="generation-1",
                       sender_revision="b1-rev-1", receiver_revision="b2-rev-1"),
        adapter.project(pairs[0]["sender_vectors"], source_id="source-0", generation_id="generation-1",
                        sender_revision="b1-rev-1", receiver_revision="b2-rev-1"),
    )
    second = LowRankAdapter(
        "B1_DETAIL", "B2_GIST", "b1-rev-1", "b2-rev-1", 32, 24, rank=8, seed=29,
    )
    second.fit(pairs, admitted=True, committed=True, epochs=30, batch_size=8, max_steps=200, slots=4)
    second_pointer = second.save(directory)
    assert second_pointer["adapter_revision"] != first["adapter_revision"]
    rolled = LowRankAdapter.rollback(directory)
    assert rolled["adapter_revision"] == first["adapter_revision"]
    restored, _ = LowRankAdapter.load_current(directory)
    assert restored.revision() == first["adapter_revision"]
    assert adapter_status(directory)["status"] == "SHADOW_CANDIDATE"


def test_checkpoint_tamper_and_symlink_fail_closed(tmp_path):
    adapter, _, _ = train_candidate()
    directory = adapter_directory(tmp_path, "B1_DETAIL", "B2_GIST", "b1-rev-1", "b2-rev-1")
    pointer = adapter.save(directory)
    path = directory / pointer["file"]
    raw = path.read_bytes()
    path.write_bytes(raw + b"tamper")
    with pytest.raises(ValueError, match="hash"):
        LowRankAdapter.load_current(directory)
    path.unlink()
    path.symlink_to(tmp_path / "outside.npz")
    with pytest.raises(ValueError, match="unsafe"):
        LowRankAdapter.load_current(directory)


def test_pairs_from_packets_joins_only_same_source_event_and_generation():
    packets = []
    values = {
        "B1_DETAIL": [[1.0, 2.0], [2.0, 3.0]],
        "B2_GIST": [[4.0, 5.0], [5.0, 6.0]],
    }
    for role in ("B1_DETAIL", "B2_GIST"):
        packets.append({
            "kind": "LatentTapPacket", "packet_id": role,
            "role": role, "event_id": "event-1", "brain_generation_id": "generation-1",
            "source_ref": {"source_id": "source-1", "modality": "text"},
            "model_revision": role + "-rev", "tap_id": role + "-tap",
        })
    packets.append({
        "kind": "LatentTapPacket", "packet_id": "bad-generation",
        "role": "B2_GIST", "event_id": "event-1", "brain_generation_id": "generation-2",
        "source_ref": {"source_id": "source-1", "modality": "text"},
        "model_revision": "B2_GIST-rev", "tap_id": "B2_GIST-tap",
    })
    def read_tap(packet):
        return {"token_ids": [1, 2], "vectors": values[packet["role"]]}
    pairs = pairs_from_packets(packets, read_tap, "B1_DETAIL", "B2_GIST")
    assert len(pairs) == 1
    assert pairs[0]["source_id"] == "source-1"
    assert pairs[0]["generation_id"] == "generation-1"


def test_resample_preserves_order_and_rejects_nonfinite_or_oversized():
    value = np.asarray([[0.0, 0.0], [2.0, 4.0], [4.0, 8.0]], dtype=np.float32)
    sampled = resample_rows(value, 5)
    assert sampled.shape == (5, 2)
    assert np.allclose(sampled[:, 0], [0, 1, 2, 3, 4])
    assert np.allclose(sampled[:, 1], [0, 2, 4, 6, 8])
    with pytest.raises(ValueError):
        resample_rows([[float("nan"), 0.0]], 1)
