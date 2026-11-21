"""V14 temporal outcome / omission evidence, no weight or action authority."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Expectation:
    key: str
    source_ref: str
    outcome: str
    earliest_ms: int
    deadline_ms: int
    probability: float
    owner: str = "WORLD"

    def __post_init__(self):
        if not all((self.key, self.source_ref, self.outcome)):
            raise ValueError("source-bound expectation required")
        if self.owner not in ("WORLD", "SELF", "ACTION", "B1_DETAIL", "B2_GIST"):
            raise ValueError("unknown owner")
        if not (type(self.earliest_ms) is int and type(self.deadline_ms) is int
                and 0 <= self.earliest_ms <= self.deadline_ms):
            raise ValueError("invalid time interval")
        if not (math.isfinite(self.probability) and 0 <= self.probability <= 1):
            raise ValueError("invalid probability")

class TemporalOutcomeTracker:
    """Bounded one-shot evidence tracker. Caller owns persistence and observation."""
    def __init__(self, capacity=128):
        if type(capacity) is not int or not 1 <= capacity <= 4096:
            raise ValueError("invalid capacity")
        self.capacity = capacity
        self.pending = {}
        self.completed = {}

    def expect(self, record):
        if not isinstance(record, Expectation):
            raise TypeError("expected Expectation")
        if record.key in self.pending or record.key in self.completed:
            raise ValueError("duplicate key")
        if len(self.pending) >= self.capacity:
            raise OverflowError("expectation capacity reached")
        self.pending[record.key] = record

    def resolve(self, key, now_ms, *, observed=None, observation_complete=False, cancelled=False):
        if key in self.completed:
            return self.completed[key]
        record = self.pending[key]
        if type(now_ms) is not int or now_ms < 0:
            raise ValueError("invalid timestamp")
        if cancelled:
            status = "CANCELLED"
        elif observed is not None:
            status = ("DIFFERENT" if observed != record.outcome else
                      "OBSERVED" if now_ms <= record.deadline_ms else "DELAYED")
        elif now_ms < record.deadline_ms:
            return {"key": key, "status": "PENDING", "prediction_error": None}
        elif observation_complete is True:
            status = "OMITTED"
        else:
            status = "CENSORED"
        error = ((1 - record.probability) if status == "OBSERVED" else
                 -record.probability if status == "OMITTED" else None)
        result = {"key": key, "status": status, "source_ref": record.source_ref,
                  "owner": record.owner, "prediction_error": error,
                  "time_ms": now_ms, "weight_update_authorized": False}
        del self.pending[key]
        self.completed[key] = result
        return result

    def emit_feedback(self, key, event, enlightened_space):
        """Use actual EnlightenedSpace.publish contract, never assert source truth."""
        result = self.completed[key]
        return enlightened_space.publish(
            event, "OUTCOME", "FEEDBACK",
            summary="temporal outcome " + result["status"] + " owner " + result["owner"],
            authority="CONTROL_ONLY")
