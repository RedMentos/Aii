"""Run11W read-only C2/Body route regret from exact immutable native ZIPs.

This is a descriptive posthoc software audit, not a new native run,
causal estimate, routing policy, scorer change or acceptance gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import PurePosixPath, Path
import re
import stat
import zipfile

SCHEMA = "v13.c2_body.route_regret.readonly.v1"
ARMS = ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "D_DISTINCT_BOTH",
        "E_SHARED_DUAL_COLD", "F_NATIVE_AUTO")
NEGATIVE = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
            "redmi_measured", "whole_system_complete",
            "comparative_utility_proven")
MAX_ZIP_BYTES = 20_000_000
MAX_MEMBER_BYTES = 5_000_000


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def source_prompt(f):
    return (f"For {f['project']}, I have a spending ceiling of {f['budget']} Euro. "
            f"{f['a']} uses {f['a_cost']} Euro and needs {f['a_days']} days. "
            f"{f['b']} uses {f['b_cost']} Euro and needs {f['b_days']} days. "
            "Everything stays local on my device; no cloud. How many Euro "
            "would remain after each named choice, and which one finishes sooner?")


def _load_zip(path, expected_sha, expected_head):
    path = Path(path)
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= MAX_ZIP_BYTES, "ZIP_MISSING_OVERSIZE_OR_SYMLINK")
    require(re.fullmatch(r"[a-f0-9]{64}", expected_sha) is not None,
            "EXPECTED_SHA_INVALID")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    require(sha == expected_sha, "ORIGINAL_ZIP_HASH_CHANGED")
    z = zipfile.ZipFile(path)
    try:
        names = z.namelist()
        require(len(names) <= 200 and len(names) == len(set(names))
                and z.testzip() is None, "ZIP_DUPLICATE_COUNT_OR_CRC")
        for item in z.infolist():
            name = item.filename
            p = PurePosixPath(name)
            mode = item.external_attr >> 16
            require(name and not p.is_absolute() and ".." not in p.parts
                    and "\\" not in name and not stat.S_ISLNK(mode)
                    and item.file_size <= MAX_MEMBER_BYTES, "ZIP_UNSAFE_MEMBER")
        require("HEAD.txt" in names and "SHA256SUMS" in names,
                "ZIP_PROVENANCE_MISSING")
        require(z.read("HEAD.txt").decode().strip() == expected_head,
                "ORIGINAL_HEAD_CHANGED")
        lines = z.read("SHA256SUMS").decode().splitlines()
        require(len(lines) == len(names) - 1, "ZIP_MANIFEST_COUNT")
        checked = set()
        for line in lines:
            fields = line.split(maxsplit=1)
            require(len(fields) == 2, "ZIP_MANIFEST_FORMAT")
            want, name = fields
            name = name.removeprefix("./")
            require(re.fullmatch(r"[a-f0-9]{64}", want) is not None
                    and name in names and name not in checked
                    and name != "SHA256SUMS", "ZIP_MANIFEST_IDENTITY")
            checked.add(name)
            require(hashlib.sha256(z.read(name)).hexdigest() == want,
                    "ZIP_INNER_HASH_CHANGED")
        require(checked == set(names) - {"SHA256SUMS"},
                "ZIP_MANIFEST_INCOMPLETE")
        return z, sha, len(names), len(checked)
    except BaseException:
        z.close()
        raise


def _score(row, slot):
    value = row.get(slot)
    require(isinstance(value, dict)
            and type(value.get("a")) is bool
            and type(value.get("b")) is bool
            and type(value.get("correct")) is int
            and value["correct"] == int(value["a"]) + int(value["b"])
            and value.get("out_of") == 2, "SCORE_TYPE_OR_SUM_INVALID")
    return value["correct"]


def audit(path, *, sha256, head, seed, schema, fixture_sha256, score_slot):
    """Verify closed original raw and compute noncausal route deltas."""
    require(type(seed) is int and seed in (163, 181), "SEED_UNREGISTERED")
    require(score_slot == ("secondary_score" if seed == 163 else "score"),
            "FROZEN_SCORE_SLOT_CHANGED")
    require(schema == ("v13.c2_body.observer_closed.seed163.v1" if seed == 163
                       else "v13.c2_body.disjoint.seed181.v1"), "SCHEMA_UNREGISTERED")
    require(fixture_sha256 == ("040e073bc1c544883a5d809d0883d6493366a8f241816c7e6dbefd30c87eaead"
                               if seed == 163 else
                               "ae4799f60316cf51412d228547662de8cb4b6523dedffd5fc02b2862d84477e3"),
            "FIXTURE_PIN_CHANGED")
    z, sha, entries, inner = _load_zip(path, sha256, head)
    try:
        names = set(z.namelist())
        require("pilot/report.json" in names, "REPORT_MISSING")
        report = json.loads(z.read("pilot/report.json"))
        require(report.get("schema") == schema and report.get("seed") == seed
                and report.get("fixture_sha256") == fixture_sha256,
                "REPORT_SOURCE_IDENTITY_CHANGED")
        fixtures = report.get("fixtures")
        require(isinstance(fixtures, list) and len(fixtures) == 4
                and len({f["project"] for f in fixtures}) == 4,
                "FIXTURE_COUNT_OR_IDENTITY")
        fixture_hash = hashlib.sha256(json.dumps(
            fixtures, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        require(fixture_hash == fixture_sha256, "FIXTURE_BYTES_CHANGED")
        require(report.get("arms") == list(ARMS)
                and report.get("arm_order") == [
                    list(ARMS[i:] + ARMS[:i]) for i in range(4)],
                "ARM_ORDER_CHANGED")
        require(report.get("learning_mode") == "RECORD_ONLY"
                and report.get("jepa_weight") == 0
                and all(report.get(k) is False for k in NEGATIVE),
                "AGE_OR_NEGATIVE_GATE_CHANGED")
        models = report.get("model_verification")
        require(isinstance(models, dict)
                and set(models) == {"needle", "language", "body", "gist"}
                and all(v == {"ok": True, "hash_checked": True}
                        for v in models.values()), "MODEL_PINS_MISSING")
        rows = report.get("rows")
        require(isinstance(rows, list) and len(rows) == 24,
                "ROW_COUNT_INVALID")
        expected_raw = set()
        per_fixture = []
        totals = {arm: 0 for arm in ARMS}
        secondary = {arm: 0 for arm in ARMS}
        all_valid = True
        invocations = selected = 0
        for i, row in enumerate(rows):
            fixture = fixtures[i // 6]
            arm = ARMS[(i // 6 + i % 6) % 6]
            require(row.get("index") == i and row.get("fixture") == fixture["project"]
                    and row.get("arm") == arm, "ROW_ORDER_OR_IDENTITY")
            name = f"pilot/raw/{i:02d}_{arm}.json"
            expected_raw.add(name)
            require(name in names, "RAW_MISSING")
            raw = json.loads(z.read(name))
            require(raw.get("index") == i and raw.get("fixture") == fixture["project"]
                    and raw.get("arm") == arm and raw.get("score") == row.get("score")
                    and raw.get("flags") == row.get("flags"), "RAW_REPORT_DIVERGENCE")
            flags = row.get("flags")
            require(isinstance(flags, dict)
                    and type(flags.get("valid_native")) is bool,
                    "NATIVE_FLAG_TYPE_INVALID")
            valid = flags["valid_native"]
            all_valid = all_valid and valid
            if valid:
                witness_name = f"pilot/preclose/{i:02d}_{arm}.json"
                require(witness_name in names, "PRECLOSE_WITNESS_MISSING")
                witness = json.loads(z.read(witness_name))
                require(isinstance(witness, dict)
                        and all(raw.get(k) == v for k, v in witness.items()),
                        "PRECLOSE_WITNESS_CHANGED")
                require(raw.get("prompt") == source_prompt(fixture)
                        and raw.get("final_output") == row.get("final_output")
                        and raw.get("event_id") == row.get("event_id")
                        and raw.get("raw_audit", {}).get("output") == row.get("final_output"),
                        "RAW_SOURCE_OR_EVENT_CHANGED")
                require(raw.get("release_capture_phase") == "after_close"
                        and flags.get("process_release_valid") is True
                        and raw.get("learning_mode") == "RECORD_ONLY"
                        and raw.get("jepa_weight") == 0,
                        "NATIVE_RELEASE_OR_AGE0_CHANGED")
                require(raw.get("secondary_score") == row.get("secondary_score"),
                        "SECONDARY_REPORT_DIVERGENCE")
                invocations += int(flags.get("native_c2_invocation") is True)
                selected += int(flags.get("native_c2_selected") is True)
                if arm == "F_NATIVE_AUTO":
                    require(type(flags.get("native_c2_invocation")) is bool
                            and type(flags.get("native_c2_selected")) is bool,
                            "C2_FLAG_TYPE_INVALID")
                per_fixture.append({"fixture": fixture["project"], "arm": arm,
                                    "score": _score(row, score_slot),
                                    "native_valid": True,
                                    "native_c2_invocation": flags.get("native_c2_invocation") is True,
                                    "native_c2_selected": flags.get("native_c2_selected") is True,
                                    "route": flags.get("route"),
                                    "route_source": flags.get("route_source"),
                                    "runner_role": flags.get("runner_role")})
            else:
                require("error_type" in raw and row.get("error_type") == raw["error_type"]
                        and row.get("score", {}).get("correct") == 0,
                        "ERROR_ROW_FORGED")
                per_fixture.append({"fixture": fixture["project"], "arm": arm,
                                    "score": 0, "native_valid": False,
                                    "error_type": raw["error_type"]})
            totals[arm] += _score(row, "score")
            if valid:
                secondary[arm] += _score(row, "secondary_score")
        actual_raw = {name for name in names if name.startswith("pilot/raw/")}
        require(actual_raw == expected_raw, "RAW_FILE_SET_CHANGED")
        require(report.get("score_totals_out_of_8") == totals
                and report.get("secondary_totals_out_of_8") == secondary,
                "REPORT_TOTALS_CHANGED")
        require(report.get("native_c2_invocations") == invocations
                and report.get("native_c2_selected") == selected,
                "C2_TOTALS_CHANGED")
        require(report.get("status") == (
            "PILOT_COMPLETE_NO_GATE" if all_valid else "PILOT_PARTIAL_RED"),
            "REPORT_STATUS_CHANGED")
        deltas = []
        if all_valid:
            for f in fixtures:
                scores = {r["arm"]: r["score"] for r in per_fixture
                          if r["fixture"] == f["project"]}
                require(set(scores) == set(ARMS), "ARM_COMPLETENESS")
                best = max(scores[a] for a in ARMS[:3])
                auto = next(r for r in per_fixture
                            if r["fixture"] == f["project"]
                            and r["arm"] == "F_NATIVE_AUTO")
                deltas.append({
                    "fixture": f["project"], "scores": scores,
                    "best_single": best,
                    "distinct_minus_best_single": scores["D_DISTINCT_BOTH"] - best,
                    "distinct_minus_shared": scores["D_DISTINCT_BOTH"] - scores["E_SHARED_DUAL_COLD"],
                    "auto_minus_best_single": scores["F_NATIVE_AUTO"] - best,
                    "auto_minus_c3": scores["F_NATIVE_AUTO"] - scores["A_C3_ONLY"],
                    "auto_native_invoked": auto["native_c2_invocation"],
                    "auto_native_selected": auto["native_c2_selected"],
                    "auto_route": auto["route"],
                    "auto_route_source": auto["route_source"],
                    "auto_runner_role": auto["runner_role"],
                })
        return {
            "schema": SCHEMA, "seed": seed, "original_zip_sha256": sha,
            "original_head": head, "zip_entries": entries,
            "inner_hashes_verified": inner, "rows_verified": len(rows),
            "native_complete": all_valid,
            "status": "DESCRIPTIVE_ROUTE_REGRET_NO_GATE" if all_valid
                      else "INCOMPLETE_NATIVE_RED_NO_COMPARISON",
            "score_slot": score_slot, "score_totals_original": totals,
            "secondary_totals_original": secondary,
            "native_c2_invocations": invocations,
            "native_c2_selected": selected, "rows": per_fixture,
            "per_fixture_deltas": deltas,
            "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
            "step2_gate_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "redmi_measured": False,
            "whole_system_complete": False,
            "comparative_utility_proven": False,
            "native_run_performed_by_auditor": False,
            "causal_claim": False,
        }
    finally:
        z.close()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--fixture-sha256", required=True)
    p.add_argument("--score-slot", choices=("score", "secondary_score"), required=True)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    report = audit(args.zip, sha256=args.sha256, head=args.head,
                   seed=args.seed, schema=args.schema,
                   fixture_sha256=args.fixture_sha256, score_slot=args.score_slot)
    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.out:
        if args.out.exists():
            raise FileExistsError("FRESH_OUTPUT_REQUIRED")
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
