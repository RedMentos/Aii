#!/usr/bin/env python3
"""Independent original Run49 real native end-to-end SHADOW report replay."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

FIXTURE_SHA = "d0f9dc7b6dabdeec0cd5343be18517c7813071abbb104b78469e695cccd6c21d"
IDS = ("Alder", "Beacon", "Grove", "Haze", "Lumen", "Reef")
SYS = ("You are a JSON formatter, not a decision maker. Copy the supplied "
       "source-verified typed JEF candidate's choice and remaining exactly. "
       "Do not recalculate or change it. Return only those two JSON keys.")
NEGATIVE = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "world_jepa_authority": "SHADOW",
            "redmi_measured": False, "whole_system_complete": False}
MODELS = {"B1_DETAIL": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
          "B2_GIST": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
          "C3_LANGUAGE": "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"}
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"


def require(ok, name):
    if not ok:
        raise ValueError("RUN49_REPLAY_" + name)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def unique(pairs):
    d = {}
    for k, v in pairs:
        require(k not in d, "DUPLICATE_JSON")
        d[k] = v
    return d


def nonfinite(_):
    raise ValueError("NONFINITE")


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def correct(raw, oracle):
    try:
        v = parse(raw)
        return int(type(v) is dict and set(v) == {"choice", "remaining"}
                   and type(v["choice"]) is str and v["choice"] in ("A", "B", "NONE", "UNKNOWN")
                   and (v["remaining"] is None or type(v["remaining"]) is int)
                   and v == oracle)
    except (ValueError, TypeError, OverflowError):
        return 0


def replay(report_path, fixture_path):
    raw = Path(fixture_path).read_bytes()
    require(sha(raw) == FIXTURE_SHA, "FIXTURE_SHA")
    fixture = parse(raw)
    require(fixture.get("seed") == 431
            and tuple(f["id"] for f in fixture.get("fixtures", [])) == IDS,
            "FIXTURE")
    report = parse(Path(report_path).read_bytes())
    require(report.get("schema") == "v13.run49.jef_c3_final_shadow_native_result.v1"
            and report.get("seed") == 431 and report.get("registered") is True
            and report.get("fixture_sha256") == FIXTURE_SHA
            and report.get("negative_gates") == NEGATIVE, "REGISTRATION")
    binding = report.get("binding", {})
    require(binding.get("model_sha256") == MODELS
            and binding.get("runner_sha256") == RUNNER_SHA, "NATIVE_BINDING")
    rows = report.get("rows")
    require(type(rows) is list and len(rows) <= 6
            and [r.get("fixture") for r in rows] == list(IDS[:len(rows)]), "ROW_ORDER")
    manifest = report.get("row_sha256")
    require(type(manifest) is dict and set(manifest) ==
            {r["fixture"] for r in rows}, "ROW_MANIFEST")
    summary = {"rows": len(rows), "structural": 0, "native_correct": 0, "gate_matched": 0}
    reasons = []
    for row in rows:
        require(manifest[row["fixture"]] == sha(canonical(row)), "ROW_SHA")
        f = next(f for f in fixture["fixtures"] if f["id"] == row["fixture"])
        require(row.get("prior_sha256") == sha(f["prior"].encode("utf-8"))
                and row.get("current_sha256") == sha(f["current"].encode("utf-8"))
                and row.get("oracle_visible_to_native") is False, "SOURCE_SHA")
        if row.get("status") != "RECORDED":
            reasons.append(row["fixture"] + ":" + str(row.get("status")))
            continue
        p, c = row.get("prior_source_ref"), row.get("current_source_ref")
        for ref, source in ((p, f["prior"]), (c, f["current"])):
            require(type(ref) is dict and ref.get("sha256") == sha(source.encode("utf-8"))
                    and ref.get("char_start") == 0
                    and ref.get("char_end") == len(source)
                    and ref.get("modality") == "text", "SOURCE_REF")
        require(p["source_id"] != c["source_id"]
                and type(row.get("current_event_id")) is str
                and type(row.get("session_id")) is str, "EVENT_BINDING")
        jef = row.get("jef_candidate")
        require(type(jef) is dict and jef.get("reason") == "EXACT_USER_SOURCE_RECIPE_SHADOW"
                and jef.get("status") == "SHADOW_NO_AUTHORITY"
                and jef.get("candidate") == f["oracle"]
                and jef.get("model_called") is False and jef.get("authority") == 0
                and row.get("jef_matches_oracle") is True, "JEF")
        refs = [sha(canonical(ref)) for ref in (p, c)]
        require(jef.get("source_ref_sha256") == refs, "JEF_SOURCE_DIGEST")
        msgs = row.get("native_prompt")
        require(type(msgs) is list and len(msgs) == 2
                and msgs[0] == {"role": "system", "content": SYS}
                and msgs[1].get("role") == "user"
                and row.get("native_prompt_sha256") == sha(canonical(msgs)), "PROMPT")
        payload = parse(msgs[1]["content"])
        require(payload == {"current_source": f["current"],
                            "typed_jef_candidate": f["oracle"],
                            "source_ref_sha256": refs,
                            "candidate_authority": 0}
                and "oracle" not in msgs[1]["content"], "PROMPT_CONTENT")
        require(row.get("native_c3_final") is True
                and row.get("native_c3_metrics", {}).get("status") == "FINAL"
                and row.get("processes_reaped") is True
                and type(row.get("process_releases")) is list
                and len(row["process_releases"]) > 0
                and all(x.get("process_reaped") is True for x in row["process_releases"]),
                "NATIVE_FINAL_REAP")
        s = correct(row.get("native_answer", ""), f["oracle"])
        require(row.get("native_score", {}).get("correct") == s, "NATIVE_SCORE")
        summary["native_correct"] += s
        summary["structural"] += 1
        gate = row.get("final_agreement", {})
        require(type(gate) is dict and gate.get("delivery_authority") == 0
                and gate.get("live_enabled") is False
                and gate.get("user_approved") is False
                and gate.get("model_called") is False
                and gate.get("store_writes") == 0
                and gate.get("tool_dispatches") == 0
                and row.get("gate_store_unchanged") is True, "GATE_NO_AUTHORITY")
        if gate.get("result") == "MATCHED_NO_AUTHORITY":
            require(gate.get("matched_candidate_sha256") == sha(canonical(f["oracle"]))
                    and gate.get("c3_output_sha256") ==
                    sha(row["native_answer"].encode("utf-8")), "GATE_DIGEST")
            summary["gate_matched"] += 1
    structural = len(rows) == summary["structural"] == 6
    signal = (structural and summary["native_correct"] == 6
              and summary["gate_matched"] == 6)
    if structural:
        require(report.get("summary") == summary
                and report.get("installed_binding_unchanged") is True
                and report.get("end_to_end_shadow_signal") is signal
                and report.get("status") ==
                ("END_TO_END_SHADOW_SIGNAL_ONLY" if signal else "UTILITY_FAIL"),
                "AGGREGATE")
    else:
        require(report.get("status") in ("STRUCTURAL_RED", "RUNNING"), "STRUCTURAL_STATUS")
    return {"schema": "v13.run49.independent_replay.v1",
            "structural_valid": bool(structural), "end_to_end_shadow_signal": bool(signal),
            "summary": summary, "original_status": report.get("status"),
            "reasons": reasons, "negative_gates": NEGATIVE,
            "scope": "LINUX_NATIVE_SHADOW_ONLY_NO_DELIVERY_OR_AGE_PROMOTION"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(replay(args.report, args.fixture), sort_keys=True))


if __name__ == "__main__":
    main()
