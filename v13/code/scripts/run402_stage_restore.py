#!/usr/bin/env python3
"""Run402: inspect/restore an observed Run401 stage-1 archive; NEVER run native inference."""
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

import run394_step2_fresh as r394
import run397_step2_resume as resume
from v13.models import catalog

SOURCE_HEAD = "c0facf60c3286064e15bc06de104c85d9344382a"
HEX = re.compile(r"[0-9a-f]{64}\Z")
RAW_EXITS = ("RUN401_DEPS_EXIT.txt", "RUN401_BOOTSTRAP_EXIT.txt",
             "RUN401_NATIVE_EXIT.txt", "RUN401_AUDIT_EXIT.txt", "RUN401_PRIVACY_EXIT.txt")
MAX_MEMBER = 16_000_000
MAX_TOTAL = 90_000_000


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe_path(name):
    require(bool(name) and not name.startswith(("/", "\\")) and "\\" not in name,
            "UNSAFE_ARCHIVE_PATH")
    parts = name.split("/")
    require(all(p not in ("", ".", "..") for p in parts), "UNSAFE_ARCHIVE_PATH")
    require(name.startswith("RUN401_") and len(parts) == 1 or
            parts[0] == "run401-full" and len(parts) > 1, "UNEXPECTED_ARCHIVE_PATH")
    return name


def _read_members(path):
    files = {}
    total = 0
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None, "ZIP_CRC_FAIL")
        for entry in z.infolist():
            name = _safe_path(entry.filename)
            require(not entry.is_dir(), "UNEXPECTED_DIRECTORY_MEMBER")
            mode = entry.external_attr >> 16
            require(stat.S_IFMT(mode) != stat.S_IFLNK, "SYMLINK_MEMBER")
            require(name not in files, "DUPLICATE_MEMBER")
            require(entry.file_size <= MAX_MEMBER, "OVERSIZED_MEMBER")
            total += entry.file_size
            require(total <= MAX_TOTAL, "OVERSIZED_ARCHIVE")
            files[name] = z.read(entry)
    return files


def _verify_sha_manifest(files):
    require("RUN401_SHA256SUMS.txt" in files, "SHA_MANIFEST_MISSING")
    expected = {}
    for line in files["RUN401_SHA256SUMS.txt"].decode("utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (?:\./)?(.+)", line)
        require(match is not None, "INVALID_SHA_LINE")
        digest, name = match.groups()
        name = _safe_path(name)
        require(name not in expected and name != "RUN401_SHA256SUMS.txt",
                "DUPLICATE_OR_SELF_SHA")
        expected[name] = digest
    require(set(files) == set(expected) | {"RUN401_SHA256SUMS.txt"},
            "UNHASHED_OR_MISSING_MEMBER")
    for name, digest in expected.items():
        require(sha(files[name]) == digest, "MEMBER_SHA_MISMATCH:" + name)
    return expected


def _validate_native_tree(root, files):
    for name in RAW_EXITS:
        require(files.get(name, b"").decode("utf-8").strip() == "0",
                "STAGE1_PREREQUISITE_RED:" + name)
    require(files.get("RUN401_HEAD.txt", b"").decode("utf-8").strip() == SOURCE_HEAD,
            "STAGE1_SOURCE_HEAD_MISMATCH")
    manifest = json.loads((root / "RUN394_PREREGISTERED_FIXTURES.json").read_bytes())
    expected_manifest = r394.manifest(r394.FIXTURES, False, list(r394.ARMS), list(r394.SEEDS))
    require(manifest == expected_manifest, "FULL_FROZEN_MANIFEST_MISMATCH")
    progress = json.loads((root / "RUN397_PROGRESS.json").read_bytes())
    require(progress.get("status") == "INCOMPLETE" and
            set(progress.get("completed", {})) == {"O_s20"} and
            progress.get("failures_preserved") == {}, "STAGE1_PROGRESS_INVALID")
    require(progress.get("canonical_gate_pass") is False and
            progress.get("step2_exit") == "UTILITY_FAIL", "FALSE_GATE_PROMOTION")
    info = progress["completed"]["O_s20"]
    require(type(info) is dict and info.get("attempt") ==
            "attempts/O_s20/attempt-0001", "UNEXPECTED_STAGE1_ATTEMPT")
    attempt = root / info["attempt"]
    require(attempt.is_dir(), "STAGE1_ATTEMPT_MISSING")
    runner_sha = catalog()["runner"]["linux_binaries"]["linux-x86_64"]["sha256"]
    actual = resume.validate_completed(attempt, "O", 20, r394.FIXTURES,
                                       manifest, current_runner_sha=runner_sha)
    require(actual == info.get("validated") and actual["rows"] == 42,
            "STAGE1_VALIDATED_RECEIPT_MISMATCH")
    receipt = json.loads((attempt / "RUN397_ATTEMPT.json").read_bytes())
    require(receipt.get("schema") == resume.SCHEMA and
            receipt.get("status") == "COMPLETE" and
            receipt.get("validated") == actual, "STAGE1_RECEIPT_MISMATCH")
    postflight = json.loads(files["RUN401_POSTFLIGHT.json"])
    require(postflight.get("stage") == "NATIVE_FULL_COHORT_PARTIAL" and
            postflight.get("completed") == ["O_s20"] and
            postflight.get("rows_verified") == 42 and
            postflight.get("remaining_arms") == 8 and
            postflight.get("validated") == actual and
            postflight.get("canonical_gate_pass") is False and
            postflight.get("step2_exit") == "UTILITY_FAIL" and
            postflight.get("redmi_measured") is False, "STAGE1_POSTFLIGHT_INVALID")
    return {"completed": ["O_s20"], "rows_verified": 42, "remaining_arms": 8,
            "validated": actual}


