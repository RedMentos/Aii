#!/usr/bin/env python3
"""P2X native C3 validation raw scorer; strict 360-call evidence, no inference."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re

SCHEMA = "v13.p2x.native_receiver_eval.v1"
FIXTURE_SHA = "cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a"
INPUT_SHA = "a7f2d70d463305a43ec03bbd758a61cc91129a411094ed60e5503d4ffe0894cf"
ANSWER_SHA = "d1cbe570ae3caa2a80177f861ba5751c93208ffccc98f8d12d90578c59555e9a"
MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNTIME_SHA = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
ARMS = ("c3_only", "b1_only", "b2_only", "both_exact", "shuffled")
ACTIONS = ("A", "B", "NONE", "UNKNOWN")
SEED = 13


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_action(output):
    if type(output) is not str:
        return "UNPARSEABLE"
    try:
        data = json.loads(output)
    except (ValueError, TypeError):
        return "UNPARSEABLE"
    if type(data) is not dict or set(data) != {"action"}:
        return "UNPARSEABLE"
    return data["action"] if type(data["action"]) is str and data["action"] in ACTIONS else "UNPARSEABLE"


def load_validation(path):
    p = Path(path)
    data = {}
    for name, expected in (("validation_inputs.jsonl", INPUT_SHA),
                           ("validation_answers.jsonl", ANSWER_SHA)):
        f = p / name
        if f.is_symlink() or sha(f.read_bytes()) != expected:
            raise ValueError("P2X validation frozen SHA mismatch: " + name)
        data[name] = [json.loads(line) for line in f.read_bytes().splitlines()]
    plan, answers = data["validation_inputs.jsonl"], data["validation_answers.jsonl"]
    if len(plan) != 360 or len(answers) != 72:
        raise ValueError("P2X frozen validation count mismatch")
    answer_ids = [a.get("id") for a in answers]
    if (len(set(answer_ids)) != 72
            or any(type(a.get("oracle_action")) is not str
                   or a["oracle_action"] not in ("A", "B", "NONE") for a in answers)
            or any(sum(a["oracle_action"] == v for a in answers) != 24
                   for v in ("A", "B", "NONE"))):
        raise ValueError("P2X frozen validation oracle balance mismatch")
    expected_pairs = [(a["id"], arm) for a in answers for arm in ARMS]
    if [(p.get("id"), p.get("arm")) for p in plan] != expected_pairs:
        raise ValueError("P2X frozen validation identity/arm order mismatch")
    for r in plan:
        if (not r["id"].startswith("P2X") or type(r.get("messages")) is not list
                or len(r["messages"]) != 1 or r["messages"][0].get("role") != "user"
                or type(r["messages"][0].get("content")) is not str
                or any(term in r["messages"][0]["content"]
                       for term in ("target_action", "oracle_action", "max_first", "max_second"))):
            raise ValueError("P2X validation model input leak/malformed")
    return plan, answers


def score(records, plan, answers, adapter_sha256=None):
    if (type(records) is not list or len(records) != 360
            or type(plan) is not list or len(plan) != 360
            or type(answers) is not list or len(answers) != 72):
        raise ValueError("P2X native raw 360/72 coverage mismatch")
    if adapter_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", adapter_sha256):
        raise ValueError("P2X invalid adapter hash")
    if [(r.get("id"), r.get("arm")) for r in records] != [(p["id"], p["arm"]) for p in plan]:
        raise ValueError("P2X native raw identity/arm order mismatch")
    oracle = {a["id"]: a["oracle_action"] for a in answers}
    summary = {arm: {kind: 0 for kind in ("exact", "wrong_committed", "unknown", "unparseable")}
               for arm in ARMS}
    parsed_rows = []
    for rec, prompt in zip(records, plan):
        dur = rec.get("duration_s")
        if (rec.get("status") != "FINAL" or rec.get("model_called") is not True
                or rec.get("native_calls") != 1 or rec.get("seed") != SEED
                or rec.get("model_sha256") != MODEL_SHA
                or rec.get("runtime_sha256") != RUNTIME_SHA
                or rec.get("adapter_sha256") != adapter_sha256
                or rec.get("input_sha256") != sha(canonical(prompt["messages"]))
                or type(dur) not in (int, float) or not math.isfinite(dur)
                or not (0 <= dur <= 90)):
            raise ValueError("P2X native raw binding/duration mismatch")
        action = strict_action(rec.get("output"))
        expected = oracle[rec["id"]] if rec["arm"] == "both_exact" else "UNKNOWN"
        kind = ("exact" if action == expected else
                "wrong_committed" if action in ("A", "B", "NONE") else
                "unknown" if action == "UNKNOWN" else "unparseable")
        summary[rec["arm"]][kind] += 1
        parsed_rows.append({"id_sha256": sha(rec["id"].encode()),
                            "arm": rec["arm"], "parsed": action,
                            "expected": expected, "kind": kind})
    if any(sum(v.values()) != 72 for v in summary.values()):
        raise ValueError("P2X native raw arm count mismatch")
    return {"schema": SCHEMA + ".score.v1",
            "status": "P2X_NATIVE_RECEIVER_DIAGNOSTIC_NO_GATE",
            "fixture_sha256": FIXTURE_SHA, "model_sha256": MODEL_SHA,
            "runtime_sha256": RUNTIME_SHA, "adapter_sha256": adapter_sha256,
            "rows": 360, "native_calls": 360, "per_arm": summary,
            "details": parsed_rows, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
            "jepa_weight": 0, "redmi_measured": False,
            "whole_system_complete": False}


def compare(base, candidate):
    if (base.get("schema") != SCHEMA + ".score.v1"
            or candidate.get("schema") != SCHEMA + ".score.v1"
            or base.get("adapter_sha256") is not None
            or not isinstance(candidate.get("adapter_sha256"), str)
            or base.get("fixture_sha256") != candidate.get("fixture_sha256") != FIXTURE_SHA
            or base.get("model_sha256") != MODEL_SHA
            or candidate.get("model_sha256") != MODEL_SHA
            or base.get("rows") != candidate.get("rows") != 360):
        raise ValueError("P2X paired native base/candidate identity mismatch")
    return {"schema": SCHEMA + ".paired.v1",
            "status": "P2X_PAIRED_NATIVE_DIAGNOSTIC_NO_GATE",
            "base_exact_both": base["per_arm"]["both_exact"]["exact"],
            "candidate_exact_both": candidate["per_arm"]["both_exact"]["exact"],
            "both_exact_delta": (candidate["per_arm"]["both_exact"]["exact"]
                                 - base["per_arm"]["both_exact"]["exact"]),
            "foreign_wrong_committed_base": base["per_arm"]["shuffled"]["wrong_committed"],
            "foreign_wrong_committed_candidate": candidate["per_arm"]["shuffled"]["wrong_committed"],
            "step2_status": "UTILITY_FAIL", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--validation-dir", required=True)
    p.add_argument("--raw", required=True)
    p.add_argument("--adapter-sha256")
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        plan, answers = load_validation(args.validation_dir)
        records = json.loads(Path(args.raw).read_text(encoding="utf-8"))
        result = score(records, plan, answers, args.adapter_sha256)
        rc = 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        result = {"schema": SCHEMA + ".score.v1", "status": "P2X_RAW_RED_PRESERVED",
                  "error": type(exc).__name__ + ": " + str(exc),
                  "step2_status": "UTILITY_FAIL", "jepa_weight": 0,
                  "whole_system_complete": False}
        rc = 2
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as f:
        f.write(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
