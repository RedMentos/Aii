"""Run127 read-only verifier for 42 matched pairs / 84 native C3 calls.

Software-only. No inference, training, mutation or STEP2 promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

SOURCE_SHA = "c0cd539ec28f9583abe25c93f48871597df6758c442782eb6fedd56ad612105f"
FIXTURE_SHA = "b8896bfba0c6c323ba1dafd12bc788e7f378bbf5d23c96e5074b3b1d058ef1d1"
MODELS = {
    "B1_DETAIL": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
    "B2_GIST": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
    "C3_LANGUAGE": "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
}
PROJECTS = ("Atlas", "Borealis", "Cygnus", "Delta", "Epsilon", "Fornax")
VARIANTS = ("b1_only", "b2_only", "both_none", "both_exact", "both_control",
            "same_policy_dual", "prompt_only_dual")
FIELDS = ("cost", "remaining", "days", "local", "eligible")
PASS = "PASS_SCOPED_NATIVE_TRANSPORT_NO_GATE"
FAIL = "FAIL_SCOPED_WRONG_COMMITTED_NO_GATE"


def need(ok, why):
    if not ok:
        raise ValueError(why)


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(obj):
    return hashlib.sha256(obj if isinstance(obj, bytes) else obj.encode("utf-8")).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def independent_score(raw, oracle):
    checks = {}
    try:
        a = json.loads(raw, object_pairs_hook=unique) if isinstance(raw, str) else raw
        if not isinstance(a, dict) or set(a) != {"project", "action", "options"}:
            raise ValueError("top-level schema")
        if not isinstance(a["options"], list) or len(a["options"]) != len(oracle["options"]):
            raise ValueError("option count")
        options = {}
        for item in a["options"]:
            if not isinstance(item, dict) or set(item) != {"entity", *FIELDS}:
                raise ValueError("option schema")
            if not isinstance(item["entity"], str) or item["entity"] in options:
                raise ValueError("duplicate/invalid entity")
            options[item["entity"]] = item
        if set(options) != {o["entity"] for o in oracle["options"]}:
            raise ValueError("entity assignment")
        checks["project"] = type(a["project"]) is str and a["project"] == oracle["project"]
        checks["action"] = type(a["action"]) is str and a["action"] == oracle["action"]
        for expected in oracle["options"]:
            actual = options[expected["entity"]]
            for field in FIELDS:
                value, got = expected[field], actual[field]
                checks[expected["entity"] + "." + field] = type(got) is type(value) and got == value
        errors = [key for key, ok in checks.items() if not ok]
    except (ValueError, TypeError) as exc:
        checks, errors = {}, ["invalid:" + str(exc)]
    n = 2 + len(FIELDS) * len(oracle["options"])
    return {"utility": sum(checks.values()) / n,
            "exact": len(checks) == n and all(checks.values()),
            "field_checks": checks, "contradictions": errors,
            "contradiction_count": len(errors), "scored_fields": n}


def action(answer):
    try:
        obj = json.loads(answer)
    except (TypeError, ValueError):
        return "INVALID"
    value = obj.get("action") if isinstance(obj, dict) else None
    return value if value in ("A", "B", "NONE", "UNKNOWN") else "INVALID"


def audit(source, prepared, raw, receipt, *, source_sha, prepared_sha, raw_sha, replay):
    """Recompute native evidence, not its stored success claims.

    replay(raw_answer, messages) must be the frozen eligibility tool in the CLI.
    Unit tests can inject a synthetic stub, never presented as native proof.
    """
    need(callable(replay), "REPLAY_REQUIRED")
    need(source_sha == SOURCE_SHA and source.get("fixture_sha256") == FIXTURE_SHA,
         "ORIGINAL_SOURCE_DRIFT")
    need(prepared.get("status") == "SOFTWARE_PREPARED_NATIVE_NOT_LAUNCHED"
         and prepared.get("original_source_sha256") == SOURCE_SHA
         and prepared.get("fixture_sha256") == FIXTURE_SHA
         and prepared.get("native_calls") == 0
         and prepared.get("pair_count") == 42
         and prepared.get("canonical_gate_pass") is False, "PREFLIGHT_DRIFT")
    fixtures = source.get("fixtures")
    need(isinstance(fixtures, list)
         and tuple(f.get("id") for f in fixtures) == PROJECTS, "FIXTURE_ORDER_DRIFT")
    oracle = {f["id"]: f["oracle"] for f in fixtures}
    pairs = prepared.get("rows")
    need(isinstance(pairs, list) and len(pairs) == 42
         and {(p.get("fixture"), p.get("variant")) for p in pairs}
         == {(p, v) for p in PROJECTS for v in VARIANTS}, "PAIR_COVERAGE_RED")
    rows = raw.get("rows")
    need(raw.get("schema") == "v13.step2.exact_rule_transport_native_rows.v1"
         and raw.get("canonical_gate_pass") is False
         and raw.get("phone_measured") is False
         and isinstance(rows, list) and len(rows) == 84, "RAW_INCOMPLETE_RED")
    need(receipt.get("schema") == "v13.step2.exact_rule_transport_matched_native.v1"
         and receipt.get("source_report_sha256") == source_sha
         and receipt.get("preflight_report_sha256") == prepared_sha
         and receipt.get("native_rows_sha256") == raw_sha
         and receipt.get("fixture_sha256") == FIXTURE_SHA
         and receipt.get("rows") == 84
         and receipt.get("body_source_seed") == 20
         and receipt.get("c3_seed") == 13
         and receipt.get("native_scope") == "LINUX_C3_42_MATCHED_PAIRS_84_CALLS"
         and receipt.get("model_hashes_before") == MODELS
         and receipt.get("model_hashes_after") == MODELS
         and receipt.get("installed_artifacts_before") == source.get("installed_artifacts")
         and receipt.get("installed_artifacts_after") == source.get("installed_artifacts")
         and receipt.get("canonical_gate_pass") is False
         and receipt.get("step2_status") == "UTILITY_FAIL"
         and receipt.get("age_authority") == 0
         and receipt.get("jepa_weight") == 0
         and receipt.get("weight_updates") is False
         and receipt.get("redmi_measured") is False
         and receipt.get("whole_system_complete") is False, "RECEIPT_DRIFT")
    hashes = raw.get("row_sha256")
    need(isinstance(hashes, dict) and len(hashes) == 84, "ROW_HASH_COUNT_RED")
    expected_keys = set()
    for i, pair in enumerate(pairs):
        source_key = pair["fixture"] + ":" + pair["variant"]
        need(pair["source_row_sha256"] == source["row_sha256"][source_key]
             and pair["oracle_visible_to_native"] is False
             and pair["native_calls"] == 0
             and isinstance(pair["injected"], bool), "PAIR_BINDING_RED")
        for mode in ("control", "treatment"):
            need(digest(canon(pair[mode + "_messages"])) == pair[mode + "_sha256"],
                 "MESSAGE_HASH_RED")
        if not pair["injected"]:
            need(pair["control_messages"] == pair["treatment_messages"],
                 "NEGATIVE_CONTROL_MUTATION_RED")
        order = ("control", "treatment") if i % 2 == 0 else ("treatment", "control")
        for j, mode in enumerate(order):
            row = rows[2 * i + j]
            key = source_key + ":" + mode
            expected_keys.add(key)
            need(row.get("fixture") == pair["fixture"]
                 and row.get("variant") == pair["variant"]
                 and row.get("mode") == mode
                 and row.get("injected") is (pair["injected"] if mode == "treatment" else False)
                 and row.get("source_row_sha256") == pair["source_row_sha256"]
                 and row.get("consumer_messages_sha256") == pair[mode + "_sha256"]
                 and row.get("oracle_visible_to_native") is False, "ROW_BINDING_RED:" + key)
            need(hashes.get(key) == digest(canon(row)), "ROW_HASH_RED:" + key)
            elapsed = row.get("elapsed_s")
            need(row.get("status") == "RECORDED"
                 and isinstance(row.get("consumer_metrics"), dict)
                 and row["consumer_metrics"].get("status") == "FINAL"
                 and isinstance(row.get("raw_answer"), str)
                 and isinstance(row.get("answer"), str)
                 and type(elapsed) in (int, float)
                 and math.isfinite(elapsed) and elapsed >= 0,
                 "NATIVE_NOT_FINAL_RED:" + key)
            computed_answer, computed_tool = replay(row["raw_answer"], pair[mode + "_messages"])
            need(row["answer"] == (computed_answer or row["raw_answer"])
                 and row.get("tool") == computed_tool, "TOOL_REPLAY_RED:" + key)
            need(row.get("action") == action(row["answer"]), "ACTION_REPLAY_RED:" + key)
            need(row.get("score") == independent_score(row["answer"], oracle[pair["fixture"]]),
                 "SCORE_REPLAY_RED:" + key)
    need(set(hashes) == expected_keys, "ROW_KEYS_RED")
    summary = {}
    for mode in ("control", "treatment"):
        summary[mode] = {}
        for variant in VARIANTS:
            subset = [r for r in rows if r["mode"] == mode and r["variant"] == variant]
            need(len(subset) == 6 and {r["fixture"] for r in subset} == set(PROJECTS),
                 "SUMMARY_COVERAGE_RED")
            summary[mode][variant] = {
                "rows": 6,
                "decision_exact": sum(r["action"] == oracle[r["fixture"]]["action"] for r in subset),
                "unknown": sum(r["action"] == "UNKNOWN" for r in subset),
                "wrong_committed": sum(r["action"] in ("A", "B", "NONE")
                                       and r["action"] != oracle[r["fixture"]]["action"] for r in subset),
                "full_json_exact": sum(bool(r["score"]["exact"]) for r in subset),
                "mean_utility": sum(r["score"]["utility"] for r in subset) / 6,
            }
    wrong = sum(x["wrong_committed"] for x in summary["treatment"].values())
    status = PASS if wrong == 0 else FAIL
    need(raw.get("status") == status and receipt.get("status") == status
         and receipt.get("treatment_wrong_committed") == wrong
         and receipt.get("summary") == summary, "SUMMARY_OR_STATUS_RED")
    matched = {}
    for pair in pairs:
        subset = {r["mode"]: r for r in rows
                  if (r["fixture"], r["variant"]) == (pair["fixture"], pair["variant"])}
        a, b = subset["control"], subset["treatment"]
        matched[pair["fixture"] + ":" + pair["variant"]] = {
            "action_exact_delta": int(b["action"] == oracle[pair["fixture"]]["action"])
                                  - int(a["action"] == oracle[pair["fixture"]]["action"]),
            "utility_delta": b["score"]["utility"] - a["score"]["utility"],
            "treatment_wrong_committed": b["action"] in ("A", "B", "NONE")
                                         and b["action"] != oracle[pair["fixture"]]["action"],
        }
    return {"status": "AUDITED_" + status, "rows": 84, "pairs": 42,
            "treatment_wrong_committed": wrong, "per_variant": summary,
            "per_fixture": matched, "canonical_gate_pass": False,
            "step2_status": "UTILITY_FAIL", "redmi_measured": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-report", "preflight-report", "native-rows", "receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    from scripts import step2_exact_rule_native_replay_preflight as preflight
    from scripts import step2_tool_replay as tool
    source = preflight.load_original(args.source_report)
    prepared = json.loads(args.preflight_report.read_text(encoding="utf-8"))
    need(canon(prepared) == canon(preflight.transform(source)), "PREFLIGHT_REGEN_RED")
    raw = json.loads(args.native_rows.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    result = audit(source, prepared, raw, receipt,
                   source_sha=file_sha(args.source_report),
                   prepared_sha=file_sha(args.preflight_report),
                   raw_sha=file_sha(args.native_rows), replay=tool.tool_answer)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["treatment_wrong_committed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
