"""Persistent Store-backed JEPA consumer for verified V13 T8 action outcomes.

This is a trainable numeric WorldJEPA + role-specific B1/B2 readout candidate.
It is not a native LLM/GGUF weight editor and is not registered in frozen
runtime.py. The Store state pointer atomically binds the immutable checkpoint
to the processed receipt cursor, replay memory and receiver heads.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import uuid

import numpy as np

from v13 import world_jepa
from v13 import world_jepa_shadow_checkpoint
from v13 import world_model
from .world_jepa_store_authority import verify_committed_transition_page


REVISION = "v14-world-jepa-store-consumer-v3"
LEGACY_REVISION = "v14-world-jepa-store-consumer-v2"
STATE_KEY = "v14.world_jepa.store_consumer"
STATE_SCHEMA = 3
LEGACY_STATE_SCHEMA = 2
MAX_ROWS = min(2048, world_model.MAX_ROWS)
DEFAULT_PAGE_SIZE = MAX_ROWS
MAX_TRACKED = 10000
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
CHECKPOINT_NAME = re.compile(r"jepa-[0-9a-f]{32}\.npz\Z")
ROLE_TARGETS = {
    "B1_DETAIL": (0, 2),
    "B2_GIST": (1,),
    "SELF_MODEL": (0, 1, 2),
}


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _vector(value, size):
    if (type(value) not in (list, tuple) or len(value) != size
            or any(not _finite_number(item) for item in value)):
        raise ValueError("invalid finite numeric vector")
    return [float(item) for item in value]


def _sha(value):
    if type(value) is not str or not SHA256.fullmatch(value):
        raise ValueError("invalid SHA256")
    return value


def _source_refs_for_row(row):
    """Return canonical complete refs; old persisted rows fall back to their event source."""
    source_id, source_sha = row.get("source_id"), row.get("source_sha256")
    if type(source_id) is not str or not source_id or len(source_id) > 256:
        raise ValueError("invalid source identity")
    _sha(source_sha)
    raw = row.get("source_refs")
    if raw is None:
        return [{"source_id": source_id, "sha256": source_sha}]
    if type(raw) is not list or not 1 <= len(raw) <= 64:
        raise ValueError("invalid source ref set")
    required = {"source_id", "sha256", "char_start", "char_end", "modality"}
    refs, seen, source_hashes = [], set(), {}
    for item in raw:
        if type(item) is not dict or set(item) != required:
            raise ValueError("invalid source ref")
        sid, digest = item.get("source_id"), item.get("sha256")
        start, end, modality = item.get("char_start"), item.get("char_end"), item.get("modality")
        if (type(sid) is not str or not sid or len(sid) > 256
                or type(start) is not int or type(end) is not int or not 0 <= start <= end
                or type(modality) is not str or not modality or len(modality) > 64):
            raise ValueError("invalid source ref identity")
        _sha(digest)
        key = (sid, digest, start, end, modality)
        if key in seen:
            raise ValueError("duplicate source ref")
        prior = source_hashes.get(sid)
        if prior is not None and prior != digest:
            raise ValueError("source identity changed digest")
        source_hashes[sid] = digest
        seen.add(key)
        refs.append({
            "source_id": sid, "sha256": digest, "char_start": start,
            "char_end": end, "modality": modality,
        })
    if (source_id, source_sha) not in {(item["source_id"], item["sha256"]) for item in refs}:
        raise ValueError("primary event source omitted from source refs")
    refs.sort(key=lambda item: (
        item["source_id"], item["sha256"], item["char_start"],
        item["char_end"], item["modality"],
    ))
    return refs


def _source_pairs(row):
    return sorted({
        (item["source_id"], item["sha256"])
        for item in _source_refs_for_row(row)
    })


def _receipt_row(receipt):
    if type(receipt.action_id) is not str or not receipt.action_id or len(receipt.action_id) > 128:
        raise ValueError("invalid verified action id")
    raw = receipt.training_row()
    proof = receipt.public_provenance()
    route = raw.get("a")
    if route not in world_model.ACTIONS:
        raise ValueError("unknown verified action route")
    source_id = proof.get("source_id")
    source_sha = _sha(proof.get("source_sha256"))
    if type(source_id) is not str or not source_id or len(source_id) > 256:
        raise ValueError("invalid verified source id")
    return {
        "action_id": receipt.action_id,
        "source_id": source_id,
        "fingerprint": _sha(receipt.fingerprint),
        "source_sha256": source_sha,
        "source_refs": _source_refs_for_row({
            "source_id": source_id, "source_sha256": source_sha,
            "source_refs": proof.get("source_refs"),
        }),
        "outcome_sha256": _sha(proof.get("outcome_sha256")),
        "created": float(receipt.created),
        "s": _vector(raw.get("s"), 4),
        "a": route,
        "y": _vector(raw.get("y"), 3),
    }


def _cohort_sha(rows):
    body = [
        {"action_id": row["action_id"], "source_id": row["source_id"],
         "source_sha256": row["source_sha256"], "fingerprint": row["fingerprint"]}
        for row in sorted(rows, key=lambda item: item["action_id"])
    ]
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _arrays(rows):
    x = np.asarray([row["s"] + [0.0, 0.0, 0.0] for row in rows], dtype=np.float64)
    a = np.asarray([world_model.onehot(row["a"]) for row in rows], dtype=np.float64)
    x2 = np.asarray([row["s"] + row["y"] for row in rows], dtype=np.float64)
    if (x.ndim != 2 or a.ndim != 2 or x2.shape != x.shape
            or not all(np.isfinite(value).all() for value in (x, a, x2))):
        raise ValueError("invalid replay arrays")

    return x, a, x2


def _source_disjoint_split(rows):
    """Deterministic holdout split over connected components of complete source lineage."""
    if type(rows) not in (list, tuple) or not 16 <= len(rows) <= MAX_ROWS:
        raise ValueError("invalid source-disjoint cohort size")
    canonical, seen_actions, source_hashes = [], set(), {}
    for item in rows:
        if type(item) is not dict:
            raise ValueError("invalid source-disjoint row")
        action_id, source_id = item.get("action_id"), item.get("source_id")
        source_sha, route = _sha(item.get("source_sha256")), item.get("a")
        if (type(action_id) is not str or not action_id or len(action_id) > 128
                or action_id in seen_actions or type(source_id) is not str
                or not source_id or len(source_id) > 256 or route not in world_model.ACTIONS):
            raise ValueError("invalid source-disjoint identity")
        refs = _source_refs_for_row(item)
        pairs = {(ref["source_id"], ref["sha256"]) for ref in refs}
        if (source_id, source_sha) not in pairs:
            raise ValueError("primary source missing from source set")
        for sid, digest in pairs:
            prior_sha = source_hashes.get(sid)
            if prior_sha is not None and prior_sha != digest:
                raise ValueError("source identity changed digest")
            source_hashes[sid] = digest
        seen_actions.add(action_id)
        canonical.append({
            "action_id": action_id, "source_id": source_id,
            "source_sha256": source_sha, "source_refs": refs,
            "fingerprint": _sha(item.get("fingerprint")),
            "outcome_sha256": _sha(item.get("outcome_sha256")),
            "created": float(item["created"]), "s": _vector(item.get("s"), 4),
            "a": route, "y": _vector(item.get("y"), 3),
        })
    canonical.sort(key=lambda item: item["action_id"])

    # Any shared source ID or content digest joins rows into one indivisible
    # component. This closes leakage through recalled/observer context refs,
    # not just the event's primary user source.
    parent = list(range(len(canonical)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        a_root, b_root = find(left), find(right)
        if a_root != b_root:
            parent[max(a_root, b_root)] = min(a_root, b_root)

    owners = {}
    row_pairs = []
    for index, row in enumerate(canonical):
        pairs = _source_pairs(row)
        row_pairs.append(pairs)
        for sid, digest in pairs:
            for token in ("id:" + sid, "sha:" + digest):
                prior = owners.get(token)
                if prior is None:
                    owners[token] = index
                else:
                    union(index, prior)

    components = {}
    for index, pairs in enumerate(row_pairs):
        components.setdefault(find(index), []).append(index)
    bucket_by_root = {}
    for root, indices in components.items():
        digests = sorted({digest for index in indices for _sid, digest in row_pairs[index]})
        # Preserve the historical source-digest partition for single-source
        # cohorts; multi-source components get a stable combined digest.
        component_digest = digests[0] if len(digests) == 1 else hashlib.sha256(
            "|".join(digests).encode("ascii")
        ).hexdigest()
        bucket_by_root[root] = int.from_bytes(bytes.fromhex(component_digest)[:8], "big") % 2

    train = [row for index, row in enumerate(canonical) if bucket_by_root[find(index)] == 0]
    holdout = [row for index, row in enumerate(canonical) if bucket_by_root[find(index)] == 1]
    train_sources = {sid for row in train for sid, _digest in _source_pairs(row)}
    holdout_sources = {sid for row in holdout for sid, _digest in _source_pairs(row)}
    train_source_hashes = {digest for row in train for _sid, digest in _source_pairs(row)}
    holdout_source_hashes = {digest for row in holdout for _sid, digest in _source_pairs(row)}
    if train_sources & holdout_sources:
        raise ValueError("source leakage across holdout")
    if train_source_hashes & holdout_source_hashes:
        raise ValueError("source digest leakage across holdout")
    if len(train) < 8 or len(holdout) < 8:
        raise ValueError("insufficient source-disjoint split rows")
    if (len({row["a"] for row in train}) < 2 or len({row["a"] for row in holdout}) < 2
            or not {row["a"] for row in holdout}.issubset({row["a"] for row in train})):
        raise ValueError("insufficient source-disjoint action support")

    def content_digest(row):
        raw = json.dumps({"s": row["s"], "a": row["a"], "y": row["y"]},
                         sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    if ({content_digest(row) for row in train} & {content_digest(row) for row in holdout}):
        raise ValueError("identical content crossed source holdout")
    train_ids = tuple(row["action_id"] for row in train)
    holdout_ids = tuple(row["action_id"] for row in holdout)
    return {
        "train": _arrays(train), "holdout": _arrays(holdout),
        "train_action_ids": train_ids, "holdout_action_ids": holdout_ids,
        "manifest": {
            "source_disjoint": True, "source_sha256_disjoint": True,
            "train_source_count": len(train_sources),
            "holdout_source_count": len(holdout_sources),
            "within_supplied_records_id_disjoint": True,
            "within_supplied_records_content_disjoint": True,
            "train_rows_sha256": _cohort_sha(train), "holdout_rows_sha256": _cohort_sha(holdout),
        },
    }


def _parameter_snapshot(model):

    return {
        "enc": {key: np.asarray(value).copy() for key, value in model.enc.items()},
        "tgt": {key: np.asarray(value).copy() for key, value in model.tgt.items()},
        "preds": [
            {key: np.asarray(value).copy() for key, value in predictor.items()}
            for predictor in model.preds
        ],
    }


def _group_delta(before, after, groups):
    total = 0.0
    for group in groups:
        left_group, right_group = before[group], after[group]
        if group == "preds":
            if len(left_group) != len(right_group):
                raise ValueError("parameter ensemble mismatch")
            pairs = []
            for left_pred, right_pred in zip(left_group, right_group):
                if set(left_pred) != set(right_pred):
                    raise ValueError("parameter snapshot mismatch")
                pairs.extend((left_pred[key], right_pred[key]) for key in left_pred)
        else:
            if set(left_group) != set(right_group):
                raise ValueError("parameter snapshot mismatch")
            pairs = [(left_group[key], right_group[key]) for key in left_group]
        for left, right in pairs:
            if left.shape != right.shape:
                raise ValueError("parameter shape changed")
            total += float(np.square(right - left).sum())
    return math.sqrt(total)


def _ridge_head(z_train, y_train, ridge=1e-3):
    z = np.asarray(z_train, dtype=np.float64)
    y = np.asarray(y_train, dtype=np.float64)
    if y.ndim == 1:
        y = y[:, None]
    if (z.ndim != 2 or y.ndim != 2 or len(z) != len(y) or len(z) < 2
            or not np.isfinite(z).all() or not np.isfinite(y).all()):
        raise ValueError("invalid role receiver training data")
    design = np.column_stack((z, np.ones(len(z), dtype=np.float64)))
    penalty = np.eye(design.shape[1], dtype=np.float64) * ridge
    penalty[-1, -1] = 0.0
    solution = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    weights, bias = solution[:-1], solution[-1]
    if not np.isfinite(weights).all() or not np.isfinite(bias).all():
        raise ValueError("nonfinite role receiver")
    return weights, bias


def _mse(prediction, target):
    value = float(np.mean(np.square(np.asarray(prediction) - np.asarray(target))))
    if not math.isfinite(value):
        raise ValueError("nonfinite receiver metric")
    return value


def receiver_utility_gate(metrics, role):
    """Require each numeric role receiver to beat its mean and latent-negative controls."""
    if role not in ROLE_TARGETS or type(metrics) is not dict:
        return {"accepted": False, "reason": "RECEIVER_METRICS_UNAVAILABLE"}
    prefix = role.lower()
    keys = (
        prefix + "_holdout_mse",
        prefix + "_mean_baseline_mse",
        prefix + "_zero_latent_mse",
        prefix + "_shuffled_latent_mse",
    )
    values = [metrics.get(key) for key in keys]
    if any(not _finite_number(value) or value < 0 for value in values):
        return {"accepted": False, "reason": "RECEIVER_METRICS_INVALID"}
    holdout, mean_baseline, zero_latent, shuffled_latent = map(float, values)
    margin = max(1e-12, max(abs(value) for value in values) * 1e-9)
    accepted = all(
        holdout + margin < baseline
        for baseline in (mean_baseline, zero_latent, shuffled_latent)
    )
    return {
        "accepted": bool(accepted),
        "reason": ("HELDOUT_BEATS_MEAN_AND_NEGATIVE_CONTROLS" if accepted
                   else "HELDOUT_DID_NOT_BEAT_ALL_CONTROLS"),
        "holdout_mse": holdout,
        "mean_baseline_mse": mean_baseline,
        "zero_latent_mse": zero_latent,
        "shuffled_latent_mse": shuffled_latent,
        "required_margin": float(margin),
    }


def _fit_role_receivers(model, train, holdout, train_rows, holdout_rows):
    z_train, _ = model.predict(train[0], train[1])
    z_holdout, _ = model.predict(holdout[0], holdout[1])
    y_train = np.asarray([row["y"] for row in train_rows], dtype=np.float64)
    y_holdout = np.asarray([row["y"] for row in holdout_rows], dtype=np.float64)
    heads, metrics = {}, {}
    for role, indices in ROLE_TARGETS.items():
        target_train = y_train[:, indices]
        target_holdout = y_holdout[:, indices]
        weights, bias = _ridge_head(z_train, target_train)
        prediction = z_holdout @ weights + bias
        mean_prediction = np.tile(target_train.mean(axis=0), (len(target_holdout), 1))
        zero_latent_prediction = np.tile(bias, (len(target_holdout), 1))
        shuffled_prediction = np.roll(z_holdout, 1, axis=0) @ weights + bias
        prefix = role.lower()
        metrics[prefix + "_holdout_mse"] = _mse(prediction, target_holdout)
        metrics[prefix + "_mean_baseline_mse"] = _mse(mean_prediction, target_holdout)
        metrics[prefix + "_zero_latent_mse"] = _mse(zero_latent_prediction, target_holdout)
        metrics[prefix + "_shuffled_latent_mse"] = _mse(shuffled_prediction, target_holdout)
        metrics[prefix + "_gain_vs_mean"] = (
            metrics[prefix + "_mean_baseline_mse"] - metrics[prefix + "_holdout_mse"]
        )
        heads[role] = {
            "target_indices": list(indices),
            "weights": weights.tolist(),
            "bias": bias.tolist(),
        }
    return heads, metrics


class WorldJEPAStoreConsumer:
    """Consume Store-verified T8 transitions into persistent WorldJEPA/receiver state.

    learning_enabled is a local per-organ lab gate. Each update also requires
    optimizer_permission=True. Both default closed; neither changes Age,
    native-model permissions, or the installed B1/B2 GGUF files.
    """

    def __init__(self, store, checkpoint_dir=None, *, learning_enabled=False,
                 seed=13, ensemble=2):
        if type(learning_enabled) is not bool:
            raise ValueError("learning_enabled must be bool")
        if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
            raise ValueError("seed")
        if type(ensemble) is not int or not 1 <= ensemble <= 16:
            raise ValueError("ensemble")
        self.store = store
        root = (Path(checkpoint_dir) if checkpoint_dir is not None
                else Path(store.home) / "v14_world_jepa")
        if root.exists() and root.is_symlink():
            raise ValueError("checkpoint directory cannot be a symlink")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not root.is_dir() or root.is_symlink():
            raise ValueError("unsafe checkpoint directory")
        try:
            os.chmod(root, 0o700)
        except OSError:
            pass
        self.home = root
        self.lock_path = self.home / "consumer.lock"
        self.learning_enabled = learning_enabled
        self.seed = seed
        self.ensemble = ensemble
        # Recover a prior process that stopped between publish and pending-name cleanup.
        with self._locked(True):
            world_jepa_shadow_checkpoint.cleanup_pending(self.home)

    @contextmanager
    def _locked(self, exclusive=True):
        if self.lock_path.is_symlink():
            raise ValueError("unsafe consumer lock")
        with open(self.lock_path, "a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _validate_record(record):
        if record is None:
            return
        required = {
            "checkpoint", "checkpoint_sha256", "source_sha256", "processed_ids",
            "scan_cursor",
            "fingerprints", "experience_rows", "train_ids", "holdout_ids",
            "receiver_heads", "metrics", "self_state", "fit_steps",
        }
        if type(record) is not dict or set(record) != required:
            raise ValueError("invalid WorldJEPA state record")
        if (type(record["checkpoint"]) is not str
                or not CHECKPOINT_NAME.fullmatch(record["checkpoint"])):
            raise ValueError("invalid checkpoint filename")
        _sha(record["checkpoint_sha256"])
        _sha(record["source_sha256"])
        fingerprints = record["fingerprints"]
        if (type(fingerprints) is not dict or len(fingerprints) > MAX_TRACKED
                or any(type(key) is not str or not key or len(key) > 128 for key in fingerprints)
                or any(type(value) is not str or not SHA256.fullmatch(value)
                       for value in fingerprints.values())):
            raise ValueError("invalid processed receipt map")
        processed = record["processed_ids"]
        if (type(processed) is not list
                or any(type(item) is not str or not item or len(item) > 128 for item in processed)
                or len(processed) != len(fingerprints)
                or set(processed) != set(fingerprints)
                or len(set(processed)) != len(processed)):
            raise ValueError("processed cursor mismatch")
        rows = record["experience_rows"]
        if type(rows) is not list or len(rows) > MAX_ROWS:
            raise ValueError("replay memory budget")
        row_ids = []
        for row in rows:
            base_row_keys = {
                "action_id", "source_id", "fingerprint", "source_sha256", "outcome_sha256",
                "created", "s", "a", "y",
            }
            if type(row) is not dict or set(row) not in (
                    base_row_keys, base_row_keys | {"source_refs"}):
                raise ValueError("invalid replay memory row")
            if (type(row["source_id"]) is not str or not row["source_id"]
                    or len(row["source_id"]) > 256
                    or row["action_id"] not in fingerprints
                    or fingerprints[row["action_id"]] != row["fingerprint"]
                    or row["a"] not in world_model.ACTIONS
                    or not _finite_number(row["created"])):
                raise ValueError("replay provenance mismatch")
            _sha(row["fingerprint"])
            _sha(row["source_sha256"])
            _sha(row["outcome_sha256"])
            _vector(row["s"], 4)
            _vector(row["y"], 3)
            row_ids.append(row["action_id"])
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("duplicate replay row")
        train_ids, holdout_ids = record["train_ids"], record["holdout_ids"]
        for ids in (train_ids, holdout_ids):
            if (type(ids) is not list
                    or any(type(item) is not str or not item for item in ids)
                    or len(set(ids)) != len(ids)):
                raise ValueError("invalid train/holdout ids")
        if (set(train_ids) & set(holdout_ids)
                or set(train_ids + holdout_ids) != set(row_ids)):
            raise ValueError("train/holdout cursor mismatch")
        row_by_id = {row["action_id"]: row for row in rows}
        source_hashes = {}
        for row in rows:
            for sid, digest in _source_pairs(row):
                prior = source_hashes.get(sid)
                if prior is not None and prior != digest:
                    raise ValueError("persisted source digest changed")
                source_hashes[sid] = digest
        train_sources = {
            sid for action_id in train_ids for sid, _digest in _source_pairs(row_by_id[action_id])
        }
        holdout_sources = {
            sid for action_id in holdout_ids for sid, _digest in _source_pairs(row_by_id[action_id])
        }
        if train_sources & holdout_sources:
            raise ValueError("persisted source holdout overlap")
        train_source_hashes = {
            digest for action_id in train_ids for _sid, digest in _source_pairs(row_by_id[action_id])
        }
        holdout_source_hashes = {
            digest for action_id in holdout_ids for _sid, digest in _source_pairs(row_by_id[action_id])
        }
        if train_source_hashes & holdout_source_hashes:
            raise ValueError("persisted source digest holdout overlap")
        def persisted_content(action_id):
            row = row_by_id[action_id]
            raw = json.dumps({"s": row["s"], "a": row["a"], "y": row["y"]},
                             sort_keys=True, separators=(",", ":"), allow_nan=False)
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if ({persisted_content(action_id) for action_id in train_ids}
                & {persisted_content(action_id) for action_id in holdout_ids}):
            raise ValueError("persisted holdout content overlap")
        heads = record["receiver_heads"]
        if type(heads) is not dict or set(heads) != set(ROLE_TARGETS):
            raise ValueError("receiver head set")
        for role, indices in ROLE_TARGETS.items():
            head = heads[role]
            if (type(head) is not dict or set(head) != {"target_indices", "weights", "bias"}
                    or head["target_indices"] != list(indices)
                    or type(head["weights"]) is not list
                    or len(head["weights"]) != world_jepa.Z
                    or type(head["bias"]) is not list
                    or len(head["bias"]) != len(indices)
                    or any(type(row) is not list or len(row) != len(indices)
                           or any(not _finite_number(value) for value in row)
                           for row in head["weights"])
                    or any(not _finite_number(value) for value in head["bias"])):
                raise ValueError("invalid receiver head parameters")
        if type(record["metrics"]) is not dict or type(record["self_state"]) is not dict:
            raise ValueError("metrics/self state")
        if type(record["fit_steps"]) is not int or record["fit_steps"] < 1:
            raise ValueError("fit step evidence")
        if type(record["scan_cursor"]) is not int or record["scan_cursor"] < 0:
            raise ValueError("scan cursor")

    @staticmethod
    def _validate_pending_rows(rows, active):
        if type(rows) is not list or len(rows) > MAX_ROWS:
            raise ValueError("pending T8 buffer budget")
        active_ids = set(active["fingerprints"]) if active is not None else set()
        seen, source_hashes = set(), {}
        required = {
            "action_id", "source_id", "fingerprint", "source_sha256", "outcome_sha256",
            "created", "s", "a", "y",
        }
        for row in rows:
            if type(row) is not dict or set(row) not in (required, required | {"source_refs"}):
                raise ValueError("invalid pending T8 row")
            action_id, source_id = row["action_id"], row["source_id"]
            if (type(action_id) is not str or not action_id or len(action_id) > 128
                    or action_id in active_ids or action_id in seen
                    or type(source_id) is not str or not source_id or len(source_id) > 256
                    or row["a"] not in world_model.ACTIONS
                    or not _finite_number(row["created"])):
                raise ValueError("pending T8 identity mismatch")
            _sha(row["fingerprint"])
            source_sha = _sha(row["source_sha256"])
            _sha(row["outcome_sha256"])
            _vector(row["s"], 4)
            _vector(row["y"], 3)
            for sid, digest in _source_pairs(row):
                prior = source_hashes.get(sid)
                if prior is not None and prior != digest:
                    raise ValueError("pending source digest changed")
                source_hashes[sid] = digest
            seen.add(action_id)

    def _read_state(self):
        payload, version = self.store.state(STATE_KEY, None)
        if payload is None:
            return {"schema": STATE_SCHEMA, "revision": REVISION,
                    "active": None, "previous": None, "scan_cursor": 0,
                    "pending_rows": []}, version
        if type(payload) is not dict:
            raise ValueError("incompatible WorldJEPA Store state")
        old_keys = {"schema", "revision", "active", "previous", "scan_cursor"}
        if (set(payload) == old_keys
                and payload.get("schema") == LEGACY_STATE_SCHEMA
                and payload.get("revision") == LEGACY_REVISION):
            self._validate_record(payload["active"])
            self._validate_record(payload["previous"])
            if type(payload["scan_cursor"]) is not int or payload["scan_cursor"] < 0:
                raise ValueError("invalid legacy scan cursor")
            return {"schema": STATE_SCHEMA, "revision": REVISION,
                    "active": payload["active"], "previous": payload["previous"],
                    "scan_cursor": payload["scan_cursor"], "pending_rows": []}, version
        expected_keys = old_keys | {"pending_rows"}
        if (set(payload) != expected_keys
                or payload.get("schema") != STATE_SCHEMA or payload.get("revision") != REVISION
                or type(payload.get("scan_cursor")) is not int or payload["scan_cursor"] < 0):
            raise ValueError("incompatible WorldJEPA Store state")
        self._validate_record(payload["active"])
        self._validate_record(payload["previous"])
        self._validate_pending_rows(payload["pending_rows"], payload["active"])
        return payload, version

    def _persist_pending(self, state, version, pending_by_id, next_cursor):
        pending_rows = sorted(
            pending_by_id.values(), key=lambda row: (row["created"], row["action_id"])
        )
        if len(pending_rows) > MAX_ROWS:
            return "PENDING_BUFFER_CAPACITY"
        next_state = dict(state)
        next_state["pending_rows"] = pending_rows
        next_state["scan_cursor"] = next_cursor
        try:
            self.store.set_state(STATE_KEY, next_state, expected=version)
        except ValueError as exc:
            if "Stale state write" in str(exc):
                return "CONCURRENT_STATE_CONFLICT_RETRY"
            raise
        return "PERSISTED"

    def _checkpoint_path(self, record):
        self._validate_record(record)
        path = self.home / record["checkpoint"]
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or unsafe WorldJEPA checkpoint")
        return path

    def _load_model(self, record):
        path = self._checkpoint_path(record)
        return world_jepa_shadow_checkpoint.load(
            path, record["source_sha256"], record["checkpoint_sha256"]
        )

    def _prune_checkpoints(self, state):
        keep = {
            record["checkpoint"]
            for record in (state.get("active"), state.get("previous"))
            if record is not None
        }
        removed = errors = 0
        for path in self.home.glob("jepa-*.npz"):
            if path.name in keep or path.is_symlink() or not path.is_file():
                continue
            try:
                path.unlink()
                removed += 1
            except OSError:
                errors += 1
        return removed, errors


    def update(self, *, limit=DEFAULT_PAGE_SIZE, steps=80, optimizer_permission=False,
               replay_mode="uniform", cancel_check=None):
        if type(limit) is not int or not 16 <= limit <= MAX_ROWS:
            raise ValueError("limit")
        if type(steps) is not int or not 1 <= steps <= 2000:
            raise ValueError("steps")
        if type(optimizer_permission) is not bool:
            raise ValueError("optimizer_permission must be bool")
        if replay_mode not in {"uniform", "none"}:
            raise ValueError("replay_mode must be uniform or none")
        if cancel_check is not None and not callable(cancel_check):
            raise ValueError("cancel_check must be callable")
        if cancel_check is not None and cancel_check():
            return {"status":"CANCELLED","pending_rows":0,"checkpoint_committed":False,
                    "native_body_weights_changed":False}
        with self._locked(True):
            state, version = self._read_state()
            receipts, rejected, next_cursor, scanned, censored_skipped, has_more = (
                verify_committed_transition_page(self.store, after_seq=state["scan_cursor"], limit=limit)
            )
            incoming = [_receipt_row(receipt) for receipt in receipts]
            active = state["active"]
            prior_fingerprints = dict(active["fingerprints"]) if active else {}
            prior_rows = {row["action_id"]: row for row in (active["experience_rows"] if active else [])}
            pending_by_id = {row["action_id"]: row for row in state["pending_rows"]}
            for action_id, row in pending_by_id.items():
                if action_id in prior_fingerprints:
                    raise ValueError("pending T8 row already committed in active checkpoint")
                prior_fingerprints[action_id] = row["fingerprint"]
                prior_rows[action_id] = row
            # Pending rows are retained, but an unchanged cohort is not retrained
            # on every post-turn callback. Re-enter it only when new verified
            # evidence arrives; otherwise the same evidence cannot improve.
            incoming_new_ids = []
            for row in incoming:
                action_id = row["action_id"]
                prior_fingerprint = prior_fingerprints.get(action_id)
                if prior_fingerprint is not None and prior_fingerprint != row["fingerprint"]:
                    raise ValueError("committed T8 receipt changed after learning")
                if prior_fingerprint is None:
                    incoming_new_ids.append(action_id)
                    prior_fingerprints[action_id] = row["fingerprint"]
                    pending_by_id[action_id] = row
                    prior_rows[action_id] = row
            new_ids = list(pending_by_id) if incoming_new_ids else []
            if len(prior_fingerprints) > MAX_TRACKED:
                raise OverflowError("processed T8 identity budget exhausted; fail closed")
            if not new_ids:
                if pending_by_id:
                    if not self.learning_enabled:
                        return {"status": "LEARNING_DISABLED", "new_receipts": 0,
                                "verified_receipts": len(receipts), "rejected_receipts": rejected,
                                "censored_skipped": censored_skipped, "scanned_rows": scanned,
                                "pending_rows": len(pending_by_id),
                                "native_body_weights_changed": False}
                    if optimizer_permission is not True:
                        return {"status": "PENDING_OPTIMIZER_PERMISSION", "new_receipts": 0,
                                "verified_receipts": len(receipts), "rejected_receipts": rejected,
                                "censored_skipped": censored_skipped, "scanned_rows": scanned,
                                "pending_rows": len(pending_by_id),
                                "native_body_weights_changed": False}
                    persisted_cursor = state["scan_cursor"]
                    if next_cursor > state["scan_cursor"]:
                        persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                        if persisted != "PERSISTED":
                            return {"status": persisted, "pending_rows": len(pending_by_id),
                                    "scan_cursor": state["scan_cursor"],
                                    "native_body_weights_changed": False}
                        persisted_cursor = next_cursor
                    return {
                        "status": "WAITING_FOR_MORE_T8_DATA", "verified_receipts": len(receipts),
                        "rejected_receipts": rejected, "censored_skipped": censored_skipped,
                        "scanned_rows": scanned, "scan_cursor": persisted_cursor,
                        "has_more": has_more, "processed": len(prior_fingerprints),
                        "pending_rows": len(pending_by_id),
                        "native_body_weights_changed": False,
                    }
                persisted_cursor = state["scan_cursor"]
                if (next_cursor > state["scan_cursor"] and self.learning_enabled is True
                        and optimizer_permission is True):
                    next_state = dict(state)
                    next_state["scan_cursor"] = next_cursor
                    self.store.set_state(STATE_KEY, next_state, expected=version)
                    persisted_cursor = next_cursor
                return {
                    "status": "NO_NEW_TRANSITIONS", "verified_receipts": len(receipts),
                    "rejected_receipts": rejected, "censored_skipped": censored_skipped,
                    "scanned_rows": scanned, "scan_cursor": persisted_cursor,
                    "has_more": has_more, "processed": len(prior_fingerprints),
                    "pending_rows": len(pending_by_id),
                    "native_body_weights_changed": False,
                }
            if not self.learning_enabled:
                return {"status": "LEARNING_DISABLED", "new_receipts": len(new_ids),
                        "verified_receipts": len(receipts), "rejected_receipts": rejected,
                        "censored_skipped": censored_skipped, "scanned_rows": scanned,
                        "pending_rows": len(pending_by_id),
                        "native_body_weights_changed": False}
            if optimizer_permission is not True:
                return {"status": "PENDING_OPTIMIZER_PERMISSION", "new_receipts": len(new_ids),
                        "verified_receipts": len(receipts), "rejected_receipts": rejected,
                        "censored_skipped": censored_skipped, "scanned_rows": scanned,
                        "pending_rows": len(pending_by_id),
                        "native_body_weights_changed": False}
            new_set = set(new_ids)
            candidates = list(prior_rows.values())
            if len(candidates) > MAX_ROWS:
                new_rows = [row for row in candidates if row["action_id"] in new_set]
                old_rows = [row for row in candidates if row["action_id"] not in new_set]
                if len(new_rows) > MAX_ROWS:
                    raise OverflowError("new T8 batch exceeds replay memory")
                keep_old = max(0, MAX_ROWS - len(new_rows))
                old_rows.sort(key=lambda row: (row["created"], row["action_id"]))
                candidates = new_rows + old_rows[-keep_old:] if keep_old else new_rows
            experience_rows = sorted(candidates, key=lambda row: row["action_id"])
            try:
                split = _source_disjoint_split(experience_rows)
            except ValueError as exc:
                persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                if persisted != "PERSISTED":
                    return {"status": persisted, "pending_rows": len(pending_by_id),
                            "scan_cursor": state["scan_cursor"],
                            "native_body_weights_changed": False}
                return {"status": "INSUFFICIENT_SOURCE_DISJOINT_T8_COHORT", "reason": str(exc),
                        "verified_receipts": len(receipts), "rejected_receipts": rejected,
                        "censored_skipped": censored_skipped, "new_receipts": len(new_ids),
                        "pending_rows": len(pending_by_id), "scanned_rows": scanned,
                        "scan_cursor": next_cursor, "has_more": has_more,
                        "native_body_weights_changed": False}
            train_ids, holdout_ids = list(split["train_action_ids"]), list(split["holdout_action_ids"])
            if set(train_ids) & set(holdout_ids):
                raise ValueError("train/holdout identity overlap")
            row_by_id = {row["action_id"]: row for row in experience_rows}
            train_rows = [row_by_id[action_id] for action_id in train_ids]
            holdout_rows = [row_by_id[action_id] for action_id in holdout_ids]
            new_train_rows = [row for row in train_rows if row["action_id"] in new_set]
            old_train_rows = [row for row in train_rows if row["action_id"] not in new_set]
            train, holdout = split["train"], split["holdout"]
            if active is not None:
                model = self._load_model(active)
                checkpoint_before = active["checkpoint_sha256"]
            else:
                model = world_jepa.WorldJEPA(seed=self.seed, ensemble=self.ensemble)
                try:
                    model.fit(*train, steps=0, log_every=1, cancel_check=cancel_check)
                except InterruptedError:
                    return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                            "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                            "native_body_weights_changed":False}
                checkpoint_before = None
            fit_steps_before = int(getattr(model, "_fit_steps", 0))
            before = _parameter_snapshot(model)
            holdout_before = model.prediction_loss(*holdout)
            old_holdout_before = old_holdout_after = None
            if active is not None:
                old_holdout_ids = set(active["holdout_ids"])
                old_holdout_rows = [row for row in active["experience_rows"] if row["action_id"] in old_holdout_ids]
                if len(old_holdout_rows) >= 2:
                    old_holdout = _arrays(old_holdout_rows)
                    old_holdout_before = model.prediction_loss(*old_holdout)
            # Uniform replay is the default. The no-replay mode is an explicit
            # ablation: it trains only on newly admitted train-fold rows while
            # retaining the complete source-disjoint cohort for future replay.
            fit_rows = (train_rows if replay_mode == "uniform" or active is None
                        else new_train_rows)
            if len(fit_rows) < 2:
                persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                if persisted != "PERSISTED":
                    return {"status": persisted, "pending_rows": len(pending_by_id),
                            "scan_cursor": state["scan_cursor"],
                            "native_body_weights_changed": False}
                return {"status": "INSUFFICIENT_NEW_TRAIN_ROWS",
                        "new_train_rows": len(new_train_rows),
                        "replay_candidate_rows": len(old_train_rows),
                        "pending_rows": len(pending_by_id),
                        "scan_cursor": next_cursor,
                        "native_body_weights_changed": False}
            fit_arrays = _arrays(fit_rows)
            try:
                model.partial_fit(*fit_arrays, steps=steps, log_every=max(1, steps // 4),
                                  cancel_check=cancel_check, allow_optimizer_bootstrap=True)
            except InterruptedError:
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            if cancel_check is not None and cancel_check():
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            after = _parameter_snapshot(model)
            holdout_after = model.prediction_loss(*holdout)
            shuffled_action_loss = model.prediction_loss(holdout[0], np.roll(holdout[1], 1, axis=0), holdout[2])
            zero_action_loss = model.prediction_loss(holdout[0], np.zeros_like(holdout[1]), holdout[2])
            if old_holdout_before is not None:
                old_holdout_after = model.prediction_loss(*old_holdout)
            fit_steps_after = int(getattr(model, "_fit_steps", 0))
            parameter_delta = _group_delta(before, after, ("enc", "preds"))
            ema_delta = _group_delta(before, after, ("tgt",))
            retention_delta = None if old_holdout_before is None else float(old_holdout_after - old_holdout_before)
            holdout_improved = bool(holdout_after < holdout_before)
            negative_controls_separated = bool(
                holdout_after < shuffled_action_loss and holdout_after < zero_action_loss
            )
            # A new cohort must not be accepted by sacrificing the previous
            # held-out cohort. This is a separate retention gate, not merely
            # telemetry; when no prior checkpoint exists there is no old cohort.
            old_holdout_retained = bool(
                old_holdout_before is None
                or (old_holdout_after is not None and old_holdout_after <= old_holdout_before)
            )
            utility_gate_accepted = (
                holdout_improved and negative_controls_separated and old_holdout_retained
            )
            if not utility_gate_accepted:
                persisted = self._persist_pending(state, version, pending_by_id, next_cursor)
                if persisted != "PERSISTED":
                    return {"status": persisted, "pending_rows": len(pending_by_id),
                            "scan_cursor": state["scan_cursor"],
                            "native_body_weights_changed": False}
                return {
                    "status": "UTILITY_GATE_REJECTED",
                    "utility_gate_accepted": False,
                    "holdout_improved": holdout_improved,
                    "negative_controls_separated": negative_controls_separated,
                    "old_holdout_retained": old_holdout_retained,
                    "retention_gate_accepted": old_holdout_retained,
                    "holdout_loss_before": float(holdout_before),
                    "holdout_loss_after": float(holdout_after),
                    "shuffled_action_holdout_loss": float(shuffled_action_loss),
                    "zero_action_holdout_loss": float(zero_action_loss),
                    "old_holdout_loss_before": None if old_holdout_before is None else float(old_holdout_before),
                    "old_holdout_loss_after": None if old_holdout_after is None else float(old_holdout_after),
                    "old_holdout_retention_delta": retention_delta,
                    "parameter_delta_norm": float(parameter_delta),
                    "ema_target_delta_norm": float(ema_delta),
                    "fit_steps_before": fit_steps_before,
                    "fit_steps_after": fit_steps_after,
                    "replay_mode": replay_mode,
                    "new_train_rows": len(new_train_rows),
                    "replay_candidate_rows": len(old_train_rows),
                    "replay_rows": len(old_train_rows) if replay_mode == "uniform" and active else 0,
                    "fit_rows": len(fit_rows),
                    "fit_action_ids": [row["action_id"] for row in fit_rows],
                    "new_train_action_ids": [row["action_id"] for row in new_train_rows],
                    "pending_rows": len(pending_by_id),
                    "scan_cursor": next_cursor,
                    "native_body_weights_changed": False,
                    "native_body_consumed": False,
                    "runtime_wired": False,
                }
            if cancel_check is not None and cancel_check():
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            receiver_heads, receiver_metrics = _fit_role_receivers(model, train, holdout, train_rows, holdout_rows)
            source_sha = _cohort_sha(experience_rows)
            if cancel_check is not None and cancel_check():
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            checkpoint_name = "jepa-" + uuid.uuid4().hex + ".npz"
            checkpoint_path = self.home / checkpoint_name
            saved = world_jepa_shadow_checkpoint.save(model, checkpoint_path, source_sha)
            checkpoint_after = _sha(saved.get("sha256"))
            if cancel_check is not None and cancel_check():
                try: checkpoint_path.unlink(missing_ok=True)
                except OSError: pass
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            previous_updates = int(active["self_state"].get("update_count", 0)) if active else 0
            metrics = {
                "source_verified": True, "verified_receipts": len(receipts),
                "rejected_receipts": rejected, "censored_skipped": censored_skipped,
                "scanned_rows": scanned, "has_more": has_more,
                "scan_cursor_before": state["scan_cursor"], "scan_cursor_after": next_cursor,
                "replay_mode": replay_mode,
                "replay_candidate_rows": len(old_train_rows),
                "replay_rows": len(old_train_rows) if replay_mode == "uniform" and active else 0,
                "new_train_rows": len(new_train_rows),
                "new_holdout_rows": len(set(new_ids) & set(holdout_ids)),
                "fit_rows": len(fit_rows),
                "fit_action_ids": [row["action_id"] for row in fit_rows],
                "new_train_action_ids": [row["action_id"] for row in new_train_rows],
                "train_rows": len(train_ids), "holdout_rows": len(holdout_ids),
                "train_source_count": split["manifest"]["train_source_count"],
                "holdout_source_count": split["manifest"]["holdout_source_count"],
                "train_holdout_id_disjoint": True,
                "train_holdout_source_disjoint": split["manifest"]["source_disjoint"],
                "train_holdout_source_sha256_disjoint": split["manifest"]["source_sha256_disjoint"],
                "train_holdout_content_disjoint": split["manifest"]["within_supplied_records_content_disjoint"],
                "holdout_loss_before": float(holdout_before), "holdout_loss_after": float(holdout_after),
                "holdout_loss_delta": float(holdout_after - holdout_before),
                "holdout_improved": holdout_improved,
                "shuffled_action_holdout_loss": float(shuffled_action_loss),
                "zero_action_holdout_loss": float(zero_action_loss),
                "negative_controls_separated": negative_controls_separated,
                "utility_gate_accepted": True,
                "old_holdout_retained": old_holdout_retained,
                "retention_gate_accepted": old_holdout_retained,
                "old_holdout_loss_before": None if old_holdout_before is None else float(old_holdout_before),
                "old_holdout_loss_after": None if old_holdout_after is None else float(old_holdout_after),
                "old_holdout_retention_delta": retention_delta,
                "parameter_delta_norm": float(parameter_delta), "ema_target_delta_norm": float(ema_delta),
                "fit_steps_before": fit_steps_before, "fit_steps_after": fit_steps_after,
                "checkpoint_sha_before": checkpoint_before, "checkpoint_sha_after": checkpoint_after,
                "optimizer_moments_persisted": saved.get("optimizer_state_persisted") is True,
                "inverse_dynamics_optimizer_persisted": saved.get("optimizer_state_persisted") is True,
                "optimizer_state_bootstrapped": saved.get("optimizer_state_bootstrapped") is True,
            }
            metrics.update(receiver_metrics)
            record = {
                "checkpoint": checkpoint_name, "checkpoint_sha256": checkpoint_after,
                "source_sha256": source_sha, "processed_ids": sorted(prior_fingerprints),
                "fingerprints": prior_fingerprints, "experience_rows": experience_rows,
                "train_ids": train_ids, "holdout_ids": holdout_ids,
                "receiver_heads": receiver_heads, "metrics": metrics,
                "self_state": {"update_count": previous_updates + 1,
                               "last_prediction_error": float(holdout_after),
                               "last_parameter_delta_norm": float(parameter_delta),
                               "last_retention_delta": retention_delta,
                               "last_scan_cursor": next_cursor},
                "fit_steps": fit_steps_after, "scan_cursor": next_cursor,
            }
            next_state = {"schema": STATE_SCHEMA, "revision": REVISION,
                          "active": record, "previous": active, "scan_cursor": next_cursor,
                          "pending_rows": []}
            if cancel_check is not None and cancel_check():
                try: checkpoint_path.unlink(missing_ok=True)
                except OSError: pass
                return {"status":"CANCELLED","pending_rows":len(pending_by_id),
                        "scan_cursor":state["scan_cursor"],"checkpoint_committed":False,
                        "native_body_weights_changed":False}
            try:
                self.store.set_state(STATE_KEY, next_state, expected=version)
            except ValueError as exc:
                try:
                    checkpoint_path.unlink(missing_ok=True)
                except OSError:
                    pass
                if "Stale state write" in str(exc):
                    return {"status": "CONCURRENT_STATE_CONFLICT_RETRY",
                            "new_receipts": len(new_ids), "checkpoint_discarded": True,
                            "native_body_weights_changed": False}
                raise
            except Exception:
                try:
                    checkpoint_path.unlink(missing_ok=True)
                except OSError:
                    pass
                raise
            pruned_checkpoints, prune_errors = self._prune_checkpoints(next_state)
            return {
                "status": "UPDATED_EXPERIMENTAL_WORLD_JEPA",
                "verified_receipts": len(receipts), "orphan_checkpoints_removed": pruned_checkpoints,
                "checkpoint_prune_errors": prune_errors, "rejected_receipts": rejected,
                "censored_skipped": censored_skipped, "scanned_rows": scanned,
                "has_more": has_more, "new_receipts": len(new_ids),
                "processed": len(prior_fingerprints), "scan_cursor": next_cursor,
                "checkpoint_sha256": checkpoint_after, "source_sha256": source_sha,
                "metrics": metrics, "native_body_weights_changed": False,
                "native_body_consumed": False, "runtime_wired": False,
                "scope": "WORLD_JEPA_EMA_SELF_MEMORY_AND_B1_B2_NUMERIC_SHADOW",
            }

    def restore(self):
        with self._locked(False):
            state, _ = self._read_state()
            active = state["active"]
            if active is None:
                return {"status": "NO_CHECKPOINT"}
            model = self._load_model(active)
            return {
                "status": "RESTORED",
                "checkpoint_sha256": active["checkpoint_sha256"],
                "fit_steps": int(model._fit_steps),
                "processed": len(active["processed_ids"]),
                "native_body_weights_changed": False,
            }


    def rollback(self):
        with self._locked(True):
            state, version = self._read_state()
            active, previous = state["active"], state["previous"]
            if previous is None:
                return {"status": "NO_PREVIOUS_CHECKPOINT"}
            self._load_model(previous)
            rollback_cursor = previous["scan_cursor"]
            self.store.set_state(
                STATE_KEY,
                {"schema": STATE_SCHEMA, "revision": REVISION,
                 "active": previous, "previous": active, "scan_cursor": rollback_cursor,
                 "pending_rows": []},
                expected=version,
            )
            return {"status": "ROLLED_BACK", "checkpoint_sha256": previous["checkpoint_sha256"],
                    "processed": len(previous["processed_ids"]), "scan_cursor": rollback_cursor,
                    "native_body_weights_changed": False}


    def readout(self, role, state, action):
        if role not in ROLE_TARGETS:
            raise ValueError("unknown receiver role")
        vector = _vector(state, 4)
        if action not in world_model.ACTIONS:
            raise ValueError("unknown action")
        with self._locked(False):
            stored, _ = self._read_state()
            active = stored["active"]
            if active is None:
                raise ValueError("WorldJEPA checkpoint unavailable")
            model = self._load_model(active)
            utility = receiver_utility_gate(active.get("metrics"), role)
            if not utility["accepted"]:
                return {
                    "role": role,
                    "status": "RECEIVER_UTILITY_REJECTED",
                    "receiver_utility": utility,
                    "checkpoint_sha256": active["checkpoint_sha256"],
                    "source_sha256": active["source_sha256"],
                    "native_body_consumed": False,
                    "native_body_weights_changed": False,
                }
            x = np.asarray([vector + [0.0, 0.0, 0.0]], dtype=np.float64)
            a = np.asarray([world_model.onehot(action)], dtype=np.float64)
            latent, spread = model.predict(x, a)
            head = active["receiver_heads"][role]
            weights = np.asarray(head["weights"], dtype=np.float64)
            bias = np.asarray(head["bias"], dtype=np.float64)
            prediction = latent[0] @ weights + bias
            if not np.isfinite(prediction).all():
                raise ValueError("nonfinite receiver prediction")
            if role == "B1_DETAIL":
                output = {
                    "predicted_action_duration_s": max(0.0, math.expm1(min(20.0, float(prediction[0])))),
                    "predicted_output_characters": max(0.0, math.expm1(min(20.0, float(prediction[1]) * 8.0))),
                }
            elif role == "B2_GIST":
                output = {"predicted_success_probability": float(np.clip(prediction[0], 0.0, 1.0))}
            else:
                output = {
                    "predicted_action_duration_s": max(0.0, math.expm1(min(20.0, float(prediction[0])))),
                    "predicted_success_probability": float(np.clip(prediction[1], 0.0, 1.0)),
                    "predicted_output_characters": max(0.0, math.expm1(min(20.0, float(prediction[2]) * 8.0))),
                }
            uncertainty = float(np.asarray(spread).reshape(-1)[0])
            if not math.isfinite(uncertainty):
                raise ValueError("nonfinite receiver uncertainty")
            return {"role": role, "prediction": output, "uncertainty": uncertainty,
                    "checkpoint_sha256": active["checkpoint_sha256"],
                    "source_sha256": active["source_sha256"], "status": "SHADOW_READOUT_ONLY",
                    "receiver_utility": utility,
                    "native_body_consumed": False, "native_body_weights_changed": False}

    def recall(self, state, action, limit=5):
        """Source-linked numeric episodic recall over the persistent T8 replay."""
        vector = _vector(state, 4)
        if action not in world_model.ACTIONS:
            raise ValueError("unknown action")
        if type(limit) is not int or not 1 <= limit <= 32:
            raise ValueError("memory recall limit")
        with self._locked(False):
            stored, _ = self._read_state()
            active = stored["active"]
            if active is None:
                return {"status": "NO_MEMORY", "items": []}
            model = self._load_model(active)
            query = np.asarray([vector + [0.0, 0.0, 0.0]], dtype=np.float64)
            query_latent = model.latent(query, target=False)[0]
            candidates = []
            for row in active["experience_rows"]:
                if row["a"] != action:
                    continue
                x = np.asarray([row["s"] + [0.0, 0.0, 0.0]], dtype=np.float64)
                latent = model.latent(x, target=False)[0]
                distance = float(np.linalg.norm(latent - query_latent))
                if not math.isfinite(distance):
                    continue
                y = row["y"]
                candidates.append({
                    "distance": distance, "action_id": row["action_id"],
                    "source_id": row["source_id"], "source_sha256": row["source_sha256"],
                    "outcome_sha256": row["outcome_sha256"], "created": row["created"],
                    "observed_outcome": {
                        "duration_s": math.expm1(min(20.0, y[0])),
                        "success": bool(y[1] >= 0.5),
                        "output_characters": math.expm1(min(20.0, y[2] * 8.0)),
                    },
                })
            candidates.sort(key=lambda item: (item["distance"], item["created"], item["action_id"]))
            items = candidates[:limit]
            for item in items:
                item["distance"] = round(item["distance"], 8)
            return {"status": "MEMORY_RECALL_SHADOW", "items": items,
                    "checkpoint_sha256": active["checkpoint_sha256"],
                    "source_sha256": active["source_sha256"],
                    "native_memory_consumed": False, "native_body_consumed": False}


@contextmanager
def source_forget_guard(store, source_id):
    """Serialize source deletion with JEPA updates and refuse false unlearning.

    Replay rows are bounded, but their parameter influence can outlive row
    eviction. Check each retained checkpoint's full scanned T8 history, not
    only its current replay rows. Pending-only rows are discarded before the
    source is deleted; any source that may have trained active/rollback weights
    blocks deletion until a real JEPA rebuild/forget path exists.
    """
    if type(source_id) is not str or not source_id or len(source_id) > 256:
        raise ValueError("invalid WorldJEPA source identity")

    root = Path(store.home) / "world_jepa"
    consumer = WorldJEPAStoreConsumer(
        store, root, learning_enabled=False
    )
    with consumer._locked(True):
        state, version = consumer._read_state()
        pending_rows = state["pending_rows"]
        pending_for_source = [
            row["action_id"] for row in pending_rows
            if source_id in {sid for sid, _digest in _source_pairs(row)}
        ]

        for label, record in (
            ("active", state["active"]),
            ("rollback", state["previous"]),
        ):
            if record is None:
                continue
            if any(
                source_id in {sid for sid, _digest in _source_pairs(row)}
                for row in record["experience_rows"]
            ):
                raise ValueError(
                    "Source is retained by a WorldJEPA "
                    + label + " checkpoint; safe unlearning is not implemented"
                )

            cursor = record["scan_cursor"]
            if cursor <= 0:
                continue
            query = (
                "SELECT a.id FROM actions a "
                "JOIN events e ON e.id=a.event_id "
                "WHERE a.rowid<=? AND e.source_id=? "
                "AND a.outcome IS NOT NULL AND a.expected LIKE ? "
                "AND a.status IN ('FINAL','FAILED','ERROR','DEADLINE','REJECTED')"
            )
            params = [cursor, source_id, '%"forecast"%']
            if pending_for_source:
                placeholders = ",".join("?" for _ in pending_for_source)
                query += " AND a.id NOT IN (" + placeholders + ")"
                params.extend(pending_for_source)
            query += " LIMIT 1"
            if store.rows(query, tuple(params)):
                raise ValueError(
                    "Source may have trained a WorldJEPA "
                    + label + " checkpoint (including evicted replay rows); "
                    "safe unlearning is not implemented"
                )
            selection_query = (
                "SELECT 1 FROM actions a "
                "JOIN events e ON e.id=a.event_id "
                "JOIN packets p ON p.kind='ActionSelection' AND p.event_id=a.event_id "
                "AND p.generation_id=e.generation_id "
                "WHERE a.rowid<=? AND a.outcome IS NOT NULL AND a.expected LIKE ? "
                "AND a.status IN ('FINAL','FAILED','ERROR','DEADLINE','REJECTED') "
                "AND p.created<=a.created "
                "AND COALESCE(json_extract(p.payload,'$.stage'),'COMMIT')!='PREDICTION' "
                "AND EXISTS (SELECT 1 FROM json_each(p.payload,'$.provenance') AS source_ref "
                "WHERE json_extract(source_ref.value,'$.source_id')=?)"
            )
            selection_params = [cursor, '%"forecast"%', source_id]
            if pending_for_source:
                placeholders = ",".join("?" for _ in pending_for_source)
                selection_query += " AND a.id NOT IN (" + placeholders + ")"
                selection_params.extend(pending_for_source)
            selection_query += " LIMIT 1"
            if store.rows(selection_query, tuple(selection_params)):
                raise ValueError(
                    "Source may have trained a WorldJEPA "
                    + label + " checkpoint through ActionSelection context "
                    "(including evicted replay rows); safe unlearning is not implemented"
                )

        if pending_for_source:
            next_state = dict(state)
            next_state["pending_rows"] = [
                row for row in pending_rows if row["action_id"] not in pending_for_source
            ]
            try:
                store.set_state(STATE_KEY, next_state, expected=version)
            except ValueError as exc:
                if "Stale state write" in str(exc):
                    raise ValueError(
                        "WorldJEPA state changed during source forget; retry"
                    ) from exc
                raise

        removed, errors = consumer._prune_checkpoints(state)
        if errors:
            raise OSError(
                "WorldJEPA orphan checkpoint cleanup failed; source deletion refused"
            )
        yield {
            "pending_rows_removed": len(pending_for_source),
            "orphan_checkpoints_removed": removed,
        }
