#!/usr/bin/env python3
"""Run418: import the exact Run413 Actions no-model ZIP, restoring only declared empty dirs.

GitHub artifact upload omits empty directories. The signed Run409 manifest
retains their names. This importer checks ZIP bytes, rejects unsafe members,
reconstructs only manifest-declared directories, and runs independent Run413
verification before publishing an atomic fresh work tree. No native inference.
"""
import argparse
import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path

import run413_export_receipt_gate as gate
import run409_safe_export as safe


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def import_artifact(archive, expected_sha256, run411_report, destination):
    archive = Path(archive).expanduser().absolute()
    dest = Path(destination).expanduser().absolute()
    require(type(expected_sha256) is str and gate.HEX.fullmatch(expected_sha256),
            "INVALID_ARTIFACT_SHA")
    require(archive.is_file() and not archive.is_symlink() and
            archive.stat().st_nlink == 1, "ARTIFACT_SOURCE_UNSAFE")
    require(sha_file(archive) == expected_sha256, "ARTIFACT_SHA_MISMATCH")
    require(dest.parent.is_dir() and not dest.exists() and not dest.is_symlink() and
            not any(p.is_symlink() for p in (dest, *dest.parents)),
            "DESTINATION_NOT_FRESH_OR_UNSAFE")
    require(type(run411_report) is dict and
            run411_report.get("status") == "STAGE2_NATIVE_PARTIAL_NO_PROMOTION",
            "RUN413_NATIVE_NOT_GREEN")
    with zipfile.ZipFile(archive, "r") as z:
        items = z.infolist()
        names = [i.filename for i in items]
        require(len(set(names)) == len(names), "DUPLICATE_ARTIFACT_MEMBER")
        require(gate.MANIFEST in names, "ARTIFACT_MANIFEST_MISSING")
        files = {}
        archive_dirs = set()
        total = 0
        for item in items:
            name = item.filename
            clean = name[:-1] if item.is_dir() else name
            gate.safe_rel(clean)
            mode = (item.external_attr >> 16) & 0xffff
            kind = stat.S_IFMT(mode)
            require(kind in ((0, stat.S_IFDIR) if item.is_dir() else
                             (0, stat.S_IFREG)), "ARTIFACT_SPECIAL_FILE")
            if item.is_dir():
                archive_dirs.add(clean)
            else:
                require(item.file_size <= gate.MAX_FILE, "ARTIFACT_FILE_TOO_LARGE")
                total += item.file_size
                require(total <= gate.MAX_TOTAL, "ARTIFACT_TOTAL_TOO_LARGE")
                files[name] = item
        manifest_raw = z.read(gate.MANIFEST)
        require(hashlib.sha256(manifest_raw).hexdigest() ==
                run411_report.get("safe_export", {}).get("manifest_sha256"),
                "ARTIFACT_MANIFEST_SHA_MISMATCH")
        manifest = json.loads(manifest_raw)
        copied = manifest.get("copied")
        directories = manifest.get("directories")
        require(type(copied) is dict and type(directories) is list and
                len(set(directories)) == len(directories),
                "ARTIFACT_INVENTORY_INVALID")
        expected = set(copied) | {gate.MANIFEST}
        require(set(files) == expected, "ARTIFACT_FILE_INVENTORY_MISMATCH")
        declared_dirs = set(directories) - {"."}
        require("." in directories and all(gate.safe_rel(d) for d in declared_dirs) and
                archive_dirs <= declared_dirs, "ARTIFACT_DIRECTORY_INVENTORY_MISMATCH")
        require(all(item["bytes"] == files[name].file_size
                    for name, item in copied.items()),
                "ARTIFACT_FILE_SIZE_MISMATCH")
        with tempfile.TemporaryDirectory(prefix="run418-import-", dir=dest.parent) as td:
            stage = Path(td) / "work"
            stage.mkdir()
            for name in sorted(declared_dirs, key=lambda x: (x.count("/"), x)):
                (stage / name).mkdir(parents=True, exist_ok=False)
            for name, item in sorted(files.items()):
                target = stage / name
                require(target.parent.is_dir(), "ARTIFACT_PARENT_MISSING")
                h = hashlib.sha256()
                with z.open(item) as reader, target.open("xb") as writer:
                    while block := reader.read(1024 * 1024):
                        h.update(block)
                        writer.write(block)
                    writer.flush()
                    os.fsync(writer.fileno())
                expected_digest = (hashlib.sha256(manifest_raw).hexdigest()
                                   if name == gate.MANIFEST else copied[name]["sha256"])
                require(h.hexdigest() == expected_digest, "ARTIFACT_MEMBER_SHA_MISMATCH")
            verified = gate.verify(stage, run411_report)
            require(verified["status"] == "RUN413_EXPORT_VERIFIED_NATIVE_PARTIAL" and
                    verified["native_rows"] == 84, "ARTIFACT_NATIVE_84_ROWS_UNVERIFIED")
            safe._rename_noreplace(stage, dest)
    empty_leaves = {d for d in declared_dirs
                    if not any(other.startswith(d + "/") for other in declared_dirs)
                    and not any(name.startswith(d + "/") for name in copied)}
    return {"run": "Run418", "status": "RUN418_NO_MODEL_IMPORT_VERIFIED",
            "artifact_sha256": expected_sha256,
            "manifest_sha256": verified["manifest_sha256"],
            "copied_files": verified["copied_files"],
            "copied_bytes": verified["copied_bytes"],
            "restored_empty_directories": len(empty_leaves),
            "restored_manifest_directories_without_zip_entries":
                len(declared_dirs - archive_dirs),
            "native_rows_verified": 84, "restored_work": str(dest),
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "redmi_measured": False, "jepa_weight": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--run411-report", type=Path, required=True)
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = import_artifact(args.archive, args.expected_sha256,
                                 json.loads(args.run411_report.read_text()),
                                 args.destination)
        code = 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError, zipfile.BadZipFile) as exc:
        result = {"run": "Run418", "status": "RUN418_IMPORT_RED_PRESERVED",
                  "errors": [type(exc).__name__ + ": " + str(exc)[:300]],
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}
        code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
