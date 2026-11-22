"""Diagnostic adapter for Microsoft FASTDIAR frame embeddings.

This is an in-memory boundary adapter only. It does not load/download weights,
decode audio, run clustering, assign identities, persist vectors, or grant
learning/action authority. FASTDIAR's repository code is MIT at v0.1.0, but
the inspected release does not state a separate checkpoint-weight license;
do not infer weight rights from the code license.

The adapter wraps an already-produced (n_frames, 192) float16 matrix into the
existing V14 RAW EAR speaker-evidence contract. It preserves the model hash and
caller-supplied frame timestamps. No confidence threshold or calibration is
attached, so the current A4 consumer must remain DEFER.
"""
from __future__ import annotations

import math
import re

from .audio_speaker_evidence import SCHEMA


MODEL_ID = "microsoft/fastdiar"
EMBEDDING_DIM = 192
FRAME_STEP_MS = 80
LOOKBACK_FRAMES = 10
MAX_FRAMES = 32
_SHA256 = re.compile(r"[0-9a-f]{64}\\Z")


def _matrix_rows(embeddings):
    tolist = getattr(embeddings, "tolist", None)
    try:
        rows = tolist() if callable(tolist) else embeddings
    except Exception as exc:
        raise ValueError("FASTDIAR embedding matrix could not be materialized") from exc
    if type(rows) not in (list, tuple) or not 1 <= len(rows) <= MAX_FRAMES:
        raise ValueError("FASTDIAR embedding matrix must contain 1..32 frames")
    result = []
    for row in rows:
        if type(row) not in (list, tuple) or len(row) != EMBEDDING_DIM:
            raise ValueError("FASTDIAR frame must contain exactly 192 values")
        vector = []
        for value in row:
            if type(value) not in (int, float):
                raise ValueError("FASTDIAR embedding values must be numeric scalars")
            number = float(value)
            if not math.isfinite(number) or abs(number) > 1.0e6:
                raise ValueError("FASTDIAR embedding contains a non-finite or out-of-range value")
            vector.append(number)
        result.append(vector)
    return result


def build_fastdiar_diagnostic_batch(
    embeddings,
    *,
    source_id: str,
    generation_id: str,
    model_revision: str,
    model_sha256: str,
    window_start_ms: int,
    window_end_ms: int,
    first_frame_end_ms: int,
) -> dict:
    """Wrap a causal FASTDIAR matrix without inventing timestamps or calibration.

    `first_frame_end_ms` is the end timestamp of the first emitted 80-ms
    embedding in this audio window. Later timestamps advance by exactly 80 ms.
    The caller must keep the FASTDIAR encoder's causal state warm across chunks
    and provide the SHA256 of the actual local checkpoint bytes.
    """
    for name, value in (("source_id", source_id), ("generation_id", generation_id),
                        ("model_revision", model_revision)):
        if type(value) is not str or not value.strip() or len(value) > 128:
            raise ValueError(f"{name} must be a non-empty string of at most 128 characters")
    if type(model_sha256) is not str or not _SHA256.fullmatch(model_sha256):
        raise ValueError("model_sha256 must be a lowercase 64-character SHA256")
    for name, value in (("window_start_ms", window_start_ms),
                        ("window_end_ms", window_end_ms),
                        ("first_frame_end_ms", first_frame_end_ms)):
        if type(value) is not int:
            raise ValueError(f"{name} must be an integer timestamp")
    if not 0 <= window_start_ms < first_frame_end_ms <= window_end_ms:
        raise ValueError("first FASTDIAR frame timestamp is outside the audio window")

    rows = _matrix_rows(embeddings)
    frames = []
    for index, vector in enumerate(rows):
        end_ms = first_frame_end_ms + index * FRAME_STEP_MS
        if end_ms > window_end_ms:
            raise ValueError("FASTDIAR frame timestamps exceed the audio window")
        frames.append({"end_ms": end_ms, "vector": vector})

    return {
        "schema": SCHEMA,
        "source_id": source_id,
        "generation_id": generation_id,
        "model_id": MODEL_ID,
        "model_revision": model_revision,
        "model_sha256": model_sha256,
        "embedding_dim": EMBEDDING_DIM,
        "frame_step_ms": FRAME_STEP_MS,
        "lookback_frames": LOOKBACK_FRAMES,
        "confidence_threshold": None,
        "calibration_id": None,
        "frames": frames,
    }


__all__ = [
    "MODEL_ID",
    "EMBEDDING_DIM",
    "FRAME_STEP_MS",
    "LOOKBACK_FRAMES",
    "build_fastdiar_diagnostic_batch",
]
