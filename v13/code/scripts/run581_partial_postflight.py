#!/usr/bin/env python3
"""Run581 retrospective read-only 28/42 original FUTURE_005 native postflight."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import stat
import zipfile

SAFE_SHA256 = "8860df4426bdfb1f07215519638b48cbb45b11266bfdd2ebd1b08e7465b9d151"
STAGES = (("A_s33_p03", ("Boreal", "Cascade")),
          ("A_s33_p04", ("Drift", "Eon")))
MISSING_STAGE = "A_s33_p02"
VARIANTS = frozenset(("b1_only", "b2_only", "both_none", "both_exact",
                      "both_control", "same_policy_dual", "prompt_only_dual"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def rescore(answer, oracle):
    """Independent strict 12-field source oracle score; malformed answers score zero."""
    try:
        value = json.loads(answer)
        if type(value) is not dict or set(value) != {"project", "action", "options"}:
            return 0.
        options = value["options"]
        if type(options) is not list or len(options) != len(oracle["options"]):
            return 0.
        got = {}
        for item in options:
            if type(item) is not dict or set(item) != {
                "entity", "cost", "remaining", "days", "local", "eligible"
            } or type(item["entity"]) is not str or item["entity"] in got:
                return 0.
            got[item["entity"]] = item
        if set(got) != {o["entity"] for o in oracle["options"]}:
            return 0.
        checks = [type(value["project"]) is str and value["project"] == oracle["project"],
                  type(value["action"]) is str and value["action"] == oracle["action"]]
        for option in oracle["options"]:
            for field in ("cost", "remaining", "days", "local", "eligible"):
                found = got[option["entity"]][field]
                checks.append(type(found) is type(option[field]) and found == option[field])
        return sum(checks) / len(checks)
    except (ValueError, TypeError, KeyError):
        return 0.


def audit(path, expected_sha=SAFE_SHA256):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("SAFE_ARCHIVE_MISSING")
    if sha(path.read_bytes()) != expected_sha:
        raise ValueError("SAFE_OUTER_SHA_CHANGED")
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or not names:
            raise ValueError("DUPLICATE_OR_EMPTY_SAFE")
        if any(info.is_dir() or stat.S_ISLNK(info.external_attr >> 16) or
               name.startswith("/") or "\\" in name or
               any(part in ("", ".", "..") for part in name.split("/"))
               for name, info in zip(names, infos)):
            raise ValueError("UNSAFE_MEMBER")
        if sum(info.file_size for info in infos) > 50_000_000 or z.testzip() is not None:
            raise ValueError("SAFE_CRC_OR_SIZE")
        read = z.read
        load = lambda name: json.loads(read(name))
        manifest = load("RUN568_SAFE_MANIFEST.json")
        copied = manifest["copied"]
        if set(copied) != set(names) - {"RUN568_SAFE_MANIFEST.json"}:
            raise ValueError("SAFE_MANIFEST_INCOMPLETE")
        for name, item in copied.items():
            raw = read(name)
            if len(raw) != item["bytes"] or sha(raw) != item["sha256"]:
                raise ValueError("SAFE_MEMBER_SHA_CHANGED:" + name)
        for suffix in ("tool_A_s33.json", "summary_A_s33.json", "step2_A_s33.json"):
            if "stage_" + MISSING_STAGE + "/" + suffix in names:
                raise ValueError("MISSING_STAGE_SOURCE_UNEXPECTEDLY_PRESENT")
        full = load("RUN500_STAGE_MAP.json")
        plan = load("RUN558_BATCH_PLAN.json")
        batch = load("RUN558_BATCH_RESULT.json")
        preflight = load("RUN558_INSTALLED_PREFLIGHT.json")
        if (plan["stage_ids"] != [MISSING_STAGE, *[s for s, _ in STAGES]]
                or batch["stage_ids"] != plan["stage_ids"]
                or plan["arm_seed_pairs"] != [["A", 33]] * 3
                or batch["rows_verified"] != 42
                or batch["canonical_gate_pass"] is not False
                or batch["step2_exit"] != "UTILITY_FAIL"):
            raise ValueError("ORIGINAL_BATCH_BINDING_CHANGED")
        if (preflight["model_sha256"] != plan["model_sha256_expected_not_retrieved"]
                or preflight["runner_sha256"] != plan["runner_sha256_expected_not_retrieved"]
                or not preflight["runtime_library_sha256"]):
            raise ValueError("PINNED_PREFLIGHT_CHANGED")
        seen = set()
        wrong = 0
        stage_stats = {}
        for stage_id, fixtures in STAGES:
            folder = "stage_" + stage_id + "/"
            result = load(folder + "RUN500_STAGE_RESULT.json")
            tool = load(folder + "tool_A_s33.json")
            summary = load(folder + "summary_A_s33.json")
            report = load(folder + "step2_A_s33.json")
            prereg = load(folder + "RUN500_STAGE_PREREG.json")
            expected_stage = next(x for x in full["stages"] if x["id"] == stage_id)
            if (prereg != expected_stage or prereg["fixture_ids"] != list(fixtures)
                    or report["fixture_sha256"] != prereg["fixture_sha256"]
                    or report["all_structural_checks_passed"] is not True
                    or report["installed_artifacts_unchanged"] is not True
                    or report["source_unchanged"] is not True
                    or report["uses_real_weights"] is not True
                    or result["rows_verified"] != 14
                    or result["stage_id"] != stage_id
                    or result["canonical_gate_pass"] is not False
                    or result["step2_exit"] != "UTILITY_FAIL"
                    or tool["installed_artifacts_unchanged"] is not True
                    or summary["run"] != "A_s33" or summary["seed"] != 33):
                raise ValueError("STAGE_BINDING_CHANGED:" + stage_id)
            receipt = next(x for x in batch["stage_receipts"] if x["stage_id"] == stage_id)
            if (receipt["receipt_sha256"] != sha(read(folder + "RUN500_STAGE_RESULT.json"))
                    or result["tool_sha256"] != sha(read(folder + "tool_A_s33.json"))
                    or result["summary_sha256"] != sha(read(folder + "summary_A_s33.json"))):
                raise ValueError("STAGE_SHA_CHANGED:" + stage_id)
            expected = {(f, v) for f in fixtures for v in VARIANTS}
            if len(tool["rows"]) != 14 or {(r["fixture"], r["variant"]) for r in tool["rows"]} != expected:
                raise ValueError("STAGE_ROW_KEYS_CHANGED:" + stage_id)
            source = {(r["fixture"], r["variant"]): r for r in report["rows"]}
            oracles = {f["id"]: f["oracle"] for f in report["fixtures"]}
            if set(source) != expected or set(oracles) != set(fixtures):
                raise ValueError("STAGE_SOURCE_MISSING:" + stage_id)
            for row in report["rows"]:
                if report["row_sha256"][row["fixture"] + ":" + row["variant"]] != sha(canon(row)):
                    raise ValueError("SOURCE_ROW_SHA_CHANGED")
            by_variant = {v: [] for v in VARIANTS}
            for row in tool["rows"]:
                key = (row["fixture"], row["variant"])
                if key in seen or row["status"] != "RECORDED" or row["oracle_visible_to_native"] is not False:
                    raise ValueError("ROW_AUTHORITY_CHANGED")
                seen.add(key)
                if (tool["row_sha256"][key[0] + ":" + key[1]] != sha(canon(row))
                        or row["consumer_messages_sha256"] != sha(canon(source[key]["consumer_messages"]))):
                    raise ValueError("ROW_SOURCE_BINDING_CHANGED")
                score = rescore(row["answer"], oracles[key[0]])
                if not math.isfinite(row["score"]["utility"]) or abs(score - row["score"]["utility"]) >= 1e-12:
                    raise ValueError("ROW_RESCORE_MISMATCH")
                by_variant[key[1]].append(score)
                try:
                    action = json.loads(row["answer"])["action"]
                except (ValueError, TypeError, KeyError):
                    action = None
                if action in ("A", "B", "NONE") and action != oracles[key[0]]["action"]:
                    wrong += 1
            for variant, scores in by_variant.items():
                if len(scores) != 2 or abs(sum(scores) / 2 - summary["tool_summary"][variant]["mean_utility"]) >= 1e-12:
                    raise ValueError("STAGE_MEAN_CHANGED")
            stage_stats[stage_id] = {"rows": 14, "tool_sha256": result["tool_sha256"],
                                     "summary_sha256": result["summary_sha256"]}
        if len(seen) != 28:
            raise ValueError("PARTIAL_ROW_COUNT_CHANGED")
        return {"schema": "V13_RUN581_PARTIAL_ORIGINAL_NATIVE_POSTFLIGHT_V1",
                "status": "PARTIAL_28_OF_42_INDEPENDENTLY_RESCORED",
                "safe_outer_sha256": expected_sha, "rows_independently_rescored": 28,
                "rows_unavailable_for_full_rescore": 14,
                "unavailable_stage": MISSING_STAGE, "wrong_committed_28": wrong,
                "stages": stage_stats, "original_native_exit": 0,
                "original_audit_exit": 1, "canonical_gate_pass": False,
                "step2_exit": "UTILITY_FAIL", "b3_l1": "FAIL",
                "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
                "redmi_measured": False,
                "claim_limit": "Retrospective 28/42 source-bound native rows; missing p02 raw, no full 42-row verification"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safe-zip", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.safe_zip)
    if args.report.exists() or args.report.is_symlink():
        raise ValueError("REPORT_ALREADY_EXISTS")
    with args.report.open("x", encoding="utf-8") as f:
        json.dump(result, f, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({key: result[key] for key in
                      ("status", "rows_independently_rescored",
                       "rows_unavailable_for_full_rescore", "wrong_committed_28")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
