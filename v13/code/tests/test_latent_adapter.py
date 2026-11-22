import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from v13.latent_adapter import (
    LatentAdapterError, fit_adapter, project_vector, save_adapter,
    load_adapter, probe_native_receiver,
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
    vector = make_pairs("probe", 1, seed=99)[0]["sender_vector"]
    kwargs = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                  sender_tap_id=adapter["sender_tap_id"], receiver_tap_id=adapter["receiver_tap_id"])
    assert np.allclose(project_vector(adapter, vector, **kwargs), project_vector(restored, vector, **kwargs), atol=1e-6)
    damaged = bytearray(path.read_bytes())
    damaged[-1] ^= 0x01
    path.write_bytes(damaged)
    with pytest.raises(LatentAdapterError, match="weight digest"):
        load_adapter(path)


def test_projected_rows_reach_existing_native_receiver_contract(tmp_path):
    adapter = fit()
    home = tmp_path / "home"
    models = home / "models"
    bins = home / "bin"
    models.mkdir(parents=True)
    bins.mkdir()
    model_path = models / "receiver.gguf"
    model_path.write_bytes(b"receiver-model-fixture")
    binary = bins / "native_latent_receiver"
    binary.write_text("""#!/usr/bin/env python3
import json, sys
REV = 'b29c606e28a01b1bc8c1351026a0fa6e616bf6c4'
if len(sys.argv) == 2 and sys.argv[1] == '--version':
    print(json.dumps({'schema':'v14.native-latent-receiver/2','runner_revision':REV,'llama_version':'v0.4.1-test'})); raise SystemExit(0)
args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
rows, dim = int(args['--rows']), int(args['--input-dim'])
positions = [int(v) for v in args['--positions'].split(',')]
raw = sys.stdin.buffer.read()
assert len(raw) > 0
print(json.dumps({'status':'DECODED','llama_version':'v0.4.1-test','receiver_input_dim':dim,'output_dim':4,'decode_status':0,'finite_output':True,'output_norm':1.0,'input_effect_rms':0.5,'zero_control_cosine':0.1,'shuffle_control_cosine':0.2,'row_shuffle_control_applicable':rows >= 2,'row_shuffle_control_cosine':0.15 if rows >= 2 else None,'repeat_cosine':1.0,'position_ids':positions,'position_mode':'ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL'}))
""", encoding="utf-8")
    binary.chmod(0o755)
    rows = [row["sender_vector"] for row in make_pairs("probe", 1, seed=99)[:2]]
    with pytest.raises(PermissionError, match="explicit confirmation"):
        probe_native_receiver(
            adapter, rows, home=home, model_path=model_path,
            source_id="source-probe", generation_id="generation-probe",
            position_ids=[0, 1], position_mode="ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL",
            deadline=__import__("time").monotonic() + 10, binary_path=binary,
        )
    result = probe_native_receiver(
        adapter, rows, home=home, model_path=model_path,
        source_id="source-probe", generation_id="generation-probe",
        position_ids=[0, 1], position_mode="ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL",
        deadline=__import__("time").monotonic() + 10, confirm=True, runtime_idle=True,
        threads=1, binary_path=binary,
    )
    assert result["status"] == "DIAGNOSTIC_ONLY"
    assert result["receiver_probe"]["status"] == "NATIVE_INPUT_EFFECT"
    assert result["receiver_probe"]["input_dim"] == adapter["receiver_dim"]
    assert result["semantic_use_proven"] is False
    assert result["production_route"] is False
    assert result["training_authority"] == result["native_receiver_authority"] == 0
