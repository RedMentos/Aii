"""Bounded source-bound speaker-similarity diagnostics from local frame embeddings.

Caller-supplied thresholds are unverified and cannot produce speaker decisions.
A separately validated, model-bound calibration artifact is required first.
This is not speaker recognition or a full diarizer. Embeddings stay in RAM;
persisted packets contain similarity evidence and provenance, never vectors.
"""
from __future__ import annotations

from array import array
from collections import OrderedDict, deque
import math
import re
import threading

from .audio_speaker_calibration import SpeakerCalibrationError, validate_calibration_artifact

SCHEMA = "v14.raw-ear-speaker-embeddings/1"
METHOD = "COSINE_LOOKBACK_DIAGNOSTIC_V1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ACTIVITY = {"SILENCE", "VOICED", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN"}


class SpeakerEvidenceError(ValueError):
    """Malformed or stale source-bound speaker embedding evidence."""


def _finite(value):
    return type(value) in (int, float) and math.isfinite(float(value))


def _unit_vector(vector, dimension):
    if not isinstance(vector, (list, tuple)) or len(vector) != dimension:
        raise SpeakerEvidenceError("speaker embedding dimension mismatch")
    values = []
    for value in vector:
        if not _finite(value) or abs(float(value)) > 1.0e6:
            raise SpeakerEvidenceError("speaker embedding contains invalid values")
        values.append(float(value))
    norm = math.sqrt(sum(value * value for value in values))
    if not math.isfinite(norm) or norm <= 1.0e-12:
        raise SpeakerEvidenceError("speaker embedding is zero or invalid")
    return array("f", (value / norm for value in values))


def _validate_batch(value, source_id, generation_id, start_ms, end_ms):
    required = {
        "schema", "source_id", "generation_id", "model_id", "model_revision",
        "model_sha256", "embedding_dim", "frame_step_ms", "lookback_frames",
        "confidence_threshold", "calibration_id", "frames",
    }
    if type(value) is not dict or set(value) != required or value.get("schema") != SCHEMA:
        raise SpeakerEvidenceError("speaker embedding schema mismatch")
    if value.get("source_id") != source_id or value.get("generation_id") != generation_id:
        raise SpeakerEvidenceError("speaker embedding source/generation mismatch")
    for key in ("model_id", "model_revision"):
        item = value.get(key)
        if type(item) is not str or not item.strip() or len(item) > 128:
            raise SpeakerEvidenceError("speaker model identity is invalid")
    digest = value.get("model_sha256")
    if type(digest) is not str or not _SHA256.fullmatch(digest.lower()):
        raise SpeakerEvidenceError("speaker model hash is invalid")
    dimension = value.get("embedding_dim")
    step_ms = value.get("frame_step_ms")
    lookback = value.get("lookback_frames")
    if type(dimension) is not int or not 2 <= dimension <= 512:
        raise SpeakerEvidenceError("speaker embedding dimension outside 2..512")
    if type(step_ms) is not int or not 20 <= step_ms <= 200:
        raise SpeakerEvidenceError("speaker frame step outside 20..200 ms")
    if type(lookback) is not int or not 1 <= lookback <= 64:
        raise SpeakerEvidenceError("speaker lookback outside 1..64 frames")
    threshold = value.get("confidence_threshold")
    calibration_id = value.get("calibration_id")
    if threshold is None:
        if calibration_id is not None:
            raise SpeakerEvidenceError("calibration id requires a confidence threshold")
    elif (not _finite(threshold) or not -1.0 <= float(threshold) <= 1.0
          or type(calibration_id) is not str or not calibration_id.strip()
          or len(calibration_id) > 128):
        raise SpeakerEvidenceError("speaker threshold/calibration binding is invalid")
    frames = value.get("frames")
    if type(frames) is not list or not 1 <= len(frames) <= 32:
        raise SpeakerEvidenceError("speaker batch must contain 1..32 frames")
    result = []
    previous = None
    tolerance = max(5, int(step_ms * 0.25))
    for frame in frames:
        if type(frame) is not dict or set(frame) != {"end_ms", "vector"}:
            raise SpeakerEvidenceError("speaker frame fields are invalid")
        end = frame.get("end_ms")
        if type(end) is not int or not start_ms < end <= end_ms:
            raise SpeakerEvidenceError("speaker frame timestamp outside audio window")
        if previous is not None and (
            end <= previous or abs((end - previous) - step_ms) > tolerance
        ):
            raise SpeakerEvidenceError("speaker frame timestamps are not monotonic at declared step")
        result.append((end, _unit_vector(frame.get("vector"), dimension)))
        previous = end
    return {
        "model_id": value["model_id"],
        "model_revision": value["model_revision"],
        "model_sha256": digest.lower(),
        "embedding_dim": dimension,
        "frame_step_ms": step_ms,
        "lookback_frames": lookback,
        "lookback_ms": step_ms * lookback,
        "confidence_threshold": None if threshold is None else float(threshold),
        "calibration_id": calibration_id,
        "frames": result,
    }


