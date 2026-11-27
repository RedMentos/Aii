import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from v13.latent_alignment_audit import (
    AuditError,
    _pool_without_position0,
    _event_pool_discarded_energy_ratio,
    audit_home,
    audit_records,
    cross_space_knn_overlap,
)


def _write_packet(home: Path, role: str, source_index: int, vectors, revision="rev-a", created=None):
    blobs = home / "data" / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    relative = f"data/blobs/{role}-{source_index}.json"
    path = home / relative
    token_ids = list(range(len(vectors)))
    path.write_text(json.dumps({"token_ids": token_ids, "vectors": vectors}), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    packet = {
        "packet_id": f"pkt_{role}_{source_index}",
        "role": role,
        "event_id": f"evt_{source_index}",
        "brain_generation_id": "gen_0001",
        "source_ref": {
            "source_id": f"src_{source_index}",
            "sha256": f"{source_index:064x}",
            "char_start": 0,
            "char_end": 12,
            "modality": "text",
        },
        "tap_id": f"{role}-tap-v1",
        "model_revision": revision,
        "runner_revision": "b10964",
        "token_ids": token_ids,
        "feature_path": relative,
        "feature_sha256": digest,
        "shape": [len(vectors), len(vectors[0])],
        "role_state": "INDEPENDENT_READ_ONLY_PREFILL",
        "receiver_read_authority": 0,
        "receiver_injection_authority": 0,
        "body_learning_authority": 0,
        "metrics": {
            "operation": "PREFILL_TAP",
            "prompt_tokens": len(token_ids),
            "embedding_dim": len(vectors[0]),
            "tap_id": f"{role}-tap-v1",
            "pooling": "none",
            "whole_sequence_prefill": True,
            "normalization": "native_final_RMSNorm_only",
            "CAN_LATENT_TAP": True,
            "CAN_LATENT_INJECT": False,
            "CAN_TRAIN_BODY": False,
        },
    }
    return {"created": created if created is not None else source_index, "payload": packet}


def _toy_rows(i, dim=4):
    base = [float(i + 1), float((i + 1) ** 2), float((i + 1) % 3 + 1), float((i * 7) % 5 + 1)]
    first = [10000.0, -10000.0, 5000.0, 2500.0]
    rest = [base[:dim], [value * 0.5 for value in base[:dim]]]
    return [first] + rest


def test_pool_excludes_position_zero_and_reports_its_dominance():
    vectors = [[1000.0, 0.0], [1.0, 0.0], [0.0, 3.0]]
    pooled, ratio, cosine = _pool_without_position0(vectors)
    assert pooled == [0.5, 1.5]
    assert ratio == 500.0
    assert cosine is not None and cosine < 1.0


def test_event_pool_discarded_energy_ratio_measures_only_within_event_variation():
    assert _event_pool_discarded_energy_ratio([
        [999.0, -999.0],
        [2.0, 4.0],
        [2.0, 4.0],
    ]) == pytest.approx(0.0)
    varied = _event_pool_discarded_energy_ratio([
        [999.0, -999.0],
        [1.0, 0.0],
        [0.0, 1.0],
    ])
    assert varied is not None and 0.0 < varied < 1.0


def test_cross_space_knn_overlap_detects_same_neighborhoods_across_dimensions():
    source = [[float(i), float(i * i + 1)] for i in range(12)]
    target = [[row[0], row[1], 0.0] for row in source]
    result = cross_space_knn_overlap(source, target, k=2, permutations=50, seed=4)
    assert result["observed_overlap"] == 1.0
    assert result["permutation_null_mean"] < 0.5
    assert result["empirical_p_value"] < 0.1


def test_audit_reads_only_paired_source_bound_taps(tmp_path):
    home = tmp_path
    records = []
    for i in range(12):
        rows = _toy_rows(i)
        records.append(_write_packet(home, "B1_DETAIL", i, rows, "b1-r1"))
        projected = [[row[0], row[1], row[2], row[3], 0.0, 0.0] for row in rows]
        records.append(_write_packet(home, "B2_GIST", i, projected, "b2-r1"))
    db = home / "data" / "db" / "brain.sqlite3"
    db.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db)
    connection.execute(
        "CREATE TABLE packets (id TEXT PRIMARY KEY, kind TEXT NOT NULL, event_id TEXT NOT NULL, "
        "generation_id TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL)"
    )
    connection.executemany(
        "INSERT INTO packets (id, kind, event_id, generation_id, payload, created) VALUES (?, ?, ?, ?, ?, ?)",
        [(record["payload"]["packet_id"], "LatentTapPacket", record["payload"]["event_id"],
          record["payload"]["brain_generation_id"], json.dumps(record["payload"]), record["created"])
         for record in records],
    )
    connection.commit()
    connection.close()

    db_before = hashlib.sha256(db.read_bytes()).hexdigest()
    result = audit_home(home, min_pairs=10, max_pairs=32, k=2, permutations=20)
    db_after = hashlib.sha256(db.read_bytes()).hexdigest()
    assert db_before == db_after
    assert result["status"] == "MEASURED_ALIGNMENT_ONLY"
    assert result["metadata_valid_tap_packets"] == 24
    cohort = result["cohorts"][0]
    assert cohort["paired_sources"] == 12
    assert cohort["alignment"]["observed_overlap"] == 1.0
    assert cohort["sender_event_pool_discarded_energy_ratio"]["median"] > 0.0
    assert cohort["receiver_event_pool_discarded_energy_ratio"]["median"] > 0.0
    assert cohort["event_pool_metric_semantics"].startswith("descriptive within-event activation variance only")
    assert cohort["position0_excluded_from_alignment_pool"] is True
    assert cohort["causal_transfer_proven"] is False
    assert result["limits"]["source_text_read"] is False
    assert result["limits"]["weights_modified"] is False
    assert result["limits"]["projection_training_performed"] is False
    assert result["limits"]["train_test_split_performed"] is False
    assert result["limits"]["read_only_sqlite"] is True


