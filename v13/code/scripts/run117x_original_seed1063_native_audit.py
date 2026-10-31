#!/usr/bin/env python3
"""Run117X independent read-only audit of original Run117W native C3 artifact."""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import io
import json
from pathlib import Path
import zipfile

from scripts.run47_jef_c3_typed_receiver_native import score
from scripts.run117v_original_native_readonly_audit import _zip_check, _source_ref
from scripts.run117w_c3_arithmetic_native import (
    ARMS, GOOD, RED, SEED, FIXTURE_SHA, SYSTEMS, C3_FILE, fixture,
)
from v13.common import dumps

SOURCE_HEAD = "978be6017a49365aa401c848a429913e88ef7b75"
RUNNER_BLOB = "b5e23fa34a8c2946455e0b232ae9874c29c0604f"
FIXTURE_BLOB = "567a0b2b13534e34aeab3b2a1b3e9372dd9b4ae1"
STAGES = ("SOURCE", "DEPS", "PACK", "ZIP", "PREFLIGHT", "INSTALL_C3",
          "NATIVE", "VERIFY", "COMPILE", "PRIVACY", "DIFF")


def _blob(data):
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _phone(raw, fixture_raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or z.testzip() is not None:
            raise ValueError("PHONE_ZIP_DUPLICATE_CRC_RED")
        manifest = json.loads(z.read("V13-Phone/WORKSPACE_FILES.json"))
        files = manifest["files"]
        if (manifest.get("schema_version") != 1
                or set(names) != {"V13-Phone/" + n for n in files}
                | {"V13-Phone/WORKSPACE_FILES.json"}):
            raise ValueError("PHONE_MANIFEST_COVERAGE_RED")
        for name, expected in files.items():
            h = sha256()
            with z.open("V13-Phone/" + name) as stream:
                while chunk := stream.read(1 << 20):
                    h.update(chunk)
            if h.hexdigest() != expected:
                raise ValueError("PHONE_MANIFEST_SHA_RED_" + name)
        runner = z.read("V13-Phone/scripts/run117w_c3_arithmetic_native.py")
        fixture_bytes = z.read(
            "V13-Phone/docs/fixtures/RUN117W_C3_ARITHMETIC_SEED1063.json")
        if (_blob(runner) != RUNNER_BLOB
                or _blob(fixture_bytes) != FIXTURE_BLOB
                or fixture_bytes != fixture_raw):
            raise ValueError("PHONE_SOURCE_PIN_RED")
        return len(files)


def _arm(arm, row):
    name = arm.get("arm")
    if name not in ARMS:
        raise ValueError("UNKNOWN_C3_ARM_RED")
    if arm.get("status") != "RECORDED":
        return False
    if (arm.get("native_final") is not True
            or arm.get("process_reaped") is not True
            or arm.get("native_metrics", {}).get("status") != "FINAL"
            or arm["native_metrics"].get("actual_model") != C3_FILE):
        raise ValueError("C3_NATIVE_RECEIPT_RED")
    messages = arm.get("messages")
    if (type(messages) is not list or len(messages) != 2
            or [m.get("role") for m in messages] != ["system", "user"]
            or messages[0].get("content") != SYSTEMS[name]):
        raise ValueError("C3_SYSTEM_ROLE_RED")
    if sha256(dumps(messages).encode()).hexdigest() != arm.get("messages_sha256"):
        raise ValueError("C3_PROMPT_HASH_RED")
    user = messages[1]["content"]
    if '"oracle"' in user or '"approved"' in user or '"answer"' in user:
        raise ValueError("C3_ORACLE_OR_AUTHORITY_LEAK_RED")
    payload = json.loads(user)
    if (payload.get("schema") != "v13.run117w.two_source_spans.v1"
            or payload.get("source_role") != "UNTRUSTED_EXACT_USER"
            or payload.get("policy", {}).get("text") != row["policy_span"]
            or payload.get("options", {}).get("text") != row["option_span"]):
        raise ValueError("C3_SOURCE_SPANS_RED")
    _source_ref(payload["policy"]["source_ref"],
                row["prior"], row["policy_span"])
    _source_ref(payload["options"]["source_ref"],
                row["current"], row["option_span"])
    if name == ARMS[2]:
        if (payload.get("typed_jef_candidate") != row["oracle"]
                or payload.get("candidate_authority") != 0
                or payload.get("candidate_origin") !=
                "DETERMINISTIC_SOURCE_RECIPE_NOT_NATIVE_JEF"):
            raise ValueError("TYPED_JEF_SOURCE_BOUND_CANDIDATE_RED")
    elif "typed_jef_candidate" in payload or "candidate_authority" in payload:
        raise ValueError("TYPED_JEF_LEAK_IN_SOURCE_ONLY_ARM_RED")
    if score(arm.get("output", ""), row["oracle"]) != arm.get("score"):
        raise ValueError("C3_ORIGINAL_OUTPUT_SCORE_RED")
    return True


def _report(report, rows):
    if (report.get("schema") != "v13.run117w.c3_arithmetic_native.v1"
            or report.get("seed") != SEED
            or report.get("fixture_sha256") != FIXTURE_SHA
            or report.get("native_c3") is not True
            or report.get("typed_candidate_precomputed") is not True
            or report.get("native_body_calls") != 0
            or report.get("native_jef_calls") != 0
            or report.get("native_c2_calls") != 0
            or report.get("age0") != "RECORD_ONLY"
            or report.get("step2_exit") != "EVIDENCE_NOT_PASSING"
            or report.get("b3") != "NO_PROMOTION"
            or report.get("body_jepa") != "UNAVAILABLE"
            or report.get("jepa_weight") != 0
            or report.get("redmi_measured") is not False
            or report.get("whole_system_complete") is not False
            or report.get("output_committed") is not False
            or report.get("tool_dispatches") != 0
            or report.get("learning_authority") != 0
            or report.get("delivery_authority") != 0):
        raise ValueError("NATIVE_NEGATIVE_GATES_RED")
    if report.get("status") not in (*GOOD, RED):
        raise ValueError("NATIVE_STATUS_UNKNOWN_RED")
    originals = {row["id"]: row for row in rows}
    seen = set()
    scores = {arm: 0 for arm in ARMS}
    counts = {arm: 0 for arm in ARMS}
    for case in report.get("rows", []):
        cid = case["id"]
        if cid not in originals or cid in seen:
            raise ValueError("NATIVE_CASE_ID_RED")
        seen.add(cid)
        row = originals[cid]
        if (case.get("prior_source_ref", {}).get("sha256") !=
                sha256(row["prior"].encode()).hexdigest()
                or case.get("current_source_ref", {}).get("sha256") !=
                sha256(row["current"].encode()).hexdigest()
                or case.get("closed_store_ok") is not True
                or case.get("no_live_output") is not True):
            raise ValueError("NATIVE_STORE_OR_SOURCE_RED")
        seen_arms = set()
        for item in case.get("arms", []):
            name = item.get("arm")
            if name not in ARMS or name in seen_arms:
                raise ValueError("DUPLICATE_C3_ARM_RED")
            seen_arms.add(name)
            if _arm(item, row):
                counts[name] += 1
                scores[name] += item["score"]["correct"]
    if (report.get("scores") != scores
            or report.get("recorded_by_arm") != counts):
        raise ValueError("NATIVE_REPORTED_SCORE_RED")
    if report["status"] in GOOD:
        if (seen != set(originals)
                or report.get("native_c3_calls") != 18
                or any(counts[arm] != 6 for arm in ARMS)):
            raise ValueError("NATIVE_COMPLETE_RECEIPT_RED")
        signal = (scores[ARMS[1]] >= scores[ARMS[0]] + 2
                  and scores[ARMS[1]] >= 4 and scores[ARMS[2]] >= 5)
        if (report.get("exploratory_arithmetic_signal") is not signal
                or report["status"] != GOOD[0 if signal else 1]):
            raise ValueError("NATIVE_SIGNAL_RECOMPUTE_RED")
    return {"original_status": report["status"],
            "native_complete": report["status"] in GOOD,
            "cases": len(seen),
            "native_c3_calls": report.get("native_c3_calls"),
            "recomputed_scores": scores,
            "recomputed_recorded_by_arm": counts,
            "typed_candidate_precomputed_not_native": True,
            "step2_promoted": False, "redmi_measured": False}


def audit(path, expected_sha, fixture_path):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != expected_sha:
        raise ValueError("ORIGINAL_OUTER_SHA_RED")
    fixture_raw = Path(fixture_path).read_bytes()
    if sha256(fixture_raw).hexdigest() != FIXTURE_SHA:
        raise ValueError("ORIGINAL_FIXTURE_SHA_RED")
    rows = fixture(fixture_path)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        inner = _zip_check(z)
        if z.read("HEAD.txt").decode().strip() != SOURCE_HEAD:
            raise ValueError("ORIGINAL_SOURCE_HEAD_RED")
        exits = {n: int(z.read(n + "_EXIT.txt").decode()) for n in STAGES}
        receipt = json.loads(z.read("RESULT.json"))
        if (receipt.get("head") != SOURCE_HEAD
                or receipt.get("exits") != exits
                or receipt.get("fixture_sha256") != FIXTURE_SHA
                or receipt.get("typed_jef_is_precomputed_not_native") is not True
                or receipt.get("step2_promoted") is not False
                or receipt.get("b3_promoted") is not False
                or receipt.get("jepa_weight") != 0
                or receipt.get("redmi_measured") is not False
                or receipt.get("whole_system_complete") is not False):
            raise ValueError("ORIGINAL_WORKFLOW_RECEIPT_RED")
        phone_count = None
        if "V13-Phone-Run117W.zip" in z.namelist():
            phone_count = _phone(z.read("V13-Phone-Run117W.zip"), fixture_raw)
        if "NATIVE_CASE/report.json" in z.namelist():
            native = _report(json.loads(z.read("NATIVE_CASE/report.json")), rows)
        else:
            native = {"original_status": "NO_NATIVE_REPORT_STRUCTURAL_RED",
                      "native_complete": False}
        return {"schema": "v13.run117x.original_seed1063_readonly_audit.v1",
                "integrity_status": "ORIGINAL_ARTIFACT_INTEGRITY_PASS",
                "artifact_sha256": expected_sha, "source_head": SOURCE_HEAD,
                "sha256sum_files_checked": inner,
                "phone_source_files_checked": phone_count,
                "original_stage_exits": exits, "native": native,
                "model_called_by_auditor": False,
                "learning_authority": 0, "delivery_authority": 0,
                "step2_promoted": False, "b3_promoted": False,
                "jepa_weight": 0, "redmi_measured": False,
                "whole_system_complete": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact", type=Path, required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("AUDIT_OUTPUT_MUST_BE_NEW")
    report = audit(args.artifact, args.sha256, args.fixture)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
