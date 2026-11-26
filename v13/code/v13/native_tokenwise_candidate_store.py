"""Private persistence for source-disjoint TOKENWISE latent-alignment candidates.

Only adapter parameters and a hashed fit manifest are persisted. Raw activation
pairs, token IDs, source text and the held-out Runtime record stay in memory.
Saved candidates remain diagnostic, authority-zero and outside production B3.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import time

from .common import dumps, file_hash
from .latent_adapter import LatentAdapterError, load_adapter, save_adapter

SCHEMA = "v14.native-tokenwise-candidate-checkpoint/1"
ROOT_PARTS = ("data", "callosum", "tokenwise_candidates")
MAX_CANDIDATES = 32
MAX_MANIFEST_BYTES = 256 * 1024
MAX_PREFIX = 64
_SHA = re.compile(r"^[0-9a-f]{64}$")
_PREFIX = re.compile(r"^[0-9a-f]{8,64}$")


class CandidateStoreError(ValueError):
    pass


def _sha(value, name):
    if type(value) is not str or not _SHA.fullmatch(value):
        raise CandidateStoreError(name + " must be a lowercase SHA-256 digest")
    return value


def _canonical_sha(value):
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def _fit_manifest(value):
    if not isinstance(value, dict) or value.get("schema") != "v14.native-tokenwise-adapter-fit/1":
        raise CandidateStoreError("fit manifest schema is unsupported")
    material = dict(value)
    supplied = _sha(material.pop("manifest_sha256", None), "fit manifest digest")
    if _canonical_sha(material) != supplied:
        raise CandidateStoreError("fit manifest digest mismatch")
    if (material.get("status") != "ALIGNMENT_CANDIDATE"
            or material.get("source_disjoint") is not True
            or material.get("session_disjoint") is not True
            or material.get("production_route") is not False
            or material.get("semantic_use_proven") is not False
            or material.get("training_authority") != 0
            or material.get("native_receiver_authority") != 0):
        raise CandidateStoreError("fit manifest is not a source/session-disjoint authority-zero candidate")
    records = material.get("record_sha256s")
    train = material.get("train_session_ids")
    holdout = material.get("holdout_session_ids")
    if (not isinstance(records, list) or not 4 <= len(records) <= 1024
            or any(type(item) is not str or not _SHA.fullmatch(item) for item in records)
            or len(set(records)) != len(records)):
        raise CandidateStoreError("fit manifest record digests are invalid")
    def sessions(items, name):
        if (not isinstance(items, list) or len(items) < 2
                or any(type(item) is not str or not item or len(item) > 128 for item in items)
                or len(set(items)) != len(items)):
            raise CandidateStoreError(name + " must contain unique bounded session IDs")
        return set(items)
    train_set = sessions(train, "train sessions")
    holdout_set = sessions(holdout, "holdout sessions")
    if train_set & holdout_set:
        raise CandidateStoreError("fit manifest session split overlaps")
    integer_fields = (
        "train_record_count", "holdout_record_count",
        "train_source_count", "holdout_source_count",
        "train_pair_count", "holdout_pair_count",
    )
    for key in integer_fields:
        if type(material.get(key)) is not int or material[key] < 1:
            raise CandidateStoreError("fit manifest has invalid " + key)
    if (material["train_record_count"] + material["holdout_record_count"] != len(records)
            or material["train_record_count"] < len(train_set)
            or material["holdout_record_count"] < len(holdout_set)):
        raise CandidateStoreError("fit manifest record counts do not match its split")
    return dict(value)


def _adapter(adapter):
    if not isinstance(adapter, dict):
        raise CandidateStoreError("candidate adapter is missing")
    try:
        from .latent_adapter import _validate_adapter
        _validate_adapter(adapter, require_candidate=True)
    except LatentAdapterError:
        raise
    except Exception as exc:
        raise CandidateStoreError("candidate adapter validation failed") from exc
    metrics = adapter.get("metrics")
    if (adapter.get("schema") != "v14.cross-organ-latent-adapter/4"
            or adapter.get("projection_scope") != "TOKENWISE"
            or adapter.get("status") != "ALIGNMENT_CANDIDATE"
            or adapter.get("holdout_policy") != "SOURCE_AND_SESSION_DISJOINT"
            or not isinstance(metrics, dict)
            or metrics.get("session_disjoint") is not True
            or adapter.get("production_route") is not False
            or adapter.get("semantic_use_proven") is not False
            or adapter.get("training_authority") != 0
            or adapter.get("native_receiver_authority") != 0):
        raise CandidateStoreError("adapter is not a diagnostic-only TOKENWISE candidate")
    return dict(adapter)


def _fsync_dir(path):
    fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_json(path):
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise CandidateStoreError("platform lacks O_NOFOLLOW for private candidate reads")
    fd = os.open(str(path), os.O_RDONLY | nofollow | getattr(os, "O_CLOEXEC", 0))
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_size > MAX_MANIFEST_BYTES
                or info.st_mode & 0o077):
            raise CandidateStoreError("candidate manifest must be a private bounded regular file")
        with os.fdopen(os.dup(fd), "rb") as stream:
            raw = stream.read(MAX_MANIFEST_BYTES + 1)
    finally:
        os.close(fd)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise CandidateStoreError("candidate manifest exceeds size limit")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise CandidateStoreError("candidate manifest cannot be decoded") from exc
    if not isinstance(value, dict):
        raise CandidateStoreError("candidate manifest must be an object")
    return value


class CandidateStore:
    def __init__(self, home):
        self.home = Path(home).expanduser().resolve(strict=True)
        if not self.home.is_dir():
            raise CandidateStoreError("Runtime home is not a directory")

    def _root(self, create=False):
        current = self.home
        for index, part in enumerate(ROOT_PARTS):
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                if not create:
                    return None
                current.mkdir(mode=0o700)
                info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise CandidateStoreError("candidate store path contains a symlink or non-directory")
            if index == len(ROOT_PARTS) - 1:
                if info.st_mode & 0o077:
                    if not create:
                        raise CandidateStoreError("candidate store directory is not private")
                    os.chmod(current, 0o700)
            return_path = current
        return return_path

    def _resolve_prefix(self, root, prefix):
        if type(prefix) is not str or not _PREFIX.fullmatch(prefix):
            raise CandidateStoreError("candidate ID prefix must be 8..64 lowercase hexadecimal characters")
        matches = []
        for item in root.iterdir():
            if item.name.startswith(prefix) and _SHA.fullmatch(item.name):
                info = item.lstat()
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                    raise CandidateStoreError("candidate entry is not a private directory")
                matches.append(item)
        if len(matches) != 1:
            if not matches:
                raise FileNotFoundError("no saved tokenwise candidate matches that ID")
            raise CandidateStoreError("candidate prefix is ambiguous; use a longer SHA prefix")
        return matches[0]

    def save(self, candidate):
        if not isinstance(candidate, dict) or not isinstance(candidate.get("record"), dict):
            raise CandidateStoreError("saving requires a currently staged candidate with an in-memory held-out record")
        adapter = _adapter(candidate.get("adapter"))
        fit = _fit_manifest(candidate.get("fit_manifest"))
        adapter_sha = _sha(adapter.get("adapter_sha256"), "adapter digest")
        root = self._root(create=True)
        existing = [item for item in root.iterdir() if _SHA.fullmatch(item.name) and item.is_dir()]
        if len(existing) >= MAX_CANDIDATES:
            raise CandidateStoreError("candidate store limit reached; no automatic pruning is allowed")
        final_dir = root / adapter_sha
        if final_dir.exists() or final_dir.is_symlink():
            loaded = self.load(adapter_sha)
            if (loaded["adapter"].get("adapter_sha256") == adapter_sha
                    and loaded["fit_manifest"].get("manifest_sha256") == fit.get("manifest_sha256")):
                return {
                    "status": "ALREADY_SAVED",
                    "candidate_id": adapter_sha,
                    "adapter_file_sha256": loaded["checkpoint"]["adapter_file_sha256"],
                    "manifest_sha256": loaded["checkpoint"]["manifest_sha256"],
                    "created_at": loaded["checkpoint"]["created_at"],
                    "record_persisted": False,
                    "pair_vectors_persisted": False,
                    "production_route": False,
                    "training_authority": 0,
                    "native_receiver_authority": 0,
                }
            raise CandidateStoreError("candidate ID collision with different fit evidence")
        temporary = Path(tempfile.mkdtemp(prefix=".pending-", dir=str(root)))
        os.chmod(temporary, 0o700)
        try:
            adapter_path = temporary / "adapter.v14lat"
            adapter_file_sha = save_adapter(adapter, adapter_path)
            os.chmod(adapter_path, 0o600)
            created_at = time.time()
            material = {
                "schema": SCHEMA,
                "adapter_sha256": adapter_sha,
                "adapter_file_sha256": adapter_file_sha,
                "fit_manifest": fit,
                "created_at": created_at,
                "record_persisted": False,
                "pair_vectors_persisted": False,
                "source_text_persisted": False,
                "token_ids_persisted": False,
                "production_route": False,
                "semantic_use_proven": False,
                "training_authority": 0,
                "native_receiver_authority": 0,
            }
            wrapper = material | {"manifest_sha256": _canonical_sha(material)}
            manifest_path = temporary / "manifest.json"
            from .common import atomic_write
            atomic_write(manifest_path, dumps(wrapper))
            os.chmod(manifest_path, 0o600)
            _fsync_dir(temporary)
            os.rename(temporary, final_dir)
            _fsync_dir(root)
        except BaseException:
            if temporary.exists():
                shutil.rmtree(temporary, ignore_errors=True)
            raise
        loaded = self.load(adapter_sha)
        return {
            "status": "SAVED",
            "candidate_id": adapter_sha,
            "adapter_file_sha256": loaded["checkpoint"]["adapter_file_sha256"],
            "manifest_sha256": loaded["checkpoint"]["manifest_sha256"],
            "created_at": loaded["checkpoint"]["created_at"],
            "record_persisted": False,
            "pair_vectors_persisted": False,
            "source_text_persisted": False,
            "token_ids_persisted": False,
            "production_route": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }

    def load(self, prefix):
        root = self._root(create=False)
        if root is None:
            raise FileNotFoundError("no saved tokenwise candidates exist")
        directory = self._resolve_prefix(root, prefix)
        manifest_path = directory / "manifest.json"
        adapter_path = directory / "adapter.v14lat"
        wrapper = _read_json(manifest_path)
        material = dict(wrapper)
        supplied = _sha(material.pop("manifest_sha256", None), "checkpoint manifest digest")
        if _canonical_sha(material) != supplied:
            raise CandidateStoreError("checkpoint manifest digest mismatch")
        adapter_sha = _sha(material.get("adapter_sha256"), "adapter digest")
        if directory.name != adapter_sha:
            raise CandidateStoreError("candidate directory and manifest IDs differ")
        if (material.get("schema") != SCHEMA
                or material.get("record_persisted") is not False
                or material.get("pair_vectors_persisted") is not False
                or material.get("source_text_persisted") is not False
                or material.get("token_ids_persisted") is not False
                or material.get("production_route") is not False
                or material.get("semantic_use_proven") is not False
                or material.get("training_authority") != 0
                or material.get("native_receiver_authority") != 0):
            raise CandidateStoreError("checkpoint authority/privacy flags are invalid")
        fit = _fit_manifest(material.get("fit_manifest"))
        info = adapter_path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise CandidateStoreError("adapter checkpoint must be a private regular file")
        adapter_file_sha = _sha(material.get("adapter_file_sha256"), "adapter file digest")
        if file_hash(adapter_path) != adapter_file_sha:
            raise CandidateStoreError("adapter checkpoint file digest mismatch")
        adapter = _adapter(load_adapter(adapter_path))
        if adapter.get("adapter_sha256") != adapter_sha:
            raise CandidateStoreError("adapter checkpoint and manifest IDs differ")
        return {
            "adapter": adapter,
            "fit_manifest": fit,
            "checkpoint": {
                "candidate_id": adapter_sha,
                "adapter_file_sha256": adapter_file_sha,
                "manifest_sha256": supplied,
                "created_at": material.get("created_at"),
                "record_persisted": False,
                "pair_vectors_persisted": False,
                "source_text_persisted": False,
                "token_ids_persisted": False,
                "production_route": False,
                "training_authority": 0,
                "native_receiver_authority": 0,
            },
        }

    def list(self):
        root = self._root(create=False)
        if root is None:
            return []
        entries = []
        for item in root.iterdir():
            if not _SHA.fullmatch(item.name):
                continue
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise CandidateStoreError("candidate entry is not a regular directory")
            wrapper = _read_json(item / "manifest.json")
            material = dict(wrapper)
            supplied = _sha(material.pop("manifest_sha256", None), "checkpoint manifest digest")
            if _canonical_sha(material) != supplied or material.get("adapter_sha256") != item.name:
                raise CandidateStoreError("candidate listing found a corrupt manifest")
            fit = _fit_manifest(material.get("fit_manifest"))
            entries.append({
                "candidate_id": item.name,
                "created_at": material.get("created_at"),
                "sender_role": None,
                "receiver_role": None,
                "train_record_count": fit.get("train_record_count"),
                "holdout_record_count": fit.get("holdout_record_count"),
                "train_pair_count": fit.get("train_pair_count"),
                "holdout_pair_count": fit.get("holdout_pair_count"),
                "record_persisted": False,
                "pair_vectors_persisted": False,
                "production_route": False,
            })
        entries.sort(key=lambda item: (item.get("created_at") or 0, item["candidate_id"]), reverse=True)
        return entries[:MAX_CANDIDATES]
