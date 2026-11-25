import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from v13.latent_adapter import (
    LatentAdapterError,
    fit_from_tap_records,
    load_adapter,
    project_rows,
    save_adapter,
)

SENDER_HASH = "a" * 64
RECEIVER_HASH = "b" * 64
SENDER_REV = "b1-r1"
RECEIVER_REV = "b2-r1"
SENDER_TAP = "b1.final-rmsnorm.v1"
RECEIVER_TAP = "b2.final-rmsnorm.v1"


def _packet(home: Path, role: str, index: int, vector, revision: str, tap_id: str, created: int):
    dim = len(vector)
    vectors = [
        [1000.0 + col for col in range(dim)],
        [float(value) for value in vector],
        [float(value) * 0.999 + 0.001 for value in vector],
    ]
    token_ids = [0, 1, 2]
    relative = f"data/blobs/{role}-{index}.json"
    path = home / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"token_ids": token_ids, "vectors": vectors}), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    source_ref = {
        "source_id": f"src_{index}",
        "sha256": hashlib.sha256(f"source-{index}".encode()).hexdigest(),
        "char_start": 0,
        "char_end": 32,
        "modality": "text",
    }
    packet = {
        "packet_id": f"pkt_{role}_{index}",
        "role": role,
        "event_id": f"evt_{index}",
        "brain_generation_id": "gen_0001",
        "source_ref": source_ref,
        "tap_id": tap_id,
        "model_revision": revision,
        "runner_revision": "b10964",
        "token_ids": token_ids,
        "feature_path": relative,
        "feature_sha256": digest,
        "shape": [3, dim],
        "role_state": "INDEPENDENT_READ_ONLY_PREFILL",
        "receiver_read_authority": 0,
        "receiver_injection_authority": 0,
        "body_learning_authority": 0,
        "metrics": {
            "operation": "PREFILL_TAP",
            "prompt_tokens": 3,
            "embedding_dim": dim,
            "tap_id": tap_id,
            "pooling": "none",
            "whole_sequence_prefill": True,
            "normalization": "native_final_RMSNorm_only",
            "CAN_LATENT_TAP": True,
            "CAN_LATENT_INJECT": False,
            "CAN_TRAIN_BODY": False,
        },
    }
    return (f"pkt_{role}_{index}", "LatentTapPacket", packet["event_id"],
            packet["brain_generation_id"], json.dumps(packet), created)


def _home(tmp_path: Path, count: int = 24, *, shuffle_receiver: bool = False):
    rng = np.random.default_rng(812)
    basis = np.asarray([
        [1.0, 0.0, 0.5, -0.2, 0.1, 0.2],
        [0.0, 1.0, 0.3, 0.4, -0.3, 0.1],
    ])
    target = np.asarray([
        [1.2, -0.4, 0.7, 0.2],
        [0.3, 0.8, -0.6, 1.0],
    ])
    rows = []
    receiver_vectors = []
    for index in range(count):
        latent = rng.normal(size=2)
        sender = latent @ basis + rng.normal(scale=0.0005, size=6)
        receiver = latent @ target + np.asarray([0.2, -0.1, 0.3, 0.05]) + rng.normal(scale=0.0005, size=4)
        rows.append((sender, receiver))
    if shuffle_receiver:
        shuffled = [item[1] for item in rows]
        rng.shuffle(shuffled)
        rows = [(item[0], shuffled[i]) for i, item in enumerate(rows)]
    for index, (sender, receiver) in enumerate(rows):
        rows_db = [
            _packet(tmp_path, "B1_DETAIL", index, sender, SENDER_REV, SENDER_TAP, index),
            _packet(tmp_path, "B2_GIST", index, receiver, RECEIVER_REV, RECEIVER_TAP, index),
        ]
        # Rebuild the tuples with the packet's actual JSON payload.
        for row in rows_db:
            rows.append(row) if False else None
        # Keep only database rows; source payloads remain in the SQLite table.
        receiver_vectors.append((sender, receiver))
        if index == 0:
            db = tmp_path / "data" / "db" / "brain.sqlite3"
            db.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(db)
            connection.execute(
                "CREATE TABLE packets (id TEXT PRIMARY KEY, kind TEXT NOT NULL, event_id TEXT NOT NULL, "
                "generation_id TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL)"
            )
        connection.executemany(
            "INSERT INTO packets (id, kind, event_id, generation_id, payload, created) VALUES (?, ?, ?, ?, ?, ?)",
            rows_db,
        )
    connection.commit()
    connection.close()
    return tmp_path, receiver_vectors


