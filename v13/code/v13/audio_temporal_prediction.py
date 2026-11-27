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
UPDATE_POLICIES = ("EVERY_FINAL", "MEMORIZED_ERROR", "TRANSIENT_CONSOLIDATE", "TRANSIENT_NO_CONSOLIDATION")
DEFAULT_MISTAKE_MEMORY_CAPACITY = 128


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
        "transient_updates": 0,
        "consolidations": 0,
        "persistent_parameter_l2": 0.0,
        "transient_parameter_l2": 0.0,
        "effective_parameter_l2": 0.0,
        "persistent_weight_delta_l2": 0.0,
        "transient_weight_delta_l2": 0.0,
        "consolidated_weight_delta_l2": 0.0,
        "consolidation_threshold": None,
        "prediction_error_mae": None,
        "persistence_baseline_mae": None,
        "improvement_mae": None,
        "excess_prediction_error": 0.0,
        "signed_prediction_error": None,
        "negative_prediction_error": None,
        "omission_prediction_error": None,
        "commission_prediction_error": None,
        "omission_attention_novelty": 0.0,
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
                 max_gradient_norm: float = 1.0, max_abs_weight: float = 2.0,
                 update_policy: str = "EVERY_FINAL",
                 mistake_memory_capacity: int = DEFAULT_MISTAKE_MEMORY_CAPACITY,
                 consolidation_threshold: float = 0.10,
                 max_transient_norm: float = 1.0):
        if not 0.0 < learning_rate <= 0.5:
            raise AudioTemporalPredictionError("learning_rate must be in (0, 0.5]")
        if type(warmup_updates) is not int or warmup_updates < 1:
            raise AudioTemporalPredictionError("warmup_updates must be a positive int")
        if not 0.0 < max_gradient_norm <= 10.0 or not 0.0 < max_abs_weight <= 10.0:
            raise AudioTemporalPredictionError("gradient and weight bounds are invalid")
        if type(update_policy) is not str or update_policy not in UPDATE_POLICIES:
            raise AudioTemporalPredictionError("update_policy is invalid")
        consolidation_threshold = _finite_number(consolidation_threshold, "consolidation_threshold")
        max_transient_norm = _finite_number(max_transient_norm, "max_transient_norm")
        if not 0.0 < consolidation_threshold <= max_transient_norm <= 10.0:
            raise AudioTemporalPredictionError("consolidation bounds must satisfy 0 < threshold <= max_transient_norm <= 10")
        if (type(mistake_memory_capacity) is not int
                or not 1 <= mistake_memory_capacity <= 4096):
            raise AudioTemporalPredictionError("mistake_memory_capacity must be in [1, 4096]")
        self.learning_rate = float(learning_rate)
        self.warmup_updates = warmup_updates
        self.max_gradient_norm = float(max_gradient_norm)
        self.max_abs_weight = float(max_abs_weight)
        self.update_policy = update_policy
        self.mistake_memory_capacity = mistake_memory_capacity
        self.consolidation_threshold = consolidation_threshold
        self.max_transient_norm = max_transient_norm
        self._mistake_keys: OrderedDict[str, None] = OrderedDict()
        self._weights = [[0.0] * FEATURE_COUNT for _ in range(INPUT_COUNT)]
        self._transient_weights = [[0.0] * FEATURE_COUNT for _ in range(INPUT_COUNT)]
        self._previous: tuple[float, ...] | None = None
        self.updates = 0
        self.transient_updates = 0
        self.consolidations = 0

    def reset(self) -> None:
        for matrix in (self._weights, self._transient_weights):
            for row in matrix:
                for index in range(FEATURE_COUNT):
                    row[index] = 0.0
        self._previous = None
        self._mistake_keys.clear()
        self.updates = 0
        self.transient_updates = 0
        self.consolidations = 0

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
        self._transient_weights = [[0.0] * FEATURE_COUNT for _ in range(INPUT_COUNT)]
        self._previous = None  # restart always performs a fresh temporal warm-up
        self._mistake_keys.clear()  # sample fingerprints are deliberately never persisted
        self.updates = updates
        self.transient_updates = 0
        self.consolidations = 0

    @staticmethod
    def _matrix_l2(matrix) -> float:
        return math.sqrt(sum(weight * weight for row in matrix for weight in row))

    def _parameter_l2(self) -> float:
        return self._matrix_l2(self._weights)

    def _transient_parameter_l2(self) -> float:
        return self._matrix_l2(self._transient_weights)

    def _effective_parameter_l2(self) -> float:
        combined = [
            [self._weights[row][col] + self._transient_weights[row][col]
             for col in range(FEATURE_COUNT)]
            for row in range(INPUT_COUNT)
        ]
        return self._matrix_l2(combined)

    @staticmethod
    def _sample_key(previous: tuple[float, ...], target: tuple[float, ...]) -> str:
        # Fingerprint the full transition, not just the target; this is not anonymisation.
        material = json.dumps(
            [[round(value, 3) for value in previous], [round(value, 3) for value in target]],
            separators=(",", ":"), allow_nan=False,
        )
        return hashlib.sha256(b"V14-A4-MISTAKE-KEY/1\\0" + material.encode("utf-8")).hexdigest()

    def _remember_mistake(self, sample_key: str) -> None:
        self._mistake_keys[sample_key] = None
        self._mistake_keys.move_to_end(sample_key)
        while len(self._mistake_keys) > self.mistake_memory_capacity:
            self._mistake_keys.popitem(last=False)

    def update(self, target_delta, *, allow_update: bool = True) -> dict:
        if type(allow_update) is not bool:
            raise AudioTemporalPredictionError("allow_update must be a bool")
        if not isinstance(target_delta, (tuple, list)) or len(target_delta) != FEATURE_COUNT:
            raise AudioTemporalPredictionError("target_delta must have 13 features")
        target = tuple(_unit(value, "target_delta") for value in target_delta)
        if self._previous is None:
            self._previous = target
            result = unavailable_prediction("WARMUP_DELTA_BASELINE")
            result.update({
                "updates": self.updates,
                "parameter_l2": self._parameter_l2(),
                "persistent_parameter_l2": self._parameter_l2(),
                "transient_parameter_l2": self._transient_parameter_l2(),
                "effective_parameter_l2": self._effective_parameter_l2(),
                "transient_updates": self.transient_updates,
                "consolidations": self.consolidations,
                "consolidation_threshold": self.consolidation_threshold,
                "update_policy": self.update_policy,
                "update_applied": False,
                "update_reason": "WARMUP_BASELINE",
                "mistake_memory_entries": len(self._mistake_keys),
            })
            return result

        previous = self._previous
        inputs = list(previous) + [1.0 if not any(previous) else 0.0]
        prediction = []
        for col in range(FEATURE_COUNT):
            value = sum(inputs[row] * (self._weights[row][col] + self._transient_weights[row][col])
                        for row in range(INPUT_COUNT))
            prediction.append(min(1.0, max(0.0, value)))

        signed_errors = [target[i] - prediction[i] for i in range(FEATURE_COUNT)]
        signed_error = sum(signed_errors) / FEATURE_COUNT
        omission_error = sum(max(0.0, -error) for error in signed_errors) / FEATURE_COUNT
        commission_error = sum(max(0.0, error) for error in signed_errors) / FEATURE_COUNT
        model_error = sum(abs(error) for error in signed_errors) / FEATURE_COUNT
        baseline_error = sum(abs(target[i] - previous[i]) for i in range(FEATURE_COUNT)) / FEATURE_COUNT

        sample_key = self._sample_key(previous, target)
        remembered_mistake = sample_key in self._mistake_keys
        current_mistake = model_error > baseline_error + 1e-12
        transient_policy = self.update_policy in ("TRANSIENT_CONSOLIDATE", "TRANSIENT_NO_CONSOLIDATION")
        if not allow_update:
            should_update = False
            update_reason = "EVALUATION_ONLY"
        elif self.update_policy == "EVERY_FINAL":
            should_update = True
            update_reason = "EVERY_FINAL"
        elif self.update_policy == "MEMORIZED_ERROR":
            if current_mistake:
                should_update = True
                update_reason = "CURRENT_ERROR"
                self._remember_mistake(sample_key)
            elif remembered_mistake:
                should_update = True
                update_reason = "REMEMBERED_ERROR"
            else:
                should_update = False
                update_reason = "NO_ERROR"
        else:
            should_update = True
            update_reason = (
                "TRANSIENT_ACCUMULATE" if self.update_policy == "TRANSIENT_CONSOLIDATE"
                else "TRANSIENT_ONLY_CONTROL"
            )

        gradient_l2 = 0.0
        clip_scale = 1.0
        transient_clip_scale = 1.0
        delta_sq = 0.0
        persistent_delta_sq = 0.0
        transient_delta_sq = 0.0
        consolidated = False
        if should_update:
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
            if transient_policy:
                proposed = [list(row) for row in self._transient_weights]
                for row in range(INPUT_COUNT):
                    if inputs[row] == 0.0:
                        continue
                    for col in range(FEATURE_COUNT):
                        proposed[row][col] -= self.learning_rate * gradients[row][col] * clip_scale
                proposed_norm = self._matrix_l2(proposed)
                transient_clip_scale = min(
                    1.0, self.max_transient_norm / max(proposed_norm, 1e-12),
                )
                for row in range(INPUT_COUNT):
                    for col in range(FEATURE_COUNT):
                        old = self._transient_weights[row][col]
                        candidate = proposed[row][col] * transient_clip_scale
                        effective = self._weights[row][col] + candidate
                        bounded = min(self.max_abs_weight, max(-self.max_abs_weight, effective))
                        new = bounded - self._weights[row][col]
                        self._transient_weights[row][col] = new
                        transient_delta_sq += (new - old) ** 2
                delta_sq = transient_delta_sq
                self.transient_updates += 1
                if (self.update_policy == "TRANSIENT_CONSOLIDATE"
                        and self._transient_parameter_l2() >= self.consolidation_threshold):
                    for row in range(INPUT_COUNT):
                        for col in range(FEATURE_COUNT):
                            old = self._weights[row][col]
                            new = min(
                                self.max_abs_weight,
                                max(-self.max_abs_weight, old + self._transient_weights[row][col]),
                            )
                            persistent_delta_sq += (new - old) ** 2
                            self._weights[row][col] = new
                            self._transient_weights[row][col] = 0.0
                    self.updates += 1
                    self.consolidations += 1
                    consolidated = True
                    update_reason = "TRANSIENT_CONSOLIDATED"
            else:
                for row in range(INPUT_COUNT):
                    if inputs[row] == 0.0:
                        continue
                    for col in range(FEATURE_COUNT):
                        old = self._weights[row][col]
                        new = min(self.max_abs_weight, max(-self.max_abs_weight,
                                  old - self.learning_rate * gradients[row][col] * clip_scale))
                        self._weights[row][col] = new
                        persistent_delta_sq += (new - old) ** 2
                delta_sq = persistent_delta_sq

        self._previous = target
        if should_update and not transient_policy:
            self.updates += 1
        surprise = max(0.0, model_error - baseline_error)
        measurement_updates = self.transient_updates if transient_policy else self.updates
        measured = measurement_updates >= self.warmup_updates
        result = {
            "schema": SCHEMA,
            "method": METHOD,
            "status": "SHADOW_MEASURED" if measured else "WARMUP",
            "feature_count": FEATURE_COUNT,
            "parameter_count": INPUT_COUNT * FEATURE_COUNT,
            "updates": self.updates,
            "transient_updates": self.transient_updates,
            "consolidations": self.consolidations,
            "persistent_parameter_l2": round(self._parameter_l2(), 8),
            "transient_parameter_l2": round(self._transient_parameter_l2(), 8),
            "effective_parameter_l2": round(self._effective_parameter_l2(), 8),
            "persistent_weight_delta_l2": round(math.sqrt(persistent_delta_sq), 8),
            "transient_weight_delta_l2": round(math.sqrt(transient_delta_sq), 8),
            "consolidated_weight_delta_l2": round(math.sqrt(persistent_delta_sq), 8) if consolidated else 0.0,
            "consolidation_threshold": self.consolidation_threshold,
            "transient_clip_scale": round(transient_clip_scale, 8),
            "prediction_error_mae": round(model_error, 8),
            "persistence_baseline_mae": round(baseline_error, 8),
            "improvement_mae": round(baseline_error - model_error, 8),
            "excess_prediction_error": round(surprise, 8),
            "signed_prediction_error": round(signed_error, 8),
            "negative_prediction_error": round(-omission_error, 8),
            "omission_prediction_error": round(omission_error, 8),
            "commission_prediction_error": round(commission_error, 8),
            "omission_attention_novelty": round(min(ATTENTION_GAIN, ATTENTION_GAIN * omission_error), 8) if measured else 0.0,
            "attention_novelty": round(min(ATTENTION_GAIN, ATTENTION_GAIN * surprise), 8) if measured else 0.0,
            "gradient_l2": round(gradient_l2, 8),
            "gradient_clip_scale": round(clip_scale, 8),
            "weight_delta_l2": round(math.sqrt(delta_sq), 8),
            "update_policy": self.update_policy,
            "update_applied": should_update,
            "update_reason": update_reason,
            "mistake_memory_entries": len(self._mistake_keys),
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
    """Bounded per-session temporal histories; optional persistence stores only numeric weights."""

    PERSISTENCE_SCHEMA = "v14.raw-ear.temporal-prediction-state/1"
    PERSISTENCE_PREFIX = "raw_ear_prediction.v1."

    def __init__(self, *, max_streams: int = MAX_STREAMS, max_gap_ms: int = MAX_GAP_MS, store=None,
                 update_policy: str = "EVERY_FINAL",
                 mistake_memory_capacity: int = DEFAULT_MISTAKE_MEMORY_CAPACITY,
                 consolidation_threshold: float = 0.10,
                 max_transient_norm: float = 1.0):
        if type(max_streams) is not int or not 1 <= max_streams <= 64:
            raise AudioTemporalPredictionError("max_streams must be in [1, 64]")
        if type(max_gap_ms) is not int or not 100 <= max_gap_ms <= 10000:
            raise AudioTemporalPredictionError("max_gap_ms must be in [100, 10000]")
        if store is not None and not all(callable(getattr(store, name, None)) for name in ("state", "tx")):
            raise AudioTemporalPredictionError("persistent Store lacks transactional state support")
        probe = AudioTemporalPredictor(
            update_policy=update_policy,
            mistake_memory_capacity=mistake_memory_capacity,
            consolidation_threshold=consolidation_threshold,
            max_transient_norm=max_transient_norm,
        )
        self.max_streams = max_streams
        self.max_gap_ms = max_gap_ms
        self.update_policy = probe.update_policy
        self.mistake_memory_capacity = probe.mistake_memory_capacity
        self.consolidation_threshold = probe.consolidation_threshold
        self.max_transient_norm = probe.max_transient_norm
        self._states = OrderedDict()
        self._lock = threading.RLock()
        self._store = store

    @property
    def persistent_weights_enabled(self) -> bool:
        return self._store is not None

    def _decorate(self, result: dict) -> dict:
        result.setdefault("update_policy", self.update_policy)
        result.setdefault("update_applied", False)
        result.setdefault("update_reason", result.get("status", "UNAVAILABLE"))
        result.setdefault("mistake_memory_entries", 0)
        result["weight_persistence"] = self.persistent_weights_enabled
        result["temporal_history_scope"] = "EPHEMERAL_SESSION_CONSENT_SCOPED_PROCESS"
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
        # Numeric weights intentionally remain shareable across sessions for the same
        # source/generation/consent scope; only temporal feature history is session-local.
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

    def _persistent_rows(self, connection):
        """Select only exact predictor keys; SQL LIKE would treat '_' in the prefix as wildcards."""
        prefix = self.PERSISTENCE_PREFIX
        return connection.execute(
            "SELECT key,payload FROM states WHERE substr(key,1,?)=?",
            (len(prefix), prefix),
        ).fetchall()

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
            rows = self._persistent_rows(connection)
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
            rows = self._persistent_rows(connection)
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
        predictor = AudioTemporalPredictor(
            update_policy=self.update_policy,
            mistake_memory_capacity=self.mistake_memory_capacity,
            consolidation_threshold=self.consolidation_threshold,
            max_transient_norm=self.max_transient_norm,
        )
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
        predictor = AudioTemporalPredictor(
            update_policy=self.update_policy,
            mistake_memory_capacity=self.mistake_memory_capacity,
            consolidation_threshold=self.consolidation_threshold,
            max_transient_norm=self.max_transient_norm,
        )
        version = previous_version
        if self._store is not None:
            version = self._save_persistent(
                source_id, generation_id, consent_scope_id, predictor, previous_version,
            )
        return _StreamState(
            consent_scope_id, start_ms, end_ms, features,
            predictor=predictor, store_version=version,
        )

    def update(self, *, source_id: str, generation_id: str, session_id: str,
               consent_scope_id: str, start_ms: int, end_ms: int,
               cues: dict, finality: str) -> dict:
        if type(source_id) is not str or not source_id.strip():
            raise AudioTemporalPredictionError("source_id must be non-empty")
        if type(generation_id) is not str or not generation_id.strip():
            raise AudioTemporalPredictionError("generation_id must be non-empty")
        if type(session_id) is not str or not session_id.strip():
            raise AudioTemporalPredictionError("session_id must be non-empty")
        self._validate_scope(consent_scope_id)
        if (type(start_ms) is not int or type(end_ms) is not int
                or start_ms < 0 or end_ms <= start_ms or end_ms - start_ms > MAX_WINDOW_MS):
            raise AudioTemporalPredictionError("audio window interval is invalid")
        if finality == "PROVISIONAL":
            return self._decorate(unavailable_prediction("PROVISIONAL_IGNORED"))
        if finality != "FINAL":
            raise AudioTemporalPredictionError("finality must be FINAL or PROVISIONAL")
        features = acoustic_feature_vector(cues)
        key = (source_id, generation_id, session_id)
        with self._lock:
            # A consent rotation invalidates every in-memory session history for this
            # source/generation, not just the currently active session key.
            stale_keys = [
                existing_key for existing_key, existing_state in self._states.items()
                if existing_key[:2] == (source_id, generation_id)
                and existing_state.consent_scope_id != consent_scope_id
            ]
            for stale_key in stale_keys:
                stale_state = self._states.pop(stale_key)
                stale_state.predictor.reset()
            consent_scope_reset = bool(stale_keys)
            state = self._states.get(key)
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
                result = unavailable_prediction(
                    reset_reason or ("RESET_CONSENT_SCOPE" if consent_scope_reset else "WARMUP_FEATURE_BASELINE")
                )
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
              generation_id: str | None = None,
              session_id: str | None = None) -> int:
        if session_id is not None and (type(session_id) is not str or not session_id.strip()):
            raise AudioTemporalPredictionError("session_id must be a non-empty string when supplied")
        with self._lock:
            keys = [key for key in self._states
                    if (source_id is None or key[0] == source_id)
                    and (generation_id is None or key[1] == generation_id)
                    and (session_id is None or key[2] == session_id)]
            for key in keys:
                state = self._states.pop(key)
                state.predictor.reset()
            # A session-only reset clears ephemeral history, not source/generation weights.
            cleared = (
                self._clear_persistent(source_id=source_id, generation_id=generation_id)
                if self._store is not None and session_id is None else 0
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


def predictive_omission_novelty(prediction: dict) -> float:
    """Capped A4 salience for a predicted acoustic change that did not occur."""
    if type(prediction) is not dict or prediction.get("status") != "SHADOW_MEASURED":
        return 0.0
    value = _unit(prediction.get("omission_prediction_error"), "omission_prediction_error")
    return round(min(ATTENTION_GAIN, ATTENTION_GAIN * value), 8)
