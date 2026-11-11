"""Bounded read-only V13 generation artifact inspection; never a learning gate.

This audits SHA/active Store bindings of LOCAL review artifacts only, not model
quality, actual weight-delta size, measured retention, Android, or native GGUF.
Large artifacts are explicitly SKIPPED rather than exhausting a phone.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat

REVISION = "v13-brain-artifact-audit-v1"
MAX_COMPONENTS = 64
MAX_TOTAL_MIB = 128
PATH = re.compile(r"checkpoints/[A-Za-z0-9_.-]{1,160}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")


def _hash_file(path, expected_bytes):
    digest = hashlib.sha256()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        meta = os.fstat(fd)
        if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1:
            raise ValueError("UNSAFE_INODE")
        if meta.st_size != expected_bytes:
            raise ValueError("FILE_CHANGED_BEFORE_HASH")
        with os.fdopen(fd, "rb", closefd=False) as source:
            total = 0
            while True:
                block = source.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > expected_bytes:
                    raise ValueError("FILE_GREW_DURING_HASH")
                digest.update(block)
            if total != expected_bytes:
                raise ValueError("FILE_TRUNCATED_DURING_HASH")
        return digest.hexdigest()
    finally:
        os.close(fd)


def inspect(runtime, budget_mib=32):
    """Requires an idle Runtime and local operator origin. No file writes."""
    if type(budget_mib) is not int or not 1 <= budget_mib <= MAX_TOTAL_MIB:
        raise ValueError(":brain audit [1..128] MiB")
    require_idle = getattr(runtime, "require_idle", None)
    if not callable(require_idle):
        raise ValueError("verified idle Runtime required for artifact audit")
    require_idle()
    store = runtime.store
    home = Path(runtime.home).resolve(strict=True)
    active = store.generation()  # validates signed manifest *format* hash
    hashes = active.get("hashes", {})
    components = active.get("components")
    if type(hashes) is not dict:
        raise ValueError("corrupt active generation hash map")
    if components is None:
        components = store.components(active)
    if type(components) is not dict or len(components) > MAX_COMPONENTS:
        raise ValueError("corrupt or oversized component manifest")
    results = []
    budget = budget_mib * 1024 * 1024
    inspected_bytes = 0
    for raw_name, entry in sorted(components.items(), key=lambda x: str(x[0])):
        status = "NOT_VERIFIED"
        name = raw_name if type(raw_name) is str and re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_-]{0,63}", raw_name
        ) else "UNKNOWN_COMPONENT"
        record = {"component": name, "status": status, "bytes_read": 0}
        if (type(entry) is not dict
                or type(entry.get("path")) is not str
                or not PATH.fullmatch(entry["path"])
                or type(entry.get("sha256")) is not str
                or not SHA.fullmatch(entry["sha256"])
                or hashes.get(entry["path"]) != entry["sha256"]
                or type(entry.get("update_id")) is not str):
            record["status"] = "INVALID_BINDING"
            results.append(record)
            continue
        row = store.one("SELECT status FROM updates WHERE id=?", (entry["update_id"],))
        if not row or row.get("status") != "COMMITTED":
            record["status"] = "UPDATE_NOT_COMMITTED"
            results.append(record)
            continue
        raw = home / entry["path"]
        if raw.is_symlink() or not raw.resolve().is_relative_to(home):
            record["status"] = "UNSAFE_PATH"
            results.append(record)
            continue
        try:
            info = raw.stat()
        except OSError:
            record["status"] = "MISSING_FILE"
            results.append(record)
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            record["status"] = "UNSAFE_INODE"
        elif info.st_size > budget:
            record["status"] = "SKIPPED_BUDGET"
        else:
            budget -= info.st_size
            try:
                digest = _hash_file(raw, info.st_size)
            except (OSError, ValueError):
                record["status"] = "FILE_CHANGED_OR_UNSAFE"
            else:
                inspected_bytes += info.st_size
                record["bytes_read"] = info.st_size
                record["status"] = (
                    "SHA_MATCH" if digest == entry["sha256"] else "SHA_MISMATCH"
                )
        results.append(record)
    return {
        "revision": REVISION, "kind": "READ_ONLY_ACTIVE_ARTIFACT_AUDIT",
        "scope": "ACTIVE_GENERATION_ONLY",
        "components": results, "component_count": len(results),
        "sha_match_count": sum(x["status"] == "SHA_MATCH" for x in results),
        "failed_count": sum(x["status"] not in (
            "SHA_MATCH", "SKIPPED_BUDGET"
        ) for x in results),
        "skipped_count": sum(x["status"] == "SKIPPED_BUDGET" for x in results),
        "bytes_read": inspected_bytes, "max_bytes": budget_mib * 1024 * 1024,
        "all_artifact_hashes_verified": bool(results) and all(
            x["status"] == "SHA_MATCH" for x in results
        ),
        "training_retention_and_redmi_proven": False,
        "claim_limit": (
            "An artifact SHA and committed generation binding do NOT establish "
            "new model learning, retention, native Redmi execution or AGI."
        ),
        "model_calls": 0, "state_mutation": False,
    }


def operator_command(runtime, args):
    if len(args) > 1:
        raise ValueError(":brain audit [MiB=1..128]")
    try:
        budget = int(args[0]) if args else 32
    except ValueError as exc:
        raise ValueError(":brain audit [MiB=1..128]") from exc
    return inspect(runtime, budget)