def inspect_archive(archive, expected_sha):
    """Return a report and validated members; no destination is touched."""
    report = {"run": "Run402", "source_run": "Run401", "status": "STAGE1_RED_PRESERVED",
              "source_head_expected": SOURCE_HEAD, "canonical_gate_pass": False,
              "step2_exit": "UTILITY_FAIL", "redmi_measured": False,
              "native_rerun": False, "errors": []}
    files = None
    try:
        require(type(expected_sha) is str and HEX.fullmatch(expected_sha),
                "EXPECTED_SHA_INVALID")
        archive = Path(archive)
        raw = archive.read_bytes()
        report["zip_sha256"] = sha(raw)
        require(report["zip_sha256"] == expected_sha, "ZIP_SHA_MISMATCH")
        files = _read_members(archive)
        digests = _verify_sha_manifest(files)
        with tempfile.TemporaryDirectory(prefix="run402-inspect-") as td:
            root = Path(td) / "run401-full"
            for name, data in files.items():
                if not name.startswith("run401-full/"):
                    continue
                dest = Path(td) / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            result = _validate_native_tree(root, files)
        report.update(result)
        report["members_verified"] = len(digests)
        report["status"] = "STAGE1_RESTORE_VERIFIED"
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError,
            zipfile.BadZipFile, UnicodeError) as exc:
        report["errors"].append(type(exc).__name__ + ": " + str(exc)[:350])
        files = None
    return report, files


def restore_archive(archive, expected_sha, destination):
    """Atomically install only the verified work tree into a fresh operator-owned directory."""
    report, files = inspect_archive(archive, expected_sha)
    if files is None:
        return report
    dest = Path(destination).expanduser().absolute()
    try:
        require(not dest.exists() and not dest.is_symlink(), "DESTINATION_NOT_FRESH")
        require(dest.parent.is_dir(), "DESTINATION_PARENT_MISSING")
        require(not any(p.is_symlink() for p in (dest, *dest.parents)),
                "DESTINATION_SYMLINK")
        with tempfile.TemporaryDirectory(prefix="run402-stage-", dir=dest.parent) as td:
            stage = Path(td) / "run401-full"
            for name, data in files.items():
                if not name.startswith("run401-full/"):
                    continue
                path = Path(td) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            for name, data in files.items():
                if name.startswith("run401-full/"):
                    require((Path(td) / name).read_bytes() == data,
                            "RESTORED_BYTES_MISMATCH:" + name)
            os.replace(stage, dest)
        report["restored_work"] = str(dest)
    except (OSError, ValueError) as exc:
        report["status"] = "STAGE1_RED_PRESERVED"
        report["errors"].append(type(exc).__name__ + ": " + str(exc)[:350])
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--destination", type=Path, help="fresh work tree; omitted = read-only audit")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = (restore_archive(args.archive, args.expected_sha256, args.destination)
              if args.destination else inspect_archive(args.archive, args.expected_sha256)[0])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "errors": result["errors"],
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(0 if result["status"] == "STAGE1_RESTORE_VERIFIED" else 2)


if __name__ == "__main__":
    main()
