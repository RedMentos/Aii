#!/usr/bin/env python3
"""Run461: atomically import O_s22 no-model Actions ZIP and verify 294 native rows.

GitHub Actions drops empty directory entries. Reconstruct only manifest-declared
directories, verify outer ZIP and inner manifest/file hashes, then run the
independent Run460 seven-receipt 294-row verifier BEFORE atomic publication. No inference, training or STEP2 gate promotion.
"""
import argparse
import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path

import run409_safe_export as safe
import run413_export_receipt_gate as gate
import run460_verify_native294 as audit


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def import_stage7(archive, expected_sha256, report, destination):
    archive = Path(archive).expanduser().absolute()
    dest = Path(destination).expanduser().absolute()
    require(type(expected_sha256) is str and gate.HEX.fullmatch(expected_sha256),
            "INVALID_ARTIFACT_SHA")
    require(archive.is_file() and not archive.is_symlink() and
            archive.stat().st_nlink == 1, "ARTIFACT_SOURCE_UNSAFE")
    require(audit.sha_file(archive) == expected_sha256, "ARTIFACT_SHA_MISMATCH")
    require(dest.parent.is_dir() and not dest.exists() and not dest.is_symlink() and
            not any(p.is_symlink() for p in (dest, *dest.parents)),
            "DESTINATION_NOT_FRESH_OR_UNSAFE")
    require(type(report) is dict and
            report.get("run") == "Run459" and
            report.get("status") == "STAGE7_NATIVE_PARTIAL_NO_PROMOTION" and
            report.get("rows_verified") == 294 and
            report.get("canonical_gate_pass") is False and
            report.get("step2_exit") == "UTILITY_FAIL", "NATIVE_294_NOT_GREEN")
    with zipfile.ZipFile(archive) as z:
        items = z.infolist()
        names = [i.filename for i in items]
        require(len(set(names)) == len(names) and gate.MANIFEST in names,
                "DUPLICATE_OR_MISSING_ARTIFACT_MANIFEST")
        files = {}
        archive_dirs = set()
        total = 0
        for item in items:
            clean = item.filename[:-1] if item.is_dir() else item.filename
            gate.safe_rel(clean)
            kind = stat.S_IFMT((item.external_attr >> 16) & 0xffff)
            require(kind in ((0, stat.S_IFDIR) if item.is_dir() else
                             (0, stat.S_IFREG)), "ARTIFACT_SPECIAL_FILE")
            if item.is_dir():
                archive_dirs.add(clean)
            else:
                require(item.file_size <= gate.MAX_FILE, "ARTIFACT_FILE_TOO_LARGE")
                total += item.file_size
                require(total <= gate.MAX_TOTAL, "ARTIFACT_TOTAL_TOO_LARGE")
                files[item.filename] = item
        raw = z.read(gate.MANIFEST)
        manifest_sha = hashlib.sha256(raw).hexdigest()
        require(manifest_sha == report.get("safe_export", {}).get("manifest_sha256"),
                "ARTIFACT_MANIFEST_SHA_MISMATCH")
        manifest = json.loads(raw)
        copied = manifest.get("copied")
        dirs = manifest.get("directories")
        require(type(copied) is dict and type(dirs) is list and
                len(set(dirs)) == len(dirs) and "." in dirs,
                "ARTIFACT_INVENTORY_INVALID")
        declared = set(dirs) - {"."}
        for name in declared:
            gate.safe_rel(name)
        require(archive_dirs <= declared and
                set(files) == set(copied) | {gate.MANIFEST},
                "ARTIFACT_INVENTORY_MISMATCH")
        for name, info in copied.items():
            require(type(info) is dict and type(info.get("bytes")) is int and
                    info["bytes"] == files[name].file_size,
                    "ARTIFACT_SIZE_MISMATCH")
        with tempfile.TemporaryDirectory(prefix="run461-import-", dir=dest.parent) as td:
            stage = Path(td) / "work"
            stage.mkdir()
            for name in sorted(declared, key=lambda x: (x.count("/"), x)):
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
                expected = manifest_sha if name == gate.MANIFEST else copied[name]["sha256"]
                require(h.hexdigest() == expected, "ARTIFACT_MEMBER_SHA_MISMATCH")
            checked = audit.verify(stage, report)
            require(checked["status"] == "RUN460_NATIVE_294_INDEPENDENTLY_VERIFIED" and
                    checked["rows_verified"] == 294 and
                    checked["canonical_gate_pass"] is False and
                    checked["step2_exit"] == "UTILITY_FAIL",
                    "NATIVE_294_NOT_VERIFIED")
            safe._rename_noreplace(stage, dest)
    return {"run": "Run461", "status": "RUN461_NATIVE294_IMPORTED_VERIFIED",
            "artifact_sha256": expected_sha256,
            "manifest_sha256": checked["manifest_sha256"],
            "rows_verified": 294, "copied_files": checked["copied_files"],
            "copied_bytes": checked["copied_bytes"],
            "restored_work": str(dest),
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "redmi_measured": False, "jepa_weight": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--stage7-report", type=Path, required=True)
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = import_stage7(args.archive, args.expected_sha256,
                               json.loads(args.stage7_report.read_text()),
                               args.destination)
        code = 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError, zipfile.BadZipFile) as exc:
        result = {"run": "Run461", "status": "RUN461_NATIVE294_IMPORT_RED_PRESERVED",
                  "errors": [type(exc).__name__ + ": " + str(exc)[:350]],
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                  "redmi_measured": False, "jepa_weight": 0}
        code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
