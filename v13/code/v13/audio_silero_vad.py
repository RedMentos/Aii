"""Optional, source-local Silero VAD v5/v6 ONNX streaming adapter.

No download, microphone capture, ASR, speaker identification, or persistent PCM.
The caller must provide a local model file and its expected SHA-256 explicitly.
The adapter is deliberately 16 kHz mono PCM16 and serial per stream.
"""
from __future__ import annotations

import hashlib
import importlib
import math
import re
import threading
from pathlib import Path

from .audio_pcm_memory import pcm16_byte_view

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_MODEL_BYTES = 10 * 1024 * 1024
_MAX_WINDOW_BYTES = 16000 * 2


def validate_vad_evidence(evidence: dict) -> dict:
    """Validate the bounded, source-free summary emitted by one VAD window."""
    required = {
        "method", "model_revision", "model_sha256", "sample_rate", "frame_ms",
        "frame_count", "speech_fraction", "mean_score", "max_score", "threshold",
        "speech_detected", "covered_ms", "pending_samples", "state_reset_reason",
        "first_frame_start_ms", "last_frame_end_ms",
    }
    if type(evidence) is not dict or set(evidence) != required:
        raise ValueError("Silero VAD evidence fields are invalid")
    if evidence["method"] != "SILERO_VAD_ONNX":
        raise ValueError("Silero VAD method is invalid")
    revision = evidence["model_revision"]
    if type(revision) is not str or not revision.strip() or len(revision) > 128:
        raise ValueError("Silero VAD model revision is invalid")
    digest = evidence["model_sha256"]
    if type(digest) is not str or not _SHA256.fullmatch(digest):
        raise ValueError("Silero VAD model digest is invalid")
    if evidence["sample_rate"] != 16000 or evidence["frame_ms"] != 32:
        raise ValueError("Silero VAD timing is invalid")
    count = evidence["frame_count"]
    if type(count) is not int or not 0 <= count <= 32:
        raise ValueError("Silero VAD frame count is invalid")
    for key in ("speech_fraction", "mean_score", "max_score", "threshold"):
        value = evidence[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Silero VAD score is invalid: " + key)
    if evidence["mean_score"] > evidence["max_score"] + 1e-6:
        raise ValueError("Silero VAD mean exceeds max score")
    if type(evidence["speech_detected"]) is not bool:
        raise ValueError("Silero VAD speech flag is invalid")
    if evidence["speech_detected"] != (count > 0 and evidence["speech_fraction"] > 0):
        raise ValueError("Silero VAD speech flag disagrees with frame scores")
    covered = evidence["covered_ms"]
    if type(covered) is not int or covered != count * 32:
        raise ValueError("Silero VAD coverage is invalid")
    pending = evidence["pending_samples"]
    if type(pending) is not int or not 0 <= pending < 512:
        raise ValueError("Silero VAD pending sample count is invalid")
    reason = evidence["state_reset_reason"]
    if reason is not None and reason not in {"NEW_STREAM", "STREAM_CHANGED", "TIME_DISCONTINUITY"}:
        raise ValueError("Silero VAD reset reason is invalid")
    first, last = evidence["first_frame_start_ms"], evidence["last_frame_end_ms"]
    if count == 0:
        if first is not None or last is not None or evidence["speech_fraction"] != 0:
            raise ValueError("empty Silero VAD window has frame evidence")
    else:
        if type(first) is not int or type(last) is not int or last - first != covered:
            raise ValueError("Silero VAD frame timestamps are invalid")
    return dict(evidence)


class SileroVADStream:
    """Stateful 16 kHz Silero ONNX stream with a <32 ms bounded PCM tail."""

    FRAME_SAMPLES = 512
    CONTEXT_SAMPLES = 64
    FRAME_MS = 32
    STATE_SHAPE = (2, 1, 128)

    def __init__(self, session, *, model_sha256: str, model_revision: str,
                 threshold: float = 0.5, numpy_module=None):
        if not callable(getattr(session, "run", None)):
            raise ValueError("ONNX session must expose run()")
        if type(model_sha256) is not str or not _SHA256.fullmatch(model_sha256):
            raise ValueError("expected model SHA-256 is required")
        if type(model_revision) is not str or not model_revision.strip() or len(model_revision) > 128:
            raise ValueError("model revision is required")
        if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 < threshold < 1:
            raise ValueError("threshold must be finite and in (0, 1)")
        self._np = numpy_module or importlib.import_module("numpy")
        self._session = session
        self.model_sha256 = model_sha256
        self.model_revision = model_revision
        self.threshold = float(threshold)
        self._lock = threading.RLock()
        self._reset_locked(clear_stream=True)

    @classmethod
    def from_onnx(cls, model_path, *, expected_sha256: str, model_revision: str,
                  threshold: float = 0.5):
        """Load only an explicitly supplied local ONNX file; never fetch or update it."""
        path = Path(model_path)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Silero ONNX model must be a regular local file, not a symlink")
        size = path.stat().st_size
        if not 1 <= size <= _MAX_MODEL_BYTES:
            raise ValueError("Silero ONNX model size is outside the 1..10 MiB bound")
        if type(expected_sha256) is not str or not _SHA256.fullmatch(expected_sha256):
            raise ValueError("expected model SHA-256 is required")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError("Silero ONNX model SHA-256 mismatch")

        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("onnxruntime is not installed; no model was downloaded") from exc
        if "CPUExecutionProvider" not in ort.get_available_providers():
            raise RuntimeError("ONNX Runtime CPUExecutionProvider is unavailable")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        if hasattr(ort, "ExecutionMode"):
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        input_names = {item.name for item in session.get_inputs()}
        if not {"input", "state", "sr"}.issubset(input_names):
            raise ValueError("ONNX model does not expose the expected Silero input contract")
        if len(session.get_outputs()) != 2:
            raise ValueError("ONNX model does not expose the expected Silero output contract")
        return cls(
            session, model_sha256=actual_sha256,
            model_revision=model_revision, threshold=threshold,
        )

    def _reset_locked(self, *, clear_stream: bool):
        np = self._np
        # Revoke retained PCM context before dropping references to old arrays.
        for buffer in (getattr(self, "_state", None),
                       getattr(self, "_context", None),
                       getattr(self, "_pending", None)):
            if hasattr(buffer, "fill"):
                buffer.fill(0)
        self._state = np.zeros(self.STATE_SHAPE, dtype=np.float32)
        self._context = np.zeros((1, self.CONTEXT_SAMPLES), dtype=np.float32)
        self._pending = np.zeros((0,), dtype=np.float32)
        self._pending_start_ms = None
        if clear_stream:
            self._stream_id = None
            self._next_start_ms = None

    def reset(self):
        """Discard recurrent state and any incomplete PCM frame."""
        with self._lock:
            self._reset_locked(clear_stream=True)

    @property
    def pending_samples(self) -> int:
        with self._lock:
            return int(self._pending.shape[0])

    def _run_frame(self, frame):
        np = self._np
        model_input = np.concatenate((self._context[0], frame)).astype(np.float32, copy=False)
        model_input = model_input.reshape(1, self.CONTEXT_SAMPLES + self.FRAME_SAMPLES)
        state_input = self._state.copy()
        scores = state = None
        try:
            outputs = self._session.run(None, {
                "input": model_input,
                "state": state_input,
                "sr": np.asarray(16000, dtype=np.int64),
            })
            if not isinstance(outputs, (tuple, list)) or len(outputs) != 2:
                raise RuntimeError("Silero ONNX session returned an invalid output tuple")
            scores = np.asarray(outputs[0], dtype=np.float32).reshape(-1)
            state = np.asarray(outputs[1], dtype=np.float32)
            if scores.size != 1 or not np.isfinite(scores[0]) or not 0 <= float(scores[0]) <= 1:
                raise RuntimeError("Silero ONNX session returned an invalid VAD score")
            if state.shape != self.STATE_SHAPE or not np.isfinite(state).all():
                raise RuntimeError("Silero ONNX session returned invalid recurrent state")
            next_state = state.copy()
            self._state.fill(0)
            self._state = next_state
            self._context[...] = model_input[:, -self.CONTEXT_SAMPLES:]
            return float(scores[0])
        finally:
            model_input.fill(0)
            state_input.fill(0)
            if scores is not None:
                scores.fill(0)
            if state is not None:
                state.fill(0)

    def push_pcm16(self, pcm, *, sample_rate: int, stream_id: str,
                   start_ms: int) -> dict:
        """Push <=1s of contiguous mono PCM16; clear temporary audio arrays."""
        view = pcm16_byte_view(pcm)
        if not view.nbytes:
            raise ValueError("Silero VAD input must be nonempty complete PCM16 bytes")
        if view.nbytes > _MAX_WINDOW_BYTES:
            raise ValueError("Silero VAD input is limited to one second")
        if type(sample_rate) is not int or sample_rate != 16000:
            raise ValueError("this Silero ONNX adapter requires 16000 Hz mono PCM16")
        if type(stream_id) is not str or not stream_id.strip() or len(stream_id) > 256:
            raise ValueError("stream_id is invalid")
        if type(start_ms) is not int or start_ms < 0:
            raise ValueError("start_ms must be a nonnegative integer")

        np = self._np
        samples = np.frombuffer(view, dtype="<i2").astype(np.float32) * (1.0 / 32768.0)
        combined = None
        try:
            with self._lock:
                reset_reason = None
                if self._stream_id is None:
                    self._stream_id = stream_id
                    self._next_start_ms = float(start_ms)
                    self._pending_start_ms = float(start_ms)
                    reset_reason = "NEW_STREAM"
                elif stream_id != self._stream_id:
                    self._reset_locked(clear_stream=True)
                    self._stream_id = stream_id
                    self._next_start_ms = float(start_ms)
                    self._pending_start_ms = float(start_ms)
                    reset_reason = "STREAM_CHANGED"
                elif self._next_start_ms is None or abs(float(start_ms) - self._next_start_ms) > 1.0:
                    self._reset_locked(clear_stream=False)
                    self._stream_id = stream_id
                    self._next_start_ms = float(start_ms)
                    self._pending_start_ms = float(start_ms)
                    reset_reason = "TIME_DISCONTINUITY"

                pending_start = self._pending_start_ms
                if pending_start is None:
                    pending_start = float(start_ms)
                combined = np.concatenate((self._pending, samples))
                frame_count = int(combined.shape[0] // self.FRAME_SAMPLES)
                scores = []
                first_frame_start = None
                try:
                    for index in range(frame_count):
                        frame = combined[
                            index * self.FRAME_SAMPLES:(index + 1) * self.FRAME_SAMPLES
                        ]
                        score = self._run_frame(frame)
                        scores.append(score)
                        if first_frame_start is None:
                            first_frame_start = pending_start + index * self.FRAME_MS
                    remainder_start = frame_count * self.FRAME_SAMPLES
                    next_pending = combined[remainder_start:].copy()
                    self._pending.fill(0)
                    self._pending = next_pending
                    self._pending_start_ms = (
                        pending_start + frame_count * self.FRAME_MS
                        if self._pending.shape[0] else None
                    )
                    self._next_start_ms = (
                        float(start_ms) + samples.shape[0] * 1000.0 / 16000.0
                    )
                except Exception:
                    self._reset_locked(clear_stream=True)
                    raise

                count = len(scores)
                speech_count = sum(score >= self.threshold for score in scores)
                speech_fraction = speech_count / count if count else 0.0
                mean_score = sum(scores) / count if count else 0.0
                max_score = max(scores) if scores else 0.0
                last_frame_end = (
                    int(round(first_frame_start + count * self.FRAME_MS))
                    if count and first_frame_start is not None else None
                )
                evidence = {
                    "method": "SILERO_VAD_ONNX",
                    "model_revision": self.model_revision,
                    "model_sha256": self.model_sha256,
                    "sample_rate": 16000,
                    "frame_ms": self.FRAME_MS,
                    "frame_count": count,
                    "speech_fraction": round(speech_fraction, 6),
                    "mean_score": round(mean_score, 6),
                    "max_score": round(max_score, 6),
                    "threshold": round(self.threshold, 6),
                    "speech_detected": bool(speech_count > 0),
                    "covered_ms": count * self.FRAME_MS,
                    "pending_samples": int(self._pending.shape[0]),
                    "state_reset_reason": reset_reason,
                    "first_frame_start_ms": int(round(first_frame_start)) if count else None,
                    "last_frame_end_ms": last_frame_end,
                }
                return validate_vad_evidence(evidence)
        finally:
            samples.fill(0)
            if combined is not None:
                combined.fill(0)
