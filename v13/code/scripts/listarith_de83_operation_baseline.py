"""Read-only seed83 frozen German operation baseline, before native results.

No C3 model invocation, arithmetic execution or live tool authority.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path

from v13.agi import listarith_de_shadow_v2_candidate as german

FIXTURE = Path(__file__).resolve().parents[1] / "specs/listarith_de83_native_shadow_frozen.json"
FIXTURE_BLOB = "cc052aa9eaecd213124f9c79df15f30637c5a80c"


def git_blob(path):
    import hashlib
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def baseline():
    if git_blob(FIXTURE) != FIXTURE_BLOB:
        raise ValueError("FROZEN_FIXTURE_CHANGED")
    d = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if d["seed"] != 83 or len(d["rows"]) != 24:
        raise ValueError("FROZEN_FIXTURE_SCHEMA_RED")
    rows = []
    for row in d["rows"]:
        p = german.propose(row["text"])
        if p["authority"] != "SHADOW_ONLY":
            raise ValueError("OPERATION_AUTHORITY_RED")
        rows.append({"id": row["id"], "expected_operation": row["expected_operation"],
                     "proposed_operation": p["proposal"], "reason": p["reason"],
                     "correct": p["proposal"] == row["expected_operation"]})
    total = sum(r["correct"] for r in rows)
    supported = sum(r["correct"] for r in rows if r["expected_operation"] is not None)
    unsupported = sum(r["correct"] for r in rows if r["expected_operation"] is None)
    fp = sum(r["expected_operation"] is None and r["proposed_operation"] is not None
             for r in rows)
    return {"schema": "v13.de83.operation_shadow_baseline.v1",
            "fixture_blob": FIXTURE_BLOB, "classifier_revision": german.REVISION,
            "rows": rows, "exact_total": total, "exact_supported": supported,
            "exact_unsupported": unsupported, "unsupported_false_positives": fp,
            "evidence_level": "SOFTWARE_SYNTHETIC_PRE_NATIVE",
            "live_tool_execution": False, "native_model_calls": 0,
            "step2_gate_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("FRESH_OUTPUT_REQUIRED")
    result = baseline()
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("exact_total", "exact_supported", "exact_unsupported",
                       "unsupported_false_positives", "evidence_level")}))


if __name__ == "__main__":
    main()
