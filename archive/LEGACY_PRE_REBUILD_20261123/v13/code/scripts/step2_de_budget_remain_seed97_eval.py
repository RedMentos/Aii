"""Frozen seed97 German budget remainder SHADOW source-only evaluation."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from v13.agi import budget_de_shadow

CODE = Path(__file__).resolve().parents[1]
FIXTURE = CODE / "specs/step2_de_budget_remain_seed97_frozen.json"
FIXTURE_BLOB = "b0d50ab64b97aa646fd5b3dd02940a8375c0eafc"


def blob_sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def evaluate():
    if blob_sha(FIXTURE) != FIXTURE_BLOB:
        raise ValueError("FROZEN_FIXTURE_CHANGED")
    d = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if (d.get("schema") != "v13.step2.de_budget_remain.shadow_frozen.v1"
            or d.get("seed") != 97 or len(d["rows"]) != 24
            or d.get("supported") != 12 or d.get("unsupported") != 12):
        raise ValueError("FIXTURE_SCHEMA_RED")
    rows = []
    for row in d["rows"]:
        got = budget_de_shadow.evaluate(row["text"])
        if got["authority"] != "SHADOW_ONLY" or got["live_tool_execution"]:
            raise ValueError("SHADOW_AUTHORITY_RED")
        expected = row["expected"]
        emitted = got["status"] == "SHADOW_RESULT"
        if expected is None:
            correct = not emitted
        else:
            correct = (emitted and got["budget"] == expected["budget"]
                       and [{k: o[k] for k in ("name", "cost", "remaining")}
                            for o in got["options"]] == expected["options"])
            if correct:
                bstart, bend = got["budget_source_span"]
                correct = str(got["budget"]) in row["text"][bstart:bend]
                for o in got["options"]:
                    start, end = o["source_span"]
                    correct &= (o["name"] in row["text"][start:end]
                                and str(o["cost"]) in row["text"][start:end])
        rows.append({"id": row["id"], "supported": expected is not None,
                     "correct": bool(correct), "emitted": emitted,
                     "reason": got["reason"], "budget": got["budget"],
                     "options": got["options"]})
    supported_correct = sum(r["correct"] for r in rows if r["supported"])
    supported_wrong = sum(r["emitted"] and not r["correct"] for r in rows if r["supported"])
    unsupported_fp = sum(r["emitted"] for r in rows if not r["supported"])
    status = ("SHADOW_DE_BUDGET_REMAINDER_SUPPORTED"
              if supported_correct == 12 and supported_wrong == 0 and unsupported_fp == 0
              else "SHADOW_DE_BUDGET_REMAINDER_NOT_SUPPORTED")
    return {"schema": "v13.step2.de_budget_remain.seed97.report.v1",
            "fixture_blob": FIXTURE_BLOB, "seed": 97,
            "status": status, "supported_correct": supported_correct,
            "supported_wrong_emitted": supported_wrong,
            "unsupported_false_positive": unsupported_fp,
            "rows": rows, "evidence_level": "SOFTWARE_SYNTHETIC_SHADOW_ONLY",
            "native_model_calls": 0, "live_tool_execution": False,
            "external_action_authority": False,
            "step2_gate_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("FRESH_OUTPUT_REQUIRED")
    result = evaluate()
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("status", "supported_correct", "supported_wrong_emitted",
                       "unsupported_false_positive", "evidence_level")}))


if __name__ == "__main__":
    main()
