import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from v13 import world_jepa_b3_supervision as supervision


class FakeReceipt:
    def __init__(self, pair, status, index):
        self.event_id = pair["event_id"]
        self.generation_id = pair["brain_generation_id"]
        self.source_ref = pair["source_ref"]
        self.status = status
        self.action_id = f"action-{index}"
        self.evidence_ref = f"T8:action-{index}:{index:064x}"


class FakeStore:
    def __init__(self, pair_rows, permissions=None):
        self.pair_rows = pair_rows
        self.states = {}
        self.versions = {}
        if permissions is not None:
            self.states["v14.world_jepa.permissions"] = permissions

    def rows(self, query, params=()):
        if "FROM packets WHERE kind=?" in query:
            return list(self.pair_rows)
        return []

    def state(self, key, default=None):
        return self.states.get(key, default), self.versions.get(key, 0)

    def set_state(self, key, value, expected=None):
        current = self.versions.get(key, 0)
        if expected is not None and expected != current:
            raise RuntimeError("state version conflict")
        self.states[key] = value
        self.versions[key] = current + 1


def _pair(index, group, label):
    digest = f"{group + 1:064x}"
    source = {
        "source_id": f"source-{group}",
        "sha256": digest,
        "char_start": index * 10,
        "char_end": index * 10 + 5,
        "modality": "text",
    }
    pair_id = f"pair-{index:03d}"
    taps = {"B1_DETAIL": f"tap-b1-{index}", "B2_GIST": f"tap-b2-{index}"}
    tap_packets = {"B1_DETAIL": f"packet-b1-{index}", "B2_GIST": f"packet-b2-{index}"}
    return {
        "packet_id": pair_id,
        "packet_schema": supervision.PAIR_SCHEMA,
        "body_pair_id": pair_id,
        "event_id": f"event-{index}",
        "brain_generation_id": "generation-1",
        "sender_roles": ["B1_DETAIL", "B2_GIST"],
        "source_ref": source,
        "provenance": [source],
        "token_alignment": "NOT_ASSUMED_DIFFERENT_NATIVE_TOKENIZERS",
        "receiver_pooling": "B2_ADAPTIVE_GIST_SLOTS;B1_SOURCE_ALIGNED_FINE_NATIVE_SLOTS",
        "injection_authority": 0,
        "learning_authority": 0,
        "tap_packet_ids": tap_packets,
        "tap_ids": taps,
        "model_revisions": {"B1_DETAIL": "b1-rev-1", "B2_GIST": "b2-rev-1"},
        "token_counts": {"B1_DETAIL": 8, "B2_GIST": 8},
        "dimensions": {"B1_DETAIL": 8, "B2_GIST": 8},
        "feature_bindings": {
            role: {
                "feature_path": f"data/blobs/{role.lower()}-{index}.npy",
                "feature_sha256": f"{index + 1:064x}",
                "shape": [8, 8],
            }
            for role in ("B1_DETAIL", "B2_GIST")
        },
        "gist_readout": {
            "tap_packet_id": tap_packets["B2_GIST"],
            "plan": {
                "tap_id": taps["B2_GIST"],
                "max_slots": 16,
                "lossless": True,
                "receiver_injection_authority": 0,
            },
        },
        "fine_readout": {
            "tap_packet_id": tap_packets["B1_DETAIL"],
            "plan": {
                "tap_id": taps["B1_DETAIL"],
                "max_slots": 64,
                "lossless": True,
                "receiver_injection_authority": 0,
                "body_learning_authority": 0,
            },
        },
    }


def _rows_and_receipts(pairs, statuses=None):
    statuses = statuses or {}
    rows = []
    receipts = []
    for index, pair in enumerate(pairs):
        rows.append({"id": pair["packet_id"], "payload": json.dumps(pair)})
        receipts.append(FakeReceipt(pair, statuses.get(index, "FINAL"), index))
    return rows, receipts


def _ready_cohort():
    pairs = []
    statuses = {}
    for group in range(8):
        label = 1 if group < 4 else 0
        status = "FINAL" if label else "ERROR"
        for offset in range(8):
            index = group * 8 + offset
            pairs.append(_pair(index, group, label))
            statuses[index] = status
    rows, receipts = _rows_and_receipts(pairs, statuses)
    return pairs, rows, receipts


