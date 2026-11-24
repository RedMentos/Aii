#!/usr/bin/env python3
"""Run117AN independent read-only audit of three immutable original Actions ZIPs.

No inference, no re-scoring, no waivers. A GREEN audit of an original RED
full-suite preserves the RED and only proves the audit's own integrity checks.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import stat
import zipfile

SCHEMA = "v13.run117an.independent_original_artifact_audit.v1"
PINS = {
    "AL": {
        "sha": "859e8cb57c21f9fe6532086a25e9a0e952e01339862bcce9911ed4e05907fb9d",
        "head": "7a9b18c8cbf46a48411beac3167a31d875a7c723",
        "schema": "v13.run117al.prewarm_model_free.v1",
        "tests": 10, "exit_key": "TEST", "expected_exit": 0,
        "stage_count": 6, "manifest_count": 15,
        "status": "INDEPENDENT_SOFTWARE_GREEN_VERIFIED",
    },
    "AM": {
        "sha": "7b6e96a3ec2f6c7e35b02724cb727e28010be28ec8d96988bf1eb6b2a1d78a5f",
        "head": "3827cbbe850d0114a8aa2fcc1380720d0a849bac",
        "schema": "v13.run117am.seed1073_model_free_preflight.v1",
        "tests": 17, "exit_key": "TEST", "expected_exit": 0,
        "stage_count": 8, "manifest_count": 18,
        "status": "INDEPENDENT_SOFTWARE_GREEN_VERIFIED",
    },
    "AJ": {
        "sha": "bbf62ce125b2df42760252b5491b10ee817065623b13f6d0cc818471a297ad48",
        "head": "bfbae24944a7d1fa5398c6cb0ed87f5d5ee65e19",
        "schema": "v13.run117aj.unfiltered_reviewchain_software_receipt.v1",
        "tests": 5152, "exit_key": "FULL", "expected_exit": 1,
        "stage_count": 14, "manifest_count": 30,
        "status": "INDEPENDENT_FULLSUITE_RED_PRESERVED",
    },
}


def fail(reason):
    raise ValueError("RUN117AN_" + reason + "_RED")


def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            fail("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def load_json(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs,
                      parse_constant=lambda _: fail("NONFINITE_JSON"))


def audit_bytes(blob, label, *, expected_outer=None):
    """expected_outer override exists for synthetic adversarial tests only."""
    if label not in PINS or type(blob) is not bytes:
        fail("INPUT")
    pin = PINS[label]
    outer = sha256(blob).hexdigest()
    if outer != (expected_outer if expected_outer is not None else pin["sha"]):
        fail("OUTER_SHA")
    try:
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(blob)) as z:
            info = z.infolist()
            names = [i.filename for i in info]
            if (not names or len(names) != len(set(names))
                    or len(names) != pin["manifest_count"] + 1
                    or sum(i.file_size for i in info) > 8 * 1024 * 1024):
                fail("ZIP_MEMBERS")
            for i in info:
                p = i.filename
                if (p.startswith("/") or "\\" in p or not p or
                        p.startswith("./") or any(x in ("", ".", "..") for x in p.split("/")) or
                        stat.S_IFMT(i.external_attr >> 16) == stat.S_IFLNK):
                    fail("ZIP_PATH")
            if z.testzip() is not None:
                fail("ZIP_CRC")
            manifest = z.read("SHA256SUMS").decode("utf-8").splitlines()
            seen = set()
            for line in manifest:
                m = re.fullmatch(r"([0-9a-f]{64})  (?:\./)?([^\n]+)", line)
                if m is None:
                    fail("MANIFEST_SHAPE")
                digest, name = m.groups()
                if name in seen or name == "SHA256SUMS" or name not in names:
                    fail("MANIFEST_DUPLICATE")
                seen.add(name)
                if sha256(z.read(name)).hexdigest() != digest:
                    fail("INNER_SHA")
            if seen != set(names) - {"SHA256SUMS"} or len(seen) != pin["manifest_count"]:
                fail("MANIFEST_COVERAGE")
            result = load_json(z.read("RESULT.json"))
            if result != load_json(z.read("RESULT_RAW.log")):
                fail("RECEIPT_MISMATCH")
            if (result.get("schema") != pin["schema"] or
                    result.get("head") != pin["head"] or
                    z.read("HEAD.txt").decode("utf-8").strip() != pin["head"]):
                fail("SOURCE_HEAD")
            exits = result.get("exits")
            if (type(exits) is not dict or len(exits) != pin["stage_count"]
                    or set(exits) != {n[:-9] for n in names if n.endswith("_EXIT.txt")}):
                fail("EXIT_COVERAGE")
            for key, rc in exits.items():
                expected = pin["expected_exit"] if key == pin["exit_key"] else 0
                if (type(rc) is not int or rc != expected or
                        z.read(key + "_EXIT.txt").decode("utf-8").strip() != str(rc)):
                    fail("EXIT_FORGED")
            if (result.get("step2_promoted") is not False or
                    result.get("b3_promoted") is not False or
                    result.get("jepa_weight") != 0 or
                    result.get("redmi_measured") is not False or
                    result.get("whole_system_complete") is not False):
                fail("NEGATIVE_GATES")
            if "CLEAN" not in z.read("PRIVACY_RAW.log").decode("utf-8"):
                fail("PRIVACY")
            raw_name = "FULL_RAW.log" if label == "AJ" else "TEST_RAW.log"
            log = z.read(raw_name).decode("utf-8")
            if not re.search(r"Ran " + str(pin["tests"]) + r" tests in [0-9.]+s", log):
                fail("TEST_COUNT")
            if label == "AJ":
                if ("FAILED (failures=5, errors=68, skipped=28)" not in log or
                        result.get("native_inference_this_run") is not False or
                        result.get("original_native_artifact_id") != 13054946077):
                    fail("ORIGINAL_FULLSUITE_RED")
            else:
                if not re.search(r"(?m)^OK$", log) or "FAILED (" in log:
                    fail("SOFTWARE_GREEN")
                if label == "AM" and (result.get("seed") != 1073 or
                        result.get("native_model_calls") != 0 or
                        result.get("fixture_sha256") !=
                        "18c0c9211daca9b1e5df12443713f6001db10ea6b5e9a778c8c9eb744d7579d1"):
                    fail("FRESH_COHORT")
                if label == "AL" and (result.get("model_calls") != 0 or
                        result.get("original_native_seed1069") !=
                        "STRUCTURAL_RED_UNCHANGED"):
                    fail("ORIGINAL_NATIVE_RED")
    except (zipfile.BadZipFile, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        fail("ARCHIVE_FORMAT")
    return {
        "schema": SCHEMA, "label": label, "status": pin["status"],
        "original_head": pin["head"], "original_zip_sha256": outer,
        "original_test_count": pin["tests"],
        "original_exit": pin["expected_exit"],
        "inner_hashes_verified": pin["manifest_count"],
        "native_inference_by_auditor": False,
        "output_committed": False, "tool_dispatches": 0,
        "learning_authority": 0, "step2_promoted": False,
        "b3_promoted": False, "body_jepa_promoted": False,
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("label", choices=sorted(PINS))
    p.add_argument("original_zip", type=Path)
    a = p.parse_args()
    print(json.dumps(audit_bytes(a.original_zip.read_bytes(), a.label),
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
