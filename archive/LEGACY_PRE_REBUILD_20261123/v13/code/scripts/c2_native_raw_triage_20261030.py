"""Read-only independent triage of frozen seed53/seed59 Linux-native artifacts.

Never re-score original rows, modify artifacts, or promote any V13 gate.
Requires the original GitHub Actions ZIPs; synthetic tests are not native proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

RUNS = {
    "seed53": {"sha256": "ae05e6d49fff080ba65424118db7259a5762fb20f9308062492c3a758a00b9e9",
               "run": 41002194549, "artifact": 12955090505, "rows": 24,
               "arms": ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "D_DISTINCT_BOTH", "E_SHARED_DUAL_COLD", "F_NATIVE_AUTO"),
               "scores": (0, 0, 0, 2, 2, 3), "invoked": 4, "selected": 0,
               "fixture": "7c5da29e274c3d63a34b68baac6ac9b6e31a968d5632b938eff7de01cf2f24d4"},
    "seed59": {"sha256": "515205f25d700a89190491f8747c23fe7f5531d176aeebcb58eb494271351138",
               "run": 41002769766, "artifact": 12954791608, "rows": 12,
               "arms": ("A_FORCED_SIMPLE", "B_NATIVE_AUTO", "C_FORCED_BOTH"),
               "scores": (0, 0, 2), "invoked": 4, "selected": 4,
               "fixture": "610b7b1c2b2d203b6388a7717394cd9c7c8460f434509167286e7bf7a972e651"},
}
NEGATIVE = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
            "redmi_measured", "whole_system_complete")


def check(condition, code):
    if not condition:
        raise ValueError(code)


def verify_zip(path: Path, expected: str):
    check(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "ZIP_SHA256_MISMATCH")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        check(len(names) == len(set(names)), "DUPLICATE_ZIP_MEMBER")
        check(all(not n.startswith("/") and ".." not in Path(n).parts and "\\" not in n
                  for n in names), "UNSAFE_ZIP_MEMBER")
        check(z.testzip() is None, "ZIP_CRC_ERROR")
        check("SHA256SUMS" in names, "MISSING_INNER_MANIFEST")
        lines = z.read("SHA256SUMS").decode("utf-8").splitlines()
        seen = set()
        for line in lines:
            check(bool(re.fullmatch(r"[0-9a-f]{64}  \./[^\n]+", line)), "INVALID_SHA256SUMS_LINE")
            digest, member = line.split("  ", 1)
            member = member[2:]
            check(member in names and member != "SHA256SUMS" and member not in seen,
                  "UNLISTED_OR_DUPLICATE_MANIFEST_MEMBER")
            seen.add(member)
            check(hashlib.sha256(z.read(member)).hexdigest() == digest,
                  "INNER_SHA256_MISMATCH")
        check(seen == set(names) - {"SHA256SUMS"}, "INCOMPLETE_INNER_MANIFEST")
        return len(lines)


def diagnose_row(row, raw):
    """Classify failed controls without upgrading a failed row to valid."""
    flags = row["flags"]
    if flags.get("valid_native") is True:
        return "VALID"
    expected = set(flags.get("expected_offer_roles", ()))
    actual = set(flags.get("body_offer_roles", ()))
    releases = raw.get("body_process_releases", ())
    released = {x.get("role") for x in releases}
    if actual != expected or released - expected:
        return "OFFER_OR_RELEASE_ROLE_CONTAMINATION"
    if actual == expected and not releases and expected:
        return "OFFER_WITHOUT_PRE_CLOSE_RELEASE_RECEIPT"
    if any(x.get("process_reaped") is not True for x in releases):
        return "BODY_PROCESS_NOT_REAPED"
    return "OTHER_INVALID_NATIVE"


def audit(path: Path, cohort: str):
    spec = RUNS[cohort]
    inner = verify_zip(path, spec["sha256"])
    with zipfile.ZipFile(path) as z:
        j = json.loads(z.read("pilot/report.json"))
        check(j["fixture_sha256"] == spec["fixture"], "FIXTURE_PIN_MISMATCH")
        check(j["status"] == "PILOT_PARTIAL_RED" and j["pilot_signal_not_gate"] is False,
              "ORIGINAL_RED_STATUS_CHANGED")
        check(j["learning_mode"] == "RECORD_ONLY" and j["jepa_weight"] == 0,
              "LEARNING_GATE_CHANGED")
        check(all(j.get(k) is False for k in NEGATIVE), "PROMOTION_GATE_CHANGED")
        check(len(j["rows"]) == spec["rows"], "ROW_COUNT_CHANGED")
        check(tuple(j["arms"]) == spec["arms"], "ARM_IDENTITIES_CHANGED")
        check(j["native_c2_invocations"] == spec["invoked"] and
              j["native_c2_selected"] == spec["selected"], "C2_COUNT_CHANGED")
        check(tuple(j["score_totals_out_of_8"][a] for a in spec["arms"]) == spec["scores"],
              "FROZEN_SCORE_CHANGED")
        counts = {}
        observed_scores = {a: 0 for a in spec["arms"]}
        invoked = selected = 0
        for i, row in enumerate(j["rows"]):
            arm = row["arm"]
            check(row["index"] == i and arm in spec["arms"], "ROW_IDENTITY_MISMATCH")
            raw = json.loads(z.read(f"pilot/raw/{i:02d}_{arm}.json"))
            check(raw["index"] == i and raw["arm"] == arm and
                  raw["fixture"] == row["fixture"] and raw["flags"] == row["flags"] and
                  raw["score"] == row["score"], "RAW_REPORT_MISMATCH")
            check(raw["learning_mode"] == "RECORD_ONLY" and raw["jepa_weight"] == 0,
                  "ROW_LEARNING_CHANGED")
            check(all(raw.get(k) is False for k in NEGATIVE), "ROW_GATE_CHANGED")
            check(raw["raw_audit"]["event_id"] == row["event_id"] and
                  raw["raw_audit"]["output"] == row["final_output"], "EVENT_OUTPUT_MISMATCH")
            check(raw["raw_audit"].get("source_errors") == [] and
                  all(x is True for x in raw["raw_audit"].get("checks", {}).values()),
                  "SOURCE_AUDIT_CHANGED")
            if row["flags"]["valid_native"] is False:
                check(row["score"]["correct"] == 0, "INVALID_ROW_SCORED")
            observed_scores[arm] += row["score"]["correct"]
            if arm in ("F_NATIVE_AUTO", "B_NATIVE_AUTO"):
                invoked += int(row["flags"]["native_c2_invocation"])
                selected += int(row["flags"]["native_c2_selected"])
            kind = diagnose_row(row, raw)
            counts[kind] = counts.get(kind, 0) + 1
        check(observed_scores == j["score_totals_out_of_8"], "SCORE_TOTAL_MISMATCH")
        check((invoked, selected) == (spec["invoked"], spec["selected"]), "C2_ROW_COUNT_MISMATCH")
        return {"cohort": cohort, "run": spec["run"], "artifact": spec["artifact"],
                "original_zip_sha256": spec["sha256"], "crc_clean": True,
                "inner_sha256_verified": inner, "rows": spec["rows"],
                "row_classification": counts, "frozen_scores_out_of_8": observed_scores,
                "native_c2_invocations": invoked, "native_c2_selected": selected,
                "original_status": "PILOT_PARTIAL_RED", "native_valid_all": False,
                "gate_promotion": False, "redmi_proof": False,
                "interpretation": "Independent read-only original-raw triage; not a new score or native rerun."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed53", type=Path, required=True)
    p.add_argument("--seed59", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps({"results": [audit(args.seed53, "seed53"),
                                  audit(args.seed59, "seed59")]}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()