"""Small versioned contracts shared by storage, activity and scheduling."""

from dataclasses import dataclass
from enum import Enum
import json
import math
from typing import Any, Dict, Tuple


class Origin(str, Enum):
    OBSERVED = "observed"
    SYNTHETIC = "synthetic"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " must be a nonempty string")
    return value


def finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + " must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(name + " must be finite")
    return result


@dataclass(frozen=True)
class Experience:
    id: str
    origin: Origin
    source_ref: str
    model_version: str
    created_utc: str
    payload_json: str
    parent_ids: Tuple[str, ...]
    sha256: str

    def payload(self) -> Dict[str, Any]:
        """Return a detached copy; changing it cannot change stored evidence."""
        return json.loads(self.payload_json)


@dataclass(frozen=True)
class Event:
    """Transport envelope; process-local sequence is not a distributed clock.

    This is a validated interchange contract, not a running event bus.
    """

    event_id: str
    kind: str
    emitter: str
    experience_id: str
    model_version: str
    snapshot_id: int
    sequence: int
    payload_json: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        for name in ("event_id", "kind", "emitter", "experience_id", "model_version"):
            nonempty(getattr(self, name), name)
        if self.kind not in {
            "experience", "path_activated", "inference_requested", "inference_finished",
            "learning_candidate", "snapshot_committed", "learning_rejected",
        }:
            raise ValueError("unknown event kind")
        if type(self.snapshot_id) is not int or self.snapshot_id < 1:
            raise ValueError("snapshot_id must be a positive integer")
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("sequence must be a nonnegative integer")
        if self.schema_version != 1:
            raise ValueError("unsupported schema version")
        payload = json.loads(self.payload_json)
        if not isinstance(payload, dict):
            raise ValueError("event payload must be an object")
        canonical_json(payload)

    def to_json(self) -> str:
        return canonical_json({
            "schema_version": self.schema_version, "event_id": self.event_id,
            "kind": self.kind, "emitter": self.emitter,
            "experience_id": self.experience_id, "model_version": self.model_version,
            "snapshot_id": self.snapshot_id, "sequence": self.sequence,
            "payload": json.loads(self.payload_json),
        })