def _fit(home, **overrides):
    args = dict(
        sender_role="B1_DETAIL",
        receiver_role="B2_GIST",
        sender_model_revision=SENDER_REV,
        receiver_model_revision=RECEIVER_REV,
        sender_tap_id=SENDER_TAP,
        receiver_tap_id=RECEIVER_TAP,
        sender_model_sha256=SENDER_HASH,
        receiver_model_sha256=RECEIVER_HASH,
        min_pairs=20,
        max_pairs=32,
        holdout_fraction=0.25,
        split_seed=11,
        rank=2,
        ridge=1e-5,
        min_relative_improvement=0.02,
        fit_seed=7,
    )
    args.update(overrides)
    return fit_from_tap_records(home, **args)


def test_persisted_taps_fit_source_disjoint_crossdim_adapter_and_roundtrip(tmp_path):
    home, rows = _home(tmp_path)
    db = home / "data" / "db" / "brain.sqlite3"
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    report = _fit(home)
    after = hashlib.sha256(db.read_bytes()).hexdigest()

    assert before == after
    assert report["status"] == "ALIGNMENT_CANDIDATE"
    assert report["paired_source_count"] == 24
    assert report["selected_pair_count"] == 24
    assert report["train_source_count"] == 18
    assert report["holdout_source_count"] == 6
    assert report["split_policy"].startswith("ONE_PAIR_PER_SOURCE_ID")
    assert report["source_text_read"] is False
    assert report["raw_activation_vectors_exported"] is False
    assert report["sqlite_written"] is False
    assert report["model_loaded"] is False
    assert report["gradient_based_training"] is False
    assert report["adapter_parameters_fitted"] is True
    assert report["body_weights_modified"] is False
    assert report["production_route"] is False
    assert report["training_authority"] == report["native_receiver_authority"] == 0

    adapter = report["adapter"]
    assert adapter["sender_dim"] == 6
    assert adapter["receiver_dim"] == 4
    assert adapter["rank"] == 2
    assert adapter["metrics"]["relative_improvement"] > 0.95
    assert adapter["metrics"]["holdout_mse"] < adapter["metrics"]["shuffled_train_mse"]

    path = tmp_path / "adapter.v14lat"
    saved_sha = save_adapter(adapter, path)
    restored = load_adapter(path)
    projected = project_rows(
        restored,
        [rows[0][0].tolist()],
        sender_model_sha256=SENDER_HASH,
        receiver_model_sha256=RECEIVER_HASH,
        sender_tap_id=SENDER_TAP,
        receiver_tap_id=RECEIVER_TAP,
    )
    assert restored["adapter_sha256"] == saved_sha
    assert len(projected) == 1 and len(projected[0]) == 4


def test_shuffled_source_pairing_is_rejected(tmp_path):
    home, _ = _home(tmp_path, shuffle_receiver=True)
    report = _fit(home)
    assert report["status"] == "REJECTED"
    assert report["adapter"]["metrics"]["holdout_mse"] >= report["adapter"]["metrics"]["mean_baseline_mse"]


def test_fit_requires_twenty_exact_source_pairs(tmp_path):
    home, _ = _home(tmp_path, count=19)
    with pytest.raises(LatentAdapterError, match="at least 20"):
        _fit(home)


def test_requested_tap_binding_must_match_persisted_packets(tmp_path):
    home, _ = _home(tmp_path)
    with pytest.raises(LatentAdapterError, match="insufficient valid source-disjoint pairs"):
        _fit(home, receiver_tap_id="unexpected-tap")


def test_corrupt_blob_cannot_enter_adapter_fit(tmp_path):
    home, _ = _home(tmp_path)
    corrupt = home / "data" / "blobs" / "B1_DETAIL-0.json"
    corrupt.write_text("{}", encoding="utf-8")
    with pytest.raises(LatentAdapterError, match="insufficient valid source-disjoint pairs"):
        _fit(home)
