#!/usr/bin/env python3
"""Run409: safe, hash-closed native work export without dereferencing model symlinks."""
import argparse
import fcntl
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from run407_stream_stage1 import _rename_noreplace

CHUNK = 1024 * 1024
FORBIDDEN_EXT = (".gguf", ".safetensors", ".cact", ".ckpt", ".pth", ".pt")
MANIFEST = "RUN409_EXPORT_MANIFEST.json"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def allowed_link(path, root, installed):
    rel = path.relative_to(root)
    parts = rel.parts
    if len(parts) < 5 or parts[0] != "attempts" or parts[-1] not in ("models", "bin"):
        return False
    if not parts[1].startswith(("O_s", "P_s", "S_s")):
        return False
    if not parts[2].startswith("attempt-") or not parts[2][8:].isdigit():
        return False
    target = installed / parts[-1]
    return target.is_dir() and not target.is_symlink() and path.resolve() == target.resolve()


def _copy_regular(source, target):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(source, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), "NONREGULAR_SOURCE_FILE")
        require(before.st_nlink == 1, "HARDLINK_SOURCE_REJECTED")
        h = hashlib.sha256()
        size = 0
        with os.fdopen(os.dup(fd), "rb") as reader, target.open("xb") as writer:
            while True:
                block = reader.read(CHUNK)
                if not block:
                    break
                writer.write(block)
                h.update(block)
                size += len(block)
            writer.flush()
            os.fsync(writer.fileno())
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                "SOURCE_CHANGED_DURING_COPY")
        require(size == before.st_size and sha_file(target) == h.hexdigest(),
                "EXPORTED_FILE_HASH_MISMATCH")
        return {"sha256": h.hexdigest(), "bytes": size}
    finally:
        os.close(fd)


def export(work, installed, destination):
    report = {"run": "Run409", "status": "EXPORT_RED_PRESERVED",
              "errors": [], "native_inference_started": False,
              "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
              "redmi_measured": False, "jepa_weight": 0}
    try:
        work = Path(work).expanduser().absolute()
        installed = Path(installed).expanduser().absolute()
        dest = Path(destination).expanduser().absolute()
        require(work.is_dir() and not work.is_symlink(), "WORK_ROOT_UNSAFE")
        require(installed.is_dir() and not installed.is_symlink(), "INSTALLED_ROOT_UNSAFE")
        require(not dest.exists() and not dest.is_symlink(), "DESTINATION_NOT_FRESH")
        require(dest.parent.is_dir() and
                not any(p.is_symlink() for p in (dest, *dest.parents)),
                "DESTINATION_PARENT_UNSAFE")
        require(not any(p.is_symlink() for p in (work, *work.parents)),
                "WORK_PARENT_SYMLINK")
        lockpath = work / "RUN397_OWNER.lock"
        require(not lockpath.is_symlink(), "OWNER_LOCK_SYMLINK")
        lock = lockpath.open("rb") if lockpath.is_file() else None
        try:
            if lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise ValueError("NATIVE_OWNER_ACTIVE") from exc
            with tempfile.TemporaryDirectory(prefix="run409-export-", dir=dest.parent) as td:
                stage = Path(td) / "work"
                stage.mkdir()
                copied = {}
                omitted = []
                directories = []
                for current, dirs, files in os.walk(work, topdown=True, followlinks=False):
                    here = Path(current)
                    rel_dir = here.relative_to(work)
                    (stage / rel_dir).mkdir(parents=True, exist_ok=True)
                    directories.append(str(rel_dir))
                    for name in sorted(list(dirs)):
                        path = here / name
                        if path.is_symlink():
                            require(allowed_link(path, work, installed),
                                    "UNSAFE_SYMLINK_DIRECTORY:" + str(path.relative_to(work)))
                            omitted.append(str(path.relative_to(work)))
                            dirs.remove(name)
                        else:
                            require(path.is_dir(), "NON_DIRECTORY_CHILD")
                    dirs.sort()
                    for name in sorted(files):
                        path = here / name
                        rel = path.relative_to(work)
                        require(not path.is_symlink(), "UNSAFE_SYMLINK_FILE:" + str(rel))
                        require(path.is_file(), "NONREGULAR_FILE:" + str(rel))
                        require(name != MANIFEST and
                                not name.lower().endswith(FORBIDDEN_EXT) and
                                "models" not in rel.parts,
                                "MODEL_OR_MANIFEST_FILE_IN_WORK:" + str(rel))
                        copied[str(rel)] = _copy_regular(path, stage / rel)
                require(copied, "EMPTY_EXPORT")
                for name, info in copied.items():
                    require(sha_file(work / name) == info["sha256"],
                            "SOURCE_CHANGED_AFTER_COPY:" + name)
                manifest = {"schema": "RUN409_SAFE_NATIVE_EXPORT_V1",
                            "source_run": "Run397", "copied": copied,
                            "omitted_installed_symlinks": sorted(omitted),
                            "directories": sorted(directories),
                            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}
                (stage / MANIFEST).write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
                _rename_noreplace(stage, dest)
            report.update({"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                           "copied_files": len(copied),
                           "copied_bytes": sum(v["bytes"] for v in copied.values()),
                           "omitted_installed_symlinks": sorted(omitted),
                           "manifest_sha256": sha_file(dest / MANIFEST),
                           "export_path": str(dest)})
        finally:
            if lock:
                lock.close()
    except (OSError, ValueError, TypeError) as exc:
        report["errors"].append(type(exc).__name__ + ": " + str(exc)[:350])
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--installed-home", type=Path, required=True)
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = export(args.work, args.installed_home, args.destination)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "errors": result["errors"],
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(0 if result["status"] == "EXPORT_VERIFIED_NO_MODEL_WEIGHTS" else 2)


if __name__ == "__main__":
    main()
