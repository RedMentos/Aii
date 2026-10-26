#!/usr/bin/env python3
"""Run407: stream-verify an observed Run401 ZIP and atomically restore its full work tree.

No model inference. Original ZIP remains untouched. Native origin must be separately bound.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path

import run402_stage_restore as stage

CHUNK = 1024 * 1024
MAX_ARCHIVE = 2_500_000_000
MAX_MEMBER = 8_000_000_000
MAX_TOTAL = 9_000_000_000
MAX_MANIFEST = 1_000_000
SMALL = set(stage.RAW_EXITS) | {"RUN401_HEAD.txt", "RUN401_POSTFLIGHT.json"}
HEX = re.compile(r"[0-9a-f]{64}\Z")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _hash_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _entry_name(info):
    name = stage._safe_path(info.filename)
    require(not info.is_dir(), "DIRECTORY_MEMBER")
    require(not (info.flag_bits & 1), "ENCRYPTED_MEMBER")
    require(stat.S_IFMT(info.external_attr >> 16) != stat.S_IFLNK, "SYMLINK_MEMBER")
    require(not name.lower().endswith((".gguf", ".safetensors", ".ckpt", ".pth", ".pt")),
            "MODEL_WEIGHTS_IN_ARTIFACT")
    require(0 <= info.file_size <= MAX_MEMBER, "MEMBER_OVERSIZED")
    return name


def _inventory(z):
    infos = {}
    total = 0
    for info in z.infolist():
        name = _entry_name(info)
        require(name not in infos, "DUPLICATE_MEMBER")
        infos[name] = info
        total += info.file_size
        require(total <= MAX_TOTAL, "TOTAL_UNCOMPRESSED_OVERSIZED")
    require("RUN401_SHA256SUMS.txt" in infos, "SHA_MANIFEST_MISSING")
    require(infos["RUN401_SHA256SUMS.txt"].file_size <= MAX_MANIFEST,
            "SHA_MANIFEST_OVERSIZED")
    require(set(SMALL) <= set(infos), "REQUIRED_NATIVE_REPORT_MISSING")
    return infos, total


def _manifest(z, infos):
    raw = z.read(infos["RUN401_SHA256SUMS.txt"]).decode("utf-8")
    expected = {}
    for line in raw.splitlines():
        m = re.fullmatch(r"([0-9a-f]{64})  (?:\./)?(.+)", line)
        require(m is not None, "INVALID_SHA_MANIFEST_LINE")
        digest, name = m.groups()
        stage._safe_path(name)
        require(name not in expected and name != "RUN401_SHA256SUMS.txt",
                "DUPLICATE_OR_SELF_SHA")
        expected[name] = digest
    require(set(infos) == set(expected) | {"RUN401_SHA256SUMS.txt"},
            "UNHASHED_OR_MISSING_MEMBER")
    return expected


def _verify_and_stage(archive, expected_sha, temporary):
    """All member bytes SHA/CRC-verified; stage only complete run401-full subtree."""
    archive = Path(archive)
    require(type(expected_sha) is str and HEX.fullmatch(expected_sha), "INVALID_EXPECTED_SHA")
    require(archive.is_file() and not archive.is_symlink(), "ARCHIVE_MISSING_OR_SYMLINK")
    require(0 < archive.stat().st_size <= MAX_ARCHIVE, "ARCHIVE_SIZE_OUT_OF_BOUNDS")
    require(_hash_file(archive) == expected_sha, "ZIP_SHA_MISMATCH")
    root = Path(temporary) / "run401-full"
    root.mkdir()
    with zipfile.ZipFile(archive) as z:
        infos, total = _inventory(z)
        expected = _manifest(z, infos)
        work_bytes = sum(info.file_size for name, info in infos.items()
                         if name.startswith("run401-full/"))
        require(shutil.disk_usage(temporary).free > work_bytes + 256_000_000,
                "INSUFFICIENT_STAGE_DISK")
        small = {}
        for name, info in infos.items():
            h = hashlib.sha256()
            output = None
            if name.startswith("run401-full/"):
                output = Path(temporary) / name
                output.parent.mkdir(parents=True, exist_ok=True)
            if output is not None:
                handle = output.open("xb")
            else:
                handle = None
            try:
                with z.open(info, "r") as member:
                    while True:
                        block = member.read(CHUNK)
                        if not block:
                            break
                        h.update(block)
                        if handle is not None:
                            handle.write(block)
                        if name in SMALL:
                            small.setdefault(name, bytearray()).extend(block)
                            require(len(small[name]) <= 2_000_000, "NATIVE_REPORT_OVERSIZED")
            finally:
                if handle is not None:
                    handle.close()
            if name != "RUN401_SHA256SUMS.txt":
                require(h.hexdigest() == expected[name], "MEMBER_SHA_MISMATCH:" + name)
        require(small["RUN401_HEAD.txt"].decode("utf-8").strip() == stage.SOURCE_HEAD,
                "STAGE1_SOURCE_HEAD_MISMATCH")
        native = stage._validate_native_tree(root, small)
        return {"native": native, "members_verified": len(expected),
                "uncompressed_bytes": total, "staged_work_bytes": work_bytes,
                "zip_sha256": expected_sha, "zip_crc_checked": True,
                "all_member_sha_checked": True}


def audit_or_restore(archive, expected_sha, destination=None):
    report = {"run": "Run407", "source_run": "Run401",
              "status": "STAGE1_STREAM_RED_PRESERVED", "errors": [],
              "native_inference_started": False, "redmi_measured": False,
              "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
              "jepa_weight": 0}
    try:
        if destination is None:
            with tempfile.TemporaryDirectory(prefix="run407-audit-") as temp:
                checked = _verify_and_stage(archive, expected_sha, temp)
        else:
            dest = Path(destination).expanduser().absolute()
            require(not dest.exists() and not dest.is_symlink(), "DESTINATION_NOT_FRESH")
            require(dest.parent.is_dir() and
                    not any(p.is_symlink() for p in (dest, *dest.parents)),
                    "DESTINATION_PARENT_UNSAFE")
            with tempfile.TemporaryDirectory(prefix="run407-stage-", dir=dest.parent) as temp:
                checked = _verify_and_stage(archive, expected_sha, temp)
                require(not dest.exists(), "DESTINATION_RACE")
                os.replace(Path(temp) / "run401-full", dest)
            report["restored_work"] = str(dest)
        report.update(checked)
        report["status"] = "STAGE1_STREAM_VERIFIED_NO_PROMOTION"
        report["rows_verified"] = 42
        report["remaining_arms"] = 8
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError, zipfile.BadZipFile, UnicodeError, EOFError) as exc:
        report["errors"].append(type(exc).__name__ + ": " + str(exc)[:350])
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--destination", type=Path, help="fresh private work tree; omit for audit")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = audit_or_restore(args.archive, args.expected_sha256, args.destination)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "errors": report["errors"],
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(0 if report["status"] == "STAGE1_STREAM_VERIFIED_NO_PROMOTION" else 2)


if __name__ == "__main__":
    main()
