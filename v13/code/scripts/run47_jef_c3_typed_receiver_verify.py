#!/usr/bin/env python3
"""Independent Run47 original native report replay; scientific RED is preserved."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

FIXTURE_SHA = "4015600687c392d7c36d17eeb289ad68fd958222d07bd87b4d7f60df0a8b0fad"
ARMS = ("A_RAW_SOURCES", "B_JEF_TYPED_CANDIDATE")
ORDER = (ARMS, ARMS[::-1], ARMS, ARMS[::-1], ARMS, ARMS[::-1])
NEGATIVE = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "world_jepa_authority": "SHADOW",
            "redmi_measured": False, "whole_system_complete": False}
MODELS = {"B1_DETAIL": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
          "B2_GIST": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
          "C3_LANGUAGE": "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"}
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
SYS_A = ("Use only the exact prior and current user sources. Apply the binding earlier "
         "project rules and select the cheapest eligible option. Return only JSON "
         "with choice and remaining. For NONE or UNKNOWN use null remaining.")
SYS_B = ("You are a JSON formatter, not a decision maker. Copy the supplied "
         "source-verified typed JEF candidate's choice and remaining exactly. "
         "Do not recalculate or change it. Return only those two JSON keys.")


def require(ok, code):
    if not ok:
        raise ValueError("RUN47_REPLAY_" + code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def unique(pairs):
    out = {}
    for k, v in pairs:
        require(k not in out, "DUPLICATE_JSON")
        out[k] = v
    return out


def nonfinite(_):
    raise ValueError("RUN47_NONFINITE")


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def score(raw, oracle):
    try:
        x = parse(raw)
        valid = (type(x) is dict and set(x) == {"choice", "remaining"}
                 and type(x["choice"]) is str and x["choice"] in ("A", "B", "NONE", "UNKNOWN")
                 and (x["remaining"] is None or type(x["remaining"]) is int))
        return int(valid and x == oracle)
    except (ValueError, TypeError, OverflowError):
        return 0


def replay(report_path, fixture_path):
    fixture_raw = Path(fixture_path).read_bytes()
    require(sha(fixture_raw) == FIXTURE_SHA, "FIXTURE_SHA")
    f = parse(fixture_raw)
    require(f.get("seed") == 409 and f.get("arms") == list(ARMS)
            and len(f.get("fixtures", [])) == 6, "FIXTURE")
    report = parse(Path(report_path).read_bytes())
    require(report.get("schema") == "v13.run47.jef_c3_native_receiver_result.v1"
            and report.get("seed") == 409 and report.get("registered") is True
            and report.get("fixture_sha256") == FIXTURE_SHA
            and report.get("negative_gates") == NEGATIVE, "REGISTRATION")
    binding = report.get("binding", {})
    require(binding.get("model_sha256") == MODELS
            and binding.get("runner_sha256") == RUNNER_SHA, "NATIVE_BINDING")
    rows = report.get("rows")
    require(type(rows) is list and len(rows) <= 12, "ROW_COUNT")
    expected = [(x["id"], arm) for x, order in zip(f["fixtures"], ORDER) for arm in order]
    require([(r.get("fixture"), r.get("arm")) for r in rows] == expected[:len(rows)],
            "ROW_ORDER")
    manifest = report.get("row_sha256")
    require(type(manifest) is dict and set(manifest) ==
            {r["fixture"] + "/" + r["arm"] for r in rows}, "ROW_MANIFEST")
    summary = {arm: {"rows": 0, "correct": 0, "structural": 0} for arm in ARMS}
    reasons = []
    for row in rows:
        key = row["fixture"] + "/" + row["arm"]
        require(manifest[key] == sha(canonical(row)), "ROW_SHA")
        fixture = next(x for x in f["fixtures"] if x["id"] == row["fixture"])
        require(row.get("prior_sha256") == sha(fixture["prior"].encode("utf-8"))
                and row.get("current_sha256") == sha(fixture["current"].encode("utf-8"))
                and row.get("oracle_visible_to_native") is False, "SOURCE_SHA")
        arm = row["arm"]
        summary[arm]["rows"] += 1
        if row.get("status") != "RECORDED":
            reasons.append(key + ":" + str(row.get("status")))
            continue
        prior, current = row.get("prior_source_ref"), row.get("current_source_ref")
        for ref, source in ((prior, fixture["prior"]), (current, fixture["current"])):
            require(type(ref) is dict and ref.get("sha256") == sha(source.encode("utf-8"))
                    and ref.get("char_start") == 0
                    and ref.get("char_end") == len(source)
                    and ref.get("modality") == "text", "SOURCE_REF")
        require(prior["source_id"] != current["source_id"], "SOURCE_ISOLATION")
        msgs = row.get("native_prompt")
        require(type(msgs) is list and len(msgs) == 2
                and msgs[0] == {"role": "system", "content": SYS_A if arm == ARMS[0] else SYS_B}
                and msgs[1].get("role") == "user"
                and row.get("native_prompt_sha256") == sha(canonical(msgs)), "PROMPT_SHA")
        payload = parse(msgs[1]["content"])
        require(payload.get("current_source") == fixture["current"]
                and "oracle" not in msgs[1]["content"], "PROMPT_CURRENT")
        if arm == ARMS[0]:
            require(payload == {"prior_source": fixture["prior"],
                                "current_source": fixture["current"]}, "ARM_A")
        else:
            jef = row.get("jef_candidate")
            require(type(jef) is dict
                    and jef.get("reason") == "EXACT_USER_SOURCE_RECIPE_SHADOW"
                    and jef.get("status") == "SHADOW_NO_AUTHORITY"
                    and jef.get("authority") == 0
                    and jef.get("model_called") is False
                    and jef.get("native_calls") == 0
                    and jef.get("candidate") == fixture["oracle"]
                    and row.get("jef_matches_oracle") is True, "JEF_TYPED")
            refs = [sha(canonical(ref)) for ref in (prior, current)]
            require(jef.get("source_ref_sha256") == refs
                    and payload == {"current_source": fixture["current"],
                                    "typed_jef_candidate": jef["candidate"],
                                    "source_ref_sha256": refs,
                                    "candidate_authority": 0}, "ARM_B")
        require(row.get("native_c3_final") is True
                and row.get("native_c3_metrics", {}).get("status") == "FINAL"
                and row.get("processes_reaped") is True
                and type(row.get("process_releases")) is list
                and len(row["process_releases"]) > 0
                and all(x.get("process_reaped") is True for x in row["process_releases"]),
                "NATIVE_FINAL_REAP")
        s = score(row.get("native_answer", ""), fixture["oracle"])
        require(row.get("score", {}).get("correct") == s, "SCORE")
        summary[arm]["correct"] += s
        summary[arm]["structural"] += 1
    structural = len(rows) == 12 and all(summary[a]["structural"] == 6 for a in ARMS)
    signal = structural and summary[ARMS[1]]["correct"] >= 5 and (
        summary[ARMS[1]]["correct"] >= summary[ARMS[0]]["correct"] + 2)
    if structural:
        require(report.get("summary") == summary
                and report.get("installed_binding_unchanged") is True
                and report.get("receiver_copy_signal") is signal
                and report.get("status") == (
                    "RECEIVER_COPY_SIGNAL_ONLY" if signal else "UTILITY_FAIL"),
                "AGGREGATE")
    else:
        require(report.get("status") in ("STRUCTURAL_RED", "RUNNING"),
                "STRUCTURAL_STATUS")
    return {"schema": "v13.run47.independent_replay.v1",
            "structural_valid": bool(structural), "receiver_copy_signal": bool(signal),
            "summary": summary, "original_status": report.get("status"),
            "reasons": reasons, "negative_gates": NEGATIVE,
            "scope": "LINUX_NATIVE_RECEIVER_FIDELITY_ONLY_NO_AGE_PROMOTION"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(replay(a.report, a.fixture), sort_keys=True))


if __name__ == "__main__":
    main()
