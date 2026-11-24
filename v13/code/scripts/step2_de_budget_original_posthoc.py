"""Read-only original STEP12 Linux-native proof -> budget SHADOW posthoc.

Original semantic failure remains failure; this does not rerun native models,
change its scorer or inject a result into ToolStep/C5.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from v13.agi.budget_de_shadow import evaluate

ORIGINAL_ZIP_SHA256 = "ad961abb8eea8d567f58cbc4f1fed67f7a79920e36564bb5527b7ea08fa4f3f7"
ORIGINAL_HEAD = "3c9e961d123e5bed1826802fc3e236c19078f5ee"


def require(ok, code):
    if not ok:
        raise ValueError(code)


def verified_zip(data):
    require(hashlib.sha256(data).hexdigest() == ORIGINAL_ZIP_SHA256,
            "ORIGINAL_ZIP_SHA256_RED")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        require(len(names) == len(set(names)) and z.testzip() is None,
                "ORIGINAL_ZIP_CRC_OR_DUPLICATE_RED")
        files = {n: z.read(n) for n in names}
    manifest = files["SHA256SUMS.txt"].decode().splitlines()
    expected = {}
    for line in manifest:
        sha, name = line.split("  ", 1)
        name = name.removeprefix("./")
        require(name not in expected, "ORIGINAL_MANIFEST_DUPLICATE")
        expected[name] = sha
    require(set(expected) == set(files) - {"SHA256SUMS.txt"},
            "ORIGINAL_MANIFEST_COVERAGE_RED")
    for name, sha in expected.items():
        require(hashlib.sha256(files[name]).hexdigest() == sha,
                "ORIGINAL_INNER_HASH_RED:" + name)
    return files, len(manifest)


def posthoc(path):
    files, inner = verified_zip(Path(path).read_bytes())
    require(files["HEAD.txt"].decode().strip() == ORIGINAL_HEAD, "ORIGINAL_HEAD_RED")
    proof = json.loads(files["proofs/step12-proof.json"])
    require(proof["status"] == "VERTICAL_CHECKS_PASS"
            and proof["phone_measured"] is False
            and len(proof["turns"]) == 2, "ORIGINAL_PROOF_IDENTITY_RED")
    turn = proof["turns"][1]
    query = turn["queries"][0]["goal"]
    output = turn["output"]
    require("Projekt Aurora" in query and "Budget: 120 Euro" in query
            and "Option Rot kostet 80 Euro" in query
            and "Option Blau kostet 110 Euro" in query
            and "Nenne die Budgetreste" in query,
            "ORIGINAL_SOURCE_QUERY_RED")
    require("120 euros" in output and "80 euros" in output and "110 euros" in output,
            "ORIGINAL_NATIVE_OUTPUT_CHANGED")
    # Preserve the historical semantic-negative: no stated 40/10 remainder.
    require(re.search(r"\b40\s*(?:euro|euros|€)\b", output, re.I) is None
            and re.search(r"\b10\s*(?:euro|euros|€)\b", output, re.I) is None,
            "ORIGINAL_SEMANTIC_NEGATIVE_CHANGED")
    shadow = evaluate(query)
    require(shadow["status"] == "SHADOW_RESULT"
            and shadow["budget"] == 120
            and [(o["name"], o["remaining"]) for o in shadow["options"]]
            == [("Rot", 40), ("Blau", 10)], "POSTHOC_SHADOW_REMAINDER_RED")
    return {"schema": "v13.step2.de_budget.original_native_posthoc.v1",
            "original_zip_sha256": ORIGINAL_ZIP_SHA256,
            "original_head": ORIGINAL_HEAD, "original_inner_sha256_count": inner,
            "original_native_semantic_status": "SEMANTIC_REQUIREMENT_FAIL",
            "original_native_remainders_stated": 0,
            "shadow_remainders_computed": 2,
            "shadow_values": [{"name": o["name"], "remaining": o["remaining"]}
                              for o in shadow["options"]],
            "evidence_level": "POSTHOC_SOFTWARE_ON_EXISTING_LINUX_NATIVE_PROOF",
            "new_native_model_calls": 0, "live_tool_execution": False,
            "external_action_authority": False,
            "step2_gate_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("FRESH_OUTPUT_REQUIRED")
    result = posthoc(args.zip)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                   sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("original_native_semantic_status",
                       "original_native_remainders_stated",
                       "shadow_remainders_computed", "evidence_level")}))


if __name__ == "__main__":
    main()
