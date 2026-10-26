#!/usr/bin/env python3
"""Run408: exact original Run401 ZIP stream audit with registered model-weight exclusion.

The original immutable ZIP is retained. This derives a *private* reusable native
work tree without duplicating public model weights. Never starts inference.
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

import run407_stream_stage1 as base
import run402_stage_restore as stage
from v13.models import catalog


def require(ok, reason):
    return base.require(ok, reason)


def _registered_models():
    """Exact immutable catalog filename -> allowed (size, sha256, role) set."""
    found = {}
    for role, model in catalog()["models"].items():
        entries = list(model.get("files", []))
        entries += list(model.get("platforms", {}).get("linux-x86_64", []))
        for f in entries:
            key = f["local_name"]
            found.setdefault(key, set()).add((f["size"], f["sha256"], role))
    return found


def _model_path(name):
    parts = Path(name).parts
    # Only the original registered arm-home models/ subtree can be omitted.
    return (len(parts) >= 7 and parts[0] == "run401-full" and
            parts[1:3] == ("attempts", "O_s20") and
            parts[3].startswith("attempt-") and parts[3][8:].isdigit() and
            "models" in parts[4:-1])



def _binary_path(name):
    """Unlisted arm-home bin bytes are preserved, never executed as a runner."""
    parts = Path(name).parts
    return (len(parts) >= 7 and parts[0] == "run401-full" and
            parts[1:3] == ("attempts", "O_s20") and
            parts[3].startswith("attempt-") and parts[3][8:].isdigit() and
            "bin" in parts[4:-1])


def _entry_name(info):
    name = stage._safe_path(info.filename)
    require(not info.is_dir(), "DIRECTORY_MEMBER")
    require(not (info.flag_bits & 1), "ENCRYPTED_MEMBER")
    require(stat.S_IFMT(info.external_attr >> 16) != stat.S_IFLNK, "SYMLINK_MEMBER")
    require(0 <= info.file_size <= base.MAX_MEMBER, "MEMBER_OVERSIZED")
    if name.lower().endswith((".gguf", ".safetensors", ".cact", ".ckpt", ".pth", ".pt")):
        require(_model_path(name), "UNREGISTERED_MODEL_PATH:" + name)
    return name


def _inventory(z):
    infos = {}
    total = 0
    for info in z.infolist():
        name = _entry_name(info)
        require(name not in infos, "DUPLICATE_MEMBER")
        infos[name] = info
        total += info.file_size
        require(total <= base.MAX_TOTAL, "TOTAL_UNCOMPRESSED_OVERSIZED")
    require("RUN401_SHA256SUMS.txt" in infos, "SHA_MANIFEST_MISSING")
    require(infos["RUN401_SHA256SUMS.txt"].file_size <= base.MAX_MANIFEST,
            "SHA_MANIFEST_OVERSIZED")
    require(set(base.SMALL) <= set(infos), "REQUIRED_NATIVE_REPORT_MISSING")
    return infos, total



def _original_manifest(z, infos):
    """Original find -type f manifest may omit dereferenced *registered* symlinks."""
    raw = z.read(infos["RUN401_SHA256SUMS.txt"]).decode("utf-8")
    expected = {}
    for line in raw.splitlines():
        m = re.fullmatch(r"([0-9a-f]{64})  (?:\./)?(.+)", line)
        require(m is not None, "INVALID_SHA_MANIFEST_LINE")
        digest, name = m.groups()
        stage._safe_path(name)
        require(name != "RUN401_SHA256SUMS.txt" and name not in expected,
                "DUPLICATE_OR_SELF_SHA")
        expected[name] = digest
    require(set(expected) <= set(infos), "UNHASHED_OR_MISSING_MEMBER")
    unlisted = set(infos) - set(expected) - {"RUN401_SHA256SUMS.txt"}
    require(all(_model_path(n) or _binary_path(n) for n in unlisted),
            "UNHASHED_OR_MISSING_MEMBER")
    return expected, sorted(unlisted)


def _verify_and_stage(archive, expected_sha, temporary):
    archive = Path(archive)
    require(type(expected_sha) is str and base.HEX.fullmatch(expected_sha),
            "INVALID_EXPECTED_SHA")
    require(archive.is_file() and not archive.is_symlink(), "ARCHIVE_MISSING_OR_SYMLINK")
    require(0 < archive.stat().st_size <= base.MAX_ARCHIVE, "ARCHIVE_SIZE_OUT_OF_BOUNDS")
    require(base._hash_file(archive) == expected_sha, "ZIP_SHA_MISMATCH")
    root = Path(temporary) / "run401-full"
    root.mkdir()
    registered = _registered_models()
    with zipfile.ZipFile(archive) as z:
        infos, total = _inventory(z)
        expected, unlisted = _original_manifest(z, infos)
        # Reject unknown model-home files rather than discarding evidence.
        for name in infos:
            if _model_path(name):
                require(Path(name).name in registered,
                        "UNKNOWN_MODEL_HOME_FILE:" + name)
        staged_bytes = sum(i.file_size for n, i in infos.items()
                           if n.startswith("run401-full/") and not _model_path(n))
        require(shutil.disk_usage(temporary).free > staged_bytes + 256_000_000,
                "INSUFFICIENT_STAGE_DISK")
        small = {}
        omitted = []
        unlisted_bin_hashes = {}
        for name, info in infos.items():
            h = hashlib.sha256()
            output = None
            if name.startswith("run401-full/") and not _model_path(name):
                output = Path(temporary) / name
                output.parent.mkdir(parents=True, exist_ok=True)
            handle = output.open("xb") if output is not None else None
            try:
                with z.open(info, "r") as member:
                    while True:
                        block = member.read(base.CHUNK)
                        if not block:
                            break
                        h.update(block)
                        if handle is not None:
                            handle.write(block)
                        if name in base.SMALL:
                            small.setdefault(name, bytearray()).extend(block)
                            require(len(small[name]) <= 2_000_000, "NATIVE_REPORT_OVERSIZED")
            finally:
                if handle is not None:
                    handle.close()
            actual = h.hexdigest()
            if name in expected:
                require(actual == expected[name], "MEMBER_SHA_MISMATCH:" + name)
            elif _binary_path(name):
                unlisted_bin_hashes[name] = {"sha256": actual, "bytes": info.file_size,
                                             "provenance": "ORIGINAL_ZIP_SHA_ONLY_NOT_EXECUTED"}
            if _model_path(name):
                matches = [role for size, digest, role in registered[Path(name).name]
                           if size == info.file_size and digest == actual]
                require(bool(matches), "REGISTERED_MODEL_SHA_MISMATCH:" + name)
                omitted.append({"path": name, "size": info.file_size,
                                "sha256": actual, "registered_roles": sorted(matches)})
        require(small["RUN401_HEAD.txt"].decode("utf-8").strip() == stage.SOURCE_HEAD,
                "STAGE1_SOURCE_HEAD_MISMATCH")
        native = stage._validate_native_tree(root, small)
        return {"native": native, "members_verified": len(infos) - 1,
                "omitted_unlisted_in_manifest": [n for n in unlisted if _model_path(n)],
                "unlisted_binary_members": [n for n in unlisted if _binary_path(n)],
                "unlisted_binary_hashes": unlisted_bin_hashes,
                "original_zip_sha256": expected_sha, "original_member_bytes": total,
                "staged_work_bytes": staged_bytes, "omitted_registered_models": omitted,
                "omitted_bytes": sum(m["size"] for m in omitted),
                "all_member_sha_checked": True, "zip_crc_checked": True,
                "original_raw_retained_external": True}


def audit_or_restore(archive, expected_sha, destination=None):
    report = {"run": "Run408", "source_run": "Run401",
              "status": "FILTERED_STAGE1_RED_PRESERVED", "errors": [],
              "native_inference_started": False, "redmi_measured": False,
              "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
              "jepa_weight": 0}
    try:
        if destination is None:
            with tempfile.TemporaryDirectory(prefix="run408-audit-") as temp:
                checked = _verify_and_stage(archive, expected_sha, temp)
        else:
            dest = Path(destination).expanduser().absolute()
            require(not dest.exists() and not dest.is_symlink(), "DESTINATION_NOT_FRESH")
            require(dest.parent.is_dir() and
                    not any(p.is_symlink() for p in (dest, *dest.parents)),
                    "DESTINATION_PARENT_UNSAFE")
            with tempfile.TemporaryDirectory(prefix="run408-stage-", dir=dest.parent) as temp:
                checked = _verify_and_stage(archive, expected_sha, temp)
                base._rename_noreplace(Path(temp) / "run401-full", dest)
            report["restored_work"] = str(dest)
        report.update(checked)
        report["status"] = "FILTERED_STAGE1_VERIFIED_NO_PROMOTION"
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
    raise SystemExit(0 if report["status"] == "FILTERED_STAGE1_VERIFIED_NO_PROMOTION" else 2)


if __name__ == "__main__":
    main()
