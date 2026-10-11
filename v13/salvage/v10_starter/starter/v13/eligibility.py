"""Ephemeral activity evidence; never persisted across process restarts."""

from dataclasses import dataclass
import time
from typing import Callable, Dict, Optional

from .contracts import finite, nonempty


@dataclass(frozen=True)
class Trace:
    path: str
    experience_id: str
    model_version: str
    snapshot_id: int
    born: float
    deadline: float
    strength: float


class Eligibility:
    """Use from the scheduler's serialized compute section.

    activate() must eventually be fed by verified backend route telemetry.
    The demo supplies explicit synthetic activation records.
    """

    def __init__(self, ttl_seconds: float = 30.0,
                 clock: Callable[[], float] = time.monotonic):
        self.ttl = finite(ttl_seconds, "ttl_seconds")
        if self.ttl <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.clock = clock
        self._traces: Dict[str, Trace] = {}

    def activate(self, path: str, experience_id: str, model_version: str,
                 snapshot_id: int, strength: float = 1.0) -> Trace:
        for name, value in (("path", path), ("experience_id", experience_id),
                            ("model_version", model_version)):
            nonempty(value, name)
        value = finite(strength, "strength")
        if not 0 < value <= 1:
            raise ValueError("strength must be in (0, 1]")
        if type(snapshot_id) is not int or snapshot_id < 1:
            raise ValueError("snapshot_id must be positive")
        now = self.clock()
        trace = Trace(path, experience_id, model_version, snapshot_id,
                      now, now + self.ttl, value)
        self._traces[path] = trace
        return trace

    def get(self, path: str, experience_id: str, model_version: str,
            snapshot_id: int) -> Optional[Trace]:
        trace = self._traces.get(path)
        if trace is None:
            return None
        now = self.clock()
        if now < trace.born or now >= trace.deadline:
            self._traces.pop(path, None)
            return None
        if trace.model_version != model_version or trace.snapshot_id != snapshot_id:
            self._traces.pop(path, None)
            return None
        if trace.experience_id != experience_id:
            return None
        return trace

    def strength(self, trace: Trace) -> float:
        return trace.strength * max(0.0, 1.0 - (self.clock() - trace.born) / self.ttl)

    def consume(self, trace: Trace) -> None:
        if self._traces.get(trace.path) == trace:
            self._traces.pop(trace.path, None)

    def clear(self, experience_id: Optional[str] = None) -> None:
        if experience_id is None:
            self._traces.clear()
        else:
            self._traces = {key: trace for key, trace in self._traces.items()
                            if trace.experience_id != experience_id}
