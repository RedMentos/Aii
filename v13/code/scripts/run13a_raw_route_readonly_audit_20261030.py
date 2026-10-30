"""Read-only posthoc Run13A original ZIP route/value-presence diagnostic.

This is NOT a scorer. Original score and strict-full outcomes are immutable.
Only a pinned, byte-identical original ZIP is accepted by the CLI.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile

from v13.common import atomic_write, dumps

ORIGINAL_SHA256 = "52b1e6c8209dba364f41a157496cccfd9d59590e84e79139879ad87e5f576a6f"
ORIGINAL_HEAD = "57cb8215ac95484e86a7e9bf1d1d2977aa6a4a35"
FIXTURE_SHA256 = "e6718093ccd83d556019223eca2d5317668d1ada25659519a699aee681a8b97f"
ARMS = ["A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "F_NATIVE_AUTO"]
ARM_ORDER = [ARMS[i % 4:] + ARMS[:i % 4] for i in range(8)]
NEGATIVE = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
            "redmi_measured", "whole_system_complete", "comparative_utility_proven")
MANIFEST_LINE = re.compile(r"([0-9a-f]{64})  \./([^\n]+)")
MAX_ZIP_BYTES = 20_000_000
MAX_MEMBER_BYTES = 5_000_000


def require(ok, why):
    if not ok:
        raise ValueError(why)


def _json(raw):
    return json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(
        ValueError("NONFINITE_JSON:" + x)))


def _read(z, name):
    info = z.getinfo(name)
    require(info.file_size <= MAX_MEMBER_BYTES, "OVERSIZE_MEMBER")
    return z.read(name)


def verify_zip(path, *, expected_sha=ORIGINAL_SHA256, expected_head=ORIGINAL_HEAD):
    path = Path(path)
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= MAX_ZIP_BYTES, "ZIP_FILE_INVALID")
    require(hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha,
            "OUTER_ZIP_SHA_MISMATCH")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        require(len(names) == len(set(names)) and len(names) <= 200,
                "DUPLICATE_OR_EXCESS_MEMBERS")
        require(all(n and not n.startswith("/") and "\\" not in n
                    and all(p not in ("", ".", "..") for p in n.split("/"))
                    and not n.endswith("/") for n in names), "UNSAFE_MEMBER")
        require(z.testzip() is None, "ZIP_CRC_MISMATCH")
        require("SHA256SUMS" in names, "MANIFEST_MISSING")
        manifest = _read(z, "SHA256SUMS").decode("utf-8").splitlines()
        expected = {}
        for line in manifest:
            m = MANIFEST_LINE.fullmatch(line)
            require(m is not None and m[2] not in expected, "MANIFEST_INVALID")
            expected[m[2]] = m[1]
        require(set(expected) == set(names) - {"SHA256SUMS"},
                "MANIFEST_MEMBERS_MISMATCH")
        for name, want in expected.items():
            require(hashlib.sha256(_read(z, name)).hexdigest() == want,
                    "MANIFEST_HASH_MISMATCH:" + name)
        require(_read(z, "HEAD.txt").decode("utf-8").strip() == expected_head,
                "HEAD_MISMATCH")
        report = _json(_read(z, "pilot/report.json"))
        witnesses = {}
        for i in range(32):
            arm = ARM_ORDER[i // 4][i % 4]
            if arm == "F_NATIVE_AUTO":
                witnesses[i] = _json(_read(
                    z, f"pilot/preclose/{i:02d}_{arm}.json"))
        return report, witnesses


def _has_exact_number(text, value):
    # Presence only: never infer that the number is tied to the right option.
    return re.search(r"(?<![\d.,])" + re.escape(str(value)) + r"(?![\d.,])",
                     text) is not None


def analyze(report, witnesses, *, expected_fixture=FIXTURE_SHA256):
    require(report.get("schema") == "v13.c2_c3_body.fulltask.run13a.v1"
            and report.get("seed") == 211
            and report.get("fixture_sha256") == expected_fixture
            and report.get("arms") == ARMS
            and report.get("arm_order") == ARM_ORDER,
            "FROZEN_COHORT_CHANGED")
    fixtures, rows = report.get("fixtures"), report.get("rows")
    require(type(fixtures) is list and len(fixtures) == 8
            and type(rows) is list and len(rows) == 32, "ROW_COUNT_CHANGED")
    require(report.get("learning_mode") == "RECORD_ONLY"
            and report.get("jepa_weight") == 0
            and all(report.get(k) is False for k in NEGATIVE),
            "NEGATIVE_GATE_CHANGED")
    per_fixture = {}
    for i, row in enumerate(rows):
        fixture = fixtures[i // 4]
        arm = ARM_ORDER[i // 4][i % 4]
        require(row.get("index") == i and row.get("fixture") == fixture["project"]
                and row.get("arm") == arm
                and row.get("flags", {}).get("valid_native") is True,
                "ROW_IDENTITY_OR_NATIVE_CHANGED")
        require(type(row.get("score", {}).get("correct")) is int
                and row["score"]["correct"] in (0, 1, 2)
                and type(row.get("full_task", {}).get("strict_full")) is bool,
                "ORIGINAL_SCORE_INVALID")
        per_fixture.setdefault(fixture["project"], {})[arm] = row

    details = []
    for j, fixture in enumerate(fixtures):
        project = fixture["project"]
        f = per_fixture[project]["F_NATIVE_AUTO"]
        b2 = per_fixture[project]["C_B2_ONLY"]
        witness = witnesses.get(f["index"])
        require(type(witness) is dict
                and witness.get("event_id") == f["event_id"]
                and witness.get("arm") == "F_NATIVE_AUTO"
                and witness.get("fixture") == project
                and witness.get("final_output") == f["final_output"]
                and witness.get("source_exact_before_close") is True
                and witness.get("observer_mode") == "off"
                and witness.get("raw_audit", {}).get("output") == f["final_output"],
                "F_WITNESS_MISMATCH")
        route_info = witness.get("route_info") or {}
        native = route_info.get("native_control") or {}
        calls = native.get("function_calls") or []
        require(type(calls) is list, "C2_CALLS_INVALID")
        routes = []
        for call in calls:
            route = (call.get("arguments") or {}).get("route") if type(call) is dict else None
            routes.append(route if route in ("simple", "detail", "gist", "both") else "UNKNOWN")
        expected_a = fixture["budget"] - fixture["a_cost"]
        expected_b = fixture["budget"] - fixture["b_cost"]
        details.append({
            "project": project,
            "f_index": f["index"],
            "f_route": f["flags"]["route"],
            "f_role": f["flags"]["runner_role"],
            "f_route_source": f["flags"]["route_source"],
            "c2_call_routes": routes,
            "c2_rejected": bool(route_info.get("native_control_rejected")),
            "original_f_numeric": f["score"]["correct"],
            "original_f_strict_full": f["full_task"]["strict_full"],
            "original_b2_numeric": b2["score"]["correct"],
            "original_b2_strict_full": b2["full_task"]["strict_full"],
            "expected_remainders": [expected_a, expected_b],
            "f_value_presence_only": [
                _has_exact_number(f["final_output"], expected_a),
                _has_exact_number(f["final_output"], expected_b)],
            "f_output_sha256": hashlib.sha256(
                f["final_output"].encode("utf-8")).hexdigest(),
        })
    return {
        "schema": "v13.run13a.readonly_route_diagnostic.v1",
        "source_zip_sha256": ORIGINAL_SHA256,
        "frozen_seed": 211,
        "original_f_numeric_total": sum(d["original_f_numeric"] for d in details),
        "original_b2_numeric_total": sum(d["original_b2_numeric"] for d in details),
        "f_role_counts": dict(Counter(d["f_role"] for d in details)),
        "f_route_counts": dict(Counter(d["f_route"] for d in details)),
        "c2_rejected_rows": sum(d["c2_rejected"] for d in details),
        "f_numeric_value_presence_both_rows": sum(all(d["f_value_presence_only"])
                                                  for d in details),
        "rows": details,
        "claim_limit": "POSTHOC VALUE PRESENCE ONLY. NOT CORRECTNESS OR RESCORING. FROZEN RUN13A RED UNCHANGED.",
        "gate_promotion": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report, witnesses = verify_zip(args.zip)
    result = analyze(report, witnesses)
    atomic_write(args.out, dumps(result) + "\n")
    print(dumps({k: result[k] for k in (
        "schema", "original_f_numeric_total", "original_b2_numeric_total",
        "f_role_counts", "f_route_counts", "c2_rejected_rows",
        "f_numeric_value_presence_both_rows", "gate_promotion")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
