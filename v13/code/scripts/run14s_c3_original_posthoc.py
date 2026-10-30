"""Run14S read-only, posthoc source-fact diagnostics for exact Run14L native ZIP.

Not a rescore of the registered experiment, not an active C3 consumer.
No native calls, no writes, no model updates and no promotion authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ORIGINAL_ZIP_SHA256 = "8ab389b2ebe5876f1b37696460a650e0f8e9d2bf49d9a2b0afa9d9c7639f8b8a"
FIXTURE_SHA256 = "a598c5f6eed3c956c3aa2f1e6f9419b8054d155e1f145aa0ca58776b26f1ffd1"
ORIGINAL_HEAD = "067920aa2d3896917e9cdd07e24b5ba0be28201c"
MODEL_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
MODEL_REVISION = "657e078c94084481950a2d555a941481f715536b"
SYSTEM = ("You are a strict data extraction engine. Return only one JSON object "
          "with six exact fields; no commentary or invented facts.")
PREFIX = ("Extract project, option_a, remaining_a, option_b, remaining_b, faster "
          "from these verified facts. Return JSON with exactly those six keys; "
          "amounts must be integers.\nVERIFIED_FACTS:\n")
SEED = 307
ARMS = ("COPY_BASELINE", "STRUCTURED_JSON")
MAX_ZIP_BYTES = 2_000_000
MAX_JSON_BYTES = 4096


def _sha(data):
    if type(data) is str:
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _reject_constant(_):
    raise ValueError("NONFINITE_JSON")


def _unique_pairs(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("DUPLICATE_JSON_KEY")
        obj[k] = v
    return obj


def _load_json(data):
    return json.loads(data, parse_constant=_reject_constant,
                      object_pairs_hook=_unique_pairs)


def _fixture(path):
    data = _load_json(Path(path).read_text(encoding="utf-8"))
    if type(data) is not dict or data.get("schema") != "v13.run14l.c3_structured_native.fixture.v1" or data.get("seed") != SEED:
        raise ValueError("FIXTURE_SCHEMA_RED")
    cases = data.get("cases")
    if (type(cases) is not list or len(cases) != 8
            or data.get("cases_sha256") != FIXTURE_SHA256
            or _sha(json.dumps(tuple(cases), sort_keys=True, separators=(",", ":"))) != FIXTURE_SHA256):
        raise ValueError("FROZEN_FIXTURE_RED")
    seen = set()
    for c in cases:
        if (type(c) is not dict or set(c) != {"project", "budget", "a", "a_cost", "a_days", "b", "b_cost", "b_days"}
                or type(c["project"]) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", c["project"])
                or c["project"] in seen or not c["project"].endswith("307")
                or any(type(c[k]) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z-]{0,31}", c[k]) for k in ("a", "b"))
                or c["a"] == c["b"]
                or any(type(c[k]) is not int for k in ("budget", "a_cost", "a_days", "b_cost", "b_days"))
                or not (0 < c["a_cost"] < c["budget"] <= 999999 and 0 < c["b_cost"] < c["budget"]
                        and 0 < c["a_days"] <= 365 and 0 < c["b_days"] <= 365 and c["a_days"] != c["b_days"])):
            raise ValueError("FROZEN_CASE_RED")
        seen.add(c["project"])
    return cases


def _answer(case):
    a, b = case["a"], case["b"]
    ra, rb = case["budget"] - case["a_cost"], case["budget"] - case["b_cost"]
    faster = a if case["a_days"] < case["b_days"] else b
    return (f"Project {case['project']}.\n{a} leaves {ra} Euro remaining.\n"
            f"{b} leaves {rb} Euro remaining.\n{faster} finishes sooner.")


def _read_original_zip(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_ZIP_BYTES or _sha(path.read_bytes()) != ORIGINAL_ZIP_SHA256:
        raise ValueError("ORIGINAL_ZIP_SHA_RED")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if (len(names) != len(set(names)) or len(names) != 40 or "SHA256SUMS" not in names
                or any(name.startswith("/") or ".." in name.split("/") or "\\" in name for name in names)
                or z.testzip() is not None):
            raise ValueError("ORIGINAL_ZIP_COVERAGE_OR_CRC_RED")
        lines = z.read("SHA256SUMS").decode("ascii").splitlines()
        if len(lines) != 39:
            raise ValueError("ORIGINAL_MANIFEST_COUNT_RED")
        covered = set()
        for line in lines:
            m = re.fullmatch(r"([0-9a-f]{64})  \./([A-Za-z0-9_./-]+)", line)
            if m is None or m[2] in covered or m[2] not in names or _sha(z.read(m[2])) != m[1]:
                raise ValueError("ORIGINAL_MANIFEST_HASH_RED")
            covered.add(m[2])
        if covered != set(names) - {"SHA256SUMS"}:
            raise ValueError("ORIGINAL_MANIFEST_COVERAGE_RED")
        if z.read("HEAD.txt").decode("ascii").strip() != ORIGINAL_HEAD:
            raise ValueError("ORIGINAL_HEAD_RED")
        for stage in ("PINS", "VENV", "DEPS", "TEST", "BOOTSTRAP", "NATIVE", "REPORT_CHECK", "COMPILE", "PRIVACY", "DIFF"):
            if z.read(f"{stage}_EXIT.txt").strip() != b"0":
                raise ValueError("ORIGINAL_STAGE_RED")
        return {name: z.read(name) for name in names if name.startswith("pilot/")}


def _parse_fenced(candidate):
    if type(candidate) is not str or len(candidate.encode("utf-8")) > MAX_JSON_BYTES:
        return "INVALID_OR_OVERSIZE", None
    if not candidate.startswith("```json\n") or not candidate.endswith("\n```"):
        return "FENCE_INCOMPLETE_OR_DIFFERENT", None
    try:
        data = _load_json(candidate[len("```json\n"):-len("\n```")])
    except (ValueError, UnicodeError):
        return "FENCED_JSON_INVALID", None
    return ("CLOSED_JSON_OBJECT", data) if type(data) is dict else ("FENCED_JSON_NOT_OBJECT", None)


def _text_four_exact(case, data):
    """Exact four source strings in order; no partial credit or fuzzy semantic judge."""
    if type(data) is not dict or type(data.get("VERIFIED_FACTS")) is not list:
        return False
    facts = data["VERIFIED_FACTS"]
    if len(facts) != 4 or any(type(x) is not str for x in facts):
        return False
    a, b = case["a"], case["b"]
    ra, rb = case["budget"] - case["a_cost"], case["budget"] - case["b_cost"]
    faster = a if case["a_days"] < case["b_days"] else b
    patterns = (
        rf"Project {re.escape(case['project'])}\.?",
        rf"{re.escape(a)} leaves {ra} [Ee]uros?(?: remaining)?\.?",
        rf"{re.escape(b)} leaves {rb} [Ee]uros?(?: remaining)?\.?",
        rf"{re.escape(faster)} finishes sooner\.?",
    )
    return all(re.fullmatch(pattern, fact) is not None for pattern, fact in zip(patterns, facts))


def audit(zip_path, fixture_path):
    """Read exact immutable original ZIP; return diagnostic counts only."""
    cases = _fixture(fixture_path)
    entries = _read_original_zip(zip_path)
    report = _load_json(entries["pilot/report.json"])
    if (type(report) is not dict or report.get("schema") != "v13.run14l.c3_structured_native.v1"
            or report.get("status") != "FIDELITY_HURT" or report.get("rows") != 16
            or report.get("fixture_sha256") != FIXTURE_SHA256
            or report.get("all_native_final_and_reaped") is not True
            or report.get("totals", {}).get("STRUCTURED_JSON", {}).get("structured_slots_exact") != 0
            or report.get("totals", {}).get("COPY_BASELINE", {}).get("full_source_faithful") != 4):
        raise ValueError("ORIGINAL_REPORT_GATE_RED")
    counts = {"fenced_json": 0, "closed_json_object": 0, "incomplete_or_invalid_json": 0,
              "exact_four_source_strings": 0, "exact_four_with_extra_keys": 0,
              "exact_four_no_extra_keys": 0, "wrong_shape_or_values": 0}
    detail = []
    pids = set()
    for i, case in enumerate(cases):
        rows = []
        for arm in ARMS:
            name = f"pilot/raw/{i:02d}_{arm}.json"
            row = _load_json(entries[name])
            answer = _answer(case)
            output = row.get("final_output")
            if (type(row) is not dict or row.get("index") != i or row.get("seed") != SEED
                    or row.get("project") != case["project"] or row.get("arm") != arm
                    or row.get("answer_sha256") != _sha(answer)
                    or row.get("model_sha256") != MODEL_SHA256
                    or row.get("model_revision") != MODEL_REVISION
                    or row.get("native_role") != "C3_LANGUAGE" or row.get("native_calls") != 1
                    or row.get("native_status") != "FINAL" or row.get("native_reaped") is not True
                    or type(row.get("native_pid")) is not int or row["native_pid"] <= 0
                    or row["native_pid"] in pids
                    or type(row.get("native_release")) is not dict
                    or row["native_release"].get("process_reaped") is not True
                    or type(output) is not str or row.get("native_output_sha256") != _sha(output)
                    or row.get("native_output_bytes") != len(output.encode("utf-8"))
                    or row.get("learning_mode") != "RECORD_ONLY" or row.get("jepa_weight") != 0
                    or row.get("step2_status") != "UTILITY_FAIL" or row.get("b3_status") != "NO_PROMOTION"
                    or row.get("body_jepa_status") != "UNAVAILABLE" or row.get("redmi_measured") is not False
                    or row.get("whole_system_complete") is not False):
                raise ValueError("ORIGINAL_NATIVE_ROW_RED")
            pids.add(row["native_pid"])
            rows.append(row)
        copy, structured = rows
        for key in ("source_event_id", "query_event_id", "context_plan_packet_id", "source_sha256", "answer_sha256"):
            if type(copy.get(key)) is not str or not copy[key] or copy[key] != structured.get(key):
                raise ValueError("ORIGINAL_PAIR_BINDING_RED")
        answer = _answer(case)
        if (structured.get("prompt_sha256") != _sha(PREFIX + answer)
                or structured.get("system_sha256") != _sha(SYSTEM)
                or structured.get("score", {}).get("structured_slots_exact") is not False
                or structured.get("score", {}).get("full_source_faithful") is not False):
            raise ValueError("ORIGINAL_STRUCTURED_PROMPT_OR_SCORE_RED")
        output = structured["final_output"]
        if output.startswith("```json\n"):
            counts["fenced_json"] += 1
        kind, parsed = _parse_fenced(output)
        exact = _text_four_exact(case, parsed)
        if kind == "CLOSED_JSON_OBJECT":
            counts["closed_json_object"] += 1
        else:
            counts["incomplete_or_invalid_json"] += 1
        if exact:
            counts["exact_four_source_strings"] += 1
            if set(parsed) == {"VERIFIED_FACTS"}:
                counts["exact_four_no_extra_keys"] += 1
            else:
                counts["exact_four_with_extra_keys"] += 1
        else:
            counts["wrong_shape_or_values"] += 1
        detail.append({"index": i, "project": case["project"], "json_shape": kind,
                       "exact_four_source_strings": exact,
                       "unverified_extra_keys": bool(exact and set(parsed) != {"VERIFIED_FACTS"}),
                       "admissible_under_strict_four_string_schema": bool(exact and set(parsed) == {"VERIFIED_FACTS"})})
    return {"schema": "v13.run14s.c3_original_posthoc.v1", "evidence_kind": "ORIGINAL_LINUX_NATIVE_RAW_POSTHOC_READONLY",
            "original_zip_sha256": ORIGINAL_ZIP_SHA256, "original_head": ORIGINAL_HEAD,
            "fixture_cases_sha256": FIXTURE_SHA256, "rows_verified": 16,
            "distinct_reaped_native_pids": len(pids), "structured_rows": 8,
            "counts": counts, "details": detail,
            "registered_original_verdict_unchanged": "FIDELITY_HURT",
            "no_intervention_efficacy_claim": True, "no_native_calls_by_audit": True,
            "no_authority": True, "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
            "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-zip", required=True, type=Path)
    p.add_argument("--fixture", required=True, type=Path)
    args = p.parse_args(argv)
    print(json.dumps(audit(args.original_zip, args.fixture), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