def test_taps_from_different_events_or_generations_do_not_pair(tmp_path):
    home = tmp_path
    sender = _write_packet(home, "B1_DETAIL", 1, _toy_rows(1))
    receiver = _write_packet(home, "B2_GIST", 1, _toy_rows(1), "b2-r1")
    receiver["payload"]["event_id"] = "evt_other"
    result = audit_records(home, [sender, receiver], min_pairs=3)
    assert result["status"] == "NO_PAIRED_TAPS"
    assert result["cohorts"] == []


def test_unpaired_sources_do_not_form_a_cohort(tmp_path):
    home = tmp_path
    records = [_write_packet(home, "B1_DETAIL", 1, _toy_rows(1))]
    result = audit_records(home, records, min_pairs=3)
    assert result["status"] == "NO_PAIRED_TAPS"
    assert result["cohorts"] == []


def test_tampered_blob_is_counted_as_invalid_and_never_used(tmp_path):
    home = tmp_path
    records = []
    for i in range(4):
        records.append(_write_packet(home, "B1_DETAIL", i, _toy_rows(i)))
        records.append(_write_packet(home, "B2_GIST", i, _toy_rows(i), "b2-r1"))
    path = home / records[0]["payload"]["feature_path"]
    path.write_text("{}", encoding="utf-8")
    result = audit_records(home, records, min_pairs=4, k=1, permutations=10)
    assert result["invalid_or_unreadable_paired_blobs"] >= 1
    assert result["status"] == "INSUFFICIENT_COHORT"


def test_authority_or_activation_kind_mismatch_is_rejected(tmp_path):
    home = tmp_path
    record = _write_packet(home, "B1_DETAIL", 1, _toy_rows(1))
    record["payload"]["receiver_injection_authority"] = 1
    result = audit_records(home, [record], min_pairs=3)
    assert result["status"] == "NO_VALID_TAPS"
    assert result["invalid_metadata_packets"] == 1


def test_path_traversal_is_rejected(tmp_path):
    home = tmp_path
    record = _write_packet(home, "B1_DETAIL", 1, _toy_rows(1))
    record["payload"]["feature_path"] = "data/blobs/../../secret.json"
    with pytest.raises(AuditError):
        from v13.latent_alignment_audit import _read_tap_blob
        _read_tap_blob(home, record["payload"])


def test_symlinked_blob_root_is_refused(tmp_path):
    home = tmp_path
    record = _write_packet(home, "B1_DETAIL", 1, _toy_rows(1))
    blobs = home / "data" / "blobs"
    moved = home / "data" / "real-blobs"
    blobs.rename(moved)
    blobs.symlink_to(moved, target_is_directory=True)
    with pytest.raises(AuditError):
        from v13.latent_alignment_audit import _read_tap_blob
        _read_tap_blob(home, record["payload"])
