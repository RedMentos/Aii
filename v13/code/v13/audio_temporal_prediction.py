# CI coverage: v14-raw-ear-fastpath and v14-raw-ear-vad-comparison validate this module and its A5/A4 consumer.
"""Consent-scoped A3 predictor for RAW EAR cue deltas.

The online shadow learner sees extracted acoustic cues only. By default its
weights are process-local; an explicit Runtime config gate may persist only
bounded numeric predictor weights. PCM, transcripts, speaker embeddings and
feature windows are never persisted. Its only effect is capped A4 novelty.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
import math
import threading
import time

SCHEMA = "v14.raw-ear.temporal-prediction/1"
METHOD = "RAW_EAR_DELTA_ONLINE_LMS_ZERO_CONTEXT_BIAS_V1"
ACTIVITY_HINTS = ("SILENCE", "VOICED", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN")
FEATURE_NAMES = (
    "f0_median", "f0_range", "energy_range", "voiced_energy_range",
    "voiced_fraction", "voicing_confidence", "activity_score",
    "prosody_change_score", "activity_silence", "activity_voiced",
    "activity_unvoiced_noise", "activity_impulsive", "activity_uncertain",
)
FEATURE_COUNT = len(FEATURE_NAMES)
INPUT_COUNT = FEATURE_COUNT + 1  # last row is active only for a zero-delta context
MAX_STREAMS = 16
MAX_WINDOW_MS = 1000
MAX_GAP_MS = 2000
ATTENTION_GAIN = 0.10


class AudioTemporalPredictionError(ValueError):
    pass


def _finite_number(value, name: str, *, optional: bool = False) -> float:
    if optional and value is None:
        return 0.0
    if type(value) not in (int, float):
        raise AudioTemporalPredictionError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise AudioTemporalPredictionError(f"{name} must be a finite number")
    return result


def _unit(value, name: str) -> float:
    result = _finite_number(value, name)
    if not 0.0 <= result <= 1.0:
        raise AudioTemporalPredictionError(f"{name} must be in [0, 1]")
    return result


def _scaled(value, name: str, maximum: float, *, minimum: float = 0.0) -> float:
    result = _finite_number(value, name, optional=True)
    return min(1.0, max(0.0, (result - minimum) / (maximum - minimum)))


def acoustic_feature_vector(cues: dict) -> tuple[float, ...]:
    """Map validated RAW EAR cues to a fixed 13-D, bounded, non-semantic vector."""
    if type(cues) is not dict:
        raise AudioTemporalPredictionError("cues must be a dict")
    activity = cues.get("activity_hint")
    if type(activity) is not str or activity not in ACTIVITY_HINTS:
        raise AudioTemporalPredictionError("activity_hint is not a known RAW EAR class")
    values = (
        _scaled(cues.get("f0_median_hz"), "f0_median_hz", 400.0, minimum=65.0),
        _scaled(cues.get("f0_range_hz"), "f0_range_hz", 335.0),
        _scaled(cues.get("energy_range_db"), "energy_range_db", 120.0),
        _scaled(cues.get("voiced_energy_range_db"), "voiced_energy_range_db", 120.0),
        _unit(cues.get("voiced_fraction"), "voiced_fraction"),
        _unit(cues.get("voicing_confidence"), "voicing_confidence"),
        _unit(cues.get("activity_score"), "activity_score"),
        _unit(cues.get("prosody_change_score"), "prosody_change_score"),
    )
    one_hot = tuple(1.0 if activity == item else 0.0 for item in ACTIVITY_HINTS)
    result = values + one_hot
    if len(result) != FEATURE_COUNT or any(not 0.0 <= item <= 1.0 for item in result):
        raise AudioTemporalPredictionError("acoustic feature vector is invalid")
    return result


def unavailable_prediction(status: str) -> dict:
    if type(status) is not str or not status:
        raise AudioTemporalPredictionError("status must be non-empty")
    return {
        "schema": SCHEMA,
        "method": METHOD,
        "status": status,
        "feature_count": FEATURE_COUNT,
        "parameter_count": INPUT_COUNT * FEATURE_COUNT,
        "updates": 0,
        "prediction_error_mae": None,
        "persistence_baseline_mae": None,
        "improvement_mae": None,
        "excess_prediction_error": 0.0,
        "attention_novelty": 0.0,
        "weight_scope": "EPHEMERAL_CONSENT_SCOPED_PROCESS",
        "weight_persistence": False,
        "training_data_persisted": False,
        "learning_authority": False,
        "action_authority": False,
        "truth_authority": False,
    }


class AudioTemporalPredictor:
    """Online LMS predictor of the next acoustic-cue delta from the prior delta."""

    def __init__(self, *, learning_rate: float = 0.20, warmup_updates: int = 4,
                 max_gradient_norm: float = 1.0, max_abs_weight: float = 2.0):
        if not 0.0 < learning_rate <= 0.5:
            raise AudioTemporalPredictionError("learning_rate must be in (0, 0.5]")
        if type(warmup_updates) is not int or warmup_updates < 1:
            raise AudioTemporalPredictionError("warmup_updates must be a positive int")
        if not 0.0 < max_gradient_norm <= 10.0 or not 0.0 < max_abs_weight <= 10.0:
            raise AudioTemporalPredictionError("gradient and weight bounds are invalid")
        self.learning_rate = float(learning_rate)
        self.warmup_updates = warmup_updates
        self.max_gradient_norm = float(max_gradient_norm)
        self.max_abs_weight = float(max_abs_weight)
        self._weights = [[0.0] * FEATURE_COUNT for _ in range(INPUT_COUNT)]
        self._previous: tuple[float, ...] | None = None
        self.updates = 0

    def reset(self) -> None:
        for row in self._weights:
            for index in range(FEATURE_COUNT):
                row[index] = 0.0
        self._previous = None
        self.updates = 0

    def state_dict(self) -> dict:
        """Return numeric weights only; temporal features are intentionally excluded."""
        return {"weights": [list(row) for row in self._weights], "updates": self.updates}

    def load_state_dict(self, state: dict) -> None:
        if not isinstance(state, dict) or set(state) != {"weights", "updates"}:
            raise AudioTemporalPredictionError("predictor state schema is invalid")
        weights = state.get("weights")
        updates = state.get("updates")
        if type(updates) is not int or not 0 <= updates <= 10_000_000:
            raise AudioTemporalPredictionError("predictor state update count is invalid")
        if not isinstance(weights, (list, tuple)) or len(weights) != INPUT_COUNT:
            raise AudioTemporalPredictionError("predictor state row count is invalid")
        clean = []
        for row in weights:
            if not isinstance(row, (list, tuple)) or len(row) != FEATURE_COUNT:
                raise AudioTemporalPredictionError("predictor state column count is invalid")
            values = []
            for value in row:
                if (type(value) not in (int, float) or not math.isfinite(float(value))
                        or abs(float(value)) > self.max_abs_weight):
                    raise AudioTemporalPredictionError("predictor state weight is outside its finite bound")
                values.append(float(value))
            clean.append(values)
        self._weights = clean
        self._previous = None  # restart always performs a fresh temporal warm-up
        self.updates = updates

    def _parameter_l2(self) -> float:
        return math.sqrt(sum(weight * weight for row in self._weights for weight in row))

    def update(self, target_delta) -> dict:
        if not isinstance(target_delta, (tuple, list)) or len(target_delta) != FEATURE_COUNT:
            raise AudioTemporalPredictionError("target_delta must have 13 features")
        target = tuple(_unit(value, "target_delta") for value in target_delta)
        if self._previous is None:
            self._previous = target
            result = unavailable_prediction("WARMUP_DELTA_BASELINE")
            result.update({"updates": self.updates, "parameter_l2": self._parameter_l2()})
            return result

        previous = self._previous
        inputs = list(previous) + [1.0 if not any(previous) else 0.0]
        prediction = []
        for col in range(FEATURE_COUNT):
            value = sum(inputs[row] * self._weights[row][col] for row in range(INPUT_COUNT))
            prediction.append(min(1.0, max(0.0, value)))

        model_error = sum(abs(target[i] - prediction[i]) for i in range(FEATURE_COUNT)) / FEATURE_COUNT
        baseline_error = sum(abs(target[i] - previous[i]) for i in range(FEATURE_COUNT)) / FEATURE_COUNT

        gradients = [[0.0] * FEATURE_COUNT for _ in range(INPUT_COUNT)]
        gradient_sq = 0.0
        for row in range(INPUT_COUNT):
            if inputs[row] == 0.0:
                continue
            for col in range(FEATURE_COUNT):
                gradient = 2.0 * inputs[row] * (prediction[col] - target[col]) / FEATURE_COUNT
                gradients[row][col] = gradient
                gradient_sq += gradient * gradient
        gradient_l2 = math.sqrt(gradient_sq)
        clip_scale = min(1.0, self.max_gradient_norm / max(gradient_l2, 1e-12))

        delta_sq = 0.0
        for row in range(INPUT_COUNT):
            if inputs[row] == 0.0:
                continue
            for col in range(FEATURE_COUNT):
                old = self._weights[row][col]
                new = min(self.max_abs_weight, max(-self.max_abs_weight,
                          old - self.learning_rate * gradients[row][col] * clip_scale))
                self._weights[row][col] = new
                delta_sq += (new - old) ** 2

        self._previous = target
        self.updates += 1
        surprise = max(0.0, model_error - baseline_error)
        measured = self.updates >= self.warmup_updates
        result = {
            "schema": SCHEMA,
            "method": METHOD,
            "status": "SHADOW_MEASURED" if measured else "WARMUP",
            "feature_count": FEATURE_COUNT,
            "parameter_count": INPUT_COUNT * FEATURE_COUNT,
            "updates": self.updates,
            "prediction_error_mae": round(model_error, 8),
            "persistence_baseline_mae": round(baseline_error, 8),
            "improvement_mae": round(baseline_error - model_error, 8),
            "excess_prediction_error": round(surprise, 8),
            "attention_novelty": round(min(ATTENTION_GAIN, ATTENTION_GAIN * surprise), 8) if measured else 0.0,
            "gradient_l2": round(gradient_l2, 8),
            "gradient_clip_scale": round(clip_scale, 8),
            "weight_delta_l2": round(math.sqrt(delta_sq), 8),
            "parameter_l2": round(self._parameter_l2(), 8),
            "learning_rate": self.learning_rate,
            "weight_scope": "EPHEMERAL_CONSENT_SCOPED_PROCESS",
            "weight_persistence": False,
            "training_data_persisted": False,
            "learning_authority": False,
            "action_authority": False,
            "truth_authority": False,
        }
        return result


class _StreamState:
    __slots__ = (
        "consent_scope_id", "last_start_ms", "last_end_ms",
        "previous_features", "predictor", "store_version",
    )

    def __init__(self, consent_scope_id: str, start_ms: int, end_ms: int,
                 features: tuple[float, ...], *, predictor=None, store_version=0):
        self.consent_scope_id = consent_scope_id
        self.last_start_ms = start_ms
        self.last_end_ms = end_ms
        self.previous_features = features
        self.predictor = predictor or AudioTemporalPredictor()
        self.store_version = store_version


class AudioTemporalPredictionRegistry:
    """Bounded streams; optional persistence stores numeric weights only, never audio/features."""

    PERSISTENCE_SCHEMA = "v14.raw-ear.temporal-prediction-state/1"
    PERSISTENCE_PREFIX = "raw_ear_prediction.v1."

    def __init__(self, *, max_streams: int = MAX_STREAMS, max_gap_ms: int = MAX_GAP_MS, store=None):
        if type(max_streams) is not int or not 1 <= max_streams <= 64:
            raise AudioTemporalPredictionError("max_streams must be in [1, 64]")
        if type(max_gap_ms) is not int or not 100 <= max_gap_ms <= 10000:
            raise AudioTemporalPredictionError("max_gap_ms must be in [100, 10000]")
        if store is not None and not all(callable(getattr(store, name, None)) for name in ("state", "tx")):
            raise AudioTemporalPredictionError("persistent Store lacks transactional state support")
        self.max_streams = max_streams
        self.max_gap_ms = max_gap_ms
        self._states = OrderedDict()
        self._lock = threading.RLock()
        self._store = store

    @property
    def persistent_weights_enabled(self) -> bool:
        return self._store is not None

    def _decorate(self, result: dict) -> dict:
        result["weight_persistence"] = self.persistent_weights_enabled
        result["weight_scope"] = (
            "LOCAL_STORE_NUMERIC_ONLY_CONSENT_SCOPED"
            if self.persistent_weights_enabled else "EPHEMERAL_CONSENT_SCOPED_PROCESS"
        )
        result["training_data_persisted"] = False
        return result

    @staticmethod
    def _validate_scope(value: str) -> None:
        if (type(value) is not str or len(value) != 64
                or any(char not in "0123456789abcdef" for char in value)):
            raise AudioTemporalPredictionError("consent_scope_id must be a SHA-256 hex digest")

    @staticmethod
    def _scope_hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _state_digest(payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(b"V14-RAW-EAR-PREDICTION-STATE/1\0" + raw).hexdigest()

    def _persistent_key(self, source_id: str, generation_id: str) -> tuple[str, str, str]:
        source_hash = self._scope_hash(source_id)
        generation_hash = self._scope_hash(generation_id)
        key_hash = self._scope_hash(source_id + "\0" + generation_id)
        return source_hash, generation_hash, self.PERSISTENCE_PREFIX + key_hash

    def _load_persistent(self, source_id, generation_id, consent_scope_id):
        source_hash, generation_hash, key = self._persistent_key(source_id, generation_id)
        payload, version = self._store.state(key, None)
        if payload is None:
            return None, version, "MISSING"
        if not isinstance(payload, dict):
            return None, version, "INVALID"
        material = {name: value for name, value in payload.items() if name != "state_sha256"}
        try:
            valid = (
                set(payload) == {
                    "schema", "status", "source_scope_sha256", "generation_scope_sha256",
                    "consent_scope_id", "method", "weights", "updates", "last_touched_ns", "state_sha256",
                }
                and payload.get("schema") == self.PERSISTENCE_SCHEMA
                and payload.get("status") == "ACTIVE"
                and payload.get("method") == METHOD
                and payload.get("source_scope_sha256") == source_hash
                and payload.get("generation_scope_sha256") == generation_hash
                and type(payload.get("last_touched_ns")) is int
                and payload.get("last_touched_ns") >= 0
                and payload.get("state_sha256") == self._state_digest(material)
            )
            state = {"weights": payload.get("weights"), "updates": payload.get("updates")}
            probe = AudioTemporalPredictor()
            probe.load_state_dict(state)
            valid = valid and payload.get("consent_scope_id") == consent_scope_id
        except (AudioTemporalPredictionError, TypeError, ValueError):
            valid = False
            state = None
        if not valid:
            if payload.get("consent_scope_id") != consent_scope_id:
                return None, version, "CONSENT_CHANGED"
            return None, version, "INVALID"
        return state, version, "OK"

    def _save_persistent(self, source_id, generation_id, consent_scope_id, predictor, expected_version):
        source_hash, generation_hash, key = self._persistent_key(source_id, generation_id)
        material = {
            "schema": self.PERSISTENCE_SCHEMA,
            "status": "ACTIVE",
            "source_scope_sha256": source_hash,
            "generation_scope_sha256": generation_hash,
            "consent_scope_id": consent_scope_id,
            "method": METHOD,
            "weights": predictor.state_dict()["weights"],
            "updates": predictor.updates,
            "last_touched_ns": time.time_ns(),
        }
        material["state_sha256"] = self._state_digest(material)
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self._store.tx() as connection:
            row = connection.execute("SELECT version FROM states WHERE key=?", (key,)).fetchone()
            current = row[0] if row else 0
            if current != expected_version:
                raise ValueError("Stale persistent predictor state write")
            version = current + 1
            connection.execute("INSERT OR REPLACE INTO states VALUES (?,?,?)", (key, version, encoded))
            rows = connection.execute(
                "SELECT key,payload FROM states WHERE key LIKE ?",
                (self.PERSISTENCE_PREFIX + "%",),
            ).fetchall()
            touched = []
            for row in rows:
                try:
                    saved = json.loads(row[1])
                    stamp = saved.get("last_touched_ns")
                    if type(stamp) is int and stamp >= 0:
                        touched.append((stamp, row[0]))
                except (TypeError, json.JSONDecodeError):
                    continue
            excess = max(0, len(touched) - self.max_streams)
            stale = [stale_key for _stamp, stale_key in sorted(touched) if stale_key != key][:excess]
            for stale_key in stale:
                connection.execute("DELETE FROM states WHERE key=?", (stale_key,))
        return version

    def _clear_persistent(self, source_id=None, generation_id=None):
        source_hash = self._scope_hash(source_id) if source_id is not None else None
        generation_hash = self._scope_hash(generation_id) if generation_id is not None else None
        with self._store.tx() as connection:
            rows = connection.execute(
                "SELECT key,payload FROM states WHERE key LIKE ?",
                (self.PERSISTENCE_PREFIX + "%",),
            ).fetchall()
            keys = []
            expected_key = (
                self._persistent_key(source_id, generation_id)[2]
                if source_id is not None and generation_id is not None else None
            )
            for row in rows:
                key, raw_payload = row[0], row[1]
                if expected_key is not None:
                    if key == expected_key:
                        keys.append(key)
                    continue
                try:
                    payload = json.loads(raw_payload)
                except (TypeError, json.JSONDecodeError):
                    continue
                if ((source_hash is None or payload.get("source_scope_sha256") == source_hash)
                        and (generation_hash is None or payload.get("generation_scope_sha256") == generation_hash)):
                    keys.append(key)
            for key in keys:
                connection.execute("DELETE FROM states WHERE key=?", (key,))
        return len(keys)

    def _new_state(self, source_id, generation_id, consent_scope_id, start_ms, end_ms, features):
        predictor = AudioTemporalPredictor()
        version = 0
        reset_reason = None
        if self._store is not None:
            saved, version, status = self._load_persistent(source_id, generation_id, consent_scope_id)
            if status == "OK":
                predictor.load_state_dict(saved)
            else:
                if status == "CONSENT_CHANGED":
                    reset_reason = "RESET_CONSENT_SCOPE"
                elif status == "INVALID":
                    reset_reason = "RESET_INVALID_PERSISTED_STATE"
                version = self._save_persistent(
                    source_id, generation_id, consent_scope_id, predictor, version,
                )
        return _StreamState(
            consent_scope_id, start_ms, end_ms, features,
            predictor=predictor, store_version=version,
        ), reset_reason

    def _reset_state(self, source_id, generation_id, consent_scope_id,
                     start_ms, end_ms, features, previous_version):
        predictor = AudioTemporalPredictor()
        version = previous_version
        if self._store is not None:
            version = self._save_persistent(
                source_id, generation_id, consent_scope_id, predictor, previous_version,
            )
        return _StreamState(
            consent_scope_id, start_ms, end_ms, features,
            predictor=predictor, store_version=version,
        )

    def update(self, *, source_id: str, generation_id: str, consent_scope_id: str,
               start_ms: int, end_ms: int, cues: dict, finality: str) -> dict:
        if type(source_id) is not str or not source_id.strip():
            raise AudioTemporalPredictionError("source_id must be non-empty")
        if type(generation_id) is not str or not generation_id.strip():
            raise AudioTemporalPredictionError("generation_id must be non-empty")
        self._validate_scope(consent_scope_id)
        if (type(start_ms) is not int or type(end_ms) is not int
                or start_ms < 0 or end_ms <= start_ms or end_ms - start_ms > MAX_WINDOW_MS):
            raise AudioTemporalPredictionError("audio window interval is invalid")
        if finality == "PROVISIONAL":
            return self._decorate(unavailable_prediction("PROVISIONAL_IGNORED"))
        if finality != "FINAL":
            raise AudioTemporalPredictionError("finality must be FINAL or PROVISIONAL")
        features = acoustic_feature_vector(cues)
        key = (source_id, generation_id)
        with self._lock:
            state = self._states.get(key)
            if state is not None and state.consent_scope_id != consent_scope_id:
                try:
                    state, reset_reason = self._new_state(
                        source_id, generation_id, consent_scope_id, start_ms, end_ms, features,
                    )
                except Exception:
                    return self._decorate(unavailable_prediction("PERSISTENCE_UNAVAILABLE"))
                self._states[key] = state
                self._states.move_to_end(key)
                result = unavailable_prediction(reset_reason or "RESET_CONSENT_SCOPE")
                result.update({
                    "updates": state.predictor.updates,
                    "parameter_l2": state.predictor._parameter_l2(),
                    "stream_count": len(self._states),
                })
                return self._decorate(result)

            if state is None:
                try:
                    state, reset_reason = self._new_state(
                        source_id, generation_id, consent_scope_id, start_ms, end_ms, features,
                    )
                except Exception:
                    return self._decorate(unavailable_prediction("PERSISTENCE_UNAVAILABLE"))
                self._states[key] = state
                while len(self._states) > self.max_streams:
                    _, evicted = self._states.popitem(last=False)
                    evicted.predictor.reset()
                result = unavailable_prediction(reset_reason or "WARMUP_FEATURE_BASELINE")
                result.update({
                    "updates": state.predictor.updates,
                    "parameter_l2": state.predictor._parameter_l2(),
                    "stream_count": len(self._states),
                })
                return self._decorate(result)

            if start_ms < state.last_start_ms or end_ms <= state.last_end_ms:
                try:
                    state = self._reset_state(
                        source_id, generation_id, consent_scope_id,
                        start_ms, end_ms, features, state.store_version,
                    )
                except Exception:
                    self._states.pop(key, None)
                    return self._decorate(unavailable_prediction("PERSISTENCE_WRITE_FAILED"))
                self._states[key] = state
                self._states.move_to_end(key)
                result = unavailable_prediction("RESET_CHRONOLOGY")
                result.update({"updates": 0, "stream_count": len(self._states)})
                return self._decorate(result)

            if start_ms - state.last_end_ms > self.max_gap_ms:
                try:
                    state = self._reset_state(
                        source_id, generation_id, consent_scope_id,
                        start_ms, end_ms, features, state.store_version,
                    )
                except Exception:
                    self._states.pop(key, None)
                    return self._decorate(unavailable_prediction("PERSISTENCE_WRITE_FAILED"))
                self._states[key] = state
                self._states.move_to_end(key)
                result = unavailable_prediction("RESET_GAP")
                result.update({"updates": 0, "stream_count": len(self._states)})
                return self._decorate(result)

            delta = tuple(abs(features[i] - state.previous_features[i]) for i in range(FEATURE_COUNT))
            state.previous_features = features
            state.last_start_ms = start_ms
            state.last_end_ms = end_ms
            self._states.move_to_end(key)
            result = state.predictor.update(delta)
            if self._store is not None:
                try:
                    state.store_version = self._save_persistent(
                        source_id, generation_id, consent_scope_id,
                        state.predictor, state.store_version,
                    )
                except Exception:
                    self._states.pop(key, None)
                    return self._decorate(unavailable_prediction("PERSISTENCE_WRITE_FAILED"))
            result["stream_count"] = len(self._states)
            result["window_start_ms"] = start_ms
            result["window_end_ms"] = end_ms
            return self._decorate(result)

    def reset(self, *, source_id: str | None = None,
              generation_id: str | None = None) -> int:
        with self._lock:
            keys = [key for key in self._states
                    if (source_id is None or key[0] == source_id)
                    and (generation_id is None or key[1] == generation_id)]
            for key in keys:
                state = self._states.pop(key)
                state.predictor.reset()
            cleared = (
                self._clear_persistent(source_id=source_id, generation_id=generation_id)
                if self._store is not None else 0
            )
            return max(len(keys), cleared)

    def __len__(self) -> int:
        with self._lock:
            return len(self._states)


def predictive_attention_novelty(prediction: dict) -> float:
    if type(prediction) is not dict or prediction.get("status") != "SHADOW_MEASURED":
        return 0.0
    value = _unit(prediction.get("excess_prediction_error"), "excess_prediction_error")
    return round(min(ATTENTION_GAIN, ATTENTION_GAIN * value), 8)
