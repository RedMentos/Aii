"""Optional, source-bound sherpa-onnx teacher ear for the existing RAW EAR -> C3 path.

This adapter is additive and lazy. It never downloads a model, opens a microphone,
persists PCM/transcripts, or grants truth/learning/action authority. RAW EAR remains
the primary acoustic stream; ASR is a separately opted-in, ephemeral A2 hypothesis.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from .audio_voice_cues import AudioConsentLease
from .percept_admission import Admission, Percept, admit


SCHEMA = "v14.a.teacher-ear/2"
MODEL_ID = "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17"
MODEL_REVISION = "d42f2d9f7ca24806fb667456a18a9f1b60f70d16"
MODEL_LICENSE = "Apache-2.0"
SHERPA_ONNX_VERSION = "2.0.3"
SAMPLE_RATE = 16000
MAX_PCM_BYTES = SAMPLE_RATE * 2
MAX_MODEL_FILE_BYTES = 1 << 30
MAX_DECODE_STEPS = 4096
MAX_TOKENS = 256
MAX_WORDS = 64
MAX_WORD_TEXT = 128
MAX_SUMMARY_CHARS = 512
TIMING_METHOD = "TOKEN_STARTS_NEXT_WORD_END_INFERRED"
_SHERPA_RUNTIME_TOKEN = object()
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LANGUAGE = re.compile(r"(?:und|[a-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3})\Z")
DEFAULT_MODEL_FILES = {
    "tokens": "tokens.txt",
    "encoder": "encoder-epoch-99-avg-1.int8.onnx",
    "decoder": "decoder-epoch-99-avg-1.int8.onnx",
    "joiner": "joiner-epoch-99-avg-1.int8.onnx",
}


@dataclass(frozen=True)
class SherpaTeacherRuntime:
    recognizer: object
    model_root: Path
    model_files: dict
    manifest: dict
    sample_rate: int = SAMPLE_RATE
    runtime_version: str = "UNKNOWN"
    _token: object = field(default=None, repr=False, compare=False)


def _clean_word(value: str) -> str:
    if type(value) is not str or not value.strip() or len(value) > MAX_WORD_TEXT:
        raise ValueError("teacher word text is invalid")
    if any(unicodedata.category(char) == "Cc" for char in value):
        raise ValueError("teacher word text contains control characters")
    return " ".join(value.split())


def _secure_file_hash(root: Path, relative_path: str) -> dict:
    if type(relative_path) is not str or not relative_path or len(relative_path) > 512:
        raise ValueError("model file path is invalid")
    relative = Path(relative_path)
    if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
        raise ValueError("model file path must remain beneath the trusted model root")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if (nofollow is None or directory is None
            or os.open not in getattr(os, "supports_dir_fd", set())):
        raise RuntimeError("secure no-follow model file access is unavailable")

    root_fd = os.open(str(root), os.O_RDONLY | directory | nofollow)
    current_fd = root_fd
    file_fd = None
    try:
        for component in relative.parts[:-1]:
            next_fd = os.open(
                component, os.O_RDONLY | directory | nofollow, dir_fd=current_fd,
            )
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        file_fd = os.open(relative.parts[-1], os.O_RDONLY | nofollow, dir_fd=current_fd)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("model component must be a regular file")
        if not 0 < before.st_size <= MAX_MODEL_FILE_BYTES:
            raise ValueError("model component size is outside the allowed bound")
        digest = hashlib.sha256()
        with os.fdopen(file_fd, "rb", closefd=False) as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        after = os.fstat(file_fd)
        before_tuple = (
            before.st_dev, before.st_ino, before.st_size,
            before.st_mtime_ns, before.st_ctime_ns,
        )
        after_tuple = (
            after.st_dev, after.st_ino, after.st_size,
            after.st_mtime_ns, after.st_ctime_ns,
        )
        if before_tuple != after_tuple:
            raise ValueError("model component changed while being hashed")
        return {"sha256": digest.hexdigest(), "size_bytes": before.st_size}
    except OSError as exc:
        raise ValueError("model component is missing or unsafe") from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if current_fd != root_fd:
            os.close(current_fd)
        os.close(root_fd)


def hash_sherpa_model_files(model_root, model_files: dict | None = None) -> dict:
    """Hash the exact local Zipformer components without following file symlinks."""
    root = Path(model_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("model_root must be a directory")
    files = dict(DEFAULT_MODEL_FILES if model_files is None else model_files)
    if set(files) != {"tokens", "encoder", "decoder", "joiner"}:
        raise ValueError("model_files must name tokens, encoder, decoder and joiner")
    components = {
        key: _secure_file_hash(root, files[key])
        for key in ("tokens", "encoder", "decoder", "joiner")
    }
    manifest_body = {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "license": MODEL_LICENSE,
        "files": components,
    }
    model_sha256 = hashlib.sha256(
        json.dumps(manifest_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        **manifest_body,
        "model_sha256": model_sha256,
        "provenance_status": "LOCAL_FILES_HASHED_UNATTESTED",
    }


def _manifest_is_valid(manifest: dict) -> bool:
    if type(manifest) is not dict:
        return False
    if (manifest.get("model_id") != MODEL_ID
            or manifest.get("model_revision") != MODEL_REVISION
            or manifest.get("license") != MODEL_LICENSE
            or manifest.get("provenance_status") != "LOCAL_FILES_HASHED_UNATTESTED"):
        return False
    files = manifest.get("files")
    if type(files) is not dict or set(files) != {"tokens", "encoder", "decoder", "joiner"}:
        return False
    for item in files.values():
        if (type(item) is not dict or type(item.get("sha256")) is not str
                or not _SHA256.fullmatch(item["sha256"])
                or type(item.get("size_bytes")) is not int or item["size_bytes"] <= 0):
            return False
    body = {
        "model_id": manifest["model_id"],
        "model_revision": manifest["model_revision"],
        "license": manifest["license"],
        "files": files,
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return type(manifest.get("model_sha256")) is str and digest == manifest["model_sha256"]


def load_sherpa_teacher_runtime(
    model_root,
    *,
    model_files: dict | None = None,
    teacher_opt_in: bool,
    transcript_consent: bool,
    num_threads: int = 1,
) -> SherpaTeacherRuntime:
    """Load only an already-present local model; no package/model installation occurs."""
    if type(teacher_opt_in) is not bool or type(transcript_consent) is not bool:
        raise ValueError("teacher opt-in flags must be literal booleans")
    if teacher_opt_in is not True or transcript_consent is not True:
        raise PermissionError("local teacher inference and transcript use require separate opt-ins")
    if type(num_threads) is not int or not 1 <= num_threads <= 2:
        raise ValueError("teacher num_threads must be 1 or 2")
    root = Path(model_root).resolve(strict=True)
    files = dict(DEFAULT_MODEL_FILES if model_files is None else model_files)
    manifest_before = hash_sherpa_model_files(root, files)
    try:
        import sherpa_onnx
    except ImportError as exc:
        raise RuntimeError("optional sherpa-onnx Python runtime is not installed") from exc
    runtime_version = str(getattr(sherpa_onnx, "__version__", "UNKNOWN"))
    if runtime_version != SHERPA_ONNX_VERSION:
        raise RuntimeError(
            f"teacher adapter requires sherpa-onnx {SHERPA_ONNX_VERSION}; "
            f"found {runtime_version}"
        )
    paths = {key: str(root / files[key]) for key in files}
    recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=paths["tokens"],
        encoder=paths["encoder"],
        decoder=paths["decoder"],
        joiner=paths["joiner"],
        num_threads=num_threads,
        sample_rate=SAMPLE_RATE,
        decoding_method="greedy_search",
        provider="cpu",
    )
    manifest_after = hash_sherpa_model_files(root, files)
    if manifest_before["model_sha256"] != manifest_after["model_sha256"]:
        raise ValueError("model files changed while the teacher recognizer was loading")
    return SherpaTeacherRuntime(
        recognizer=recognizer,
        model_root=root,
        model_files=files,
        manifest=manifest_after,
        sample_rate=SAMPLE_RATE,
        runtime_version=runtime_version,
        _token=_SHERPA_RUNTIME_TOKEN,
    )


def _as_sequence(value, name: str) -> list:
    if callable(getattr(value, "tolist", None)):
        value = value.tolist()
    if type(value) not in (list, tuple):
        raise ValueError(name + " must be a sequence")
    return list(value)


def _words_from_token_starts(tokens, timestamps, *, start_ms: int, end_ms: int) -> list[dict]:
    token_list = _as_sequence(tokens, "tokens")
    time_list = _as_sequence(timestamps, "timestamps")
    if not 1 <= len(token_list) <= MAX_TOKENS or len(token_list) != len(time_list):
        raise ValueError("teacher tokens/timestamps must have equal bounded lengths")
    duration_ms = end_ms - start_ms
    groups = []
    current_text = ""
    current_start = None
    previous_token_time = -1.0
    for index, (token, timestamp) in enumerate(zip(token_list, time_list)):
        if type(token) is not str or not token or len(token) > MAX_WORD_TEXT:
            raise ValueError("teacher token is invalid")
        if any(unicodedata.category(char) == "Cc" for char in token):
            raise ValueError("teacher token contains control characters")
        if type(timestamp) not in (int, float) or not math.isfinite(float(timestamp)):
            raise ValueError("teacher token timestamp is invalid")
        token_time = float(timestamp)
        if token_time < previous_token_time or not 0.0 <= token_time < duration_ms / 1000.0:
            raise ValueError("teacher token timestamps are non-monotonic or outside the audio window")
        previous_token_time = token_time

        starts_word = index == 0 or token[:1].isspace() or token.startswith(("▁", "Ġ"))
        text = token.lstrip()
        if text.startswith(("▁", "Ġ")):
            text = text[1:]
        if starts_word:
            if current_text:
                groups.append((current_text, current_start))
            current_text = text
            current_start = token_time
        else:
            current_text += text
    if current_text:
        groups.append((current_text, current_start))
    if not groups:
        raise ValueError("teacher result contains no timestamped words")

    words = []
    previous_end = start_ms
    for index, (word_text, relative_start) in enumerate(groups):
        word_start = start_ms + int(round(relative_start * 1000.0))
        if index + 1 < len(groups):
            word_end = start_ms + int(round(groups[index + 1][1] * 1000.0))
        else:
            word_end = end_ms
        clean = _clean_word(word_text)
        if word_start < previous_end or word_end <= word_start or word_end > end_ms:
            raise ValueError("teacher word timing is empty, overlapping or outside the audio window")
        words.append({"text": clean, "start_ms": word_start, "end_ms": word_end})
        previous_end = word_end
    if len(words) > MAX_WORDS:
        raise ValueError("teacher word count exceeds the bound")
    return words


def _summary(language: str, words: list[dict]) -> tuple[str, bool]:
    prefix = f"teacher_hypothesis[lang={language}] "
    parts = []
    for word in words:
        token = (
            f"{word['start_ms']}-{word['end_ms']}:"
            f"{json.dumps(word['text'], ensure_ascii=False)}"
        )
        candidate = prefix + " ".join(parts + [token])
        if len(candidate) > MAX_SUMMARY_CHARS - 20:
            break
        parts.append(token)
    omitted = len(parts) < len(words)
    suffix = f" …(+{len(words) - len(parts)} words)" if omitted else ""
    return (prefix + " ".join(parts) + suffix)[:MAX_SUMMARY_CHARS], omitted


def validate_teacher_ear_result(
    value: dict,
    *,
    source_id: str,
    generation_id: str,
    source_sha256: str,
    model_sha256: str,
    start_ms: int,
    end_ms: int,
    finality: str,
    language: str = "en",
    consent_active: bool,
    teacher_opt_in: bool,
    transcript_consent: bool,
) -> dict:
    """Validate a local teacher result against the exact live PCM source and consent."""
    if type(consent_active) is not bool or consent_active is not True:
        raise PermissionError("current audio consent lease is required for teacher output")
    if type(teacher_opt_in) is not bool or type(transcript_consent) is not bool:
        raise ValueError("teacher opt-in flags must be literal booleans")
    if teacher_opt_in is not True or transcript_consent is not True:
        raise PermissionError("local teacher use and transcript use require separate opt-ins")
    if type(source_id) is not str or not source_id.strip() or len(source_id) > 128:
        raise ValueError("audio source id is invalid")
    if type(generation_id) is not str or not generation_id.strip() or len(generation_id) > 128:
        raise ValueError("audio generation id is invalid")
    if (type(source_sha256) is not str or type(model_sha256) is not str
            or not _SHA256.fullmatch(source_sha256) or not _SHA256.fullmatch(model_sha256)):
        raise ValueError("audio/model SHA-256 is invalid")
    if type(start_ms) is not int or type(end_ms) is not int or not 0 <= start_ms < end_ms:
        raise ValueError("audio interval is invalid")
    if finality != "FINAL":
        raise ValueError("teacher output is only admitted for FINAL audio windows")
    if type(language) is not str or not _LANGUAGE.fullmatch(language):
        raise ValueError("teacher language tag is invalid")

    required = {
        "schema", "source_id", "generation_id", "source_sha256", "model_id",
        "model_revision", "model_sha256", "language", "start_ms", "end_ms",
        "finality", "network_used", "raw_audio_persisted", "timing_method", "words",
    }
    if type(value) is not dict or set(value) != required or value.get("schema") != SCHEMA:
        raise ValueError("teacher-ear schema mismatch")
    if (value["source_id"] != source_id or value["generation_id"] != generation_id
            or value["source_sha256"] != source_sha256):
        raise PermissionError("teacher result is not bound to the exact current PCM source")
    if value["model_id"] != MODEL_ID or value["model_revision"] != MODEL_REVISION:
        raise ValueError("teacher model identity/revision is not the pinned Zipformer candidate")
    if value["model_sha256"] != model_sha256:
        raise ValueError("teacher model hash differs from the loaded local model manifest")
    if value["start_ms"] != start_ms or value["end_ms"] != end_ms:
        raise ValueError("teacher result interval differs from the current PCM window")
    if value["finality"] != finality or value["language"] != language:
        raise ValueError("teacher finality/language differs from the current audio window")
    if value["network_used"] is not False or value["raw_audio_persisted"] is not False:
        raise PermissionError("teacher path must remain local and must not persist raw audio")
    if value["timing_method"] != TIMING_METHOD:
        raise ValueError("teacher token timing method is not supported")

    words = value["words"]
    if type(words) is not list or not 1 <= len(words) <= MAX_WORDS:
        raise ValueError("teacher word count must be in 1..64")
    clean_words = []
    previous_end = start_ms
    for item in words:
        if type(item) is not dict or set(item) != {"text", "start_ms", "end_ms"}:
            raise ValueError("teacher word fields are invalid")
        text = _clean_word(item["text"])
        word_start, word_end = item["start_ms"], item["end_ms"]
        if (type(word_start) is not int or type(word_end) is not int
                or not start_ms <= word_start < word_end <= end_ms
                or word_start < previous_end):
            raise ValueError("teacher word timestamps are invalid or overlapping")
        clean_words.append({"text": text, "start_ms": word_start, "end_ms": word_end})
        previous_end = word_end

    summary, truncated = _summary(language, clean_words)
    source_seed = chr(0).join((
        source_id, generation_id, source_sha256, model_sha256,
        str(start_ms), str(end_ms),
    )).encode("utf-8")
    teacher_source_id = "audio_teacher_" + hashlib.sha256(source_seed).hexdigest()[:24]
    return {
        "status": "CALLER_SUPPLIED_UNVERIFIED",
        "source_id": source_id,
        "source_sha256": source_sha256,
        "generation_id": generation_id,
        "teacher_source_id": teacher_source_id,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_sha256": model_sha256,
        "model_provenance_status": "LOCAL_FILES_HASHED_UNATTESTED",
        "language": language,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "finality": finality,
        "word_count": len(clean_words),
        "summary": summary,
        "summary_truncated": truncated,
        "timing_method": TIMING_METHOD,
        "authority": "TEACHER_HYPOTHESIS",
        "truth_authority": 0,
        "persistence": "EPHEMERAL_ONLY",
        "network_used": False,
        "raw_audio_persisted": False,
        "learning_authority": False,
        "action_authority": False,
    }


def enrich_audio_result_with_sherpa_teacher(
    runtime,
    audio_result: dict,
    pcm16,
    *,
    teacher_runtime: SherpaTeacherRuntime,
    consent_lease: AudioConsentLease,
    teacher_opt_in: bool,
    transcript_consent: bool,
    temporal_state=None,
    vad_stream=None,
    token_budget: int = 512,
) -> dict:
    """Run an optional local teacher and add its hypothesis to the existing C3 admission."""
    if type(teacher_opt_in) is not bool or type(transcript_consent) is not bool:
        raise ValueError("teacher opt-in flags must be literal booleans")
    if teacher_opt_in is not True or transcript_consent is not True:
        return {"status": "DEFERRED_NOT_CONSENTED", "authority": "NONE"}
    if (not isinstance(teacher_runtime, SherpaTeacherRuntime)
            or teacher_runtime._token is not _SHERPA_RUNTIME_TOKEN):
        raise TypeError("teacher_runtime must come from load_sherpa_teacher_runtime")
    if not _manifest_is_valid(teacher_runtime.manifest):
        raise ValueError("teacher runtime model manifest is invalid")
    if type(token_budget) is not int or isinstance(token_budget, bool) or token_budget < 0:
        raise ValueError("token_budget must be a nonnegative integer")
    if type(audio_result) is not dict or audio_result.get("status") != "CALLER_SUPPLIED_PCM16_A5_A4_C3_ADMISSION":
        raise ValueError("audio result is not the canonical RAW EAR consumer result")

    packet = audio_result.get("packet")
    if type(packet) is not dict or packet.get("modality") != "audio":
        raise ValueError("audio PerceptPacket is missing")
    source_ref = packet.get("source_ref")
    segments = packet.get("segments")
    if type(source_ref) is not dict or type(segments) is not list or len(segments) != 1:
        raise ValueError("audio source/segment binding is invalid")
    segment = segments[0]
    if type(segment) is not dict:
        raise ValueError("audio segment is invalid")
    source_id = source_ref.get("source_id")
    source_sha256 = source_ref.get("sha256")
    generation_id = packet.get("generation_id") or packet.get("brain_generation_id")
    receipt = segment.get("consent_receipt_ref")
    start_ms, end_ms = segment.get("start_ms"), segment.get("end_ms")
    finality = segment.get("finality")
    if (type(source_id) is not str or not source_id
            or type(generation_id) is not str or not generation_id
            or type(receipt) is not str or not receipt
            or type(start_ms) is not int or type(end_ms) is not int
            or finality not in {"FINAL", "PROVISIONAL"}):
        raise ValueError("audio source/interval metadata is invalid")
    if not isinstance(consent_lease, AudioConsentLease) or not consent_lease.matches(
        runtime, source_id, generation_id, receipt,
        temporal_state=temporal_state, vad_stream=vad_stream,
        require_state=True,
    ):
        raise PermissionError("a live source-bound audio consent lease is required")
    if finality == "PROVISIONAL":
        return {"status": "DEFERRED_PROVISIONAL", "authority": "NONE"}
    if teacher_runtime.sample_rate != SAMPLE_RATE:
        raise ValueError("loaded teacher sample rate is not 16 kHz")
    if type(pcm16) not in (bytes, bytearray, memoryview):
        raise ValueError("PCM16 input must be bytes-like")
    raw = bytes(pcm16)
    if not raw or len(raw) % 2 or len(raw) > MAX_PCM_BYTES:
        raise ValueError("PCM16 input length is outside the one-second bound")
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if type(source_sha256) is not str or not _SHA256.fullmatch(source_sha256) or actual_sha256 != source_sha256:
        raise PermissionError("teacher PCM bytes differ from the source-bound PerceptPacket")
    duration_ms = len(raw) * 1000.0 / (2 * SAMPLE_RATE)
    if abs(duration_ms - (end_ms - start_ms)) > 2.0:
        raise ValueError("PCM16 duration differs from the PerceptPacket interval")

    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("NumPy is required only when the optional ASR teacher is enabled") from exc
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    manifest = teacher_runtime.manifest
    if (type(manifest) is not dict or manifest.get("model_id") != MODEL_ID
            or manifest.get("model_revision") != MODEL_REVISION
            or type(manifest.get("model_sha256")) is not str
            or not _SHA256.fullmatch(manifest["model_sha256"])):
        raise ValueError("teacher runtime model manifest is invalid")
    recognizer = teacher_runtime.recognizer
    for method in ("create_stream", "is_ready", "decode_stream", "get_result"):
        if not callable(getattr(recognizer, method, None)):
            raise TypeError("sherpa-onnx recognizer is missing a required streaming method")
    stream = recognizer.create_stream()
    stream.accept_waveform(SAMPLE_RATE, samples)
    stream.accept_waveform(
        SAMPLE_RATE, np.zeros(int(0.5 * SAMPLE_RATE), dtype=np.float32),
    )
    stream.input_finished()
    for _ in range(MAX_DECODE_STEPS):
        if not recognizer.is_ready(stream):
            break
        recognizer.decode_stream(stream)
    else:
        raise RuntimeError("sherpa-onnx decode exceeded the bounded step limit")
    result = recognizer.get_result(stream)
    if getattr(result, "is_final", True) is not True:
        raise ValueError("sherpa-onnx result is not final for the finalized PCM window")
    tokens = getattr(result, "tokens", None)
    timestamps = getattr(result, "timestamps", None)
    if timestamps is None:
        raise ValueError("sherpa-onnx model did not return token timestamps")
    words = _words_from_token_starts(
        tokens, timestamps, start_ms=start_ms, end_ms=end_ms,
    )
    model_sha256 = teacher_runtime.manifest.get("model_sha256")
    value = {
        "schema": SCHEMA,
        "source_id": source_id,
        "generation_id": generation_id,
        "source_sha256": source_sha256,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_sha256": model_sha256,
        "language": "en",
        "start_ms": start_ms,
        "end_ms": end_ms,
        "finality": finality,
        "network_used": False,
        "raw_audio_persisted": False,
        "timing_method": TIMING_METHOD,
        "words": words,
    }
    hypothesis = validate_teacher_ear_result(
        value,
        source_id=source_id,
        generation_id=generation_id,
        source_sha256=source_sha256,
        model_sha256=model_sha256,
        start_ms=start_ms,
        end_ms=end_ms,
        finality=finality,
        language="en",
        consent_active=consent_lease.active,
        teacher_opt_in=teacher_opt_in,
        transcript_consent=transcript_consent,
    )
    hypothesis["runtime_version"] = teacher_runtime.runtime_version
    hypothesis["runtime_provenance_status"] = "PYPI_WHEEL_WITHOUT_PROVENANCE"
    base = audio_result.get("c3_admission")
    if not isinstance(base, Admission):
        raise ValueError("existing RAW EAR C3 admission is missing")
    teacher_percept = Percept(
        source_id=hypothesis["teacher_source_id"],
        modality="audio",
        start_ms=start_ms,
        end_ms=end_ms,
        summary=hypothesis["summary"],
        consent=True,
        final=True,
        priority=-1,
    )
    merged = admit(base.selected + (teacher_percept,), token_budget)
    audio_result["c3_admission"] = merged
    hypothesis["c3_admission_status"] = (
        "ADMITTED" if hypothesis["teacher_source_id"] in {
            item.source_id for item in merged.selected
        } else "OMITTED_BUDGET"
    )
    audio_result["teacher_ear"] = hypothesis
    return hypothesis


__all__ = [
    "SCHEMA",
    "MODEL_ID",
    "MODEL_REVISION",
    "MODEL_LICENSE",
    "SHERPA_ONNX_VERSION",
    "SAMPLE_RATE",
    "DEFAULT_MODEL_FILES",
    "SherpaTeacherRuntime",
    "hash_sherpa_model_files",
    "load_sherpa_teacher_runtime",
    "validate_teacher_ear_result",
    "enrich_audio_result_with_sherpa_teacher",
]