def test_collect_labels_requires_exact_event_generation_and_source(monkeypatch):
    good = _pair(0, 0, 1)
    wrong_source = _pair(1, 1, 0)
    rows, receipts = _rows_and_receipts([good, wrong_source], {0: "FINAL", 1: "ERROR"})
    # The second packet's only receipt is bound to a different source digest.
    mismatched = FakeReceipt(wrong_source, "ERROR", 1)
    mismatched.source_ref = dict(wrong_source["source_ref"], sha256="f" * 64)
    monkeypatch.setattr(
        supervision, "verify_committed_transitions",
        lambda store, limit: ([receipts[0], mismatched], 0),
    )
    result = supervision.collect_t8_outcome_labels(FakeStore(rows), limit=8)
    assert result["pair_count"] == 1
    assert result["labels"] == [1]
    assert result["label_provenance"] == [receipts[0].evidence_ref]
    assert result["unmatched_pair_count"] == 1
    assert result["status"] == "INSUFFICIENT_VERIFIED_PAIRS"


def test_collect_rejects_authority_violation_and_duplicate_span(monkeypatch):
    first = _pair(0, 0, 1)
    bad_authority = _pair(1, 1, 0)
    bad_authority["receiver_pooling"] = "TEXT_MESSAGE"
    duplicate_span = _pair(2, 0, 1)
    duplicate_span["source_ref"] = dict(first["source_ref"])
    duplicate_span["provenance"] = [duplicate_span["source_ref"]]
    rows, receipts = _rows_and_receipts([first, bad_authority, duplicate_span])
    monkeypatch.setattr(
        supervision, "verify_committed_transitions",
        lambda store, limit: (receipts, 0),
    )
    result = supervision.collect_t8_outcome_labels(FakeStore(rows), limit=8)
    assert result["pair_count"] == 1
    assert result["invalid_pair_count"] == 2
    assert result["labels"] == [1]


def test_shadow_training_is_off_without_both_local_permissions(monkeypatch, tmp_path):
    pairs, rows, receipts = _ready_cohort()
    monkeypatch.setattr(
        supervision, "verify_committed_transitions",
        lambda store, limit: (receipts, 0),
    )
    store = FakeStore(rows, permissions={"learning_enabled": True, "optimizer_permission": False})
    cognition = types.SimpleNamespace(
        r=types.SimpleNamespace(
            home=tmp_path,
            models=types.SimpleNamespace(revision=lambda role: {
                "B1_DETAIL": "b1-rev-1", "B2_GIST": "b2-rev-1"
            }[role]),
        )
    )
    result = supervision.train_l1_shadow_from_t8(store, cognition, tmp_path)
    assert result["status"] == "PENDING_OPTIMIZER_PERMISSION"
    assert not any(key.startswith(supervision.STATE_KEY) for key in store.states)


def test_source_disjoint_cohort_requires_four_groups_per_outcome(monkeypatch):
    pairs = []
    statuses = {}
    for group in range(6):
        label = 1 if group < 3 else 0
        status = "FINAL" if label else "ERROR"
        for offset in range(12):
            index = group * 12 + offset
            pairs.append(_pair(index, group, label))
            statuses[index] = status
    rows, receipts = _rows_and_receipts(pairs, statuses)
    monkeypatch.setattr(
        supervision, "verify_committed_transitions",
        lambda store, limit: (receipts, 0),
    )
    result = supervision.collect_t8_outcome_labels(FakeStore(rows), limit=128)
    assert result["pair_count"] == 72
    assert result["source_group_counts"] == {"FINAL": 3, "NONFINAL_OBSERVED": 3}
    assert result["status"] == "INSUFFICIENT_SOURCE_GROUPS"


