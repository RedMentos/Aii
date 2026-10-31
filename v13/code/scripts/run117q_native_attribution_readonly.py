"""Read-only Run116 original-native causal-attribution boundary audit.

The frozen Run116 typed-JEF arm includes the deterministic correct answer
before C3 inference. A formatter copy is not evidence of C3 reasoning, Body
complementarity, learned utility or STEP2 acceptance. No experiment rerun.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import zipfile

ORIGINAL_SHA256 = "71de9bb7bc2899f5aee67f58b55d13514d0a9b0d870cd98ae5e8f2f1850d11c5"
SOURCE_HEAD = "df08a4ce311317bdfd322ba7c7520d9fe8fb2b93"
FIXTURE_SHA256 = "e31e2d68331cc4280e161b2dbdbd022f493325ca234f050cda06065fa6775a69"
IDS = ("Ardent", "Birch", "Cetus", "Dawn", "Eider", "Fjord")
ARMS = ("RAW_TWO_SOURCE_ROLE", "TYPED_JEF_ROLE", "TYPED_JEF_WITH_BODY_ROLE")
FIXTURE_PATH = "V13-Phone/docs/fixtures/RUN116_B1B2_JEF_C3_SEED1019.json"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("DUPLICATE_JSON_KEY_RED")
        out[k] = v
    return out


def _parse(raw):
    v = json.loads(raw, object_pairs_hook=_unique)
    if (type(v) is not dict or set(v) != {"choice", "remaining"}
            or v["choice"] not in ("A", "B", "NONE")
            or (v["choice"] == "NONE") != (v["remaining"] is None)
            or (v["remaining"] is not None
                and (type(v["remaining"]) is not int or v["remaining"] < 0))):
        raise ValueError("C3_OUTPUT_SCHEMA_RED")
    return v


def summarize(rows, fixture_rows):
    """Independent paired scores, answer-in-prompt and role confounds."""
    if (len(rows) != len(fixture_rows)
            or [r.get("id") for r in rows] != [f.get("id") for f in fixture_rows]):
        raise ValueError("COHORT_ORDER_RED")
    correct = {arm: 0 for arm in ARMS}
    token_counts = {arm: [] for arm in ARMS}
    comparisons = []
    for row, fixture in zip(rows, fixture_rows):
        oracle = fixture["oracle"]
        if (type(oracle) is not dict or set(oracle) != {"choice", "remaining"}
                or len(row.get("arms", [])) != 3
                or set(a.get("arm") for a in row["arms"]) != set(ARMS)):
            raise ValueError("ARM_OR_ORACLE_RED")
        arms = {a["arm"]: a for a in row["arms"]}
        matched = {}
        source_data = None
        for name in ARMS:
            a = arms[name]
            if (a.get("native_final") is not True
                    or a.get("process_reaped") is not True
                    or a.get("status") != "RECORDED"
                    or len(a.get("messages", [])) != 2
                    or [m.get("role") for m in a["messages"]] != ["system", "user"]):
                raise ValueError("NATIVE_RECEIPT_OR_ROLE_RED")
            msg = a["messages"]
            msg_sha = _sha(json.dumps(msg, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":"), allow_nan=False).encode())
            if a.get("messages_sha256") != msg_sha:
                raise ValueError("PROMPT_HASH_RED")
            data = json.loads(msg[1]["content"], object_pairs_hook=_unique)
            sources = data.get("sources")
            if (type(sources) is not list or len(sources) != 2
                    or [s.get("text") for s in sources] !=
                    [fixture["prior"], fixture["current"]]):
                raise ValueError("EXACT_USER_SOURCE_RED")
            if source_data is None:
                source_data = sources
            elif sources != source_data:
                raise ValueError("SOURCE_NOT_EQUAL_ACROSS_ARMS_RED")
            if name == ARMS[0]:
                if "typed_jef_candidate" in data:
                    raise ValueError("RAW_ARM_ANSWER_LEAK_RED")
            else:
                if (data.get("typed_jef_candidate") != oracle
                        or data.get("typed_candidate_authority") != 0
                        or data.get("typed_candidate_origin") !=
                        "DETERMINISTIC_EXACT_USER_SOURCE_RECIPE_NOT_MODEL"
                        or "Copy typed_jef_candidate.choice" not in msg[0]["content"]):
                    raise ValueError("TYPED_ANSWER_IN_PROMPT_RED")
            output = _parse(a["output"])
            matched[name] = output == oracle
            if int(a.get("score", {}).get("correct", -1)) != int(matched[name]):
                raise ValueError("ORIGINAL_SCORE_MISMATCH_RED")
            correct[name] += int(matched[name])
            native = a.get("native_metrics", {})
            if (native.get("status") != "FINAL"
                    or type(native.get("prompt_tokens")) is not int
                    or native["prompt_tokens"] <= 0):
                raise ValueError("NATIVE_METRICS_RED")
            token_counts[name].append(native["prompt_tokens"])
        comparisons.append({"id": row["id"],
                            "raw_correct": matched[ARMS[0]],
                            "typed_correct": matched[ARMS[1]],
                            "typed_with_body_correct": matched[ARMS[2]]})
    return {
        "schema": "v13.run117q.original_native_attribution.v1",
        "rows": len(rows), "scores": correct,
        "paired_raw_to_typed_improved": sum(not x["raw_correct"] and x["typed_correct"] for x in comparisons),
        "paired_raw_to_typed_worsened": sum(x["raw_correct"] and not x["typed_correct"] for x in comparisons),
        "paired_typed_to_body_improved": sum(not x["typed_correct"] and x["typed_with_body_correct"] for x in comparisons),
        "paired_typed_to_body_worsened": sum(x["typed_correct"] and not x["typed_with_body_correct"] for x in comparisons),
        "median_prompt_tokens": {k: statistics.median(v) for k, v in token_counts.items()},
        "per_case": comparisons,
        "typed_candidate_is_deterministic_oracle_in_user_prompt": True,
        "c3_reasoning_gain_proven": False,
        "b1b2_complementarity_proven": False,
        "learning_gain_proven": False,
        "step2_promoted": False,
        "redmi_measured": False,
        "whole_system_complete": False,
        "claim": "SIX_CASE_FORMATTER_COPY_NONINTERFERENCE_ONLY",
    }


def audit(original_zip):
    original_zip = Path(original_zip)
    if _sha(original_zip.read_bytes()) != ORIGINAL_SHA256:
        raise ValueError("ORIGINAL_OUTER_SHA_RED")
    with zipfile.ZipFile(original_zip) as outer:
        if outer.testzip() is not None:
            raise ValueError("OUTER_ZIP_CRC_RED")
        for line in outer.read("SHA256SUMS").decode().splitlines():
            h, name = line.split("  ", 1)
            if _sha(outer.read(name.removeprefix("./"))) != h:
                raise ValueError("INNER_SHA256_RED")
        if (outer.read("HEAD.txt").decode().strip() != SOURCE_HEAD
                or any(outer.read(x).decode().strip() != "0"
                       for x in ("NATIVE_EXIT.txt", "VERIFY_EXIT.txt"))):
            raise ValueError("ORIGINAL_SOURCE_OR_EXIT_RED")
        report = json.loads(outer.read("NATIVE_CASE/report.json"))
        if (report.get("native") is not True
                or report.get("native_body_calls") != 18
                or report.get("native_c3_calls") != 18
                or report.get("native_jef_calls") != 0
                or report.get("native_c2_calls") != 0
                or report.get("output_committed") is not False
                or report.get("jepa_weight") != 0
                or report.get("whole_system_complete") is not False
                or report.get("fixture_sha256") != FIXTURE_SHA256):
            raise ValueError("ORIGINAL_NATIVE_SCOPE_RED")
        with zipfile.ZipFile(outer.open("V13-Phone-Run116-Native.zip")) as phone:
            if phone.testzip() is not None:
                raise ValueError("PHONE_CRC_RED")
            raw = phone.read(FIXTURE_PATH)
            if _sha(raw) != FIXTURE_SHA256:
                raise ValueError("FROZEN_FIXTURE_SHA_RED")
            fixture = json.loads(raw)
            if ([r["id"] for r in fixture["rows"]] != list(IDS)
                    or fixture.get("seed") != 1019):
                raise ValueError("FROZEN_FIXTURE_ORDER_RED")
        result = summarize(report["rows"], fixture["rows"])
        if result["scores"] != report["scores"]:
            raise ValueError("ORIGINAL_AGGREGATE_SCORE_RED")
        result["original_sha256"] = ORIGINAL_SHA256
        result["source_head"] = SOURCE_HEAD
        result["fixture_sha256"] = FIXTURE_SHA256
        return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--original-zip", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    result = audit(args.original_zip)
    encoded = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("scores", "paired_raw_to_typed_improved",
          "paired_typed_to_body_improved", "claim")}, sort_keys=True))


if __name__ == "__main__":
    main()
