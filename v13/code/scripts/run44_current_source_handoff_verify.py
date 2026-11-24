#!/usr/bin/env python3
"""Independent stdlib replay of original Run44 raw; no native inference."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ARMS = ("A_CURRENT_ONLY", "B_VERIFIED_B2_TO_C3", "C_RAW_PRIOR_TO_C3")
ORDER = (("A_CURRENT_ONLY", "B_VERIFIED_B2_TO_C3", "C_RAW_PRIOR_TO_C3"),
         ("B_VERIFIED_B2_TO_C3", "C_RAW_PRIOR_TO_C3", "A_CURRENT_ONLY"),
         ("C_RAW_PRIOR_TO_C3", "A_CURRENT_ONLY", "B_VERIFIED_B2_TO_C3"),
         ("A_CURRENT_ONLY", "C_RAW_PRIOR_TO_C3", "B_VERIFIED_B2_TO_C3"))
FIXTURE_SHA256 = "9dd92347af6275c8cd687a05aa4f1c63bbf5ba9f84a05af0b4c43e211fc6e530"
NEGATIVE = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "world_jepa_authority": "SHADOW",
            "redmi_measured": False, "whole_system_complete": False}


def require(ok, label):
    if not ok:
        raise ValueError("RUN44_REPLAY_" + label)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def exact_score(raw, oracle):
    try:
        value = json.loads(raw, parse_constant=lambda _: require(False, "NONFINITE"))
        return int(type(value) is dict and set(value) == {"choice", "remaining"}
                   and type(value["choice"]) is str and value["choice"] in ARMS_CHOICES
                   and (value["remaining"] is None or type(value["remaining"]) is int)
                   and value == oracle)
    except (ValueError, TypeError, OverflowError):
        return 0


ARMS_CHOICES = ("A", "B", "NONE", "UNKNOWN")


def replay(report_path, fixture_path):
    raw = Path(fixture_path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256, "FIXTURE_HASH")
    fixture = json.loads(raw)
    report = json.loads(Path(report_path).read_bytes())
    require(report.get("schema") == "v13.run44.current_source_handoff_native_result.v1"
            and report.get("registered") is True and report.get("seed") == 307
            and report.get("fixture_sha256") == FIXTURE_SHA256
            and report.get("negative_gates") == NEGATIVE, "REGISTRATION")
    rows = report.get("rows")
    require(type(rows) is list and len(rows) == 12, "TWELVE_ROWS")
    expected = [(f["id"], arm) for f, order in zip(fixture["fixtures"], ORDER) for arm in order]
    require([(r.get("fixture"), r.get("arm")) for r in rows] == expected,
            "ORDER_AND_UNIQUE")
    require(type(report.get("row_sha256")) is dict and len(report["row_sha256"]) == 12,
            "ROW_MANIFEST")
    counts = {a: {"rows": 0, "correct": 0, "structural": 0} for a in ARMS}
    for row in rows:
        key = row["fixture"] + "/" + row["arm"]
        require(report["row_sha256"].get(key) == digest(row), "ROW_HASH")
        f = next(f for f in fixture["fixtures"] if f["id"] == row["fixture"])
        require(row.get("prior_sha256") == hashlib.sha256(f["prior"].encode()).hexdigest()
                and row.get("current_sha256") == hashlib.sha256(f["current"].encode()).hexdigest()
                and row.get("oracle_visible_to_native") is False, "SOURCE_BINDING")
        msgs = row.get("native_prompt")
        require(type(msgs) is list and len(msgs) == 2
                and msgs[0].get("role") == "system" and msgs[1].get("role") == "user",
                "NATIVE_PROMPT")
        require(row.get("native_prompt_sha256") == digest(msgs), "PROMPT_HASH")
        payload = json.loads(msgs[1]["content"])
        require("oracle" not in msgs[1]["content"] and
                payload.get("current_source") == f["current"], "PROMPT_SOURCE")
        if row["arm"] == "A_CURRENT_ONLY":
            require(set(payload) == {"current_source"}, "ARM_A_CONTEXT")
        elif row["arm"] == "C_RAW_PRIOR_TO_C3":
            require(set(payload) == {"prior_source", "current_source"}
                    and payload["prior_source"] == f["prior"], "ARM_C_CONTEXT")
        else:
            require(set(payload) == {"current_source", "analysts"}
                    and type(payload["analysts"]) is list and payload["analysts"],
                    "ARM_B_CONTEXT")
            require(row.get("prior_quote_verified") is True
                    and len(row.get("native_b2_finals", [])) == 2
                    and all(v is True for v in row["native_b2_finals"]),
                    "ARM_B_B2")
            require(all(q in f["prior"] or q in f["current"]
                        for q in row.get("verified_quote_texts", [])),
                    "ARM_B_QUOTE_SCOPE")
        require(row.get("native_c3_final") is True and
                row.get("native_c3_metrics", {}).get("status") == "FINAL"
                and row.get("processes_reaped") is True
                and type(row.get("process_releases")) is list
                and row["process_releases"]
                and all(x.get("process_reaped") is True for x in row["process_releases"]),
                "NATIVE_FINAL_AND_REAPED")
        require(row.get("status") == "RECORDED", "ROW_STRUCTURAL")
        actual = exact_score(row.get("native_answer", ""), f["oracle"])
        require(row.get("score", {}).get("correct") == actual, "ORIGINAL_SCORE")
        counts[row["arm"]]["rows"] += 1
        counts[row["arm"]]["correct"] += actual
        counts[row["arm"]]["structural"] += 1
    require(counts == report.get("summary"), "SUMMARY")
    require(report.get("installed_binding_unchanged") is True, "MODEL_BINDING")
    a, b, c = (counts[arm]["correct"] for arm in ARMS)
    signal = b >= a+2 and b >= c-1 and b >= 2
    require(report.get("pilot_signal") is signal, "SIGNAL")
    status = "PILOT_SIGNAL_ONLY_NO_PROMOTION" if signal else "UTILITY_FAIL"
    require(report.get("status") == status, "STATUS")
    return {"schema": "v13.run44.independent_original_replay.v1",
            "status": status, "structural_valid": True, "pilot_signal": signal,
            "summary": counts, "negative_gates": NEGATIVE}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    result = replay(args.report, args.fixture)
    print(json.dumps(result, sort_keys=True))
    if not result["pilot_signal"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
