"""Source-bound, optional ASR-teacher hypothesis for the RAW EAR path.

The adapter accepts a caller-supplied local teacher result; it does not load a
model, open a microphone, write PCM, persist transcript text, or grant truth,
learning, speaker-identity, or action authority. The transcript is an ephemeral
C3 hint, separate from the persistent acoustic RAW EAR packet.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata

SCHEMA = "v14.a.teacher-ear/1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LANGUAGE = re.compile(r"(?:und|[a-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3})\Z")
MAX_WORDS = 64
MAX_WORD_TEXT = 128
MAX_SUMMARY_CHARS = 512


def _clean_word(text: str) -> str:
    if type(text) is not str or not text.strip() or len(text) > MAX_WORD_TEXT:
        raise ValueError("teacher word text is invalid")
    if any(unicodedata.category(char) == "Cc" for char in text):
        raise ValueError("teacher word text contains control characters")
    return " ".join(text.split())


def _summary(language: str, words: list[dict]) -> tuple[str, bool]:
    prefix = f"teacher_hypothesis[lang={language}] "
    parts = []
    for word in words:
        token = f"{word['start_ms']}-{word['end_ms']}:{json.dumps(word['text'], ensure_ascii=False)}"
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
    start_ms: int,
    end_ms: int,
    finality: str,
    consent_active: bool,
    teacher_opt_in: bool,
    transcript_consent: bool,
) -> dict:
    """Validate a timed teacher result against the exact PCM window and lease.

    model_sha256 and the provider network_used assertion are provenance claims,
    not attestation. The result therefore remains TEACHER_HYPOTHESIS.
    """
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
    if type(source_sha256) is not str or not _SHA256.fullmatch(source_sha256):
        raise ValueError("audio source hash is invalid")
    if type(start_ms) is not int or type(end_ms) is not int or not 0 <= start_ms < end_ms:
        raise ValueError("audio interval is invalid")
    if finality not in {"FINAL", "PROVISIONAL"}:
        raise ValueError("audio finality is invalid")

    required = {
        "schema", "source_id", "generation_id", "source_sha256", "model_id",
        "model_revision", "model_sha256", "language", "start_ms", "end_ms",
        "finality", "network_used", "raw_audio_persisted", "words",
    }
    if type(value) is not dict or set(value) != required or value.get("schema") != SCHEMA:
        raise ValueError("teacher-ear schema mismatch")
    if (value["source_id"] != source_id or value["generation_id"] != generation_id
            or value["source_sha256"] != source_sha256):
        raise PermissionError("teacher result is not bound to the exact current PCM source")
    if value["start_ms"] != start_ms or value["end_ms"] != end_ms:
        raise ValueError("teacher result interval differs from the current PCM window")
    if value["finality"] != finality:
        raise ValueError("teacher finality differs from the current audio window")
    if value["network_used"] is not False or value["raw_audio_persisted"] is not False:
        raise PermissionError("teacher path must be local and must not persist raw audio")
    for key in ("model_id", "model_revision"):
        item = value[key]
        if type(item) is not str or not item.strip() or len(item) > 128:
            raise ValueError("teacher model identity is invalid")
    model_sha256 = value["model_sha256"]
    if type(model_sha256) is not str or not _SHA256.fullmatch(model_sha256):
        raise ValueError("teacher model hash is invalid")
    language = value["language"]
    if type(language) is not str or not _LANGUAGE.fullmatch(language):
        raise ValueError("teacher language tag is invalid")
    words = value["words"]
    if type(words) is not list or not 1 <= len(words) <= MAX_WORDS:
        raise ValueError("teacher word count must be in 1..64")

    clean_words = []
    previous_start = start_ms
    for item in words:
        if type(item) is not dict or set(item) != {"text", "start_ms", "end_ms", "confidence"}:
            raise ValueError("teacher word fields are invalid")
        text = _clean_word(item["text"])
        word_start, word_end = item["start_ms"], item["end_ms"]
        confidence = item["confidence"]
        if (type(word_start) is not int or type(word_end) is not int
                or not start_ms <= word_start < word_end <= end_ms
                or word_start < previous_start):
            raise ValueError("teacher word timestamps are invalid or non-monotonic")
        if (type(confidence) not in (int, float) or not math.isfinite(float(confidence))
                or not 0.0 <= float(confidence) <= 1.0):
            raise ValueError("teacher confidence must be finite and in [0,1]")
        clean_words.append({"text": text, "start_ms": word_start, "end_ms": word_end})
        previous_start = word_start

    summary, truncated = _summary(language, clean_words)
    source_seed = "\0".join((
        source_id, generation_id, source_sha256, model_sha256,
        str(start_ms), str(end_ms),
    )).encode("utf-8")
    return {
        "status": "CALLER_SUPPLIED_UNVERIFIED",
        "source_id": source_id,
        "source_sha256": source_sha256,
        "generation_id": generation_id,
        "teacher_source_id": "audio_teacher_" + hashlib.sha256(source_seed).hexdigest()[:24],
        "model_id": value["model_id"],
        "model_revision": value["model_revision"],
        "model_sha256": model_sha256,
        "model_provenance_status": "CALLER_ASSERTED_UNVERIFIED",
        "language": language,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "finality": finality,
        "word_count": len(clean_words),
        "summary": summary,
        "summary_truncated": truncated,
        "authority": "TEACHER_HYPOTHESIS",
        "truth_authority": 0,
        "persistence": "EPHEMERAL_ONLY",
        "network_used": False,
        "raw_audio_persisted": False,
        "learning_authority": False,
        "action_authority": False,
    }
