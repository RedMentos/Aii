"""Source-scoped sufficient statistics for exact deletion of the A3 ridge head.

This reconstructs only V13's closed-form linear Projector. It does not unlearn
the image feature extractor, text encoder, teacher, or any GGUF model.
"""
from __future__ import annotations

import io
import json
import math
import os
import stat
import uuid
import zipfile
from pathlib import Path

from .common import digest
from .vision_source_lineage import unlink_projector_artifact

SCHEMA = "v13.a3.source-sufficient-stats/1"
SOURCE_STATS_MODE = "EXACT_SOURCE_STATS_V1"
MAX_SOURCE_STATS = 32
MAX_FEATURE_DIM = 512
MAX_TARGET_DIM = 1024
MAX_ROWS_PER_SOURCE = 100_000
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 8 * 1024 * 1024
_EXPECTED_MEMBERS = {"meta.npy", "sx.npy", "sxx.npy", "sy.npy", "sxy.npy"}


def _np():
    import numpy
    return numpy


def sufficient_statistics(X, Y):
    """Return fp64 additive moments for the exact standardized+bias ridge fit."""
    np = _np()
    X = np.asarray(X, dtype=np.float64)
    Y = np.asarray(Y, dtype=np.float64)
    if X.ndim != 2 or Y.ndim != 2 or X.shape[0] != Y.shape[0] or X.shape[0] < 1:
        raise ValueError("A3 source statistics require aligned non-empty matrices")
    n, d = X.shape
    c = Y.shape[1]
    if n > MAX_ROWS_PER_SOURCE or not (1 <= d <= MAX_FEATURE_DIM) or not (1 <= c <= MAX_TARGET_DIM):
        raise ValueError("A3 source statistics exceed bounded dimensions")
    if not np.isfinite(X).all() or not np.isfinite(Y).all():
        raise ValueError("A3 source statistics reject non-finite inputs")
    return {
        "n": int(n),
        "sx": X.sum(axis=0, dtype=np.float64),
        "sxx": X.T @ X,
        "sy": Y.sum(axis=0, dtype=np.float64),
        "sxy": X.T @ Y,
    }


def _vision_dir_fd(home):
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise OSError("no-follow directory operations unavailable")
    if os.open not in getattr(os, "supports_dir_fd", set()):
        raise OSError("descriptor-relative open unavailable")
    root = Path(home).resolve(strict=True)
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    root_fd = os.open(str(root), flags)
    data_fd = vision_fd = None
    try:
        data_fd = os.open("data", flags | os.O_NOFOLLOW, dir_fd=root_fd)
        vision_fd = os.open("vision", flags | os.O_NOFOLLOW, dir_fd=data_fd)
        return root_fd, data_fd, vision_fd
    except Exception:
        if vision_fd is not None:
            os.close(vision_fd)
        if data_fd is not None:
            os.close(data_fd)
        os.close(root_fd)
        raise


def _close_vision_dir(fds):
    if fds:
        for fd in reversed(fds):
            if fd is not None:
                os.close(fd)


def _valid_name(name):
    return (type(name) is str and name.endswith(".npz")
            and (name.startswith("projector-stats-") or name.startswith("tiles-stats-"))
            and "/" not in name and "\\" not in name and name not in (".", ".."))


def _write_artifact(home, name, raw):
    if not _valid_name(name) or len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("invalid or oversized A3 statistics artifact")
    if (os.rename not in getattr(os, "supports_dir_fd", set())
            or os.unlink not in getattr(os, "supports_dir_fd", set())):
        raise OSError("descriptor-relative rename/unlink unavailable")
    fds = _vision_dir_fd(home)
    _, _, vision_fd = fds
    temp_name = ".pending-a3stats-" + uuid.uuid4().hex
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    fd = None
    renamed = False
    try:
        fd = os.open(temp_name, flags, 0o600, dir_fd=vision_fd)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            fd = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(temp_name, name, src_dir_fd=vision_fd, dst_dir_fd=vision_fd)
        renamed = True
        os.fsync(vision_fd)
    except Exception:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(name if renamed else temp_name, dir_fd=vision_fd)
        except OSError:
            pass
        raise
    finally:
        _close_vision_dir(fds)


