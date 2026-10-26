#!/usr/bin/env python3
"""Run413: independently verify Run409's exported native work, never the model ZIP.

Fail closed on any unlisted file, symlink, hardlink, changed hash, model-shaped
path, registered model hash, or falsely promoted native/Redmi/JEPA claim.
"""
import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path

from v13.models import catalog

HEX = re.compile(r"[0-9a-f]{64}\Z")
MANIFEST = "RUN409_EXPORT_MANIFEST.json"
FORBIDDEN_EXT = (".gguf", ".safetensors", ".cact", ".ckpt", ".pth", ".pt")
MAX_FILE = 128_000_000
MAX_TOTAL = 300_000_000


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_rel(name):
    require(type(name) is str and bool(name) and not name.startswith("/") and
            "\\" not in name and
            all(part not in ("", ".", "..") for part in name.split("/")),
            "UNSAFE_EXPORT_PATH")
    require("models" not in name.split("/") and
            not name.lower().endswith(FORBIDDEN_EXT), "MODEL_PATH_IN_EXPORT")
    return name


def registered_model_hashes():
    result = set()
    for model in catalog()["models"].values():
        for item in (list(model.get("files", [])) +
                     list(model.get("platforms", {}).get("linux-x86_64", []))):
            result.add(item["sha256"])
    return result


def verify(destination, run411_report):
    root = Path(destination).absolute()
    require(root.is_dir() and not root.is_symlink(), "EXPORT_ROOT_UNSAFE")
    require(type(run411_report) is dict and
            run411_report.get("run") == "Run411", "INVALID_RUN411_REPORT")
    require(run411_report.get("native_execute_requested") is True and
            run411_report.get("canonical_gate_pass") is False and
            run411_report.get("step2_exit") == "UTILITY_FAIL" and
            run411_report.get("redmi_measured") is False and
            type(run411_report.get("jepa_weight")) is int and
            run411_report["jepa_weight"] == 0, "FALSE_RUN411_GATE_PROMOTION")
    exported = run411_report.get("safe_export")
    require(type(exported) is dict and
            exported.get("status") == "EXPORT_VERIFIED_NO_MODEL_WEIGHTS" and
            exported.get("errors") == [], "RUN409_EXPORT_NOT_GREEN")
    manifest_path = root / MANIFEST
    require(manifest_path.is_file() and not manifest_path.is_symlink(),
            "EXPORT_MANIFEST_UNSAFE")
    digest = sha_file(manifest_path)
    require(exported.get("manifest_sha256") == digest, "EXPORT_MANIFEST_SHA_MISMATCH")
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get("schema") == "RUN409_SAFE_NATIVE_EXPORT_V1" and
            manifest.get("source_run") == "Run397" and
            manifest.get("canonical_gate_pass") is False and
            manifest.get("step2_exit") == "UTILITY_FAIL", "EXPORT_MANIFEST_INVALID")
    copied = manifest.get("copied")
    omitted = manifest.get("omitted_installed_symlinks")
    dirs = manifest.get("directories")
    require(type(copied) is dict and bool(copied) and
            type(omitted) is list and type(dirs) is list, "EXPORT_INVENTORY_MISSING")
    require(len(set(omitted)) == len(omitted) and
            all(type(x) is str and
                re.fullmatch(r"attempts/(?:O|P|S)_s(?:20|21|22)/attempt-[0-9]+/.+/(?:models|bin)", x)
                for x in omitted), "UNEXPECTED_OMITTED_SYMLINK")
    expected = {safe_rel(name) for name in copied}
    require(len(expected) == len(copied), "DUPLICATE_EXPORT_PATH")
    require("RUN397_PROGRESS.json" in expected and
            "RUN394_PREREGISTERED_FIXTURES.json" in expected,
            "FROZEN_PROGRESS_MISSING")
    observed = set()
    observed_dirs = set()
    total = 0
    models = registered_model_hashes()
    for current, folders, files in os.walk(root, topdown=True, followlinks=False):
        observed_dirs.add(Path(current).relative_to(root).as_posix())
        for folder in folders:
            p = Path(current) / folder
            require(not p.is_symlink() and p.is_dir(), "EXPORT_SYMLINK_DIRECTORY")
        for filename in files:
            p = Path(current) / filename
            require(not p.is_symlink(), "EXPORT_SYMLINK_FILE")
            info = p.stat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                    "EXPORT_NONREGULAR_OR_HARDLINK")
            rel = p.relative_to(root).as_posix()
            if rel == MANIFEST:
                continue
            safe_rel(rel)
            require(rel in copied, "UNLISTED_EXPORT_FILE:" + rel)
            record = copied[rel]
            require(type(record) is dict and
                    type(record.get("bytes")) is int and
                    record["bytes"] == info.st_size and
                    info.st_size <= MAX_FILE and
                    type(record.get("sha256")) is str and
                    HEX.fullmatch(record["sha256"]), "EXPORT_FILE_METADATA_INVALID")
            digest = sha_file(p)
            require(digest == record["sha256"] and digest not in models,
                    "EXPORT_HASH_OR_MODEL_IDENTITY_MISMATCH")
            total += info.st_size
            require(total <= MAX_TOTAL, "EXPORT_TOTAL_EXCEEDS_BUDGET")
            observed.add(rel)
    require(observed == expected, "MISSING_EXPORTED_FILE")
    require(len(set(dirs)) == len(dirs) and set(dirs) == observed_dirs,
            "DIRECTORY_INVENTORY_MISMATCH")
    require(exported.get("copied_files") == len(observed) and
            exported.get("copied_bytes") == total, "RUN409_RECEIPT_MISMATCH")
    progress = json.loads((root / "RUN397_PROGRESS.json").read_text())
    require(progress.get("canonical_gate_pass") is False and
            progress.get("step2_exit") == "UTILITY_FAIL", "PROGRESS_FALSE_PROMOTION")
    stage = run411_report.get("status")
    if stage == "STAGE2_NATIVE_PARTIAL_NO_PROMOTION":
        require(run411_report.get("native_execute_attempted") is True and
                run411_report.get("native_execution_performed") is True and
                run411_report.get("rows_verified") == 84 and
                run411_report.get("completed") == ["O_s20", "P_s20"] and
                set(progress.get("completed", {})) == {"O_s20", "P_s20"} and
                not progress.get("failures_preserved"), "NATIVE_84_ROW_RECEIPT_MISMATCH")
    else:
        require(stage == "STAGE2_RED_PRESERVED", "UNEXPECTED_NATIVE_STATUS")
    return {"status": ("RUN413_EXPORT_VERIFIED_NATIVE_PARTIAL" if
                       stage == "STAGE2_NATIVE_PARTIAL_NO_PROMOTION" else
                       "RUN413_EXPORT_VERIFIED_NATIVE_RED"),
            "copied_files": len(observed), "copied_bytes": total,
            "manifest_sha256": sha_file(manifest_path),
            "native_rows": run411_report.get("rows_verified", 0),
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "redmi_measured": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--export", type=Path, required=True)
    p.add_argument("--run411-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = verify(args.export, json.loads(args.run411_report.read_text()))
        code = 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        result = {"status": "RUN413_EXPORT_RED_PRESERVED", "error": str(exc)[:300],
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}
        code = 2
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
