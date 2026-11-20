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
from v13 import world_jepa_action_outcome_adapter
from v13 import world_jepa_shadow_checkpoint
from v13 import world_model
from t8_store_authority import verify_committed_transitions


REVISION = "v14-world-jepa-store-consumer-v1"
STATE_KEY = "v14.world_jepa.store_consumer"
MAX_ROWS = min(2048, world_model.MAX_ROWS)
MAX_TRACKED = 10000
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
CHECKPOINT_NAME = re.compile(r"jepa-[0-9a-f]{32}\.npz\Z")
ROLE_TARGETS = {
    "B1_DETAIL": (0, 2),
    "B2_GIST": (1,),
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


def _receipt_row(receipt):
    if type(receipt.action_id) is not str or not receipt.action_id or len(receipt.action_id) > 128:
        raise ValueError("invalid verified action id")
    raw = receipt.training_row()
    proof = receipt.public_provenance()
    route = raw.get("a")
    if route not in world_model.ACTIONS:
        raise ValueError("unknown verified action route")
    return {
        "action_id": receipt.action_id,
        "fingerprint": _sha(receipt.fingerprint),
        "source_sha256": _sha(proof.get("source_sha256")),
        "outcome_sha256": _sha(proof.get("outcome_sha256")),
        "created": float(receipt.created),
        "s": _vector(raw.get("s"), 4),
        "a": route,
        "y": _vector(raw.get("y"), 3),
    }


def _cohort_sha(rows):
    body = [
        {"action_id": row["action_id"], "fingerprint": row["fingerprint"]}
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
            if type(row) is not dict or set(row) != {
                "action_id", "fingerprint", "source_sha256", "outcome_sha256",
                "created", "s", "a", "y",
            }:
                raise ValueError("invalid replay memory row")
            if (row["action_id"] not in fingerprints
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
                or not set(train_ids + holdout_ids).issubset(set(row_ids))):
            raise ValueError("train/holdout cursor mismatch")
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

    def _read_state(self):
        payload, version = self.store.state(STATE_KEY, None)
        if payload is None:
            return {"schema": 1, "revision": REVISION, "active": None, "previous": None}, version
        if (type(payload) is not dict or set(payload) != {"schema", "revision", "active", "previous"}
                or payload["schema"] != 1 or payload["revision"] != REVISION):
            raise ValueError("incompatible WorldJEPA Store state")
        self._validate_record(payload["active"])
        self._validate_record(payload["previous"])
        return payload, version

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

    def update(self, *, limit=MAX_ROWS, steps=80, optimizer_permission=False):
        if type(limit) is not int or not 1 <= limit <= MAX_ROWS:
            raise ValueError("limit")
        if type(steps) is not int or not 1 <= steps <= 2000:
            raise ValueError("steps")
        if type(optimizer_permission) is not bool:
            raise ValueError("optimizer_permission must be bool")

        receipts, rejected = verify_committed_transitions(self.store, limit=limit)
        incoming = [_receipt_row(receipt) for receipt in receipts]
        with self._locked(True):
            state, version = self._read_state()
            active = state["active"]
            prior_fingerprints = dict(active["fingerprints"]) if active else {}
            prior_rows = {
                row["action_id"]: row for row in (active["experience_rows"] if active else [])
            }
            new_ids = []
            buffer_added = []
            for row in incoming:
                action_id = row["action_id"]
                prior_fingerprint = prior_fingerprints.get(action_id)
                if prior_fingerprint is not None and prior_fingerprint != row["fingerprint"]:
                    raise ValueError("committed T8 receipt changed after learning")
                if prior_fingerprint is None:
                    new_ids.append(action_id)
                    prior_fingerprints[action_id] = row["fingerprint"]
                if action_id not in prior_rows:
                    buffer_added.append(action_id)
                prior_rows[action_id] = row
            if len(prior_fingerprints) > MAX_TRACKED:
                raise OverflowError("processed T8 identity budget exhausted; fail closed")
            if not new_ids and not buffer_added:
                return {
                    "status": "NO_NEW_TRANSITIONS",
                    "verified_receipts": len(receipts),
                    "rejected_receipts": rejected,
                    "processed": len(prior_fingerprints),
                    "native_body_weights_changed": False,
                }
            if not self.learning_enabled:
                return {
                    "status": "LEARNING_DISABLED",
                    "new_receipts": len(new_ids),
                    "verified_receipts": len(receipts),
                    "rejected_receipts": rejected,
                    "native_body_weights_changed": False,
                }
            if optimizer_permission is not True:
                return {
                    "status": "PENDING_OPTIMIZER_PERMISSION",
                    "new_receipts": len(new_ids),
                    "verified_receipts": len(receipts),
                    "rejected_receipts": rejected,
                    "native_body_weights_changed": False,
                }

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
            raw_rows = [
                {"action_id": row["action_id"], "s": row["s"], "a": row["a"], "y": row["y"]}
                for row in experience_rows
            ]
            try:
                split = world_jepa_action_outcome_adapter.build(raw_rows)
            except ValueError as exc:
                return {
                    "status": "INSUFFICIENT_DISJOINT_T8_COHORT",
                    "reason": str(exc),
                    "verified_receipts": len(receipts),
                    "rejected_receipts": rejected,
                    "new_receipts": len(new_ids),
                    "native_body_weights_changed": False,
                }

            train_ids = list(split["train_action_ids"])
            holdout_ids = list(split["holdout_action_ids"])
            if set(train_ids) & set(holdout_ids):
                raise ValueError("train/holdout identity overlap")
            row_by_id = {row["action_id"]: row for row in experience_rows}
            train_rows = [row_by_id[action_id] for action_id in train_ids]
            holdout_rows = [row_by_id[action_id] for action_id in holdout_ids]
            train, holdout = split["train"], split["holdout"]
            if active is not None:
                model = self._load_model(active)
                checkpoint_before = active["checkpoint_sha256"]
            else:
                model = world_jepa.WorldJEPA(seed=self.seed, ensemble=self.ensemble)
                # A zero-gradient fit creates the frozen no-update baseline.
                model.fit(*train, steps=0, log_every=1)
                checkpoint_before = None

            fit_steps_before = int(getattr(model, "_fit_steps", 0))
            before = _parameter_snapshot(model)
            holdout_before = model.prediction_loss(*holdout)
            old_holdout_before = old_holdout_after = None
            if active is not None:
                old_holdout_ids = set(active["holdout_ids"])
                old_holdout_rows = [
                    row for row in active["experience_rows"]
                    if row["action_id"] in old_holdout_ids
                ]
                if len(old_holdout_rows) >= 2:
                    old_holdout = _arrays(old_holdout_rows)
                    old_holdout_before = model.prediction_loss(*old_holdout)

            model.partial_fit(
                *train, steps=steps, log_every=max(1, steps // 4)
            )
            after = _parameter_snapshot(model)
            holdout_after = model.prediction_loss(*holdout)
            shuffled_action_loss = model.prediction_loss(
                holdout[0], np.roll(holdout[1], 1, axis=0), holdout[2]
            )
            zero_action_loss = model.prediction_loss(
                holdout[0], np.zeros_like(holdout[1]), holdout[2]
            )
            if old_holdout_before is not None:
                old_holdout_after = model.prediction_loss(*old_holdout)

            receiver_heads, receiver_metrics = _fit_role_receivers(
                model, train, holdout, train_rows, holdout_rows
            )
            source_sha = _cohort_sha(experience_rows)
            checkpoint_name = "jepa-" + uuid.uuid4().hex + ".npz"
            checkpoint_path = self.home / checkpoint_name
            saved = world_jepa_shadow_checkpoint.save(model, checkpoint_path, source_sha)
            checkpoint_after = _sha(saved.get("sha256"))
            fit_steps_after = int(getattr(model, "_fit_steps", 0))
            parameter_delta = _group_delta(before, after, ("enc", "preds"))
            ema_delta = _group_delta(before, after, ("tgt",))
            previous_updates = (
                int(active["self_state"].get("update_count", 0)) if active else 0
            )
            retention_delta = (
                None if old_holdout_before is None
                else float(old_holdout_after - old_holdout_before)
            )
            metrics = {
                "source_verified": True,
                "verified_receipts": len(receipts),
                "rejected_receipts": rejected,
                "replay_rows": len(set(active["train_ids"]) & set(train_ids)) if active else 0,
                "new_train_rows": len(set(new_ids) & set(train_ids)),
                "new_holdout_rows": len(set(new_ids) & set(holdout_ids)),
                "train_rows": len(train_ids),
                "holdout_rows": len(holdout_ids),
                "train_holdout_id_disjoint": True,
                "train_holdout_content_disjoint": bool(
                    split["manifest"]["within_supplied_records_id_disjoint"]
                ),
                "holdout_loss_before": float(holdout_before),
                "holdout_loss_after": float(holdout_after),
                "holdout_loss_delta": float(holdout_after - holdout_before),
                "shuffled_action_holdout_loss": float(shuffled_action_loss),
                "zero_action_holdout_loss": float(zero_action_loss),
                "old_holdout_loss_before": (
                    None if old_holdout_before is None else float(old_holdout_before)
                ),
                "old_holdout_loss_after": (
                    None if old_holdout_after is None else float(old_holdout_after)
                ),
                "old_holdout_retention_delta": retention_delta,
                "parameter_delta_norm": float(parameter_delta),
                "ema_target_delta_norm": float(ema_delta),
                "fit_steps_before": fit_steps_before,
                "fit_steps_after": fit_steps_after,
                "checkpoint_sha_before": checkpoint_before,
                "checkpoint_sha_after": checkpoint_after,
                "optimizer_moments_persisted": False,
                "inverse_dynamics_optimizer_persisted": False,
            }
            metrics.update(receiver_metrics)
            record = {
                "checkpoint": checkpoint_name,
                "checkpoint_sha256": checkpoint_after,
                "source_sha256": source_sha,
                "processed_ids": sorted(prior_fingerprints),
                "fingerprints": prior_fingerprints,
                "experience_rows": experience_rows,
                "train_ids": train_ids,
                "holdout_ids": holdout_ids,
                "receiver_heads": receiver_heads,
                "metrics": metrics,
                "self_state": {
                    "update_count": previous_updates + 1,
                    "last_prediction_error": float(holdout_after),
                    "last_parameter_delta_norm": float(parameter_delta),
                    "last_retention_delta": retention_delta,
                },
                "fit_steps": fit_steps_after,
            }
            next_state = {
                "schema": 1,
                "revision": REVISION,
                "active": record,
                "previous": active,
            }
            try:
                self.store.set_state(STATE_KEY, next_state, expected=version)
            except ValueError as exc:
                try:
                    checkpoint_path.unlink(missing_ok=True)
                except OSError:
                    pass
                if "Stale state write" in str(exc):
                    return {
                        "status": "CONCURRENT_STATE_CONFLICT_RETRY",
                        "new_receipts": len(new_ids),
                        "checkpoint_discarded": True,
                        "native_body_weights_changed": False,
                    }
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
                "verified_receipts": len(receipts),
                "orphan_checkpoints_removed": pruned_checkpoints,
                "checkpoint_prune_errors": prune_errors,
                "rejected_receipts": rejected,
                "new_receipts": len(new_ids),
                "processed": len(prior_fingerprints),
                "checkpoint_sha256": checkpoint_after,
                "source_sha256": source_sha,
                "metrics": metrics,
                "native_body_weights_changed": False,
                "native_body_consumed": False,
                "runtime_wired": False,
                "scope": "WORLD_JEPA_EMA_AND_B1_B2_NUMERIC_READOUT_SHADOW",
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
            # Verify the complete prior checkpoint before changing the Store pointer.
            self._load_model(previous)
            self.store.set_state(
                STATE_KEY,
                {"schema": 1, "revision": REVISION,
                 "active": previous, "previous": active},
                expected=version,
            )
            return {
                "status": "ROLLED_BACK",
                "checkpoint_sha256": previous["checkpoint_sha256"],
                "processed": len(previous["processed_ids"]),
                "native_body_weights_changed": False,
            }

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
                duration_s = max(0.0, math.expm1(min(20.0, float(prediction[0]))))
                characters = max(0.0, math.expm1(min(20.0, float(prediction[1]) * 8.0)))
                output = {
                    "predicted_action_duration_s": duration_s,
                    "predicted_output_characters": characters,
                }
            else:
                output = {
                    "predicted_success_probability": float(np.clip(prediction[0], 0.0, 1.0))
                }
            uncertainty = float(np.asarray(spread).reshape(-1)[0])
            if not math.isfinite(uncertainty):
                raise ValueError("nonfinite receiver uncertainty")
            return {
                "role": role,
                "prediction": output,
                "uncertainty": uncertainty,
                "checkpoint_sha256": active["checkpoint_sha256"],
                "source_sha256": active["source_sha256"],
                "status": "SHADOW_READOUT_ONLY",
                "native_body_consumed": False,
                "native_body_weights_changed": False,
            }
