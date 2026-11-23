"""Read-only independent seed61 frozen-scorer replay of original RED native ZIPs.

Never promotes STEP2, B3, Body-JEPA, age, Redmi or whole-system gates.
Original source/model/fixture/scorer bytes are not changed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ORIGINALS = {
    "first": ("5296bf6bdf9fda8ac2c2b95ec9b73e10a1a1eb53574038c803a9d3ac12c55ad1",
              "5ac90444fe2e0317a954cb4ed94730900b33d92c"),
    "second": ("dd7d00dc04a82180171bc3d1739bb21cd53ead7d3a05e26e4e6ac3b2b8e8556a",
               "45624d16f53cad1ae95e3a5cfc5a7467f32d527c"),
}
SCORER_BLOBS = {
    "c2_body_controlled_utility_seed53_20261030.py": "b10bcdcb2cf2a2151c95cd432b7b0b5e6c5aac6b",
    "step2_expression_diagnostic_20261030.py": "f6bb6c26237f9c94a29a9eeac5ecc6c5fa129ad3",
    "step2_paired_raw_validator_audit_20261030.py": "fcd44ccce3b8b40d65a25187a78b0a8d49d9609d",
}
ARMS = ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "D_DISTINCT_BOTH",
        "E_SHARED_DUAL_COLD", "F_NATIVE_AUTO")
NEGATIVE = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
            "redmi_measured", "whole_system_complete")


def require(value, code):
    if not value:
        raise ValueError(code)


def strict_equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(strict_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    return a == b


def score_wire_equal(recomputed, persisted):
    """Exact JSON roundtrip fixes tuple/list identity only, never score values."""
    try:
        return strict_equal(json.loads(json.dumps(recomputed, allow_nan=False)), persisted)
    except (TypeError, ValueError, OverflowError):
        return False


def git_blob_sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def frozen_scorer():
    base = Path(__file__).resolve().parent
    for name, blob in SCORER_BLOBS.items():
        require(git_blob_sha(base / name) == blob, "FROZEN_SCORER_SOURCE_CHANGED:" + name)
    from scripts.c2_body_controlled_utility_seed53_20261030 import score_pair
    return score_pair


def replay_zip(path, original, scorer):
    """Validate original ZIP, inner hashes, 24 source-bound rows, PIDs and score."""
    require(original in ORIGINALS, "UNKNOWN_ORIGINAL")
    want_sha, want_head = ORIGINALS[original]
    require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == want_sha,
            "ORIGINAL_ZIP_SHA256_CHANGED")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        require(len(names) == len(set(names)) and z.testzip() is None,
                "ZIP_DUPLICATE_OR_CRC_RED")
        require(all(not n.startswith("/") and ".." not in n.split("/") for n in names),
                "ZIP_PATH_RED")
        require(z.read("HEAD.txt").decode().strip() == want_head, "HEAD_CHANGED")
        manifest = "SHA256SUMS" in names
        require(manifest == (original == "second"), "ORIGINAL_MANIFEST_STATE_CHANGED")
        verified = 0
        if manifest:
            entries = {}
            for line in z.read("SHA256SUMS").decode().splitlines():
                digest, name = line.split("  ", 1)
                name = name.removeprefix("./")
                require(len(digest) == 64 and name not in entries, "BAD_MANIFEST_ENTRY")
                entries[name] = digest
            require(set(entries) == set(names) - {"SHA256SUMS"}, "MANIFEST_COVERAGE_RED")
            for name, digest in entries.items():
                require(hashlib.sha256(z.read(name)).hexdigest() == digest,
                        "MANIFEST_DIGEST_RED:" + name)
                verified += 1
        report = json.loads(z.read("pilot/report.json"))
        require(report["schema"] == "v13.c2_body.isolated_postclose.seed61.v1"
                and report["seed"] == 61 and report["learning_mode"] == "RECORD_ONLY"
                and report["jepa_weight"] == 0 and report["arms"] == list(ARMS)
                and len(report["fixtures"]) == 4 and len(report["rows"]) == 24,
                "REPORT_SCHEMA_RED")
        for gate in (*NEGATIVE, "comparative_utility_proven"):
            require(report[gate] is False, "REPORT_GATE_RED:" + gate)
        totals = {arm: 0 for arm in ARMS}
        invoked = selected = 0
        all_raw = set()
        for i, row in enumerate(report["rows"]):
            fixture = report["fixtures"][i // 6]
            arm = report["arm_order"][i // 6][i % 6]
            require(row["index"] == i and row["arm"] == arm and
                    row["fixture"] == fixture["project"], "ROW_ORDER_RED")
            name = f"pilot/raw/{i:02d}_{arm}.json"
            all_raw.add(name)
            raw = json.loads(z.read(name))
            require(raw["index"] == i and raw["event_id"] == row["event_id"]
                    and raw["session_id"] == row["session_id"]
                    and raw["final_output"] == row["final_output"]
                    and raw["flags"] == row["flags"] and raw["score"] == row["score"],
                    "RAW_REPORT_BINDING_RED")
            audit = raw["raw_audit"]
            require(audit["event_id"] == row["event_id"] and
                    audit["output"] == row["final_output"] and
                    audit["source_errors"] == [] and audit["checks"] and
                    all(v is True for v in audit["checks"].values()), "SOURCE_BINDING_RED")
            require(row["flags"]["valid_native"] is True and
                    row["flags"]["postclose_release_valid"] is True and
                    row["flags"]["final_pid_reaped"] is True, "NATIVE_ROW_FLAG_RED")
            require(raw["learning_mode"] == "RECORD_ONLY" and raw["jepa_weight"] == 0,
                    "RAW_LEARNING_RED")
            for gate in NEGATIVE:
                require(raw[gate] is False, "RAW_GATE_RED:" + gate)
            post = raw["postclose_releases"]
            pre = raw["preclose_releases"]
            require(all(p in post for p in pre) and
                    all(p["process_reaped"] is True for p in post), "RELEASE_RED")
            receipts = {(p["role"], p["before"]["pid"]) for p in post}
            runner = audit["output_metadata"]["runner"]
            require((runner["role"], runner["memory"]["pid"]) in receipts and
                    row["flags"]["final_runner_pid"] == runner["memory"]["pid"],
                    "FINAL_PID_RED")
            offers = audit["offers"]
            for offer in offers:
                require((offer["role"], offer["native_metrics"]["memory"]["pid"]) in receipts,
                        "OFFER_PID_RED")
            if arm in ARMS[:3]:
                require(raw["observer_mode"] == "off" and not offers and
                        {p["role"] for p in post} == {runner["role"]},
                        "SINGLE_ROLE_CONTAMINATION_RED")
            else:
                require(raw["observer_mode"] == "background", "OBSERVER_MODE_RED")
            if arm == "F_NATIVE_AUTO":
                require(raw["native_c2_alive_before_close"] is True and
                        raw["native_c2_process_reaped"] is True and
                        raw["native_c2_source_exact_before_close"] is True and
                        type(raw["native_c2_pid"]) is int and
                        raw["route_info"]["native_control_metrics"]["memory"]["pid"] ==
                        raw["native_c2_pid"] and
                        raw["context_packet"]["event_id"] == row["event_id"] and
                        raw["context_packet"]["session_id"] == row["session_id"] and
                        raw["context_packet"]["external_action_authority"] is False,
                        "C2_CONTEXT_OR_PID_RED")
                invoked += int(row["flags"]["native_c2_invocation"])
                selected += int(row["flags"]["native_c2_selected"])
            require(score_wire_equal(scorer(fixture, row["final_output"]), row["score"]),
                    "FROZEN_SCORE_REPLAY_RED:" + str(i))
            require(type(row["score"]["correct"]) is int and
                    row["score"]["correct"] == int(row["score"]["a"]) +
                    int(row["score"]["b"]), "SCORE_TOTAL_RED")
            totals[arm] += row["score"]["correct"]
        require({n for n in names if n.startswith("pilot/raw/")} == all_raw,
                "RAW_COVERAGE_RED")
        require(totals == report["score_totals_out_of_8"] and
                invoked == report["native_c2_invocations"] and
                selected == report["native_c2_selected"], "TOTALS_RED")
        stages = {n.removesuffix("_EXIT.txt"): z.read(n).decode().strip()
                  for n in names if n.endswith("_EXIT.txt")}
        require(all(stages.get(k) == "0" for k in
                    ("PINS", "VENV", "DEPS", "TEST", "BOOTSTRAP", "NATIVE")),
                "NATIVE_PREREQUISITES_RED")
        require(stages.get("REPORT_CHECK") == ("1" if original == "second" else None),
                "ORIGINAL_RED_STAGE_CHANGED")
        return {
            "schema": "v13.c2.seed61.frozen_scorer_replay.v1",
            "original": original, "zip_sha256": want_sha,
            "source_head": want_head, "native_rows": 24,
            "frozen_scorer_json_wire_exact": "24/24",
            "inner_sha256_verified": verified,
            "original_workflow": "RED", "stage_exits": stages,
            "score_totals_original": totals,
            "native_c2_invocations": invoked, "native_c2_selected": selected,
            "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
            "step2_gate_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "redmi_measured": False,
            "whole_system_complete": False,
            "status": "POSTHOC_REPLAY_ONLY_ORIGINAL_WORKFLOW_RED_NO_GATE",
        }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original", choices=ORIGINALS)
    p.add_argument("zip", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    result = replay_zip(a.zip, a.original, frozen_scorer())
    content = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.out:
        if a.out.exists():
            raise FileExistsError("FRESH_OUTPUT_REQUIRED")
        a.out.write_text(content)
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
