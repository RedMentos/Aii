import hashlib
import json

import numpy as np
import pytest

from v13.latent_adapter import (
    LatentAdapterError, fit_adapter, project_event, project_rows, project_vector, save_adapter,
    load_adapter,
)

SENDER_HASH = "a" * 64
RECEIVER_HASH = "b" * 64


def make_pairs(prefix, groups, *, seed, shuffled=False):
    rng = np.random.default_rng(seed)
    basis = np.asarray([[1.0, 0.0], [0.0, 1.0], [0.5, 0.3], [-0.2, 0.4], [0.1, -0.3], [0.2, 0.1]])
    target = np.asarray([[1.2, -0.4, 0.7, 0.2], [0.3, 0.8, -0.6, 1.0]])
    rows = []
    for group in range(groups):
        for sample in range(4):
            z = rng.normal(size=2)
            x = z @ basis.T + rng.normal(scale=0.001, size=6)
            y = z @ target + np.asarray([0.2, -0.1, 0.3, 0.05]) + rng.normal(scale=0.001, size=4)
            rows.append({"pair_id": f"{prefix}-pair-{group}-{sample}", "source_id": f"{prefix}-source-{group}", "sender_vector": x.tolist(), "receiver_vector": y.tolist()})
    if shuffled:
        values = [row["receiver_vector"] for row in rows]
        rng.shuffle(values)
        for row, value in zip(rows, values):
            row["receiver_vector"] = value
    return rows


def fit(train=None, holdout=None, **overrides):
    args = dict(
        sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
        sender_tap_id="b2.gist.layer-final.v1", receiver_tap_id="c3.input-embedding.v1",
        sender_model_revision="b2-test-r1", receiver_model_revision="c3-test-r1",
        sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
        rank=2, ridge=1e-5,
    )
    args.update(overrides)
    return fit_adapter(train or make_pairs("train", 10, seed=1), holdout or make_pairs("hold", 5, seed=2), **args)


def test_low_rank_adapter_generalizes_across_disjoint_sources():
    adapter = fit()
    assert adapter["status"] == "ALIGNMENT_CANDIDATE"
    assert adapter["sender_dim"] == 6 and adapter["receiver_dim"] == 4
    assert adapter["rank"] == 2
    assert adapter["metrics"]["relative_improvement"] > 0.95
    assert adapter["metrics"]["holdout_mse"] < adapter["metrics"]["shuffled_train_mse"]
    assert adapter["production_route"] is False
    assert adapter["semantic_use_proven"] is False
    assert adapter["training_authority"] == adapter["native_receiver_authority"] == 0


def test_source_group_leakage_is_rejected():
    train = make_pairs("train", 8, seed=1)
    holdout = make_pairs("hold", 4, seed=2)
    holdout[0]["source_id"] = train[0]["source_id"]
    with pytest.raises(LatentAdapterError, match="source leakage"):
        fit_adapter(train, holdout, sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
                    sender_tap_id="s", receiver_tap_id="r", sender_model_revision="s1",
                    receiver_model_revision="r1", sender_model_sha256=SENDER_HASH,
                    receiver_model_sha256=RECEIVER_HASH, rank=2)


def test_shuffled_pairing_does_not_open_alignment_candidate_gate():
    adapter = fit(train=make_pairs("train", 10, seed=1, shuffled=True), holdout=make_pairs("hold", 5, seed=2))
    assert adapter["status"] == "REJECTED"


def test_projection_rejects_wrong_model_or_tap_binding():
    adapter = fit()
    vector = make_pairs("probe", 1, seed=99)[0]["sender_vector"]
    with pytest.raises(LatentAdapterError, match="binding mismatch"):
        project_vector(adapter, vector, sender_model_sha256="c"*64,
                       receiver_model_sha256=RECEIVER_HASH,
                       sender_tap_id=adapter["sender_tap_id"], receiver_tap_id=adapter["receiver_tap_id"])


def test_checkpoint_roundtrip_and_tamper_detection(tmp_path):
    adapter = fit()
    path = tmp_path / "adapter.v14lat"
    saved_hash = save_adapter(adapter, path)
    restored = load_adapter(path)
    assert restored["adapter_sha256"] == saved_hash
    assert restored["projection_scope"] == "PAIRED_VECTOR"
    vector = make_pairs("probe", 1, seed=99)[0]["sender_vector"]
    kwargs = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                  sender_tap_id=adapter["sender_tap_id"], receiver_tap_id=adapter["receiver_tap_id"])
    assert np.allclose(project_vector(adapter, vector, **kwargs), project_vector(restored, vector, **kwargs), atol=1e-6)
    damaged = bytearray(path.read_bytes())
    damaged[-1] ^= 0x01
    path.write_bytes(damaged)
    with pytest.raises(LatentAdapterError, match="weight digest"):
        load_adapter(path)


def test_projection_scope_prevents_event_vector_broadcast_to_token_rows():
    event_adapter = fit()
    vector = make_pairs("probe", 1, seed=99)[0]["sender_vector"]
    bindings = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                    sender_tap_id=event_adapter["sender_tap_id"], receiver_tap_id=event_adapter["receiver_tap_id"])
    with pytest.raises(LatentAdapterError, match="event-level adapter"):
        project_rows(event_adapter, [vector, vector], **bindings)

    token_adapter = fit(projection_scope="TOKENWISE")
    token_bindings = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                          sender_tap_id=token_adapter["sender_tap_id"], receiver_tap_id=token_adapter["receiver_tap_id"])
    projected = project_rows(token_adapter, [vector, vector], **token_bindings)
    assert len(projected) == 2 and all(len(row) == token_adapter["receiver_dim"] for row in projected)
    with pytest.raises(LatentAdapterError, match="tokenwise adapter"):
        project_event(token_adapter, vector, **token_bindings)
