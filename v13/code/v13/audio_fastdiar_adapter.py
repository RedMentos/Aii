"""Diagnostic adapter for Microsoft FASTDIAR frame embeddings.

This is an in-memory boundary adapter only. It does not load/download weights,
decode audio, run clustering, assign identities, persist vectors, or grant
learning/action authority. FASTDIAR's repository code is MIT at v0.1.0, but
the inspected release does not state a separate checkpoint-weight license;
do not infer weight rights from the code license.

The adapter wraps an already-produced (n_frames, 192) float16 matrix into the
existing V14 RAW EAR speaker-evidence contract. It hashes the actual local
checkpoint file beneath a caller-trusted model root using no-follow directory
descriptors and binds the batch to the SHA-256 of the exact current PCM chunk.
The embedding producer and its prior recurrent state remain caller-supplied and
are not cryptographically attested. Frame timestamps remain caller-supplied.
No confidence threshold or calibration is attached, so A4 must remain DEFER.
"""
from __future__ import annotations

import hashlib
import math
import os
import stat
from pathlib import Path

from .audio_speaker_evidence import SCHEMA


MODEL_ID = "microsoft/fastdiar"
MODEL_REVISION = "e7f9bbccf98865216f48a04868d74f1d53c8734e"
EMBEDDING_DIM = 192
FRAME_STEP_MS = 80
LOOKBACK_FRAMES = 10
MAX_FRAMES = 32
MAX_CHECKPOINT_BYTES = 1 << 30


def _checkpoint_sha256(checkpoint_path, checkpoint_root):
    """Hash one regular checkpoint file without following path-component symlinks.

    The root is a trusted ModelManager-owned directory. The relative path is
    opened component-by-component with O_NOFOLLOW/O_DIRECTORY so a replaced
    parent or final symlink cannot redirect the hash outside that root.
    """
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory is None or os.open not in getattr(os, "supports_dir_fd", set()):
        raise ValueError("secure checkpoint path access is unavailable on this platform")

    try:
        root = Path(checkpoint_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("checkpoint root must be a directory")
        supplied = Path(checkpoint_path)
        relative = supplied.relative_to(root) if supplied.is_absolute() else supplied
        if (not relative.parts or any(part in ("", ".", "..") for part in relative.parts)
                or relative.is_absolute()):
            raise ValueError("checkpoint path must remain beneath the model root")

        root_fd = os.open(str(root), os.O_RDONLY | directory | nofollow)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("checkpoint root/path is missing or unsafe") from exc

    current_fd = root_fd
    file_fd = None
    try:
        for component in relative.parts[:-1]:
            next_fd = os.open(
                component, os.O_RDONLY | directory | nofollow, dir_fd=current_fd
            )
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd

        file_fd = os.open(
            relative.parts[-1], os.O_RDONLY | nofollow, dir_fd=current_fd
        )
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("checkpoint must be a regular file")
        if not 0 < before.st_size <= MAX_CHECKPOINT_BYTES:
            raise ValueError("checkpoint size is outside the allowed bound")

        digest = hashlib.sha256()
        with os.fdopen(file_fd, "rb", closefd=False) as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)

        after = os.fstat(file_fd)
        stable_before = (
            before.st_dev, before.st_ino, before.st_size,
            before.st_mtime_ns, before.st_ctime_ns,
        )
        stable_after = (
            after.st_dev, after.st_ino, after.st_size,
            after.st_mtime_ns, after.st_ctime_ns,
        )
        if stable_before != stable_after:
            raise ValueError("checkpoint changed while it was being hashed")
        return digest.hexdigest()
    except OSError as exc:
        raise ValueError("checkpoint path is missing or unsafe") from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if current_fd != root_fd:
            os.close(current_fd)
        os.close(root_fd)


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
    current_chunk_sha256: str,
    model_revision: str,
    checkpoint_path,
    checkpoint_root,
    window_start_ms: int,
    window_end_ms: int,
    first_frame_end_ms: int,
) -> dict:
    """Wrap a causal FASTDIAR matrix and hash the exact local checkpoint bytes.

    current_chunk_sha256 must hash the exact PCM16 chunk passed to the RAW EAR
    consumer. It does not attest the caller-supplied encoder or its prior state.
    first_frame_end_ms is the end timestamp of the first emitted 80-ms embedding;
    later timestamps advance by exactly 80 ms. The checkpoint is never changed.
    """
    for name, value in (("source_id", source_id), ("generation_id", generation_id)):
        if type(value) is not str or not value.strip() or len(value) > 128:
            raise ValueError(f"{name} must be a non-empty string of at most 128 characters")
    if model_revision != MODEL_REVISION:
        raise ValueError("model_revision must match the pinned FASTDIAR v0.1.0 commit")
    if (type(current_chunk_sha256) is not str or len(current_chunk_sha256) != 64
            or any(char not in "0123456789abcdef" for char in current_chunk_sha256)):
        raise ValueError("current_chunk_sha256 must be a lowercase SHA-256 digest")
    model_sha256 = _checkpoint_sha256(checkpoint_path, checkpoint_root)
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
        "model_revision": MODEL_REVISION,
        "model_sha256": model_sha256,
        "current_chunk_sha256": current_chunk_sha256,
        "embedding_dim": EMBEDDING_DIM,
        "frame_step_ms": FRAME_STEP_MS,
        "lookback_frames": LOOKBACK_FRAMES,
        "confidence_threshold": None,
        "calibration_id": None,
        "frames": frames,
    }


__all__ = [
    "MODEL_ID",
    "MODEL_REVISION",
    "EMBEDDING_DIM",
    "FRAME_STEP_MS",
    "LOOKBACK_FRAMES",
    "build_fastdiar_diagnostic_batch",
]