def test_bidirectional_shadow_trainer_uses_verified_labels_and_is_idempotent(
    monkeypatch, tmp_path
):
    pairs, rows, receipts = _ready_cohort()
    monkeypatch.setattr(
        supervision, "verify_committed_transitions",
        lambda store, limit: (receipts, 0),
    )
    store = FakeStore(
        rows,
        permissions={"learning_enabled": True, "optimizer_permission": True},
    )
    cognition = types.SimpleNamespace(
        r=types.SimpleNamespace(
            home=tmp_path,
            models=types.SimpleNamespace(revision=lambda role: {
                "B1_DETAIL": "b1-rev-1", "B2_GIST": "b2-rev-1"
            }[role]),
        )
    )
    calls = []

    class StubBridge:
        def __init__(self, d, K, r, h, classes, seed, direction, aux=0):
            self.d, self.K, self.r, self.h = d, K, r, h
            self.classes, self.aux = classes, aux
            self.p = {"Q": np.asarray([float(seed)], dtype=np.float32)}

        @classmethod
        def load(cls, prefix, sender_revision, receiver_revision):
            seed = int(Path(prefix).name.split("-")[-1])
            bridge = cls(8, 4, 8, 16, 2, seed, "B1_TO_B2")
            bridge.p = {"Q": np.asarray([float(seed + 1)], dtype=np.float32)}
            return bridge

    def train_l1_shadow(cognition_arg, pair_packets, labels, label_provenance,
                        task_id, label_source, **kwargs):
        calls.append({
            "pair_count": len(pair_packets),
            "labels": list(labels),
            "label_provenance": list(label_provenance),
            "task_id": task_id,
            "label_source": label_source,
            "direction": kwargs["direction"],
        })
        return {
            "status": "L1_SHADOW_CANDIDATES_SAVED_NOT_PROMOTED",
            "l1_utility_gate": "NOT_RUN_MISSING_L0_CHANNEL_BASELINES_AND_ROLE_RETENTION",
            "latent_authority": 0,
            "receiver_injection_authority": 0,
            "body_learning_authority": 0,
            "sender_revision": "b1-rev-1",
            "receiver_revision": "b2-rev-1",
            "report_path": f"b3/shadow/{kwargs['direction']}/report.json",
            "seed_reports": [
                {
                    "seed": seed,
                    "candidate_weights": f"b3/shadow/{kwargs['direction']}/seed-{seed}.npz",
                    "manifest_sha256": f"{seed:064x}",
                    "reload_identical": True,
                }
                for seed in kwargs["seeds"]
            ],
        }

    b3pairs_module = types.ModuleType("v13.b3pairs")
    b3train_module = types.ModuleType("v13.b3train")
    b3train_module.train_l1_shadow = train_l1_shadow
    b3bridge_module = types.ModuleType("v13.b3bridge")
    b3bridge_module.Bridge = StubBridge
    monkeypatch.setitem(sys.modules, "v13.b3pairs", b3pairs_module)
    monkeypatch.setitem(sys.modules, "v13.b3train", b3train_module)
    monkeypatch.setitem(sys.modules, "v13.b3bridge", b3bridge_module)
    package = sys.modules["v13"]
    monkeypatch.setattr(package, "b3pairs", b3pairs_module, raising=False)
    monkeypatch.setattr(package, "b3train", b3train_module, raising=False)
    monkeypatch.setattr(package, "b3bridge", b3bridge_module, raising=False)

    first = supervision.train_l1_shadow_directions_from_t8(
        store, cognition, tmp_path, directions=("B1_TO_B2", "B2_TO_B1"),
        seeds=(11, 17), epochs=1, head_steps=25,
    )
    assert first["status"] == "COMPLETED"
    assert set(first["directions"]) == {"B1_TO_B2", "B2_TO_B1"}
    assert len(calls) == 2
    assert all(call["pair_count"] == 64 for call in calls)
    assert all(call["label_source"] == supervision.LABEL_SOURCE for call in calls)
    assert all(len(call["label_provenance"]) == 64 for call in calls)
    assert all(call["labels"].count(1) == 32 and call["labels"].count(0) == 32 for call in calls)
    assert first["directions"]["B1_TO_B2"]["parameter_delta_l2"] == pytest.approx(1.0)
    assert first["directions"]["B2_TO_B1"]["receiver_injection_authority"] == 0

    second = supervision.train_l1_shadow_directions_from_t8(
        store, cognition, tmp_path, directions=("B1_TO_B2", "B2_TO_B1"),
        seeds=(11, 17), epochs=1, head_steps=25,
    )
    assert second["status"] == "COMPLETED"
    assert all(value["status"] == "ALREADY_TRAINED"
               for value in second["directions"].values())
    assert len(calls) == 2


def test_empty_pair_store_does_not_scan_t8_history(monkeypatch):
    called = []
    monkeypatch.setattr(
        supervision, "verify_committed_transitions",
        lambda store, limit: called.append(limit) or ([], 0),
    )
    result = supervision.collect_t8_outcome_labels(FakeStore([]), limit=64)
    assert result["status"] == "NO_PAIRED_TAPS"
    assert result["pair_count"] == 0
    assert called == []
