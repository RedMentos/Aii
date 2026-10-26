#!/usr/bin/env python3
"""Run398: independently verify a downloaded Run395 raw ZIP, then run Run396 on actual rows."""
import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path

import run396_step2_pilot_audit as postflight

RUN395_HEAD = "48d2119dbbc7077da10b625ca4ff5819bfc74730"
EXIT_FILES = ("RUN395_DEPS_EXIT.txt", "RUN395_FIXTURE_EXIT.txt", "RUN395_BOOTSTRAP_EXIT.txt",
              "RUN395_NATIVE_EXIT.txt", "RUN395_AUDIT_EXIT.txt", "RUN395_PRIVACY_EXIT.txt")
HEX = re.compile(r"[0-9a-f]{64}\Z")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def closed_members(z):
    """No symlinks, duplicate paths, traversal, zip bombs or hidden bytes."""
    files = {}
    total = 0
    for info in z.infolist():
        name = info.filename
        require(not info.is_dir(), "UNEXPECTED_ZIP_DIRECTORY")
        require(name and name == str(Path(name)) and
                not name.startswith(("/", "\\")) and "\\" not in name and
                ".." not in Path(name).parts, "UNSAFE_ZIP_PATH")
        require(not (info.external_attr >> 16) & 0o170000 == 0o120000, "SYMLINK_ZIP_MEMBER")
        require(name not in files, "DUPLICATE_ZIP_MEMBER")
        require(info.file_size <= 12_000_000, "OVERSIZED_RAW_MEMBER")
        total += info.file_size
        require(total <= 100_000_000, "OVERSIZED_RAW_ARCHIVE")
        files[name] = z.read(info)
    return files


def verify_manifest(files):
    require("RUN395_SHA256SUMS.txt" in files, "RAW_SHA_MANIFEST_MISSING")
    lines = files["RUN395_SHA256SUMS.txt"].decode("utf-8").splitlines()
    expected = {}
    for line in lines:
        m = re.fullmatch(r"([0-9a-f]{64})  (?:\./)?(RUN395_[A-Za-z0-9_.-]+|run395-pilot/[A-Za-z0-9_.-]+\.json)", line)
        require(m is not None, "UNSAFE_OR_INVALID_RAW_SHA_LINE")
        h, name = m.groups()
        require(name not in expected, "DUPLICATE_RAW_SHA_ENTRY")
        expected[name] = h
    require(set(files) == set(expected) | {"RUN395_SHA256SUMS.txt"},
            "UNHASHED_OR_MISSING_RAW_MEMBER")
    for name, digest in expected.items():
        require(sha(files[name]) == digest, "RAW_SHA_MISMATCH:" + name)
    require(files["RUN395_HEAD.txt"].decode("utf-8").strip() == RUN395_HEAD,
            "RUN395_EXACT_HEAD_MISMATCH")
    return expected


def audit(zip_path, expected_zip_sha256=None):
    zip_path = Path(zip_path)
    raw = zip_path.read_bytes()
    zip_sha = sha(raw)
    result = {"run": "Run398", "source_run": "Run395", "zip_sha256": zip_sha,
              "source_head_expected": RUN395_HEAD, "native_rerun": False,
              "redmi_measured": False, "canonical_gate_pass": False,
              "step2_exit": "UTILITY_FAIL", "status": "PILOT_RED_PRESERVED",
              "errors": [], "postflight": None}
    try:
        if expected_zip_sha256 is not None:
            require(HEX.fullmatch(expected_zip_sha256) and zip_sha == expected_zip_sha256,
                    "RAW_ZIP_SHA_MISMATCH")
        with zipfile.ZipFile(zip_path) as z:
            require(z.testzip() is None, "RAW_ZIP_CRC_FAIL")
            files = closed_members(z)
        manifest = verify_manifest(files)
        result["members_sha256"] = manifest
        for name in EXIT_FILES:
            require(files.get(name, b"").decode("utf-8").strip() == "0",
                    "RUN395_PREREQUISITE_OR_NATIVE_RED:" + name)
        expected_json = {"RUN394_PREREGISTERED_FIXTURES.json", "RUN394_RESULT.json"}
        expected_json |= {f"{prefix}_{arm}_s20.json" for prefix in ("step2", "tool", "summary")
                          for arm in ("O", "P", "S")}
        expected_json |= {f"tool_{arm}_s20.preregistration.json" for arm in ("O", "P", "S")}
        have_json = {Path(name).name for name in files if name.startswith("run395-pilot/")}
        require(expected_json <= have_json, "RUN395_NATIVE_JSON_INCOMPLETE")
        with tempfile.TemporaryDirectory(prefix="run398-readonly-") as tmp:
            dest = Path(tmp)
            for name, data in files.items():
                if name.startswith("run395-pilot/") and name.endswith(".json"):
                    (dest / Path(name).name).write_bytes(data)
            result["postflight"] = postflight.audit(dest)
        require(result["postflight"]["rows_verified"] == 42, "NATIVE_ROW_COUNT_NOT_42")
        result["status"] = "PILOT_POSTFLIGHT_VERIFIED"
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        result["errors"].append(type(exc).__name__ + ": " + str(exc)[:350])
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-zip", type=Path, required=True)
    p.add_argument("--expected-sha256")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = audit(args.raw_zip, args.expected_sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "errors": report["errors"],
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}, sort_keys=True))
    raise SystemExit(0 if report["status"] == "PILOT_POSTFLIGHT_VERIFIED" else 2)


if __name__ == "__main__":
    main()