def _read_artifact(home, relative):
    path = Path(relative) if type(relative) is str else None
    if (path is None or path.is_absolute() or len(path.parts) != 3
            or path.parts[:2] != ("data", "vision")
            or any(part in ("", ".", "..") for part in path.parts)
            or not _valid_name(path.name)):
        raise ValueError("unsafe A3 statistics artifact path")
    fds = _vision_dir_fd(home)
    _, _, vision_fd = fds
    fd = None
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(path.name, flags, dir_fd=vision_fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size < 1 or info.st_size > MAX_ARTIFACT_BYTES:
            raise ValueError("A3 statistics artifact is not a bounded regular file")
        chunks = []
        total = 0
        while True:
            block = os.read(fd, min(1024 * 1024, MAX_ARTIFACT_BYTES + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total > MAX_ARTIFACT_BYTES:
                raise ValueError("A3 statistics artifact exceeds byte limit")
        return b"".join(chunks)
    finally:
        if fd is not None:
            os.close(fd)
        _close_vision_dir(fds)


def _encode(meta, stats):
    np = _np()
    buffer = io.BytesIO()
    np.savez(
        buffer,
        meta=np.asarray(json.dumps(meta, sort_keys=True, separators=(",", ":"))),
        sx=np.asarray(stats["sx"], dtype=np.float64),
        sxx=np.asarray(stats["sxx"], dtype=np.float64),
        sy=np.asarray(stats["sy"], dtype=np.float64),
        sxy=np.asarray(stats["sxy"], dtype=np.float64),
    )
    raw = buffer.getvalue()
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("A3 statistics artifact exceeds byte limit")
    return raw


def save_source_statistics(home, prefix, source_id, source_sha256, X, Y,
                           feature_schema, encoder, ridge):
    if prefix not in ("projector", "tiles"):
        raise ValueError("unknown A3 projector statistics family")
    if (type(source_id) is not str or not source_id or len(source_id) > 256
            or type(source_sha256) is not str or len(source_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in source_sha256)):
        raise ValueError("invalid A3 statistics source binding")
    if type(feature_schema) is not str or not feature_schema or len(feature_schema) > 128:
        raise ValueError("invalid A3 feature schema")
    if type(encoder) is not str or not encoder or len(encoder) > 256:
        raise ValueError("invalid A3 encoder revision")
    if type(ridge) not in (int, float) or not math.isfinite(float(ridge)) or not (float(ridge) > 0.0):
        raise ValueError("invalid A3 ridge value")
    stats = sufficient_statistics(X, Y)
    meta = {
        "schema": SCHEMA,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "feature_schema": feature_schema,
        "encoder": encoder,
        "ridge": float(ridge),
        "n": stats["n"],
        "d": int(stats["sx"].shape[0]),
        "c": int(stats["sy"].shape[0]),
    }
    raw = _encode(meta, stats)
    name = prefix + "-stats-" + uuid.uuid4().hex + ".npz"
    _write_artifact(home, name, raw)
    return {
        "source_id": source_id,
        "source_sha256": source_sha256,
        "path": "data/vision/" + name,
        "sha256": digest(raw),
        "n": stats["n"],
    }


def build_source_statistics(home, prefix, X, Y, keys, training_sources,
                            feature_schema, encoder, ridge):
    """Persist per-source moments, or explicitly disable exact deletion above the cap."""
    if type(training_sources) is not list:
        raise ValueError("A3 training source lineage must be a list")
    if len(training_sources) > MAX_SOURCE_STATS:
        return [], "SOURCE_CAP_EXCEEDED"
    source_map = {}
    for item in training_sources:
        if type(item) is not dict or set(item) != {"source_id", "sha256"}:
            raise ValueError("invalid A3 training source lineage")
        sid, sha = item["source_id"], item["sha256"]
        if (type(sid) is not str or not sid or type(sha) is not str or len(sha) != 64
                or any(ch not in "0123456789abcdef" for ch in sha) or sid in source_map):
            raise ValueError("duplicate or malformed A3 training source")
        source_map[sid] = sha
    if not source_map:
        raise ValueError("A3 training source lineage is empty")
    groups = {}
    for index, key in enumerate(keys):
        if type(key) is not str or ":" not in key:
            raise ValueError("A3 training key lacks a source binding")
        sid = key.split(":", 1)[0]
        if sid not in source_map:
            raise ValueError("A3 training key is outside its source lineage")
        groups.setdefault(sid, []).append(index)
    if set(groups) != set(source_map):
        raise ValueError("A3 source statistics do not cover the training rows")
    np = _np()
    X = np.asarray(X, dtype=np.float64)
    Y = np.asarray(Y, dtype=np.float64)
    if X.ndim != 2 or Y.ndim != 2 or X.shape[0] != Y.shape[0] or X.shape[0] != len(keys):
        raise ValueError("A3 source statistics row mismatch")
    created = []
    try:
        for sid in sorted(source_map):
            idx = groups[sid]
            created.append(save_source_statistics(
                home, prefix, sid, source_map[sid], X[idx], Y[idx],
                feature_schema, encoder, ridge,
            ))
    except OSError:
        remove_source_statistics(home, created)
        return [], "UNAVAILABLE_STORAGE"
    except Exception:
        remove_source_statistics(home, created)
        raise
    return created, SOURCE_STATS_MODE


def remove_source_statistics(home, records):
    failed = []
    for record in records if type(records) is list else []:
        if not unlink_projector_artifact(home, record):
            failed.append(record.get("source_id", "unknown") if type(record) is dict else "unknown")
    return failed


def load_source_statistics(home, record):
    np = _np()
    if type(record) is not dict:
        raise ValueError("invalid A3 source-stat record")
    raw = _read_artifact(home, record.get("path"))
    if type(record.get("sha256")) is not str or digest(raw) != record["sha256"]:
        raise ValueError("A3 source-stat digest mismatch")
    with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
        infos = archive.infolist()
        if len(infos) != len(_EXPECTED_MEMBERS) or {item.filename for item in infos} != _EXPECTED_MEMBERS:
            raise ValueError("A3 source-stat archive members mismatch")
        if sum(item.file_size for item in infos) > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("A3 source-stat archive expands beyond byte limit")
        if any(item.file_size > MAX_UNCOMPRESSED_BYTES for item in infos):
            raise ValueError("A3 source-stat member exceeds byte limit")
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        if set(data.files) != {"meta", "sx", "sxx", "sy", "sxy"}:
            raise ValueError("A3 source-stat arrays mismatch")
        meta_raw = data["meta"]
        if meta_raw.shape != () or meta_raw.dtype.kind not in ("U", "S"):
            raise ValueError("A3 source-stat metadata is malformed")
        meta_value = meta_raw.item()
        if isinstance(meta_value, bytes):
            meta_value = meta_value.decode("utf-8")
        if type(meta_value) is not str:
            raise ValueError("A3 source-stat metadata is not UTF-8 text")
        meta = json.loads(meta_value)
        sx, sxx, sy, sxy = (np.asarray(data[name]) for name in ("sx", "sxx", "sy", "sxy"))
    if type(meta) is not dict or meta.get("schema") != SCHEMA:
        raise ValueError("unsupported A3 source-stat schema")
    sid, source_sha = meta.get("source_id"), meta.get("source_sha256")
    if (type(sid) is not str or sid != record.get("source_id")
            or type(source_sha) is not str or source_sha != record.get("source_sha256")
            or len(source_sha) != 64 or any(ch not in "0123456789abcdef" for ch in source_sha)):
        raise ValueError("A3 source-stat source binding mismatch")
    n, d, c = meta.get("n"), meta.get("d"), meta.get("c")
    ridge = meta.get("ridge")
    if (type(n) is not int or not (1 <= n <= MAX_ROWS_PER_SOURCE)
            or type(d) is not int or not (1 <= d <= MAX_FEATURE_DIM)
            or type(c) is not int or not (1 <= c <= MAX_TARGET_DIM)
            or type(ridge) not in (int, float) or not math.isfinite(float(ridge)) or not (float(ridge) > 0.0)):
        raise ValueError("A3 source-stat dimensions or ridge are invalid")
    if (type(meta.get("feature_schema")) is not str or not meta["feature_schema"] or len(meta["feature_schema"]) > 128
            or type(meta.get("encoder")) is not str or not meta["encoder"] or len(meta["encoder"]) > 256):
        raise ValueError("A3 source-stat feature/encoder revision is invalid")
    if (sx.shape != (d,) or sxx.shape != (d, d) or sy.shape != (c,) or sxy.shape != (d, c)
            or any(array.dtype != np.dtype("float64") for array in (sx, sxx, sy, sxy))
            or not all(np.isfinite(array).all() for array in (sx, sxx, sy, sxy))):
        raise ValueError("A3 source-stat tensor shape/dtype is invalid")
    if record.get("n") != n:
        raise ValueError("A3 source-stat row count mismatch")
    return meta, {"n": n, "sx": sx, "sxx": sxx, "sy": sy, "sxy": sxy}


def _merge_statistics(items):
    np = _np()
    if not items:
        raise ValueError("no retained A3 source statistics")
    first = items[0]
    merged = {
        "n": 0,
        "sx": np.zeros_like(first["sx"], dtype=np.float64),
        "sxx": np.zeros_like(first["sxx"], dtype=np.float64),
        "sy": np.zeros_like(first["sy"], dtype=np.float64),
        "sxy": np.zeros_like(first["sxy"], dtype=np.float64),
    }
    for item in items:
        if (item["sx"].shape != merged["sx"].shape or item["sxx"].shape != merged["sxx"].shape
                or item["sy"].shape != merged["sy"].shape or item["sxy"].shape != merged["sxy"].shape):
            raise ValueError("A3 source-stat dimensions differ")
        merged["n"] += item["n"]
        for key in ("sx", "sxx", "sy", "sxy"):
            merged[key] += item[key]
    return merged


def _projector_from_statistics(stats, ridge, projector_class):
    np = _np()
    n, sx, sxx, sy, sxy = (stats[key] for key in ("n", "sx", "sxx", "sy", "sxy"))
    if n < 1:
        raise ValueError("no retained A3 training rows")
    mu = sx / float(n)
    variance = np.maximum(np.diag(sxx) / float(n) - mu * mu, 0.0)
    sd = np.sqrt(variance) + 1e-6
    centered = sxx - np.outer(sx, sx) / float(n)
    gram = centered / (sd[:, None] * sd[None, :])
    gram = (gram + gram.T) * 0.5
    cross = (sxy - np.outer(sx, sy) / float(n)) / sd[:, None]
    weights = np.linalg.solve(gram + float(ridge) * np.eye(len(mu), dtype=np.float64), cross)
    bias = sy / float(n)
    projector = projector_class(float(ridge))
    projector.mu = mu
    projector.sd = sd
    projector.W = np.vstack((weights, bias))
    projector.n = int(n)
    return projector


def rebuild_without_source(home, projector_record, source_id, source_sha256,
                           remaining_images, projector_class, min_train):
    """Reconstruct the same ridge optimum from all live source stats except one.

    Returns (result, None) on exact source deletion, or (None, reason) so the
    caller can safely fall back to full projector invalidation.
    """
    try:
        if type(projector_record) is not dict or projector_record.get("source_stats_mode") != SOURCE_STATS_MODE:
            raise ValueError("source statistics are unavailable")
        records = projector_record.get("source_stats")
        lineage = projector_record.get("training_sources")
        if type(records) is not list or not records or len(records) > MAX_SOURCE_STATS or type(lineage) is not list:
            raise ValueError("source statistics are missing or unbounded")
        loaded = {}
        metas = []
        for item in records:
            meta, stats = load_source_statistics(home, item)
            sid = meta["source_id"]
            if sid in loaded:
                raise ValueError("duplicate source-stat record")
            loaded[sid] = (item, meta, stats)
            metas.append(meta)
        lineage_map = {}
        for item in lineage:
            if type(item) is not dict or set(item) != {"source_id", "sha256"}:
                raise ValueError("malformed projector source lineage")
            sid, sha = item["source_id"], item["sha256"]
            if (type(sid) is not str or not sid or type(sha) is not str or len(sha) != 64
                    or any(ch not in "0123456789abcdef" for ch in sha) or sid in lineage_map):
                raise ValueError("duplicate projector source lineage")
            lineage_map[sid] = sha
        if set(lineage_map) != set(loaded):
            raise ValueError("source-stat coverage does not match projector lineage")
        for sid, (_, meta, _) in loaded.items():
            if lineage_map[sid] != meta["source_sha256"]:
                raise ValueError("projector lineage digest differs from source statistics")
        if type(remaining_images) is not dict or source_id in remaining_images:
            raise ValueError("forgotten source is still present in the live image registry")
        if type(min_train) is not int or min_train < 1:
            raise ValueError("invalid A3 minimum training count")
        if source_id not in loaded or lineage_map.get(source_id) != source_sha256:
            raise ValueError("forgotten source is not covered by exact statistics")
        first = metas[0]
        for meta in metas:
            if any(meta.get(key) != first.get(key) for key in ("feature_schema", "encoder", "ridge", "d", "c")):
                raise ValueError("source-stat training revisions differ")
        if sum(meta["n"] for meta in metas) != projector_record.get("n"):
            raise ValueError("source-stat row count does not match projector")
        if projector_record.get("feature_schema") != first["feature_schema"]:
            raise ValueError("projector feature schema differs from source statistics")
        if projector_record.get("encoder") != first["encoder"]:
            raise ValueError("projector encoder revision differs from source statistics")
        if float(projector_record.get("ridge", first["ridge"])) != float(first["ridge"]):
            raise ValueError("projector ridge differs from source statistics")
        if first["feature_schema"].endswith(":global"):
            captions = projector_record.get("captions")
            if type(captions) is not dict or len(captions) != projector_record.get("n"):
                raise ValueError("global projector caption lineage is incomplete")
            caption_counts = {}
            for key, value in captions.items():
                if (type(key) is not str or ":" not in key or type(value) is not str or not value
                        or key.split(":", 1)[0] not in lineage_map):
                    raise ValueError("global projector caption source binding is invalid")
                sid = key.split(":", 1)[0]
                caption_counts[sid] = caption_counts.get(sid, 0) + 1
            expected_counts = {sid: loaded[sid][1]["n"] for sid in lineage_map}
            if caption_counts != expected_counts:
                raise ValueError("global projector caption counts differ from source statistics")
        remaining_records = []
        remaining_lineage = []
        remaining_stats = []
        for sid in sorted(loaded):
            item, meta, stats = loaded[sid]
            if sid == source_id:
                if meta["source_sha256"] != source_sha256:
                    raise ValueError("forgotten source digest differs")
                continue
            image = remaining_images.get(sid)
            ref = image.get("ref") if type(image) is dict else None
            if type(ref) is not dict or ref.get("sha256") != meta["source_sha256"]:
                raise ValueError("retained source is not live with its exact digest")
            remaining_records.append(item)
            remaining_lineage.append({"source_id": sid, "sha256": meta["source_sha256"]})
            remaining_stats.append(stats)
        merged = _merge_statistics(remaining_stats)
        if merged["n"] < min_train:
            raise ValueError("retained rows fall below A3 minimum training count")
        projector = _projector_from_statistics(merged, first["ridge"], projector_class)
        return {
            "projector": projector,
            "remaining_stats": remaining_records,
            "removed_stats": [loaded[source_id][0]],
            "training_sources": remaining_lineage,
            "n": merged["n"],
            "encoder": first["encoder"],
            "feature_schema": first["feature_schema"],
            "ridge": float(first["ridge"]),
        }, None
    except Exception as exc:
        return None, type(exc).__name__ + ": " + str(exc)[:180]
