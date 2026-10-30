"""Read-only, exact-original-ZIP Run13A route/output comparison.

POSTHOC. Never modifies the frozen scorer or promotes any utility gate.
Requires original 32-row Linux-native ZIP; string equality is not causality.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

ZIP_SHA256 = "52b1e6c8209dba364f41a157496cccfd9d59590e84e79139879ad87e5f576a6f"
FIXTURE_SHA256 = "e6718093ccd83d556019223eca2d5317668d1ada25659519a699aee681a8b97f"
ARMS = ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "F_NATIVE_AUTO")
ORDER = tuple(ARMS[i % 4:] + ARMS[:i % 4] for i in range(8))
MAX_ZIP_BYTES = 5_000_000
NEGATIVE = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
            "redmi_measured", "whole_system_complete", "comparative_utility_proven")


def require(ok, why):
    if not ok:
        raise ValueError(why)


def analyze_report(report):
    """Pure, strictly source-bound descriptive comparison, no new scoring."""
    cases = report.get("fixtures")
    rows = report.get("rows")
    require(type(cases) is list and len(cases) == 8
            and type(rows) is list and len(rows) == 32, "COHORT_SIZE_CHANGED")
    digest = hashlib.sha256(json.dumps(
        tuple(cases), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(digest == FIXTURE_SHA256 and report.get("seed") == 211
            and report.get("arms") == list(ARMS)
            and report.get("arm_order") == [list(x) for x in ORDER],
            "FROZEN_SOURCE_CHANGED")
    require(report.get("learning_mode") == "RECORD_ONLY"
            and report.get("jepa_weight") == 0
            and all(report.get(k) is False for k in NEGATIVE),
            "GATE_CHANGED")
    route_counts, role_counts = Counter(), Counter()
    output_matches, per_project = Counter(), []
    numeric, full = {a: 0 for a in ARMS}, {a: 0 for a in ARMS}
    for i, case in enumerate(cases):
        block = rows[4*i:4*i+4]
        require([r.get("arm") for r in block] == list(ORDER[i])
                and all(r.get("fixture") == case["project"]
                        and r.get("index") == 4*i+j
                        for j, r in enumerate(block)),
                "ARM_OR_PROJECT_IDENTITY_CHANGED")
        by_arm = {r["arm"]: r for r in block}
        for arm, row in by_arm.items():
            flags = row.get("flags")
            score = row.get("score")
            task = row.get("full_task")
            require(type(flags) is dict and flags.get("valid_native") is True
                    and flags.get("body_offer_roles") == []
                    and flags.get("expected_offer_roles") == []
                    and flags.get("observer_mode") == "off"
                    and type(row.get("final_output")) is str
                    and type(score) is dict
                    and type(score.get("correct")) is int
                    and 0 <= score["correct"] <= 2
                    and type(task) is dict
                    and type(task.get("strict_full")) is bool,
                    "ROW_INVALID")
            numeric[arm] += score["correct"]
            full[arm] += int(task["strict_full"])
        f = by_arm["F_NATIVE_AUTO"]
        flags = f["flags"]
        require(flags.get("native_c2_invocation") is True
                and f.get("strict_admission", {}).get("matches") is True,
                "C2_STRICT_CHANGED")
        route, role = flags.get("route"), flags.get("runner_role")
        require(route in ("simple", "detail", "gist", "both")
                and role in ("C3_LANGUAGE", "B1_DETAIL", "B2_GIST"),
                "ROUTE_ROLE_INVALID")
        route_counts[route] += 1
        role_counts[role] += 1
        matches = [a for a in ARMS[:3]
                   if f["final_output"] == by_arm[a]["final_output"]]
        for arm in matches:
            output_matches[arm] += 1
        per_project.append({
            "project": case["project"], "f_route": route, "f_final_role": role,
            "f_native_selected": flags.get("native_c2_selected") is True,
            "f_identical_to_arms": matches,
            "f_numeric": f["score"]["correct"],
            "b2_numeric": by_arm["C_B2_ONLY"]["score"]["correct"],
            "f_full": f["full_task"]["strict_full"],
            "b2_full": by_arm["C_B2_ONLY"]["full_task"]["strict_full"],
        })
    require(numeric == report.get("score_totals_out_of_16")
            and full == report.get("strict_full_totals_out_of_8"),
            "FROZEN_TOTALS_CHANGED")
    return {
        "schema": "v13.run13a.route_counterfactual.posthoc.v1",
        "evidence": "POSTHOC_EXACT_STRING_COMPARISON_NOT_CAUSAL_OR_GATE",
        "projects": per_project, "route_counts": dict(route_counts),
        "final_role_counts": dict(role_counts),
        "f_identical_output_arm_counts": dict(output_matches),
        "f_identical_to_some_single_arm": sum(
            bool(x["f_identical_to_arms"]) for x in per_project),
        "f_native_selected": sum(x["f_native_selected"] for x in per_project),
        "f_numeric": numeric["F_NATIVE_AUTO"],
        "b2_numeric": numeric["C_B2_ONLY"],
        "f_full": full["F_NATIVE_AUTO"],
        "b2_full": full["C_B2_ONLY"],
        "comparative_utility_proven": False, "step2_gate_promoted": False,
        "redmi_measured": False, "whole_system_complete": False,
    }


def inspect_zip(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= MAX_ZIP_BYTES,
            "ZIP_MISSING_SYMLINK_OR_OVERSIZE")
    require(hashlib.sha256(path.read_bytes()).hexdigest() == ZIP_SHA256,
            "ORIGINAL_ZIP_HASH_CHANGED")
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None, "ZIP_CRC_RED")
        names = z.namelist()
        require(len(names) == len(set(names)), "DUPLICATE_ZIP_ENTRY")
        listed = set()
        for line in z.read("SHA256SUMS").decode().splitlines():
            parts = line.split("  ", 1)
            require(len(parts) == 2, "BAD_MANIFEST")
            want, name = parts
            name = name.removeprefix("./")
            require(name not in listed and name != "SHA256SUMS" and name in names,
                    "MANIFEST_ENTRY_CHANGED")
            require(hashlib.sha256(z.read(name)).hexdigest() == want,
                    "INNER_HASH_CHANGED")
            listed.add(name)
        require(listed == set(names) - {"SHA256SUMS"} and len(listed) == 96,
                "MANIFEST_COVERAGE_CHANGED")
        report = json.loads(z.read("pilot/report.json"))
        result = analyze_report(report)
        for i, row in enumerate(report["rows"]):
            arm = ORDER[i//4][i%4]
            raw = json.loads(z.read(f"pilot/raw/{i:02d}_{arm}.json"))
            require(raw.get("final_output") == row["final_output"]
                    and raw.get("flags") == row["flags"]
                    and raw.get("score") == row["score"]
                    and raw.get("full_task") == row["full_task"],
                    "RAW_REPORT_IDENTITY_CHANGED")
    return {**result, "source_zip_sha256": ZIP_SHA256,
            "manifest_verified": 96, "native_rows": 32}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(inspect_zip(a.zip), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
