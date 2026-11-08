"""Bounded, source-bound incremental World-JEPA replay; no deployment authority.

The journal is only valid paired with a matching model checkpoint generation.
It must never be persisted independently as proof of committed model updates.
"""
import hashlib
import json

from .world_jepa_action_outcome_adapter import build

SCHEMA = "v13.world_jepa.replay.v1"


class ReplaySession:
    def __init__(self, source_sha256, max_seen=8192):
        if (type(source_sha256) is not str or len(source_sha256) != 64
                or any(c not in "0123456789abcdef" for c in source_sha256)):
            raise ValueError("source SHA256 required")
        if type(max_seen) is not int or not 32 <= max_seen <= 65536:
            raise ValueError("invalid journal capacity")
        self.source = source_sha256
        self.max_seen = max_seen
        self.seen = {}
        self.holdout_seen = {}
        self.batches = 0

    @staticmethod
    def _digest(row):
        return hashlib.sha256(json.dumps(row, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode()).hexdigest()

    def update(self, model, records, steps=20):
        """Train on unseen train-partition IDs, never on holdout IDs."""
        if type(steps) is not int or not 1 <= steps <= 2000:
            raise ValueError("invalid update steps")
        split = build(records)
        ids = split["train_action_ids"]
        holdout_ids = split["holdout_action_ids"]
        by_id = {r["action_id"]: r for r in records}
        proposed = dict(self.seen)
        proposed_holdout = dict(self.holdout_seen)
        for ident in holdout_ids:
            digest = self._digest(by_id[ident])
            if ident in proposed_holdout and proposed_holdout[ident] != digest:
                raise ValueError("previous holdout action ID changed content")
            proposed_holdout[ident] = digest
        if set(proposed) & set(proposed_holdout):
            raise ValueError("train/holdout identity collision")
        for ident in ids:
            digest = self._digest(by_id[ident])
            if ident in proposed and proposed[ident] != digest:
                raise ValueError("previous action ID changed content")
            proposed[ident] = digest
        fresh = [i for i, ident in enumerate(ids) if ident not in self.seen]
        if not fresh:
            return {"updated": False, "new_rows": 0, "journal": self.snapshot()}
        if len(proposed) + len(proposed_holdout) > self.max_seen:
            raise ValueError("journal full: explicit new generation required")
        train = tuple(a[fresh] for a in split["train"])
        holdout = split["holdout"]
        before = model.prediction_loss(*holdout) if hasattr(model, "enc") else None
        if before is None:
            model.fit(*train, steps=steps, log_every=max(1, steps // 4))
        else:
            model.partial_fit(*train, steps=steps, log_every=max(1, steps // 4))
        after = model.prediction_loss(*holdout)
        self.seen = proposed
        self.holdout_seen = proposed_holdout
        self.batches += 1
        return {"updated": True, "new_rows": len(fresh),
                "holdout_loss_before": before, "holdout_loss_after": after,
                "holdout_delta": None if before is None else after - before,
                "active_model_promoted": False, "journal": self.snapshot()}

    def snapshot(self):
        return {"schema": SCHEMA, "source_sha256": self.source,
                "max_seen": self.max_seen, "batches": self.batches,
                "seen": dict(sorted(self.seen.items())),
                "holdout_seen": dict(sorted(self.holdout_seen.items())),
                "durable_without_matching_model_checkpoint": False}

    @classmethod
    def restore(cls, snapshot, source_sha256):
        if type(snapshot) is not dict or set(snapshot) != {
                "schema", "source_sha256", "max_seen", "batches", "seen", "holdout_seen",
                "durable_without_matching_model_checkpoint"}:
            raise ValueError("invalid replay journal")
        if (snapshot["schema"] != SCHEMA or snapshot["source_sha256"] != source_sha256
                or snapshot["durable_without_matching_model_checkpoint"] is not False):
            raise ValueError("replay journal source/authority mismatch")
        obj = cls(source_sha256, snapshot["max_seen"])
        seen = snapshot["seen"]
        holdout_seen = snapshot["holdout_seen"]
        if (type(seen) is not dict or type(holdout_seen) is not dict
                or len(seen) + len(holdout_seen) > obj.max_seen
                or bool(set(seen) & set(holdout_seen))
                or any(type(k) is not str or not 1 <= len(k) <= 128
                       or type(v) is not str or len(v) != 64
                       or any(c not in "0123456789abcdef" for c in v)
                       for k, v in seen.items())
                or any(type(k) is not str or not 1 <= len(k) <= 128
                       or type(v) is not str or len(v) != 64
                       or any(c not in "0123456789abcdef" for c in v)
                       for k, v in holdout_seen.items())
                or type(snapshot["batches"]) is not int or snapshot["batches"] < 0):
            raise ValueError("invalid replay journal contents")
        obj.seen = dict(seen)
        obj.holdout_seen = dict(holdout_seen)
        obj.batches = snapshot["batches"]
        return obj
