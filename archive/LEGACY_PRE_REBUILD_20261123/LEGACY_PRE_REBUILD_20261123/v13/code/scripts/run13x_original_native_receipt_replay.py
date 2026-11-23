"""Run13X: read-only original Run13T native ZIP / Run13W receipt replay.

Never mutates original raw, reconstructs Store, runs a model, or promotes gates.
All selection counts are conditional counterfactuals WITHOUT source recheck.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import zipfile

from scripts.run13k_c3_copy_native import COPY_PREFIX, COPY_SUFFIX
from v13.agi.c3_source_fidelity_shadow_run13m import audit_source_facts
from v13.agi.jef_c3_shadow_fallback_run13v import _native_receipt_ok, MODEL_SHA, MODEL_REVISION
from v13.agi.jef_c3_shadow_prompt_run13i import PREFIX

ORIGINAL_ZIP_SHA256 = "86f728599312518bfa67efa0ae16e66be0eaec9ccfd8c3da8710fba40192717c"
FIXTURE_SHA256 = "c9a28de0e7fb198015b4b8845096d31f4af43f5c9679df7a8019a55ee4767b11"
SCHEMA = "v13.run13t.c3_verbatim_heldout_native.v1"
ARMS = ("COPY_BASELINE", "COPY_STRICT")
ROW_KEYS = set("""answer_sha256 arm b3_status body_jepa_status context_plan_packet_id
exact_copy fidelity_reason final_output index jepa_weight learning_mode
model_revision model_sha256 native_calls native_metrics native_pid native_reaped
native_release native_role native_status project prompt_sha256 query_event_id
redmi_measured schema score seed source_event_id source_facts_verified
source_sha256 step2_status system_sha256 whole_system_complete wrong_claims""".split())
HEX = re.compile(r"[0-9a-f]{64}\Z")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _pairs(items):
    obj = {}
    for key, value in items:
        if key in obj:
            raise ValueError("RUN13X_DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def _nonfinite(value):
    raise ValueError("RUN13X_NONFINITE_JSON:" + value)


def strict_json(raw):
    obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                     parse_constant=_nonfinite)
    if type(obj) is not dict:
        raise ValueError("RUN13X_JSON_OBJECT_REQUIRED")
    return obj


def load_cases(fixture):
    data = strict_json(Path(fixture).read_bytes())
    cases = data.get("cases")
    if (data.get("schema") != "v13.run13t.c3_verbatim_heldout.fixture.v1"
            or type(data.get("seed")) is not int or data["seed"] != 283
            or type(cases) is not list or len(cases) != 8
            or data.get("cases_sha256") != FIXTURE_SHA256
            or sha(json.dumps(cases, sort_keys=True,
                              separators=(",", ":")).encode()) != FIXTURE_SHA256):
        raise ValueError("RUN13X_FIXTURE_PIN_RED")
    return cases


def expected_answer(case):
    faster = case["a"] if case["a_days"] < case["b_days"] else case["b"]
    return (f"Project {case['project']}.\n"
            f"{case['a']} leaves {case['budget'] - case['a_cost']} Euro remaining.\n"
            f"{case['b']} leaves {case['budget'] - case['b_cost']} Euro remaining.\n"
            f"{faster} finishes sooner.")


def source_link(answer):
    return {
        "reason": "VERIFIED_JEF_TO_C3_SHADOW_CANDIDATE",
        "status": "SHADOW_NO_AUTHORITY", "delivery_authority": 0,
        "context_authority": 0, "native_calls": 0,
        "weight_updates": False, "answer": answer,
        "answer_sha256": sha(answer.encode("utf-8")),
        "candidate_prompt": PREFIX + answer,
        "prompt_sha256": sha((PREFIX + answer).encode("utf-8")),
    }


def audit_row(row, case, index, arm):
    """Check original row then derive a non-authenticating output receipt."""
    if type(row) is not dict or set(row) != ROW_KEYS:
        raise ValueError("RUN13X_ROW_SCHEMA_RED")
    answer = expected_answer(case)
    answer_hash = sha(answer.encode("utf-8"))
    prompt_hash = sha((COPY_PREFIX + answer + COPY_SUFFIX).encode("utf-8"))
    if (row.get("schema") != SCHEMA or type(row.get("seed")) is not int
            or row["seed"] != 283 or type(row.get("index")) is not int
            or row["index"] != index or row.get("project") != case["project"]
            or row.get("arm") != arm or row.get("answer_sha256") != answer_hash
            or row.get("prompt_sha256") != prompt_hash
            or row.get("model_sha256") != MODEL_SHA
            or row.get("model_revision") != MODEL_REVISION
            or any(type(row.get(k)) is not str or not row[k]
                   for k in ("source_event_id", "query_event_id",
                             "context_plan_packet_id"))
            or type(row.get("source_sha256")) is not str
            or HEX.fullmatch(row["source_sha256"]) is None
            or type(row.get("system_sha256")) is not str
            or HEX.fullmatch(row["system_sha256"]) is None
            or row.get("learning_mode") != "RECORD_ONLY"
            or type(row.get("jepa_weight")) is not int
            or row["jepa_weight"] != 0
            or row.get("step2_status") != "UTILITY_FAIL"
            or row.get("b3_status") != "NO_PROMOTION"
            or row.get("body_jepa_status") != "UNAVAILABLE"
            or row.get("redmi_measured") is not False
            or row.get("whole_system_complete") is not False):
        raise ValueError("RUN13X_SOURCE_OR_GATE_RED")
    metrics = row.get("native_metrics")
    if (row.get("native_status") != "FINAL"
            or row.get("native_role") != "C3_LANGUAGE"
            or type(row.get("native_calls")) is not int or row["native_calls"] != 1
            or row.get("native_reaped") is not True
            or type(row.get("native_pid")) is not int or row["native_pid"] <= 0
            or type(row.get("native_release")) is not dict
            or row["native_release"].get("process_reaped") is not True
            or type(metrics) is not dict or metrics.get("status") != "FINAL"
            or metrics.get("role") != "C3_LANGUAGE"
            or metrics.get("actual_model") != "LFM2.5-350M-QAD-Q4_0.gguf"
            or type(row.get("final_output")) is not str):
        raise ValueError("RUN13X_NATIVE_RECEIPT_RED")
    output = row["final_output"]
    raw_bytes = output.encode("utf-8")
    receipt = dict(row)
    receipt["native_output_sha256"] = sha(raw_bytes)
    receipt["native_output_bytes"] = len(raw_bytes)
    linked = source_link(answer)
    linked.update({
        "source_event_id": row["source_event_id"],
        "query_event_id": row["query_event_id"],
        "context_plan_packet_id": row["context_plan_packet_id"],
    })
    if not _native_receipt_ok(receipt, linked, output):
        raise ValueError("RUN13X_OUTPUT_RECEIPT_BINDING_RED")
    fidelity = audit_source_facts(linked, output)
    verified = fidelity.get("result") == "FACTS_EXACT"
    if (type(row.get("source_facts_verified")) is not bool
            or row["source_facts_verified"] is not verified
            or row.get("fidelity_reason") != fidelity.get("reason")):
        raise ValueError("RUN13X_ORIGINAL_FIDELITY_MISMATCH")
    return {"receipt": receipt, "snapshot": linked,
            "output": output, "source_facts_verified": verified,
            "native_pid": row["native_pid"],
            "source_ids": tuple(row[k] for k in (
                "source_event_id", "query_event_id", "context_plan_packet_id")),
            "system_sha256": row["system_sha256"]}


def _archive_entries(archive):
    names = archive.namelist()
    if len(names) != len(set(names)) or "SHA256SUMS" not in names:
        raise ValueError("RUN13X_ARCHIVE_DUPLICATE_OR_NO_MANIFEST")
    if archive.testzip() is not None:
        raise ValueError("RUN13X_ARCHIVE_CRC_RED")
    manifest = archive.read("SHA256SUMS").decode("ascii").splitlines()
    covered = set()
    for line in manifest:
        if "  ./" not in line:
            raise ValueError("RUN13X_MANIFEST_FORMAT_RED")
        digest, name = line.split("  ./", 1)
        if HEX.fullmatch(digest) is None or name in covered or name not in names:
            raise ValueError("RUN13X_MANIFEST_ENTRY_RED")
        if sha(archive.read(name)) != digest:
            raise ValueError("RUN13X_MANIFEST_HASH_RED")
        covered.add(name)
    if covered != set(names) - {"SHA256SUMS"} or len(covered) != 39:
        raise ValueError("RUN13X_MANIFEST_COVERAGE_RED")
    expected = {f"pilot/raw/{i:02d}_{arm}.json"
                for i in range(8) for arm in ARMS}
    actual = {name for name in names if name.startswith("pilot/raw/")}
    if actual != expected or "pilot/report.json" not in covered:
        raise ValueError("RUN13X_RAW_COVERAGE_RED")


def replay(archive_path, fixture_path):
    """No Store snapshot in original ZIP: output is CONDITIONAL only."""
    cases = load_cases(fixture_path)
    if sha(Path(archive_path).read_bytes()) != ORIGINAL_ZIP_SHA256:
        raise ValueError("RUN13X_ORIGINAL_ZIP_SHA_RED")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            _archive_entries(archive)
            report = strict_json(archive.read("pilot/report.json"))
            if (report.get("status") != "FIDELITY_HURT"
                    or report.get("rows") != 16
                    or report.get("fixture_sha256") != FIXTURE_SHA256
                    or report.get("utility_gate_promoted") is not False
                    or report.get("whole_system_complete") is not False):
                raise ValueError("RUN13X_ORIGINAL_REPORT_RED")
            verified, fallback, pids = 0, 0, set()
            for index, case in enumerate(cases):
                pair = []
                for arm in ARMS:
                    row = strict_json(archive.read(
                        f"pilot/raw/{index:02d}_{arm}.json"))
                    audit = audit_row(row, case, index, arm)
                    if audit["native_pid"] in pids:
                        raise ValueError("RUN13X_DUPLICATE_NATIVE_PID")
                    pids.add(audit["native_pid"])
                    verified += int(audit["source_facts_verified"])
                    fallback += int(not audit["source_facts_verified"])
                    pair.append(audit)
                if (pair[0]["source_ids"] != pair[1]["source_ids"]
                        or pair[0]["system_sha256"] == pair[1]["system_sha256"]):
                    raise ValueError("RUN13X_PAIR_SOURCE_OR_SYSTEM_RED")
            if verified != 3 or fallback != 13:
                raise ValueError("RUN13X_ORIGINAL_DIAGNOSTIC_DRIFT")
    except (zipfile.BadZipFile, UnicodeError, KeyError) as exc:
        raise ValueError("RUN13X_ARCHIVE_OR_TEXT_RED") from exc
    return {
        "status": "RUN13X_ORIGINAL_NATIVE_OUTPUT_RECEIPT_REPLAY_VALID",
        "evidence": "ORIGINAL_LINUX_NATIVE_RAW_READONLY_PLUS_SYNTHETIC_RECEIPT_FIELDS",
        "original_zip_sha256": ORIGINAL_ZIP_SHA256,
        "original_native_rows": 16, "distinct_native_pids": len(pids),
        "counterfactual_c3_facts_candidates": verified,
        "counterfactual_jef_fallback_candidates": fallback,
        "conditional_on_valid_store_source_recheck": True,
        "source_store_rechecked": False, "native_receipt_attested": False,
        "original_diagnostic": "FIDELITY_HURT",
        "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
        "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False, "utility_gate_promoted": False,
    }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-zip", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(replay(args.original_zip, args.fixture), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
