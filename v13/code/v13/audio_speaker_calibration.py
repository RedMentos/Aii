"""Local, source/session/speaker-disjoint calibration for RAW EAR speaker evidence.

The artifact contains metrics and digests only; raw PCM, embeddings and speaker
labels are never written. A plain hash is integrity, not a digital signature.
The runtime remains DEFER unless a local owner-approved manifest references an
exact held-out-passing artifact bound to the active embedding model.
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path
import hashlib
import json
import math
import os
import re
import stat

SCHEMA = "v14.raw-ear-speaker-calibration/1"
MANIFEST_SCHEMA = "v14.raw-ear-speaker-calibration-manifest/1"
METHOD = "SOURCE_SESSION_SPEAKER_DISJOINT_COSINE_V1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CALIBRATION_ID = re.compile(r"[0-9a-f]{16}\Z")
_MIN_SPEAKERS = 6
_MIN_PAIRS = 20
_MAX_SAMPLES = 4096
_MAX_PAIRS = 50000
_MAX_ARTIFACT_BYTES = 65536


class SpeakerCalibrationError(ValueError):
    """Invalid, stale, or non-passing speaker calibration evidence."""


def _finite(value):
    return type(value) in (int, float) and math.isfinite(float(value))


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _normalize(vector, dimension):
    if type(vector) is not list or len(vector) != dimension:
        raise SpeakerCalibrationError("embedding dimension mismatch")
    values = []
    for value in vector:
        if not _finite(value) or abs(float(value)) > 1.0e6:
            raise SpeakerCalibrationError("embedding contains invalid values")
        values.append(float(value))
    norm = math.sqrt(sum(value * value for value in values))
    if not math.isfinite(norm) or norm <= 1.0e-12:
        raise SpeakerCalibrationError("embedding is zero or invalid")
    return tuple(value / norm for value in values)


def _rate(numerator, denominator):
    return float(numerator) / float(denominator) if denominator else 1.0


def _pair_scores(samples):
    positives, negatives = [], []
    for left, right in combinations(samples, 2):
        if left["source_id"] == right["source_id"] or left["session_id"] == right["session_id"]:
            continue
        score = max(-1.0, min(1.0, sum(a * b for a, b in zip(left["vector"], right["vector"]))))
        (positives if left["speaker_id"] == right["speaker_id"] else negatives).append(score)
    if len(positives) > _MAX_PAIRS:
        step = len(positives) / _MAX_PAIRS
        positives = [positives[int(i * step)] for i in range(_MAX_PAIRS)]
    if len(negatives) > _MAX_PAIRS:
        step = len(negatives) / _MAX_PAIRS
        negatives = [negatives[int(i * step)] for i in range(_MAX_PAIRS)]
    return positives, negatives


def _metrics(positives, negatives, threshold):
    false_accepts = sum(score >= threshold for score in negatives)
    false_rejects = sum(score < threshold for score in positives)
    far = _rate(false_accepts, len(negatives))
    frr = _rate(false_rejects, len(positives))
    return {
        "false_accept_rate": round(far, 6),
        "false_reject_rate": round(frr, 6),
        "true_accept_rate": round(1.0 - frr, 6),
        "true_reject_rate": round(1.0 - far, 6),
        "balanced_accuracy": round(((1.0 - frr) + (1.0 - far)) / 2.0, 6),
    }


def _choose_threshold(positives, negatives, max_far):
    if len(positives) < _MIN_PAIRS or len(negatives) < _MIN_PAIRS:
        raise SpeakerCalibrationError("calibration split needs at least 20 positive and 20 negative pairs")
    candidates = sorted(set(positives + negatives))
    eligible = []
    for threshold in candidates:
        metrics = _metrics(positives, negatives, threshold)
        if metrics["false_accept_rate"] <= max_far:
            eligible.append((metrics["false_reject_rate"], -threshold, threshold))
    if not eligible:
        raise SpeakerCalibrationError("no threshold meets the calibration false-accept limit")
    return min(eligible)[2]


def _validate_binding(model_id, model_revision, model_sha256, embedding_dim,
                      frame_step_ms, lookback_frames):
    for name, value in (("model_id", model_id), ("model_revision", model_revision)):
        if type(value) is not str or not value.strip() or len(value) > 128:
            raise SpeakerCalibrationError(name + " is invalid")
    if type(model_sha256) is not str or not _SHA256.fullmatch(model_sha256):
        raise SpeakerCalibrationError("model_sha256 is invalid")
    if type(embedding_dim) is not int or not 2 <= embedding_dim <= 512:
        raise SpeakerCalibrationError("embedding_dim is outside 2..512")
    if type(frame_step_ms) is not int or not 20 <= frame_step_ms <= 200:
        raise SpeakerCalibrationError("frame_step_ms is outside 20..200")
    if type(lookback_frames) is not int or not 1 <= lookback_frames <= 64:
        raise SpeakerCalibrationError("lookback_frames is outside 1..64")


def build_calibration_artifact(samples, *, model_id, model_revision, model_sha256,
                               embedding_dim, frame_step_ms, lookback_frames,
                               dataset_id, dataset_revision, dataset_license,
                               max_false_accept_rate=0.05, max_false_reject_rate=0.20,
                               dataset_kind="REAL_LOCAL"):
    """Build a model-bound report from caller-supplied embeddings and opaque labels.

    Speaker identities are deterministically split before pair scoring. Both the
    speaker IDs and all source/session IDs must be disjoint across calibration and
    held-out partitions. The returned artifact is runtime-eligible only for a
    REAL_LOCAL dataset and only after it is added to the local approved manifest.
    """
    _validate_binding(model_id, model_revision, model_sha256, embedding_dim,
                      frame_step_ms, lookback_frames)
    if not _finite(max_false_accept_rate) or not 0 < float(max_false_accept_rate) < 0.5:
        raise SpeakerCalibrationError("max_false_accept_rate must be in (0, 0.5)")
    if not _finite(max_false_reject_rate) or not 0 < float(max_false_reject_rate) < 0.5:
        raise SpeakerCalibrationError("max_false_reject_rate must be in (0, 0.5)")
    if dataset_kind not in {"REAL_LOCAL", "SYNTHETIC_TEST"}:
        raise SpeakerCalibrationError("dataset_kind is invalid")
    for name, value in (("dataset_id", dataset_id), ("dataset_revision", dataset_revision),
                        ("dataset_license", dataset_license)):
        if type(value) is not str or not value.strip() or len(value) > 256 or value.strip().upper() == "UNKNOWN":
            raise SpeakerCalibrationError(name + " must be explicit and non-empty")
    if type(samples) is not list or not 1 <= len(samples) <= _MAX_SAMPLES:
        raise SpeakerCalibrationError("samples must contain 1..4096 utterances")

    parsed, sample_ids = [], set()
    required = {"sample_id", "source_id", "session_id", "speaker_id", "vector"}
    for item in samples:
        if type(item) is not dict or set(item) != required:
            raise SpeakerCalibrationError("sample fields are invalid")
        for name in ("sample_id", "source_id", "session_id", "speaker_id"):
            value = item[name]
            if type(value) is not str or not value.strip() or len(value) > 128:
                raise SpeakerCalibrationError(name + " is invalid")
        if item["sample_id"] in sample_ids:
            raise SpeakerCalibrationError("duplicate sample_id")
        sample_ids.add(item["sample_id"])
        parsed.append({
            "sample_id": item["sample_id"],
            "source_id": item["source_id"],
            "session_id": item["session_id"],
            "speaker_id": item["speaker_id"],
            "vector": _normalize(item["vector"], embedding_dim),
        })

    speakers = sorted({item["speaker_id"] for item in parsed},
                       key=lambda value: hashlib.sha256(("v14-speaker-split-v1:" + value).encode()).hexdigest())
    if len(speakers) < _MIN_SPEAKERS:
        raise SpeakerCalibrationError("at least six distinct speakers are required")
    split_at = len(speakers) // 2
    calibration_speakers = set(speakers[:split_at])
    heldout_speakers = set(speakers[split_at:])
    if len(calibration_speakers) < 3 or len(heldout_speakers) < 3:
        raise SpeakerCalibrationError("each split needs at least three speakers")

    calibration = [item for item in parsed if item["speaker_id"] in calibration_speakers]
    heldout = [item for item in parsed if item["speaker_id"] in heldout_speakers]
    cal_sources = {item["source_id"] for item in calibration}
    test_sources = {item["source_id"] for item in heldout}
    cal_sessions = {item["session_id"] for item in calibration}
    test_sessions = {item["session_id"] for item in heldout}
    if cal_sources & test_sources or cal_sessions & test_sessions:
        raise SpeakerCalibrationError("source/session leakage across calibration and holdout")

    for split_name, split, split_speakers in (
        ("calibration", calibration, calibration_speakers),
        ("heldout", heldout, heldout_speakers),
    ):
        for speaker in split_speakers:
            rows = [item for item in split if item["speaker_id"] == speaker]
            if len({item["source_id"] for item in rows}) < 2 or len({item["session_id"] for item in rows}) < 2:
                raise SpeakerCalibrationError(split_name + " speaker needs at least two sources and sessions")

    cal_pos, cal_neg = _pair_scores(calibration)
    held_pos, held_neg = _pair_scores(heldout)
    if min(len(held_pos), len(held_neg)) < _MIN_PAIRS:
        raise SpeakerCalibrationError("held-out split needs at least 20 positive and 20 negative pairs")
    threshold = _choose_threshold(cal_pos, cal_neg, float(max_false_accept_rate))
    heldout_metrics = _metrics(held_pos, held_neg, threshold)
    status = ("HELDOUT_PASS"
              if heldout_metrics["false_accept_rate"] <= float(max_false_accept_rate)
              and heldout_metrics["false_reject_rate"] <= float(max_false_reject_rate)
              else "HELDOUT_FAIL")

    manifest = sorted((item["sample_id"], item["source_id"], item["session_id"], item["speaker_id"])
                      for item in parsed)
    artifact = {
        "schema": SCHEMA,
        "method": METHOD,
        "dataset_kind": dataset_kind,
        "dataset_id": dataset_id,
        "dataset_revision": dataset_revision,
        "dataset_license": dataset_license,
        "model_id": model_id,
        "model_revision": model_revision,
        "model_sha256": model_sha256,
        "embedding_dim": embedding_dim,
        "frame_step_ms": frame_step_ms,
        "lookback_frames": lookback_frames,
        "source_disjoint": True,
        "session_disjoint": True,
        "speaker_disjoint": True,
        "manifest_sha256": hashlib.sha256(_canonical(manifest)).hexdigest(),
        "calibration_speaker_count": len(calibration_speakers),
        "heldout_speaker_count": len(heldout_speakers),
        "calibration_positive_pairs": len(cal_pos),
        "calibration_negative_pairs": len(cal_neg),
        "heldout_positive_pairs": len(held_pos),
        "heldout_negative_pairs": len(held_neg),
        "max_false_accept_rate": float(max_false_accept_rate),
        "max_false_reject_rate": float(max_false_reject_rate),
        "threshold": round(float(threshold), 8),
        "heldout_metrics": heldout_metrics,
        "status": status,
    }
    digest = _digest(artifact)
    artifact["calibration_id"] = digest[:16]
    artifact["artifact_sha256"] = digest
    return artifact


def validate_calibration_artifact(artifact, *, model_id, model_revision, model_sha256,
                                  embedding_dim, frame_step_ms, lookback_frames):
    """Validate a report and exact model/temporal binding; never accepts synthetic reports."""
    required = {
        "schema", "method", "dataset_kind", "dataset_id", "dataset_revision", "dataset_license",
        "model_id", "model_revision", "model_sha256",
        "embedding_dim", "frame_step_ms", "lookback_frames", "source_disjoint", "session_disjoint",
        "speaker_disjoint", "manifest_sha256", "calibration_speaker_count", "heldout_speaker_count",
        "calibration_positive_pairs", "calibration_negative_pairs", "heldout_positive_pairs",
        "heldout_negative_pairs", "max_false_accept_rate", "max_false_reject_rate", "threshold",
        "heldout_metrics", "status", "calibration_id", "artifact_sha256",
    }
    if type(artifact) is not dict or set(artifact) != required:
        raise SpeakerCalibrationError("calibration artifact fields are invalid")
    _validate_binding(model_id, model_revision, model_sha256, embedding_dim, frame_step_ms, lookback_frames)
    if artifact["schema"] != SCHEMA or artifact["method"] != METHOD:
        raise SpeakerCalibrationError("calibration artifact schema/method mismatch")
    if artifact["dataset_kind"] != "REAL_LOCAL" or artifact["status"] != "HELDOUT_PASS":
        raise SpeakerCalibrationError("only real-local held-out-passing artifacts are eligible")
    for key in ("dataset_id", "dataset_revision", "dataset_license"):
        if type(artifact[key]) is not str or not artifact[key].strip() or len(artifact[key]) > 256 or artifact[key].strip().upper() == "UNKNOWN":
            raise SpeakerCalibrationError("calibration dataset provenance is incomplete")
    if not all(artifact[key] is True for key in ("source_disjoint", "session_disjoint", "speaker_disjoint")):
        raise SpeakerCalibrationError("calibration splits are not disjoint")
    for key, expected in (("model_id", model_id), ("model_revision", model_revision),
                          ("model_sha256", model_sha256), ("embedding_dim", embedding_dim),
                          ("frame_step_ms", frame_step_ms), ("lookback_frames", lookback_frames)):
        if artifact[key] != expected:
            raise SpeakerCalibrationError("calibration model/temporal binding mismatch")
    if type(artifact["manifest_sha256"]) is not str or not _SHA256.fullmatch(artifact["manifest_sha256"]):
        raise SpeakerCalibrationError("manifest digest is invalid")
    for key in ("calibration_speaker_count", "heldout_speaker_count", "calibration_positive_pairs",
                "calibration_negative_pairs", "heldout_positive_pairs", "heldout_negative_pairs"):
        if type(artifact[key]) is not int or artifact[key] < 3:
            raise SpeakerCalibrationError("calibration sample count is invalid")
    if min(artifact["calibration_positive_pairs"], artifact["calibration_negative_pairs"],
           artifact["heldout_positive_pairs"], artifact["heldout_negative_pairs"]) < _MIN_PAIRS:
        raise SpeakerCalibrationError("calibration pair count is below the minimum")
    for key in ("max_false_accept_rate", "max_false_reject_rate"):
        if not _finite(artifact[key]) or not 0 < float(artifact[key]) < 0.5:
            raise SpeakerCalibrationError("calibration error-rate limit is invalid")
    if not _finite(artifact["threshold"]) or not -1.0 <= float(artifact["threshold"]) <= 1.0:
        raise SpeakerCalibrationError("calibration threshold is invalid")
    metrics = artifact["heldout_metrics"]
    metric_keys = {"false_accept_rate", "false_reject_rate", "true_accept_rate", "true_reject_rate", "balanced_accuracy"}
    if type(metrics) is not dict or set(metrics) != metric_keys:
        raise SpeakerCalibrationError("held-out metrics are invalid")
    if any(not _finite(metrics[key]) or not 0 <= float(metrics[key]) <= 1 for key in metric_keys):
        raise SpeakerCalibrationError("held-out metric is outside [0,1]")
    if (metrics["false_accept_rate"] > artifact["max_false_accept_rate"]
            or metrics["false_reject_rate"] > artifact["max_false_reject_rate"]):
        raise SpeakerCalibrationError("held-out metrics do not meet the declared limits")
    payload = {key: value for key, value in artifact.items() if key not in {"calibration_id", "artifact_sha256"}}
    digest = _digest(payload)
    if artifact["artifact_sha256"] != digest or artifact["calibration_id"] != digest[:16]:
        raise SpeakerCalibrationError("calibration artifact hash mismatch")
    return dict(artifact)


def _read_regular_file(path, max_bytes):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise SpeakerCalibrationError("calibration file is unavailable or unsafe") from None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            raise SpeakerCalibrationError("calibration file is not a bounded regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise SpeakerCalibrationError("calibration file exceeds its size bound")
        return raw
    finally:
        os.close(descriptor)


def load_approved_calibration(home, calibration_id, *, model_id, model_revision, model_sha256,
                              embedding_dim, frame_step_ms, lookback_frames):
    """Read a locally allowlisted artifact; no network, writes, or implicit model download.

    The local manifest is an owner-controlled opt-in, not a cryptographic signature.
    File hashes detect corruption/replacement; they do not authenticate the owner.
    """
    if type(calibration_id) is not str or not _CALIBRATION_ID.fullmatch(calibration_id):
        raise SpeakerCalibrationError("calibration_id is invalid")
    home_path = Path(home).resolve(strict=True)
    models_path = home_path / "models"
    root = models_path / "speaker_calibration"
    if (models_path.is_symlink() or not models_path.is_dir()
            or root.is_symlink() or not root.is_dir()):
        raise SpeakerCalibrationError("speaker calibration directory is unavailable or unsafe")
    try:
        models_real = models_path.resolve(strict=True)
        root_real = root.resolve(strict=True)
        if root_real.parent != models_real:
            raise SpeakerCalibrationError("speaker calibration directory escapes the model root")
    except OSError:
        raise SpeakerCalibrationError("speaker calibration directory cannot be resolved") from None

    manifest_path = root / "approved.json"
    raw_manifest = _read_regular_file(manifest_path, _MAX_ARTIFACT_BYTES)
    try:
        manifest = json.loads(raw_manifest.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise SpeakerCalibrationError("speaker calibration approval manifest is unreadable") from None
    if (type(manifest) is not dict or set(manifest) != {"schema", "entries"}
            or manifest.get("schema") != MANIFEST_SCHEMA or type(manifest.get("entries")) is not list
            or len(manifest["entries"]) > 64):
        raise SpeakerCalibrationError("speaker calibration approval manifest schema mismatch")
    seen_ids = set()
    for item in manifest["entries"]:
        if (type(item) is not dict or set(item) != {"calibration_id", "artifact_sha256", "enabled"}
                or type(item["calibration_id"]) is not str
                or not _CALIBRATION_ID.fullmatch(item["calibration_id"])
                or type(item["artifact_sha256"]) is not str
                or not _SHA256.fullmatch(item["artifact_sha256"])
                or type(item["enabled"]) is not bool
                or item["calibration_id"] in seen_ids):
            raise SpeakerCalibrationError("speaker calibration manifest entry is invalid or duplicated")
        seen_ids.add(item["calibration_id"])
    matches = [entry for entry in manifest["entries"] if entry["calibration_id"] == calibration_id]
    if len(matches) != 1:
        raise SpeakerCalibrationError("calibration is not uniquely allowlisted")
    entry = matches[0]
    if entry["enabled"] is not True:
        raise SpeakerCalibrationError("calibration is disabled")
    artifact_path = root / (calibration_id + ".json")
    raw = _read_regular_file(artifact_path, _MAX_ARTIFACT_BYTES)
    if hashlib.sha256(raw).hexdigest() != entry["artifact_sha256"]:
        raise SpeakerCalibrationError("allowlisted calibration file hash mismatch")
    try:
        artifact = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise SpeakerCalibrationError("calibration artifact is unreadable") from None
    return validate_calibration_artifact(
        artifact, model_id=model_id, model_revision=model_revision, model_sha256=model_sha256,
        embedding_dim=embedding_dim, frame_step_ms=frame_step_ms, lookback_frames=lookback_frames,
    )
