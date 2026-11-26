"""Bounded, consent-scoped timing expectations over RAW EAR activity classes.

This is an A3/A4 shadow signal, not semantic event recognition. It learns only
short inter-onset intervals for VOICED/IMPULSIVE acoustic activity, and calls an
omission only when a valid FINAL SILENCE/non-target window crosses an expected
window. Missing capture, uncertain cues and provisional windows are censored.
No PCM, transcript, speaker vector or user content is retained.
"""
from __future__ import annotations

from collections import OrderedDict
import math
import threading
from statistics import median

SCHEMA = "v14.raw-ear.event-expectation/1"
METHOD = "BOUNDED_TIMED_ACTIVITY_EXPECTATION_V1"
EVENT_CLASSES = ("VOICED", "IMPULSIVE")
OBSERVED_CLASSES = EVENT_CLASSES + ("SILENCE", "UNVOICED_NOISE", "UNCERTAIN")
MAX_STREAMS = 16
MAX_INTERVALS = 8
MAX_WINDOW_MS = 1000
MAX_GAP_MS = 2000
MIN_INTERVAL_MS = 250
MAX_INTERVAL_MS = 60_000
MIN_INTERVALS = 3
MIN_CONFIDENCE = 0.45
MIN_ACTIVITY_SCORE = 0.5
MAX_TOLERANCE_MS = 1000
MIN_TOLERANCE_MS = 250
ATTENTION_GAIN = 0.05


class AudioEventExpectationError(ValueError):
    pass


def unavailable_expectation(status: str) -> dict:
    if type(status) is not str or not status:
        raise AudioEventExpectationError("status must be non-empty")
    return {
        "schema": SCHEMA,
        "method": METHOD,
        "status": status,
        "observed_activity": None,
        "expected_events": [],
        "omissions": [],
        "omission_detected": False,
        "timing_confidence_proxy": 0.0,
        "attention_novelty": 0.0,
        "stream_count": 0,
        "interval_samples": 0,
        "state_scope": "EPHEMERAL_CONSENT_SCOPED_PROCESS",
        "state_persistence": False,
        "training_data_persisted": False,
        "calibrated_probability": False,
        "event_identity_authority": False,
        "learning_authority": False,
        "action_authority": False,
        "truth_authority": False,
    }


