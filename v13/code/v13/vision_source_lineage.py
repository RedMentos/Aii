"""Source-bound invalidation for the V13/V14 shadow vision projectors.

The ridge projectors are trained from source-derived captions/features. A source
forget must not leave weights that were fitted using that source. New projectors
record exact contributing source IDs and image hashes; legacy or malformed
lineage is treated as unknown and therefore invalidated conservatively.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def source_lineage(images: dict, keys) -> list[dict]:
    """Resolve every training key to an exact live IMAGE source and digest."""
    source_ids = set()
    for key in keys:
        if type(key) is not str or ":" not in key:
            raise ValueError("vision training key lacks a source binding")
        source_id = key.split(":", 1)[0]
        if not source_id:
            raise ValueError("vision training key has an empty source id")
        source_ids.add(source_id)
    if not source_ids:
        raise ValueError("vision training set has no source lineage")
    lineage = []
    for source_id in sorted(source_ids):
        record = images.get(source_id) if type(images) is dict else None
        ref = record.get("ref") if type(record) is dict else None
        sha256 = ref.get("sha256") if type(ref) is dict else None
        if (type(ref) is not dict or ref.get("source_id") != source_id
                or type(sha256) is not str or not _SHA256.fullmatch(sha256)):
            raise ValueError("vision training source is missing or malformed")
        lineage.append({"source_id": source_id, "sha256": sha256})
    return lineage


def projector_uses_source(record: dict, source_id: str) -> bool:
    """Unknown/legacy lineage invalidates; proven-disjoint lineage may survive."""
    if type(record) is not dict:
        return False
    lineage = record.get("training_sources")
    if type(lineage) is not list or not lineage:
        return True
    seen = set()
    for item in lineage:
        if type(item) is not dict or set(item) != {"source_id", "sha256"}:
            return True
        sid, sha256 = item.get("source_id"), item.get("sha256")
        if (type(sid) is not str or not sid
                or type(sha256) is not str or not _SHA256.fullmatch(sha256)
                or sid in seen):
            return True
        seen.add(sid)
    stats_mode = record.get("source_stats_mode")
    stats_records = record.get("source_stats")
    if stats_mode == "EXACT_SOURCE_STATS_V1":
        if type(stats_records) is not list or not stats_records:
            return True
        stats_seen = {}
        for item in stats_records:
            if type(item) is not dict or set(item) != {"source_id", "source_sha256", "path", "sha256", "n"}:
                return True
            sid = item.get("source_id")
            source_sha = item.get("source_sha256")
            path = item.get("path")
            artifact_sha = item.get("sha256")
            count = item.get("n")
            if (type(sid) is not str or not sid or sid in stats_seen
                    or type(source_sha) is not str or not _SHA256.fullmatch(source_sha)
                    or type(artifact_sha) is not str or not _SHA256.fullmatch(artifact_sha)
                    or type(path) is not str or not path.startswith("data/vision/")
                    or type(count) is not int or count < 1):
                return True
            stats_seen[sid] = source_sha
        if stats_seen != {item["source_id"]: item["sha256"] for item in lineage}:
            return True
    elif stats_mode in ("SOURCE_CAP_EXCEEDED", "UNAVAILABLE_STORAGE"):
        if stats_records != []:
            return True
    elif stats_mode is not None or stats_records is not None:
        return True

    captions = record.get("captions")
    if type(captions) is dict:
        prefix = source_id + ":"
        if any(type(key) is str and key.startswith(prefix) for key in captions):
            return True
    return source_id in seen


def invalidate_projectors(state: dict, source_id: str) -> list[tuple[str, dict]]:
    """Clear every affected/unknown projector from persistent state before unlink."""
    invalidated = []
    for key in ("projector", "tile_projector"):
        record = state.get(key)
        if isinstance(record, dict) and projector_uses_source(record, source_id):
            state[key] = None
            invalidated.append((key, record))
    return invalidated


def _safe_unlink(home, relative: str, expected_parts: tuple[str, str], valid_name) -> bool:
    """Unlink beneath home without following a symlink in any directory component."""
    if type(relative) is not str:
        return False
    rel = Path(relative)
    if (rel.is_absolute() or len(rel.parts) != 3
            or rel.parts[:2] != expected_parts
            or any(part in ("", ".", "..") for part in rel.parts)
            or not valid_name(rel.name)):
        return False
    if (not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY")
            or os.open not in getattr(os, "supports_dir_fd", set())
            or os.unlink not in getattr(os, "supports_dir_fd", set())):
        return False

    root_fd = parent_fd = None
    try:
        root = Path(home).resolve(strict=True)
        flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
        root_fd = os.open(str(root), flags)
        parent_fd = root_fd
        for part in rel.parts[:-1]:
            next_fd = os.open(part, flags | os.O_NOFOLLOW, dir_fd=parent_fd)
            if parent_fd != root_fd:
                os.close(parent_fd)
            parent_fd = next_fd
        try:
            os.unlink(rel.parts[-1], dir_fd=parent_fd)
        except FileNotFoundError:
            return True
        return True
    except FileNotFoundError:
        return True
    except (OSError, TypeError, ValueError):
        return False
    finally:
        if parent_fd is not None and parent_fd != root_fd:
            os.close(parent_fd)
        if root_fd is not None:
            os.close(root_fd)


def unlink_projector_artifact(home, record: dict) -> bool:
    """Remove only a generated projector artifact under data/vision."""
    relative = record.get("path") if type(record) is dict else None
    def valid_name(name):
        return (name.endswith(".npz")
                and (name.startswith("projector-") or name.startswith("tiles-")))
    return _safe_unlink(home, relative, ("data", "vision"), valid_name)


def unlink_source_blob(home, sha256: str) -> bool:
    """Remove only a content-addressed IMAGE blob beneath data/blobs."""
    if type(sha256) is not str or not _SHA256.fullmatch(sha256):
        return False
    return _safe_unlink(home, "data/blobs/" + sha256, ("data", "blobs"),
                        lambda name: bool(_SHA256.fullmatch(name)))
