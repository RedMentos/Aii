"""Strict offline scorer for the preregistered Run11 bilingual Age0 prompt cohort.

This script NEVER runs a model or verifies claimed native provenance. Supplied
answers are untrusted external data. A lexical score is not semantic utility.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

APP = Path(__file__).resolve().parents[1]
FIXTURE = APP / "specs/age0-bilingual-arith-heldout-20261028.json"
FIXTURE_BLOB = "ceda0a5cb506cf09885652b24893cf7d8fdff63b"
BASELINE_PROMPT = "a74d7517a7ab70e801e177b58da057e57fd3460c"
CANDIDATE_PROMPT = "646c6f31b52ca2664c1952af7c7e842fc3e20885"
PROMPTS = {BASELINE_PROMPT, CANDIDATE_PROMPT}
ROLES = {"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"}
NUMBER = re.compile(r"(?<![\w.])[-+]?[0-9]+(?:[.,][0-9]+)?(?![\w])")
UNKNOWN = re.compile(
    r"\b(?:unknown|not stated|not provided|not specified|cannot determine|"
    r"can't determine|i don't know|not enough information|unbekannt|"
    r"nicht angegeben|nicht genannt|nicht bekannt|keine angabe|"
    r"weiß ich nicht|unklar)\b", re.I
)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SHA1 = re.compile(r"[0-9a-f]{40}\Z")


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def fixture(path=FIXTURE):
    raw = Path(path).read_bytes()
    if _git_blob(raw) != FIXTURE_BLOB:
        raise ValueError("Frozen heldout corpus Git blob mismatch")
    data = json.loads(raw)
    if data.get("schema") != "v13.age0.bilingual_numeric_heldout.v1":
        raise ValueError("Unexpected heldout schema")
    rows = data["items"]
    if len(rows) != 16 or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Frozen heldout row count/identity mismatch")
    return rows


def _decimal(text):
    try:
        n = Decimal(text.replace(",", "."))
        return n if n.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def numeric_proxy(answer, item):
    """Conservative lexical result proxy, NOT proof of a correct explanation."""
    # Explicit denial/uncertainty must never be mistaken for an asserted result.\n    if UNKNOWN.search(answer) or re.search(r"\\b(?:not|isn.t|incorrect|wrong|falsch|nicht|maybe|perhaps|vielleicht|unsicher)\\b", answer, re.I):\n        return False\n    numbers = [_decimal(m.group(0)) for m in NUMBER.finditer(answer)]
    expected = _decimal(item["expected"])
    allowed = {_decimal(x) for x in item["operands"]} | {expected}
    return expected in numbers and all(n is not None and n in allowed for n in numbers)


def score(path, items):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    if data.get("schema") != "v13.age0.bilingual_numeric_answers.v1":
        raise ValueError("Unrecognized answer manifest schema")
    if data.get("prompt_git_blob") not in PROMPTS:
        raise ValueError("Prompt is not a preregistered baseline/candidate")
    if not isinstance(data.get("source_commit"), str) or not SHA1.fullmatch(data["source_commit"]):
        raise ValueError("Missing source commit")
    if not isinstance(data.get("model_sha256"), str) or not SHA256.fullmatch(data["model_sha256"]):
        raise ValueError("Missing model SHA256")
    rows = data.get("rows")
    if not isinstance(rows, list) or len(rows) != len(items):
        raise ValueError("Missing or extra answer rows")
    by_id = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ValueError("Invalid answer row")
        if row["id"] in by_id:
            raise ValueError("Duplicate answer row: " + row["id"])
        by_id[row["id"]] = row
    if set(by_id) != {x["id"] for x in items}:
        raise ValueError("Unknown or missing answer IDs")
    counts = {"numeric": 0, "numeric_proxy_match": 0,
              "unsupported": 0, "unsupported_uncertainty_marker": 0}
    per_item = []
    for item in items:
        row = by_id[item["id"]]
        if row.get("prompt") != item["prompt"]:
            raise ValueError("Question drift: " + item["id"])
        if row.get("status") != "FINAL" or row.get("runner_role") not in ROLES:
            raise ValueError("Missing final/runner evidence: " + item["id"])
        if row.get("tool_call") is not None or row.get("learning_mode") != "RECORD_ONLY":
            raise ValueError("Age0 authority violation: " + item["id"])
        weight = row.get("jepa_weight")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or weight != 0:
            raise ValueError("Age0 jepa_weight violation: " + item["id"])
        answer = row.get("answer")
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 20000:
            raise ValueError("Missing/oversized final answer: " + item["id"])
        if item["kind"] == "numeric":
            match = numeric_proxy(answer, item)
            counts["numeric"] += 1
            counts["numeric_proxy_match"] += int(match)
        elif item["kind"] == "unsupported":
            match = bool(UNKNOWN.search(answer))
            counts["unsupported"] += 1
            counts["unsupported_uncertainty_marker"] += int(match)
        else:
            raise ValueError("Unknown frozen item kind")
        per_item.append({"id": item["id"], "lang": item["lang"],
                         "kind": item["kind"], "lexical_proxy_match": match,
                         "runner_role": row["runner_role"],
                         "answer_sha256": hashlib.sha256(answer.encode()).hexdigest()})
    return {"prompt_git_blob": data["prompt_git_blob"], "source_commit": data["source_commit"],
            "model_sha256": data["model_sha256"], "input_sha256": hashlib.sha256(raw).hexdigest(),
            "counts": counts, "items": per_item}


def evaluate(answers, compare=None, corpus=FIXTURE):
    items = fixture(corpus)
    first = score(answers, items)
    results = [first]
    if compare is not None:
        second = score(compare, items)
        if first["prompt_git_blob"] == second["prompt_git_blob"]:
            raise ValueError("Paired comparison requires distinct frozen prompt versions")
        if first["model_sha256"] != second["model_sha256"]:
            raise ValueError("Paired comparison requires identical model bytes")
        results.append(second)
    return {
        "schema": "v13.age0.bilingual_numeric_offline_score.v1",
        "evidence_kind": "SOFTWARE_OFFLINE_SCORER_ONLY",
        "fixture_git_blob": FIXTURE_BLOB,
        "runs": results,
        "external_native_claims_verified": False,
        "semantic_grounding_verified": False,
        "phone_measured": False,
        "age0_tool_authority": False,
        "jepa_weight": 0,
        "step2_utility": "FAIL",
        "b3_l1": "FAIL",
        "body_jepa": "UNAVAILABLE",
        "lp3_heldout": "FAIL",
        "whole_system_complete": False,
        "claim_limit": "Author labels; numeric and uncertainty lexical proxies only. "
                       "Source/model SHA strings in external manifests are not independently verified.",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--answers", required=True, type=Path)
    ap.add_argument("--compare", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    report = evaluate(args.answers, args.compare)
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite existing score")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"evidence_kind": report["evidence_kind"],
                      "counts": [r["counts"] for r in report["runs"]]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