def _finite_unit(value, name: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise AudioEventExpectationError(f"{name} must be finite")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise AudioEventExpectationError(f"{name} must be in [0, 1]")
    return result


def _scope_valid(value: str) -> bool:
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _timing_stats(intervals: list[int]) -> tuple[float, float, float, float]:
    centre = float(median(intervals))
    deviations = [abs(float(value) - centre) for value in intervals]
    mad = float(median(deviations))
    tolerance = min(MAX_TOLERANCE_MS, max(MIN_TOLERANCE_MS, 0.15 * centre, 2.5 * mad))
    sample_confidence = min(0.90, len(intervals) / (len(intervals) + 2.0))
    spread_ratio = (max(intervals) - min(intervals)) / max(centre, 1.0)
    instability = max(2.0 * mad / max(centre, 1.0), 0.5 * spread_ratio)
    stability = max(0.0, 1.0 - min(1.0, instability))
    confidence = sample_confidence * stability
    return centre, mad, tolerance, confidence


class _StreamState:
    __slots__ = (
        "consent_scope_id", "last_start_ms", "last_end_ms", "last_activity",
        "last_event_ms", "intervals", "expected_next_ms",
    )

    def __init__(self, consent_scope_id: str, start_ms: int, end_ms: int):
        self.consent_scope_id = consent_scope_id
        self.last_start_ms = start_ms
        self.last_end_ms = end_ms
        self.last_activity = None
        self.last_event_ms = {name: None for name in EVENT_CLASSES}
        self.intervals = {name: [] for name in EVENT_CLASSES}
        self.expected_next_ms = {name: None for name in EVENT_CLASSES}


class AudioEventExpectationRegistry:
    """Small process-local what/when expectation over acoustic activity classes."""

    def __init__(self, *, max_streams: int = MAX_STREAMS, max_gap_ms: int = MAX_GAP_MS):
        if type(max_streams) is not int or not 1 <= max_streams <= 64:
            raise AudioEventExpectationError("max_streams must be in [1, 64]")
        if type(max_gap_ms) is not int or not 100 <= max_gap_ms <= 10_000:
            raise AudioEventExpectationError("max_gap_ms must be in [100, 10000]")
        self.max_streams = max_streams
        self.max_gap_ms = max_gap_ms
        self._states: OrderedDict[tuple[str, str], _StreamState] = OrderedDict()
        self._lock = threading.RLock()

    @staticmethod
    def _base(status: str, activity: str | None, stream_count: int) -> dict:
        result = unavailable_expectation(status)
        result.update({"observed_activity": activity, "stream_count": stream_count})
        return result

    def update(self, *, source_id: str, generation_id: str, consent_scope_id: str,
               start_ms: int, end_ms: int, cues: dict, finality: str) -> dict:
        with self._lock:
            return self._update(
                source_id=source_id, generation_id=generation_id,
                consent_scope_id=consent_scope_id, start_ms=start_ms,
                end_ms=end_ms, cues=cues, finality=finality,
            )

    def _update(self, *, source_id: str, generation_id: str, consent_scope_id: str,
                start_ms: int, end_ms: int, cues: dict, finality: str) -> dict:
        if type(source_id) is not str or not source_id.strip():
            raise AudioEventExpectationError("source_id must be non-empty")
        if type(generation_id) is not str or not generation_id.strip():
            raise AudioEventExpectationError("generation_id must be non-empty")
        if not _scope_valid(consent_scope_id):
            raise AudioEventExpectationError("consent_scope_id must be a SHA-256 hex digest")
        if (type(start_ms) is not int or type(end_ms) is not int or start_ms < 0
                or end_ms <= start_ms or end_ms - start_ms > MAX_WINDOW_MS):
            raise AudioEventExpectationError("audio window interval is invalid")
        if finality == "PROVISIONAL":
            return self._base("PROVISIONAL_IGNORED", None, len(self._states))
        if finality != "FINAL":
            raise AudioEventExpectationError("finality must be FINAL or PROVISIONAL")
        if type(cues) is not dict:
            raise AudioEventExpectationError("cues must be a dict")
        activity = cues.get("activity_hint")
        if type(activity) is not str or activity not in OBSERVED_CLASSES:
            raise AudioEventExpectationError("activity_hint is invalid")
        activity_score = _finite_unit(cues.get("activity_score"), "activity_score")
        key = (source_id, generation_id)
        state = self._states.get(key)
        if state is not None and state.consent_scope_id != consent_scope_id:
            self._states.pop(key, None)
            self._states[key] = _StreamState(consent_scope_id, start_ms, end_ms)
            return self._base("RESET_CONSENT_SCOPE", activity, len(self._states))
        if state is None:
            state = _StreamState(consent_scope_id, start_ms, end_ms)
            self._states[key] = state
            while len(self._states) > self.max_streams:
                self._states.popitem(last=False)
            # Process the first FINAL window below so the first onset is not lost.
        elif start_ms < state.last_start_ms or end_ms <= state.last_end_ms:
            self._states.pop(key, None)
            return self._base("RESET_CHRONOLOGY", activity, len(self._states))
        elif start_ms - state.last_end_ms > self.max_gap_ms:
            self._states[key] = _StreamState(consent_scope_id, start_ms, end_ms)
            self._states.move_to_end(key)
            return self._base("RESET_GAP", activity, len(self._states))

        state.last_start_ms = start_ms
        state.last_end_ms = end_ms
        self._states.move_to_end(key)
        if activity == "UNCERTAIN" or activity_score < MIN_ACTIVITY_SCORE:
            # A censored window breaks the current onset chain. Keep the bounded
            # interval distribution, but never carry a pending omission across
            # a window whose activity class is not reliable.
            state.last_activity = None
            for name in EVENT_CLASSES:
                state.last_event_ms[name] = None
                state.expected_next_ms[name] = None
            status = (
                "CENSORED_UNCERTAIN" if activity == "UNCERTAIN"
                else "CENSORED_LOW_CONFIDENCE"
            )
            result = self._base(status, activity, len(self._states))
            result["interval_samples"] = sum(len(values) for values in state.intervals.values())
            return result

        event_class = activity if activity in EVENT_CLASSES else None
        new_onset = event_class is not None and state.last_activity != event_class
        omissions = []
        expected_events = []

        # Score an expected event before changing the interval model. A late
        # event can therefore be both an omission of the expected window and a
        # newly observed onset; this is one bounded omission, not a transcript.
        for name in EVENT_CLASSES:
            intervals = state.intervals[name]
            expected = state.expected_next_ms[name]
            if expected is None or len(intervals) < MIN_INTERVALS:
                continue
            centre, mad, tolerance, confidence = _timing_stats(intervals)
            expected_events.append({
                "activity_class": name,
                "expected_at_ms": int(expected),
                "tolerance_ms": int(round(tolerance)),
                "timing_confidence_proxy": round(confidence, 6),
            })
            if name == event_class:
                observed_lateness = start_ms - expected
                if new_onset and observed_lateness > tolerance and confidence >= MIN_CONFIDENCE:
                    omissions.append({
                        "activity_class": name,
                        "expected_at_ms": int(expected),
                        "observed_at_ms": start_ms,
                        "lateness_ms": int(observed_lateness),
                        "timing_confidence_proxy": round(confidence, 6),
                    })
                elif not new_onset and start_ms <= expected + tolerance and end_ms >= expected - tolerance:
                    # A continuous active window fulfils the expected event once.
                    # Do not leave an already-observed expectation pending until silence.
                    state.expected_next_ms[name] = int(round(expected + centre))
            elif start_ms <= expected and end_ms >= expected + tolerance and confidence >= MIN_CONFIDENCE:
                omissions.append({
                    "activity_class": name,
                    "expected_at_ms": int(expected),
                    "observed_at_ms": None,
                    "lateness_ms": int(end_ms - expected),
                    "timing_confidence_proxy": round(confidence, 6),
                })
                state.expected_next_ms[name] = int(round(expected + centre))

        if event_class is not None and new_onset:
            previous = state.last_event_ms[event_class]
            if previous is not None:
                interval = start_ms - previous
                if MIN_INTERVAL_MS <= interval <= MAX_INTERVAL_MS:
                    values = state.intervals[event_class]
                    values.append(interval)
                    if len(values) > MAX_INTERVALS:
                        del values[0]
            state.last_event_ms[event_class] = start_ms
            values = state.intervals[event_class]
            state.expected_next_ms[event_class] = (
                int(round(start_ms + median(values))) if values else None
            )
            state.last_activity = event_class
        elif event_class is None:
            state.last_activity = None
        else:
            state.last_activity = event_class

        measured = any(len(values) >= MIN_INTERVALS for values in state.intervals.values())
        scores = [
            item["timing_confidence_proxy"]
            * min(1.0, item["lateness_ms"] / max(1, next(
                (event["tolerance_ms"] for event in expected_events
                 if event["activity_class"] == item["activity_class"]), MIN_TOLERANCE_MS
            )))
            for item in omissions
        ]
        score = max(scores, default=0.0)
        return {
            "schema": SCHEMA,
            "method": METHOD,
            "status": "SHADOW_MEASURED" if measured else "WARMUP",
            "observed_activity": activity,
            "expected_events": expected_events,
            "omissions": omissions,
            "omission_detected": bool(omissions),
            "timing_confidence_proxy": round(max(
                (item["timing_confidence_proxy"] for item in expected_events), default=0.0
            ), 6),
            "attention_novelty": round(min(ATTENTION_GAIN, ATTENTION_GAIN * score), 8),
            "stream_count": len(self._states),
            "interval_samples": sum(len(values) for values in state.intervals.values()),
            "state_scope": "EPHEMERAL_CONSENT_SCOPED_PROCESS",
            "state_persistence": False,
            "training_data_persisted": False,
            "calibrated_probability": False,
            "event_identity_authority": False,
            "learning_authority": False,
            "action_authority": False,
            "truth_authority": False,
            "window_start_ms": start_ms,
            "window_end_ms": end_ms,
        }

    def reset(self, *, source_id: str | None = None,
              generation_id: str | None = None) -> int:
        with self._lock:
            keys = [key for key in self._states
                    if (source_id is None or key[0] == source_id)
                    and (generation_id is None or key[1] == generation_id)]
            for key in keys:
                self._states.pop(key, None)
            return len(keys)

    def __len__(self) -> int:
        with self._lock:
            return len(self._states)


def predictive_event_omission_novelty(prediction: dict) -> float:
    if type(prediction) is not dict or prediction.get("status") != "SHADOW_MEASURED":
        return 0.0
    if prediction.get("omission_detected") is not True:
        return 0.0
    value = _finite_unit(prediction.get("attention_novelty"), "attention_novelty")
    return round(min(ATTENTION_GAIN, value), 8)
