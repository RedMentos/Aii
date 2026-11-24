#!/usr/bin/env python3
"""Independent read-only audit of frozen Run44 original raw receipts (posthoc)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FIXTURE_SHA256 = "9dd92347af6275c8cd687a05aa4f1c63bbf5ba9f84a05af0b4c43e211fc6e530"
ARMS = ("A_CURRENT_ONLY", "B_VERIFIED_B2_TO_C3", "C_RAW_PRIOR_TO_C3")
ORDER = (
    ("A_CURRENT_ONLY", "B_VERIFIED_B2_TO_C3", "C_RAW_PRIOR_TO_C3"),
    ("B_VERIFIED_B2_TO_C3", "C_RAW_PRIOR_TO_C3", "A_CURRENT_ONLY"),
    ("C_RAW_PRIOR_TO_C3", "A_CURRENT_ONLY", "B_VERIFIED_B2_TO_C3"),
    ("A_CURRENT_ONLY", "C_RAW_PRIOR_TO_C3", "B_VERIFIED_B2_TO_C3"),
)
NEGATIVE = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "world_jepa_authority": "SHADOW",
            "redmi_measured": False, "whole_system_complete": False}
MODELS = {
    "B1_DETAIL": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
    "B2_GIST": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
    "C3_LANGUAGE": "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
}
SYS = (
    "Use only supplied source text. Do not infer a missing budget or deadline. "
    "Apply earlier project rules if available, otherwise say UNKNOWN. "
    "An option is eligible only if cost <= budget, days <= deadline, and "
    "local if local-only is required. Choose the cheapest eligible option. "
    "If no eligible option exists choose NONE. If budget is missing choose UNKNOWN. "
    "Return only a JSON object with choice and remaining; remaining is null "
    "for NONE or UNKNOWN. No explanation."
)


class AuditError(ValueError):
    pass


def need(condition, label):
    if not condition:
        raise AuditError("RUN45A_" + label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8"))


def no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise AuditError("RUN45A_DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def strict_json(raw):
    return json.loads(raw, object_pairs_hook=no_duplicates,
                      parse_constant=lambda _: need(False, "NONFINITE"))


def strict_score(answer, oracle):
    try:
        obj = strict_json(answer)
    except (ValueError, TypeError, OverflowError):
        return 0
    return int(type(obj) is dict and set(obj) == {"choice", "remaining"}
               and type(obj["choice"]) is str
               and obj["choice"] in ("A", "B", "NONE", "UNKNOWN")
               and (obj["remaining"] is None or type(obj["remaining"]) is int)
               and obj == oracle)


def validate_quote(q, row, fixture):
    need(type(q) is dict and q.get("semantic_truth_authority") is False,
         "QUOTE_AUTHORITY")
    need(q.get("verification") in ("EXACT_SOURCE_SUBSTRING_ONLY",
                                   "EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE"),
         "QUOTE_VERIFICATION")
    ref = q.get("source_ref")
    need(type(ref) is dict and type(q.get("text")) is str and q["text"],
         "QUOTE_SHAPE")
    for name in ("prior", "current"):
        base = row.get(name + "_source_ref")
        source = fixture[name]
        if not isinstance(base, dict):
            continue
        if ref.get("source_id") != base.get("source_id"):
            continue
        need(ref.get("sha256") == base.get("sha256") == sha(source.encode("utf-8"))
             and ref.get("modality") == base.get("modality"),
             "QUOTE_SOURCE_IDENTITY")
        a, b = ref.get("char_start"), ref.get("char_end")
        x, y = base.get("char_start"), base.get("char_end")
        need(all(type(v) is int for v in (a, b, x, y))
             and 0 <= x <= a < b <= y <= len(source), "QUOTE_RANGE")
        need(source[a:b] == q["text"], "QUOTE_SPAN")
        return name
    raise AuditError("RUN45A_QUOTE_FOREIGN_SOURCE")


def audit(report_path, fixture_path):
    fixture_bytes = Path(fixture_path).read_bytes()
    need(sha(fixture_bytes) == FIXTURE_SHA256, "FIXTURE_HASH")
    fixture = strict_json(fixture_bytes)
    need(type(fixture) is dict and fixture.get("seed") == 307
         and len(fixture.get("fixtures", [])) == 4, "FIXTURE_SCHEMA")
    report = strict_json(Path(report_path).read_bytes())
    need(type(report) is dict and report.get("schema")
         == "v13.run44.current_source_handoff_native_result.v1"
         and report.get("registered") is True and report.get("seed") == 307
         and report.get("fixture_sha256") == FIXTURE_SHA256
         and report.get("negative_gates") == NEGATIVE, "REGISTRATION")
    need(report.get("binding", {}).get("model_sha256") == MODELS,
         "MODEL_HASHES")
    rows = report.get("rows")
    need(type(rows) is list and len(rows) <= 12, "ROW_COUNT")
    expected = [(f["id"], arm) for f, order in zip(fixture["fixtures"], ORDER)
                for arm in order]
    need([(r.get("fixture"), r.get("arm")) for r in rows] == expected[:len(rows)],
         "ROW_ORDER")
    manifest = report.get("row_sha256")
    need(type(manifest) is dict and set(manifest)
         == {r["fixture"] + "/" + r["arm"] for r in rows}, "ROW_MANIFEST")
    counts = {a: {"rows": 0, "correct": 0, "structural": 0} for a in ARMS}
    reasons = []
    for row in rows:
        key = row["fixture"] + "/" + row["arm"]
        need(manifest[key] == digest(row), "ROW_DIGEST")
        f = next(f for f in fixture["fixtures"] if f["id"] == row["fixture"])
        need(row.get("prior_sha256") == sha(f["prior"].encode("utf-8"))
             and row.get("current_sha256") == sha(f["current"].encode("utf-8"))
             and row.get("oracle_visible_to_native") is False, "SOURCE_HASHES")
        arm = row["arm"]
        counts[arm]["rows"] += 1
        if row.get("status") != "RECORDED":
            reasons.append(key + ":ORIGINAL_STRUCTURAL_" + str(row.get("status")))
            continue
        msgs = row.get("native_prompt")
        need(type(msgs) is list and len(msgs) == 2
             and msgs[0] == {"role": "system", "content": SYS}
             and msgs[1].get("role") == "user"
             and type(msgs[1].get("content")) is str
             and digest(msgs) == row.get("native_prompt_sha256"),
             "NATIVE_PROMPT")
        payload = strict_json(msgs[1]["content"])
        need(type(payload) is dict and payload.get("current_source") == f["current"]
             and "oracle" not in msgs[1]["content"], "PROMPT_SOURCE")
        if arm == ARMS[0]:
            need(set(payload) == {"current_source"}, "A_CONTEXT")
        elif arm == ARMS[2]:
            need(set(payload) == {"current_source", "prior_source"}
                 and payload["prior_source"] == f["prior"], "C_CONTEXT")
        else:
            need(set(payload) == {"current_source", "analysts"}
                 and type(payload["analysts"]) is list and len(payload["analysts"]) == 1,
                 "B_CONTEXT")
            need(row.get("native_b2_finals") == [True, True]
                 and row.get("prior_quote_verified") is True,
                 "B_PRODUCER_FINAL")
            refs, texts, prior_count = [], [], 0
            for analyst in payload["analysts"]:
                need(analyst.get("role") == "B2_GIST"
                     and analyst.get("hypothesis_authority") == "MODEL_HYPOTHESIS_NOT_FACT"
                     and type(analyst.get("verified_quotes")) is list,
                     "B_ANALYST_AUTHORITY")
                for q in analyst["verified_quotes"]:
                    origin = validate_quote(q, row, f)
                    prior_count += int(origin == "prior")
                    refs.append(q["source_ref"])
                    texts.append(q["text"])
            need(prior_count >= 1 and refs == row.get("verified_quote_refs")
                 and texts == row.get("verified_quote_texts"), "B_QUOTE_RECEIPTS")
        need(row.get("native_c3_final") is True
             and row.get("native_c3_metrics", {}).get("status") == "FINAL"
             and row.get("processes_reaped") is True
             and type(row.get("process_releases")) is list
             and len(row["process_releases"]) > 0
             and all(v.get("process_reaped") is True
                     for v in row["process_releases"]), "NATIVE_FINAL_REAP")
        counts[arm]["structural"] += 1
        score = strict_score(row.get("native_answer", ""), f["oracle"])
        counts[arm]["correct"] += score
        if row.get("score", {}).get("correct") != score:
            reasons.append(key + ":ORIGINAL_SCORE_DISAGREEMENT")
    if len(rows) < 12:
        reasons.append("ORIGINAL_INCOMPLETE_ROWS")
    original = report.get("summary")
    if len(rows) == 12 and original != counts:
        reasons.append("ORIGINAL_SUMMARY_DISAGREEMENT")
    a, b, c = (counts[x]["correct"] for x in ARMS)
    structural = len(rows) == 12 and all(counts[x]["structural"] == 4 for x in ARMS)
    signal = structural and b >= a + 2 and b >= c - 1 and b >= 2
    if structural and report.get("pilot_signal") is not signal:
        reasons.append("ORIGINAL_SIGNAL_DISAGREEMENT")
    if structural and report.get("installed_binding_unchanged") is not True:
        reasons.append("MODEL_BINDING_CHANGED")
    if structural and report.get("status") not in (
            ("PILOT_SIGNAL_ONLY_NO_PROMOTION" if signal else "UTILITY_FAIL"),):
        reasons.append("ORIGINAL_STATUS_DISAGREEMENT")
    if not structural:
        status = "ORIGINAL_INCOMPLETE"
    elif reasons:
        status = "AUDIT_RED"
    else:
        status = "AUDIT_GREEN_STRUCTURAL"
    return {"schema": "v13.run45a.independent_run44_original_raw_audit.v1",
            "status": status, "reasons": reasons, "strict_summary": counts,
            "strict_pilot_signal": bool(signal), "negative_gates": NEGATIVE,
            "scope": "POSTHOC_READ_ONLY_NO_ORIGINAL_SCORE_OR_AGE_PROMOTION"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.report, args.fixture)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "AUDIT_GREEN_STRUCTURAL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
