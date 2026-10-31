#!/usr/bin/env python3
"""Independent read-only audit of original Run117U GitHub Actions artifact.

Never calls a model, never changes original ZIP/fixture and never promotes gates.
A valid RED artifact remains RED; integrity and scientific outcome are separate.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from scripts.run47_jef_c3_typed_receiver_native import score
from scripts.run117s_body_complementarity_preflight import (
    ARMS, FIXTURE_SHA, SYSTEM, fixture,
)
from scripts.run117u_seed1061_native_three_arm import (
    GOOD, BODY_RED, STRUCTURAL_RED, SCHEMA_NAME,
)
from v13.common import dumps

SOURCE_HEAD = "a85eb4d3d0050f26404517d49c51c7843f0e933e"
RUNNER_BLOB = "1b06bb8b6f237f21f9d1df7e8a15bb2e0a74ff8e"
SELECTOR_BLOB = "b3d756eff9b1dbd7079b220ab0e0f20eded340c0"
FIXTURE_BLOB = "f7741de466571e67e48720395f32acbcb32ff14a"
MODEL_NAMES = {
    "B1_DETAIL": ("LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
                  "6767265158422fb8a19c62ceb45f16f05363615b"),
    "B2_GIST": ("Qwen3.5-0.8B-Q4_0.gguf",
                "8fea620810c4afa23dd6443f999a48574c1611a3"),
}
C3_NAME = "LFM2.5-350M-QAD-Q4_0.gguf"
STAGES = ("SOURCE", "DEPS", "PACK", "ZIP", "PREFLIGHT", "INSTALL_C3",
          "INSTALL_BODIES", "NATIVE", "VERIFY", "COMPILE", "PRIVACY", "DIFF")


def _git_blob(raw):
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _zip_check(z):
    names = z.namelist()
    if (len(names) != len(set(names))
            or "SHA256SUMS" not in names or z.testzip() is not None):
        raise ValueError("ZIP_DUPLICATE_CRC_OR_MANIFEST_RED")
    for name in names:
        path = PurePosixPath(name)
        if (path.is_absolute() or ".." in path.parts
                or not name or "\\" in name):
            raise ValueError("ZIP_PATH_RED")
    lines = z.read("SHA256SUMS").decode().splitlines()
    seen = set()
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise ValueError("ZIP_SHA256SUMS_SHAPE_RED")
        digest, path = match.groups()
        name = path.removeprefix("./")
        if name in seen or name not in names or name == "SHA256SUMS":
            raise ValueError("ZIP_SHA256SUMS_COVERAGE_RED")
        seen.add(name)
        if sha256(z.read(name)).hexdigest() != digest:
            raise ValueError("ZIP_INNER_SHA_RED_" + name)
    if seen != set(names) - {"SHA256SUMS"}:
        raise ValueError("ZIP_SHA256SUMS_COVERAGE_RED")
    return len(seen)


def _phone_check(raw, fixture_raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or z.testzip() is not None:
            raise ValueError("PHONE_ZIP_CRC_OR_DUPLICATE_RED")
        manifest = json.loads(z.read("V13-Phone/WORKSPACE_FILES.json"))
        files = manifest["files"]
        if (manifest.get("schema_version") != 1
                or set(names) != {"V13-Phone/" + name for name in files}
                | {"V13-Phone/WORKSPACE_FILES.json"}):
            raise ValueError("PHONE_SOURCE_MANIFEST_RED")
        for name, expected in files.items():
            h = sha256()
            with z.open("V13-Phone/" + name) as stream:
                while chunk := stream.read(1 << 20):
                    h.update(chunk)
            if h.hexdigest() != expected:
                raise ValueError("PHONE_SOURCE_HASH_RED_" + name)
        pins = {
            "scripts/run117u_seed1061_native_three_arm.py": RUNNER_BLOB,
            "v13/b2_salient_source_excerpt_shadow_candidate.py": SELECTOR_BLOB,
            "docs/fixtures/RUN117S_BODY_COMPLEMENTARITY_SEED1061.json":
                FIXTURE_BLOB,
        }
        for name, expected in pins.items():
            data = z.read("V13-Phone/" + name)
            if _git_blob(data) != expected:
                raise ValueError("PHONE_SOURCE_PIN_RED_" + name)
        if (z.read("V13-Phone/docs/fixtures/RUN117S_BODY_COMPLEMENTARITY_SEED1061.json")
                != fixture_raw):
            raise ValueError("PHONE_FIXTURE_BYTES_RED")
        return len(files)


def _source_ref(ref, source, exact):
    if (type(ref) is not dict or ref.get("modality") != "text"
            or ref.get("sha256") != sha256(source.encode()).hexdigest()
            or type(ref.get("char_start")) is not int
            or type(ref.get("char_end")) is not int
            or not 0 <= ref["char_start"] <= ref["char_end"] <= len(source)
            or source[ref["char_start"]:ref["char_end"]] != exact):
        raise ValueError("SOURCE_REF_BYTES_RED")


def _arm_check(arm, row, name):
    if arm.get("arm") != name:
        raise ValueError("ARM_NAME_RED")
    if arm.get("status") == "BODY_QUOTE_UNAVAILABLE":
        if name != ARMS[2] or arm.get("score") is not None:
            raise ValueError("BODY_UNAVAILABLE_SCORE_RED")
        return False
    if arm.get("status") != "RECORDED":
        return False
    if (arm.get("native_final") is not True
            or arm.get("process_reaped") is not True
            or arm.get("native_metrics", {}).get("status") != "FINAL"
            or arm["native_metrics"].get("actual_model") != C3_NAME):
        raise ValueError("C3_NATIVE_RECEIPT_RED")
    messages = arm.get("messages")
    if (type(messages) is not list or len(messages) != 2
            or [m.get("role") for m in messages] != ["system", "user"]
            or messages[0].get("content") != SYSTEM):
        raise ValueError("C3_ROLE_SYSTEM_RED")
    user = messages[1]["content"]
    if ('"oracle"' in user or "typed_jef_candidate" in user
            or '"answer"' in user or '"approved"' in user):
        raise ValueError("C3_ANSWER_LEAK_RED")
    if sha256(dumps(messages).encode()).hexdigest() != arm.get("messages_sha256"):
        raise ValueError("C3_PROMPT_HASH_RED")
    payload = json.loads(user)
    if name == ARMS[0]:
        sources = payload.get("sources", [])
        if [s.get("text") for s in sources] != [row["prior"], row["current"]]:
            raise ValueError("RAW_SOURCE_RED")
        for source, record in zip((row["prior"], row["current"]), sources):
            _source_ref(record["source_ref"], source, source)
    elif name == ARMS[1]:
        spans = payload.get("spans", [])
        if [s.get("text") for s in spans] != [row["policy_span"], row["option_span"]]:
            raise ValueError("SELECTOR_SOURCE_RED")
        for source, record in zip((row["prior"], row["current"]), spans):
            _source_ref(record["source_ref"], source, record["text"])
    else:
        if (payload.get("body_hypotheses_are_facts") is not False
                or payload.get("quote_semantic_truth_authority") is not False
                or payload.get("body_hypotheses_not_forwarded") is not True
                or "sources" in payload or "body_observations" in payload):
            raise ValueError("BODY_AUTHORITY_RED")
        quotes = payload.get("verified_quotes")
        if type(quotes) is not list or not quotes:
            raise ValueError("BODY_QUOTES_MISSING_RED")
        for q in quotes:
            text = q["text"]
            ref = q["source_ref"]
            sources = [s for s in (row["prior"], row["current"])
                       if sha256(s.encode()).hexdigest() == ref.get("sha256")]
            if len(sources) != 1:
                raise ValueError("BODY_QUOTE_FOREIGN_SOURCE_RED")
            _source_ref(ref, sources[0], text)
            if q.get("semantic_truth_authority") is not False:
                raise ValueError("BODY_SEMANTIC_AUTHORITY_RED")
        if (not any(row["policy_span"] in q["text"] for q in quotes)
                or not any(row["option_span"] in q["text"] for q in quotes)):
            raise ValueError("BODY_REQUIRED_QUOTES_RED")
    original = score(arm.get("output", ""), row["oracle"])
    if original != arm.get("score"):
        raise ValueError("NATIVE_OUTPUT_SCORE_MISMATCH_RED")
    return True


def _report_check(report, rows):
    if (report.get("schema") != SCHEMA_NAME
            or report.get("seed") != 1061
            or report.get("fixture_sha256") != FIXTURE_SHA
            or report.get("native") is not True
            or report.get("synthetic_body_observers") is not False
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
            or report.get("delivery_authority") != 0
            or report.get("native_jef_calls") != 0
            or report.get("native_c2_calls") != 0):
        raise ValueError("NATIVE_NEGATIVE_GATES_RED")
    if report.get("status") not in (*GOOD, BODY_RED, STRUCTURAL_RED):
        raise ValueError("NATIVE_STATUS_UNKNOWN_RED")
    originals = {r["id"]: r for r in rows}
    seen = set()
    scores = {a: 0 for a in ARMS}
    recorded = {a: 0 for a in ARMS}
    for case in report.get("rows", []):
        cid = case["id"]
        if cid not in originals or cid in seen:
            raise ValueError("NATIVE_CASE_ID_RED")
        seen.add(cid)
        row = originals[cid]
        if (case.get("prior_source_ref", {}).get("sha256") !=
                sha256(row["prior"].encode()).hexdigest()
                or case.get("current_source_ref", {}).get("sha256") !=
                sha256(row["current"].encode()).hexdigest()):
            raise ValueError("NATIVE_USER_SOURCE_REF_RED")
        if (case.get("closed_store_ok") is not True
                or case.get("no_live_output") is not True):
            raise ValueError("NATIVE_STORE_OR_OUTPUT_RED")
        for offer in case.get("offers", []):
            if offer.get("status") == "RECORDED":
                role = offer["role"]
                if (role not in MODEL_NAMES
                        or offer.get("process_reaped") is not True
                        or offer.get("native_metrics", {}).get("status") != "FINAL"
                        or offer["native_metrics"].get("actual_model") !=
                        MODEL_NAMES[role][0]
                        or offer.get("model_revision") != MODEL_NAMES[role][1]):
                    raise ValueError("BODY_MODEL_PIN_OR_REAP_RED")
        seen_arms = set()
        for arm in case.get("arms", []):
            name = arm.get("arm")
            if name not in ARMS or name in seen_arms:
                raise ValueError("DUPLICATE_OR_UNKNOWN_ARM_RED")
            seen_arms.add(name)
            if _arm_check(arm, row, name):
                recorded[name] += 1
                scores[name] += arm["score"]["correct"]
    if (report.get("scores") != scores
            or report.get("recorded_by_arm") != recorded):
        raise ValueError("REPORTED_SCORES_MISMATCH_RED")
    if report["status"] in GOOD:
        if (seen != set(originals)
                or any(recorded[a] != 6 for a in ARMS)
                or report.get("native_body_calls") != 18
                or report.get("native_c3_calls") != 18):
            raise ValueError("NATIVE_COMPLETE_COHORT_RED")
        none = [c for c in report["rows"] if c["id"] in ("Cinder", "Flux")]
        no_false_none = all(
            next(a for a in c["arms"] if a["arm"] == ARMS[2])
            ["score"]["parsed"] == {"choice": "NONE", "remaining": None}
            for c in none)
        signal = (scores[ARMS[2]] >= scores[ARMS[1]] + 2
                  and scores[ARMS[2]] >= scores[ARMS[0]] + 1
                  and no_false_none)
        if (report.get("exploratory_body_selection_signal") is not signal
                or report["status"] != GOOD[0 if signal else 1]):
            raise ValueError("EXPLORATORY_SIGNAL_RECOMPUTE_RED")
    elif report["status"] == BODY_RED:
        if (seen != set(originals)
                or recorded[ARMS[0]] != 6 or recorded[ARMS[1]] != 6
                or recorded[ARMS[2]] == 6):
            raise ValueError("PARTIAL_BODY_CLASSIFICATION_RED")
    return {"original_status": report["status"],
            "native_body_calls_recorded": report.get("native_body_calls"),
            "native_c3_calls_recorded": report.get("native_c3_calls"),
            "recomputed_scores": scores, "recomputed_recorded_by_arm": recorded,
            "cases_with_raw_report": len(seen),
            "native_complete": report["status"] in GOOD,
            "step2_promoted": False, "redmi_measured": False}


def audit(path, expected_sha, fixture_path):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != expected_sha:
        raise ValueError("ORIGINAL_OUTER_SHA_RED")
    fixture_raw = Path(fixture_path).read_bytes()
    if sha256(fixture_raw).hexdigest() != FIXTURE_SHA:
        raise ValueError("FROZEN_FIXTURE_SHA_RED")
    rows = fixture(fixture_path)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        inner = _zip_check(z)
        if z.read("HEAD.txt").decode().strip() != SOURCE_HEAD:
            raise ValueError("ORIGINAL_SOURCE_HEAD_RED")
        exits = {name: int(z.read(name + "_EXIT.txt").decode())
                 for name in STAGES}
        receipt = json.loads(z.read("RESULT.json"))
        if (receipt.get("head") != SOURCE_HEAD
                or receipt.get("exits") != exits
                or receipt.get("fixture_sha256") != FIXTURE_SHA
                or receipt.get("step2_promoted") is not False
                or receipt.get("b3_promoted") is not False
                or receipt.get("jepa_weight") != 0
                or receipt.get("redmi_measured") is not False
                or receipt.get("whole_system_complete") is not False):
            raise ValueError("ORIGINAL_WORKFLOW_RECEIPT_RED")
        phone_count = None
        if "V13-Phone-Run117U.zip" in z.namelist():
            phone_count = _phone_check(z.read("V13-Phone-Run117U.zip"),
                                       fixture_raw)
        if "NATIVE_CASE/report.json" in z.namelist():
            native = _report_check(json.loads(z.read("NATIVE_CASE/report.json")),
                                   rows)
        else:
            native = {"original_status": "NO_NATIVE_REPORT_STRUCTURAL_RED",
                      "native_complete": False,
                      "step2_promoted": False, "redmi_measured": False}
        return {"schema": "v13.run117v.original_native_readonly_audit.v1",
                "integrity_status": "ORIGINAL_ARTIFACT_INTEGRITY_PASS",
                "artifact_sha256": expected_sha, "source_head": SOURCE_HEAD,
                "sha256sum_files_checked": inner,
                "phone_source_files_checked": phone_count,
                "original_stage_exits": exits, "native": native,
                "model_called_by_auditor": False,
                "learning_authority": 0, "delivery_authority": 0,
                "step2_promoted": False, "b3_promoted": False,
                "body_jepa_promoted": False, "jepa_weight": 0,
                "redmi_measured": False, "whole_system_complete": False}


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
