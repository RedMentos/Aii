"""Append-only observations and atomically published, validated scalar snapshots.

SQLite integrity is an application invariant, not protection against a person
who can replace the database or remove its triggers. One Repository instance
belongs to one thread. Native model tensors are deliberately absent.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from types import MappingProxyType
from typing import Callable, Dict, Iterator, Mapping, Optional, Sequence, Tuple
import uuid

from .contracts import Experience, Origin, canonical_json, finite, nonempty


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS experiences (
  id TEXT PRIMARY KEY,
  origin TEXT NOT NULL CHECK(origin IN ('observed', 'synthetic')),
  source_ref TEXT NOT NULL CHECK(length(trim(source_ref)) > 0),
  model_version TEXT NOT NULL,
  created_utc TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  parent_ids_json TEXT NOT NULL,
  sha256 TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS immutable_experience_update
BEFORE UPDATE ON experiences BEGIN SELECT RAISE(ABORT, 'experiences are immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_experience_delete
BEFORE DELETE ON experiences BEGIN SELECT RAISE(ABORT, 'experiences are immutable'); END;
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_id INTEGER REFERENCES snapshots(id),
  model_version TEXT NOT NULL,
  weights_json TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  report_json TEXT NOT NULL,
  created_utc TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS immutable_snapshot_update
BEFORE UPDATE ON snapshots BEGIN SELECT RAISE(ABORT, 'snapshots are immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_snapshot_delete
BEFORE DELETE ON snapshots BEGIN SELECT RAISE(ABORT, 'snapshots are immutable'); END;
CREATE TABLE IF NOT EXISTS live_state (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  snapshot_id INTEGER NOT NULL REFERENCES snapshots(id)
);
CREATE TABLE IF NOT EXISTS derived_cache (
  cache_key TEXT PRIMARY KEY,
  snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
  model_version TEXT NOT NULL,
  value_json TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Snapshot:
    id: int
    parent_id: Optional[int]
    model_version: str
    weights: Mapping[str, float]
    sha256: str


@dataclass(frozen=True)
class ValidationReport:
    passed: bool
    validator: str
    checks: Tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.passed) is not bool:
            raise ValueError("passed must be boolean")
        nonempty(self.validator, "validator")
        if not isinstance(self.checks, tuple) or not self.checks:
            raise ValueError("validation checks must be a nonempty tuple")
        for check in self.checks:
            nonempty(check, "validation check")


class ValidationFailed(ValueError):
    pass


class StaleSnapshot(ValueError):
    pass


class Repository:
    def __init__(self, path: str = ":memory:") -> None:
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def __enter__(self) -> "Repository":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self.db.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        else:
            self.db.execute("COMMIT")

    def append_experience(self, origin: Origin, source_ref: str,
                          payload: Dict[str, object], model_version: str,
                          parent_ids: Sequence[str] = ()) -> Experience:
        origin = Origin(origin)
        nonempty(source_ref, "source_ref")
        nonempty(model_version, "model_version")
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        payload_json = canonical_json(payload)
        parents = tuple(sorted(set(parent_ids)))
        with self.transaction():
            for parent_id in parents:
                parent = self.experience(parent_id)
                if origin == Origin.OBSERVED and parent.origin == Origin.SYNTHETIC:
                    raise ValueError("synthetic content cannot be promoted to observed evidence")
            values = {
                "id": uuid.uuid4().hex, "origin": origin.value, "source_ref": source_ref,
                "model_version": model_version, "created_utc": utc_now(),
                "payload_json": payload_json, "parent_ids_json": canonical_json(parents),
            }
            values["sha256"] = digest(values)
            self.db.execute(
                "INSERT INTO experiences VALUES (:id, :origin, :source_ref, :model_version, "
                ":created_utc, :payload_json, :parent_ids_json, :sha256)", values)
        return self.experience(values["id"])

    def experience(self, experience_id: str) -> Experience:
        row = self.db.execute("SELECT * FROM experiences WHERE id = ?", (experience_id,)).fetchone()
        if row is None:
            raise KeyError("unknown experience: " + experience_id)
        values = dict(row)
        expected = values.pop("sha256")
        if digest(values) != expected:
            raise ValueError("experience integrity check failed")
        return Experience(row["id"], Origin(row["origin"]), row["source_ref"],
                          row["model_version"], row["created_utc"], row["payload_json"],
                          tuple(json.loads(row["parent_ids_json"])), row["sha256"])

    def observed_evidence(self) -> Tuple[Experience, ...]:
        """External observations, not claims that their payloads are true."""
        rows = self.db.execute("SELECT id FROM experiences WHERE origin = 'observed' ORDER BY rowid")
        return tuple(self.experience(row["id"]) for row in rows)

    @staticmethod
    def _weights(weights: Mapping[str, float]) -> Dict[str, float]:
        if not isinstance(weights, Mapping) or not weights:
            raise ValueError("weights must be a nonempty mapping")
        return {nonempty(key, "path"): finite(value, "weight") for key, value in weights.items()}

    def initialize(self, weights: Mapping[str, float], model_version: str) -> Snapshot:
        values = self._weights(weights)
        nonempty(model_version, "model_version")
        with self.transaction():
            if self.db.execute("SELECT 1 FROM live_state").fetchone() is not None:
                raise ValueError("repository is already initialized")
            snapshot_id = self._insert_snapshot(None, model_version, values, {
                "passed": True, "validator": "bootstrap-schema-only",
                "checks": ["finite scalar values", "nonempty version"],
            })
            self.db.execute("INSERT INTO live_state VALUES (1, ?)", (snapshot_id,))
        return self.snapshot(snapshot_id)

    def _insert_snapshot(self, parent_id: Optional[int], model_version: str,
                         weights: Mapping[str, float], report: Dict[str, object]) -> int:
        sha = digest({"model_version": model_version, "weights": weights})
        cursor = self.db.execute(
            "INSERT INTO snapshots(parent_id, model_version, weights_json, sha256, report_json, "
            "created_utc) VALUES (?, ?, ?, ?, ?, ?)",
            (parent_id, model_version, canonical_json(weights), sha, canonical_json(report), utc_now()))
        return cursor.lastrowid

    def snapshot(self, snapshot_id: int) -> Snapshot:
        row = self.db.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        if row is None:
            raise KeyError("unknown snapshot")
        weights = json.loads(row["weights_json"])
        if digest({"model_version": row["model_version"], "weights": weights}) != row["sha256"]:
            raise ValueError("snapshot integrity check failed")
        return Snapshot(row["id"], row["parent_id"], row["model_version"],
                        MappingProxyType(weights), row["sha256"])

    def current(self) -> Snapshot:
        row = self.db.execute("SELECT snapshot_id FROM live_state WHERE singleton = 1").fetchone()
        if row is None:
            raise ValueError("repository has no initial snapshot")
        return self.snapshot(row["snapshot_id"])

    def commit(self, candidate: Mapping[str, float], expected_snapshot_id: int,
               model_version: str,
               validator: Callable[[Mapping[str, float], Snapshot], ValidationReport]) -> Snapshot:
        values = self._weights(candidate)
        nonempty(model_version, "model_version")
        base = self.current()
        if base.id != expected_snapshot_id:
            raise StaleSnapshot("candidate was computed against an old snapshot")
        report = validator(MappingProxyType(values), base)
        if not isinstance(report, ValidationReport) or not report.passed:
            raise ValidationFailed("candidate rejected; live snapshot unchanged")
        with self.transaction():
            if self.current().id != expected_snapshot_id:
                raise StaleSnapshot("live snapshot changed during validation")
            sid = self._insert_snapshot(base.id, model_version, values, {
                "passed": report.passed, "validator": report.validator, "checks": report.checks,
            })
            self.db.execute("UPDATE live_state SET snapshot_id = ? WHERE singleton = 1", (sid,))
            self.db.execute("DELETE FROM derived_cache")
        return self.snapshot(sid)

    def rollback(self, target_id: int, expected_snapshot_id: int) -> Snapshot:
        target = self.snapshot(target_id)
        return self.commit(
            target.weights, expected_snapshot_id, target.model_version,
            lambda values, base: ValidationReport(
                True, "verified-snapshot-restore",
                ("restored immutable snapshot " + str(target_id), "finite values and content hash")),
        )

    def cache_put(self, key: str, value: object) -> None:
        nonempty(key, "cache key")
        with self.transaction():
            current = self.current()
            self.db.execute("INSERT OR REPLACE INTO derived_cache VALUES (?, ?, ?, ?)",
                            (key, current.id, current.model_version, canonical_json(value)))

    def cache_get(self, key: str) -> Optional[object]:
        row = self.db.execute(
            "SELECT c.value_json FROM derived_cache c JOIN live_state l "
            "ON c.snapshot_id = l.snapshot_id JOIN snapshots s ON s.id = l.snapshot_id "
            "WHERE c.cache_key = ? AND c.model_version = s.model_version", (key,)).fetchone()
        return None if row is None else json.loads(row["value_json"])
