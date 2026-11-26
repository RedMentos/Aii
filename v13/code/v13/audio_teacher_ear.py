"""Consent-separated, source-bound optional RAW EAR teacher transcript adapter.

This module never captures audio, loads a model, persists transcript text, or
grants learning/action authority. A caller may supply a teacher hypothesis only
while a distinct teacher-use AND transcript-use provider lease is held.
"""
from contextlib import contextmanager
import hashlib
import json
import re
import threading
import unicodedata


_SCHEMA = "v14.raw-ear-teacher-result/1"
_TOKEN = object()
_LANGUAGE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class TeacherEarConsentLease:
    """Ephemeral thread-bound lease for two distinct teacher/transcript grants."""

    __slots__ = (
        "_token", "source_id", "generation_id", "teacher_receipt",
        "transcript_receipt", "_active", "_thread_id",
    )

    def __init__(
        self, source_id, generation_id, teacher_receipt, transcript_receipt,
        *, _token=None,
    ):
        if _token is not _TOKEN:
            raise PermissionError("TeacherEarConsentLease must be provider-created")
        self._token = _token
        self.source_id = source_id
        self.generation_id = generation_id
        self.teacher_receipt = teacher_receipt
        self.transcript_receipt = transcript_receipt
        self._active = True
        self._thread_id = threading.get_ident()

    @property
    def active(self):
        return self._active is True

    def matches(self, source_id, generation_id, teacher_receipt, transcript_receipt):
        return bool(
            self._token is _TOKEN
            and self._active is True
            and self._thread_id == threading.get_ident()
            and self.source_id == source_id
            and self.generation_id == generation_id
            and self.teacher_receipt == teacher_receipt
            and self.transcript_receipt == transcript_receipt
            and teacher_receipt != transcript_receipt
        )

    def __repr__(self):
        return "<TeacherEarConsentLease active=%s>" % self.active

    def __reduce__(self):
        raise TypeError("TeacherEarConsentLease is ephemeral and cannot be serialized")

    def __copy__(self):
        raise TypeError("TeacherEarConsentLease cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("TeacherEarConsentLease cannot be copied")


@contextmanager
def teacher_ear_consent_lease(
    source_id, generation_id, teacher_receipt, transcript_receipt,
    consent_check, consent_guard,
):
    """Hold both distinct opt-ins for the complete Runtime generation.

    The provider's guard must atomically cover both receipt scopes and use the
    same synchronization primitive as revocation. It must yield literal True
    only while BOTH grants remain active. The Runtime must register its
    two-phase revocation subscription before entering this context.
    """
    for name, value, limit in (
        ("source_id", source_id, 128),
        ("generation_id", generation_id, 128),
        ("teacher_receipt", teacher_receipt, 256),
        ("transcript_receipt", transcript_receipt, 256),
    ):
        if type(value) is not str or not value.strip() or len(value) > limit:
            raise PermissionError("separate teacher/transcript consent scope is invalid")
    if teacher_receipt == transcript_receipt:
        raise PermissionError("teacher-use and transcript-use require distinct receipts")
    if not callable(consent_check) or not callable(consent_guard):
        raise PermissionError("separate teacher and transcript consent provider is required")
    try:
        if consent_check(source_id, teacher_receipt, transcript_receipt) is not True:
            raise PermissionError("teacher/transcript consent is not current")
        manager = consent_guard(source_id, teacher_receipt, transcript_receipt)
    except Exception as exc:
        if isinstance(exc, PermissionError):
            raise
        raise PermissionError("teacher/transcript consent preflight failed") from None
    if not hasattr(manager, "__enter__") or not hasattr(manager, "__exit__"):
        raise PermissionError("teacher/transcript consent guard must return a context manager")
    with manager as active:
        if active is not True:
            raise PermissionError("teacher/transcript consent lease is not active")
        lease = TeacherEarConsentLease(
            source_id, generation_id, teacher_receipt, transcript_receipt,
            _token=_TOKEN,
        )
        try:
            yield lease
        finally:
            lease._active = False


def validate_teacher_ear_result(
    value, *, source_id, generation_id, source_sha256, start_ms, end_ms,
    finality, teacher_receipt, transcript_receipt, teacher_lease,
):
    """Validate a caller-supplied ASR hypothesis against a live two-scope lease.

    The returned summary is ephemeral. Callers must not put it in PerceptPacket,
    Store, replay, logs, memory, or the persistent Context OS. It may be added
    only to the active C3 dispatch copy after persistent context has been saved.
    """
    if not isinstance(teacher_lease, TeacherEarConsentLease) or not teacher_lease.matches(
        source_id, generation_id, teacher_receipt, transcript_receipt,
    ):
        raise PermissionError("a live separate teacher/transcript lease is required")
    if type(source_sha256) is not str or not _SHA256.fullmatch(source_sha256):
        raise ValueError("audio source SHA-256 is invalid")
    if type(start_ms) is not int or type(end_ms) is not int or start_ms < 0 or end_ms <= start_ms:
        raise ValueError("audio interval is invalid")
    if end_ms - start_ms > 1000:
        raise ValueError("teacher result exceeds the one-second audio window")
    if type(finality) is not str or finality not in ("FINAL", "PROVISIONAL"):
        raise ValueError("audio finality is invalid")
    if type(value) is not dict:
        raise ValueError("teacher result must be an object")

    required = {
        "schema", "source_id", "generation_id", "source_sha256", "start_ms",
        "end_ms", "finality", "model_id", "model_revision", "model_sha256",
        "language", "words", "network_used", "raw_audio_persisted",
    }
    if set(value) != required or value.get("schema") != _SCHEMA:
        raise ValueError("teacher result schema is not exact")
    if (
        value["source_id"] != source_id
        or value["generation_id"] != generation_id
        or value["source_sha256"] != source_sha256
        or value["start_ms"] != start_ms
        or value["end_ms"] != end_ms
        or value["finality"] != finality
    ):
        raise ValueError("teacher result does not match the exact audio source/window")
    if value["network_used"] is not False or value["raw_audio_persisted"] is not False:
        raise PermissionError("teacher result must be local and non-persistent")
    if (
        type(value["model_id"]) is not str or not value["model_id"].strip()
        or len(value["model_id"]) > 96
        or type(value["model_revision"]) is not str or not value["model_revision"].strip()
        or len(value["model_revision"]) > 96
        or type(value["model_sha256"]) is not str
        or not _SHA256.fullmatch(value["model_sha256"])
    ):
        raise ValueError("teacher model provenance is incomplete")
    if type(value["language"]) is not str or not _LANGUAGE.fullmatch(value["language"]):
        raise ValueError("teacher language tag is invalid")
    words = value["words"]
    if type(words) is not list or len(words) > 64:
        raise ValueError("teacher words must be a bounded list")

    rendered = []
    previous_start = start_ms
    for word in words:
        if type(word) is not dict or set(word) != {"start_ms", "end_ms", "text"}:
            raise ValueError("teacher word record schema is not exact")
        word_start = word["start_ms"]
        word_end = word["end_ms"]
        text = word["text"]
        if (
            type(word_start) is not int or type(word_end) is not int
            or word_start < start_ms or word_end <= word_start
            or word_end > end_ms or word_start < previous_start
            or type(text) is not str or not text or len(text) > 128
        ):
            raise ValueError("teacher word timestamp/text is invalid")
        normalized = unicodedata.normalize("NFKC", text)
        if any(unicodedata.category(char).startswith("C") for char in normalized):
            raise ValueError("teacher word contains control characters")
        normalized = " ".join(normalized.split())
        if not normalized:
            raise ValueError("teacher word is empty after normalization")
        rendered.append("%d-%dms:%s" % (word_start, word_end, normalized))
        previous_start = word_start

    summary = " ".join(rendered)
    if len(summary) > 512:
        raise ValueError("teacher summary exceeds the ephemeral prompt budget")
    teacher_source_id = "teacher-" + hashlib.sha256(
        json.dumps(
            {
                "source_id": source_id,
                "generation_id": generation_id,
                "source_sha256": source_sha256,
                "model_sha256": value["model_sha256"],
                "start_ms": start_ms,
                "end_ms": end_ms,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:24]
    return {
        "status": "CALLER_SUPPLIED_UNVERIFIED",
        "authority": "TEACHER_HYPOTHESIS",
        "learning_authority": False,
        "action_authority": False,
        "persistence": "EPHEMERAL_ONLY",
        "raw_audio_persisted": False,
        "network_used": False,
        "teacher_source_id": teacher_source_id,
        "source_id": source_id,
        "generation_id": generation_id,
        "source_sha256": source_sha256,
        "model_id": value["model_id"],
        "model_revision": value["model_revision"],
        "model_sha256": value["model_sha256"],
        "language": value["language"],
        "finality": finality,
        "word_count": len(rendered),
        "summary": summary,
    }