class _Stream:
    def __init__(self, metadata, max_frames):
        self.metadata = dict(metadata)
        self.frames = deque(maxlen=max_frames)
        self.last_end_ms = None


class SpeakerChangeEvidenceRegistry:
    """Bounded per-source/generation cosine look-back state; vectors remain RAM-only."""

    def __init__(self, *, max_streams=16, max_frames=128, reset_gap_ms=2000):
        if type(max_streams) is not int or not 1 <= max_streams <= 256:
            raise ValueError("max_streams must be in 1..256")
        if type(max_frames) is not int or not 16 <= max_frames <= 1024:
            raise ValueError("max_frames must be in 16..1024")
        if type(reset_gap_ms) is not int or reset_gap_ms < 0:
            raise ValueError("reset_gap_ms must be nonnegative")
        self.max_streams = max_streams
        self.max_frames = max_frames
        self.reset_gap_ms = reset_gap_ms
        self._states = OrderedDict()
        self._lock = threading.RLock()

    def update(self, *, source_id, generation_id, start_ms, end_ms,
               activity_hint, embeddings, calibration_artifact=None):
        if type(source_id) is not str or not source_id.strip() or len(source_id) > 128:
            raise SpeakerEvidenceError("speaker source id is invalid")
        if type(generation_id) is not str or not generation_id.strip() or len(generation_id) > 128:
            raise SpeakerEvidenceError("speaker generation id is invalid")
        if type(start_ms) is not int or type(end_ms) is not int or not 0 <= start_ms < end_ms:
            raise SpeakerEvidenceError("speaker window timestamps are invalid")
        if activity_hint not in _ACTIVITY:
            raise SpeakerEvidenceError("speaker activity hint is invalid")
        batch = _validate_batch(embeddings, source_id, generation_id, start_ms, end_ms)
        calibration = None
        if calibration_artifact is not None:
            try:
                calibration = validate_calibration_artifact(
                    calibration_artifact,
                    model_id=batch["model_id"],
                    model_revision=batch["model_revision"],
                    model_sha256=batch["model_sha256"],
                    embedding_dim=batch["embedding_dim"],
                    frame_step_ms=batch["frame_step_ms"],
                    lookback_frames=batch["lookback_frames"],
                )
            except SpeakerCalibrationError as exc:
                raise SpeakerEvidenceError("speaker calibration artifact is invalid") from exc
            if (batch["confidence_threshold"] is not None
                    and not math.isclose(
                        batch["confidence_threshold"], calibration["threshold"],
                        rel_tol=0.0, abs_tol=1e-8,
                    )):
                raise SpeakerEvidenceError("speaker threshold differs from the approved calibration")
            if (batch["calibration_id"] is not None
                    and batch["calibration_id"] != calibration["calibration_id"]):
                raise SpeakerEvidenceError("speaker calibration id differs from the approved artifact")

        effective_threshold = calibration["threshold"] if calibration is not None else batch["confidence_threshold"]
        effective_calibration_id = calibration["calibration_id"] if calibration is not None else batch["calibration_id"]
        calibration_receipt_sha256 = calibration["artifact_sha256"] if calibration is not None else None
        metadata = {
            "model_id": batch["model_id"],
            "model_revision": batch["model_revision"],
            "model_sha256": batch["model_sha256"],
            "embedding_dim": batch["embedding_dim"],
            "frame_step_ms": batch["frame_step_ms"],
            "lookback_frames": batch["lookback_frames"],
            "lookback_ms": batch["lookback_ms"],
            "confidence_threshold": effective_threshold,
            "calibration_id": effective_calibration_id,
            "calibration_receipt_sha256": calibration_receipt_sha256,
        }
        key = (source_id, generation_id)
        with self._lock:
            for old_key in list(self._states):
                if old_key[0] == source_id and old_key[1] != generation_id:
                    del self._states[old_key]
            state = self._states.get(key)
            reset_reason = None
            if state is None:
                state = _Stream(metadata, self.max_frames)
            elif state.metadata != metadata:
                state = _Stream(metadata, self.max_frames)
                reset_reason = "MODEL_OR_CALIBRATION_CHANGED"
            elif state.last_end_ms is not None and start_ms - state.last_end_ms > self.reset_gap_ms:
                state = _Stream(metadata, self.max_frames)
                reset_reason = "STREAM_GAP"

            latest = None
            frame_evidence = []
            candidate_count = 0
            peak_candidate_change_score = 0.0
            peak_candidate_frame_end_ms = None
            peak_candidate_reference_age_ms = None
            if self.max_frames < batch["lookback_frames"] + 2:
                raise SpeakerEvidenceError("speaker history bound is shorter than the configured lookback")
            # A batch is one publication unit. Every frame in it must compare
            # against the history that existed before this batch; otherwise a
            # later frame can compare with an earlier same-batch frame from the
            # new speaker and overwrite the cross-window change evidence.
            history = tuple(state.frames)
            last_seen_end_ms = state.last_end_ms
            tolerance = max(40, int(batch["frame_step_ms"] * 1.5))
            threshold_status = (
                "LOCAL_APPROVED_REPORT_HASH_MATCH"
                if calibration is not None else (
                    "CALLER_ASSERTED_UNVERIFIED"
                    if batch["confidence_threshold"] is not None else "NOT_CONFIGURED"
                )
            )
            for frame_end, vector in batch["frames"]:
                if last_seen_end_ms is not None and frame_end <= last_seen_end_ms:
                    raise SpeakerEvidenceError("speaker frames must advance across windows")
                target_ms = frame_end - batch["lookback_ms"]
                candidates = [
                    (abs(previous_end - target_ms), previous_end, previous_vector)
                    for previous_end, previous_vector in history
                    if previous_end < frame_end and abs(previous_end - target_ms) <= tolerance
                ]
                if candidates:
                    _, reference_end, reference_vector = min(candidates, key=lambda item: item[0])
                    similarity = max(-1.0, min(1.0, sum(a * b for a, b in zip(vector, reference_vector))))
                    threshold = effective_threshold
                    # Only a locally allowlisted, source/session/speaker-disjoint
                    # held-out report can gate a non-identifying A4 hint. The
                    # report hash is integrity, not a digital signature.
                    if calibration is None:
                        gate_passed = None
                        candidate = None
                        candidate_kind = None
                        interpretation = (
                            "SIMILARITY_ONLY_UNCALIBRATED"
                            if threshold is not None else "SIMILARITY_ONLY_NO_THRESHOLD"
                        )
                    else:
                        gate_passed = similarity >= threshold
                        candidate = not gate_passed
                        candidate_kind = "CHANGE_OR_OVERLAP" if candidate else "CONTINUITY"
                        interpretation = (
                            "LOCAL_CALIBRATION_CHANGE_OR_OVERLAP_HINT"
                            if candidate else "LOCAL_CALIBRATION_CONTINUITY_HINT"
                        )
                    change_score = round(max(0.0, min(1.0, (1.0 - similarity) * 0.5)), 6)
                    frame_record = {
                        "status": "MEASURED",
                        "frame_end_ms": frame_end,
                        "reference_age_ms": frame_end - reference_end,
                        "cosine_similarity": round(similarity, 6),
                        "change_score": change_score,
                        "confidence_threshold": threshold,
                        "threshold_status": threshold_status,
                        "confidence_gate_passed": gate_passed,
                        "speaker_change_candidate": candidate,
                        "candidate_kind": candidate_kind,
                        "interpretation": interpretation,
                    }
                    frame_evidence.append(frame_record)
                    latest = frame_record
                    if candidate is True:
                        candidate_count += 1
                        if change_score > peak_candidate_change_score:
                            peak_candidate_change_score = change_score
                            peak_candidate_frame_end_ms = frame_end
                            peak_candidate_reference_age_ms = frame_end - reference_end
                last_seen_end_ms = frame_end

            # Publish the new frames only after all comparisons used the same
            # pre-batch snapshot. The next call may then use this batch as history.
            state.frames.extend(batch["frames"])
            state.last_end_ms = batch["frames"][-1][0]

            self._states.pop(key, None)
            self._states[key] = state
            while len(self._states) > self.max_streams:
                self._states.popitem(last=False)
            if latest is None:
                latest = {
                    "status": "WARMUP",
                    "frame_end_ms": batch["frames"][-1][0],
                    "reference_age_ms": None,
                    "cosine_similarity": None,
                    "change_score": None,
                    "confidence_threshold": effective_threshold,
                    "threshold_status": threshold_status,
                    "confidence_gate_passed": None,
                    "speaker_change_candidate": None,
                    "candidate_kind": None,
                    "interpretation": "LOOKBACK_NOT_YET_AVAILABLE",
                }
            peak_candidate = None if calibration is None else candidate_count > 0
            return {
                "method": METHOD,
                "source_id": source_id,
                "generation_id": generation_id,
                "model_id": batch["model_id"],
                "model_revision": batch["model_revision"],
                "model_sha256": batch["model_sha256"],
                "embedding_dim": batch["embedding_dim"],
                "frame_step_ms": batch["frame_step_ms"],
                "lookback_frames": batch["lookback_frames"],
                "lookback_ms": batch["lookback_ms"],
                "frame_count": len(batch["frames"]),
                "threshold_status": threshold_status,
                "calibration_id": effective_calibration_id,
                "calibration_receipt_sha256": calibration_receipt_sha256,
                "confidence_threshold": effective_threshold,
                "reset_reason": reset_reason,
                **latest,
                "frame_evidence": frame_evidence,
                "candidate_count": candidate_count,
                "peak_candidate_change_score": round(peak_candidate_change_score, 6),
                "peak_candidate_frame_end_ms": peak_candidate_frame_end_ms,
                "peak_candidate_reference_age_ms": peak_candidate_reference_age_ms,
                "peak_speaker_change_candidate": peak_candidate,
                "speaker_label": None,
                "identity_authority": False,
                "learning_authority": False,
                "action_authority": False,
            }

    def reset(self, *, source_id=None, generation_id=None):
        if source_id is None and generation_id is not None:
            raise ValueError("generation_id requires source_id")
        if source_id is not None and (
            type(source_id) is not str or not source_id.strip() or len(source_id) > 128
        ):
            raise ValueError("source_id is invalid")
        if generation_id is not None and (
            type(generation_id) is not str or not generation_id.strip() or len(generation_id) > 128
        ):
            raise ValueError("generation_id is invalid")
        with self._lock:
            keys = [
                key for key in self._states
                if source_id is None or (
                    key[0] == source_id and
                    (generation_id is None or key[1] == generation_id)
                )
            ]
            for key in keys:
                del self._states[key]
            return len(keys)

    def __len__(self):
        with self._lock:
            return len(self._states)
