#!/usr/bin/env python3
"""Independent read-only Run36 native receipt audit (stdlib; no V13 runtime import).

Source-locked to original artifact 13022018458. No native inference, no promotion.
"""
import argparse
import hashlib
import io
import json
import math
import re
import zipfile
from pathlib import Path

ORIGINAL_SHA = "2ad28dc3823751971254fc4b34501c3a131895cfad6eb4299993eb92b2b07f0f"
HEAD = "d421badbc5adde9707ad37ea8f219fa0483bf01a"
SUITES = {
    "de": "bd14d242ccf91e4ffe8b24c5a17db924e1902c9e740e3dbb2abe11b9e25c3062",
    "en": "962c261e4b9512b5e23262bb486afb0910357c8278c9e3eb8e4da9da1aee73eb",
}
MODELS = {
    "B1_DETAIL": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
    "B2_GIST": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
    "C3_LANGUAGE": "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
}
STAGES = ("DEPS", "VENV", "COMPILE", "PINS", "TEST", "NATIVE",
          "REPORT_CHECK", "PRIVACY", "DIFF")
PINS = {
    "v13/code/docs/AG12_NATIVE_FINITE_CONFIDENCE_INCIDENCE_PREREG_RUN36_20261031.md": "a3aa063ef1a4da6cb6b49f8a75a63587d15327f1",
    "v13/code/v13/agi/solver_confidence_native_incidence_candidate.py": "e02d23713e91f982ceea4a85e0b362581aa48e59",
    "v13/code/tests/test_run36_ag12_native_confidence_incidence.py": "13d806c9c896d58926846ab898ff7ea9d007a960",
    "v13/code/scripts/run36_ag12_native_confidence_incidence.py": "f2c94817610a9c5aad385feefaa2766c7fdd440a",
    "v13/code/v13/agi/solver_confidence_finite_candidate.py": "46982818f6c6078d823c97388c1a4ec250d82e14",
    "v13/code/v13/agi/solver.py": "66a9419143c456f01747b4796fb327b3b36711b3",
    "v13/code/scripts/run27_ag12_three_organ_native.py": "f7c23a2467b3daeae4875b7e18b1a6d83fcdbb47",
    "v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md": "218464b12a2d27d92524c751922fa8e1c3fb0ea7",
}


def need(ok, reason):
    if not ok:
        raise ValueError("RUN37_AUDIT_RED:" + reason)


def probability(v):
    return type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1


def calibration(cal, expected_n):
    need(type(cal) is dict and probability(cal.get("brier"))
         and probability(cal.get("ece")), "CALIBRATION")
    bins = cal.get("bins")
    need(type(bins) is list and bool(bins), "CALIBRATION_BINS")
    total = correct = 0
    prev = 0.
    for b in bins:
        n, lo, hi = b.get("n"), b.get("lo"), b.get("hi")
        need(type(n) is int and n > 0 and probability(lo)
             and probability(hi) and prev <= lo < hi, "BIN_SHAPE")
        acc, conf = b.get("accuracy"), b.get("confidence")
        need(probability(acc) and probability(conf)
             and lo <= conf <= hi, "BIN_VALUES")
        need(abs(round(acc * n) - acc * n) <= .005, "BIN_ACCURACY")
        total += n
        correct += round(acc * n)
        prev = hi
    need(total == expected_n, "BIN_TOTAL")
    return correct


def audit_bytes(blob, expected_sha=ORIGINAL_SHA):
    need(hashlib.sha256(blob).hexdigest() == expected_sha, "OUTER_SHA256")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        need(z.testzip() is None, "CRC")
        names = z.namelist()
        need(len(names) == len(set(names))
             and all("/" not in name and "\\" not in name for name in names),
             "MEMBER_NAMES")
        allowed = {"HEAD.txt", "PINS.txt", "PINS_RAW.log", "SHA256SUMS",
                   "REPORT.json", "REPORT_CHECK_RAW.log", "PRIVACY_RAW.log",
                   "TEST_RAW.log", "NATIVE_RAW.log"}
        for stage in STAGES:
            allowed.update((stage + "_EXIT.txt", stage + "_RAW.log"))
        need(set(names) == allowed, "MEMBER_SET")
        sums = {}
        for line in z.read("SHA256SUMS").decode().splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  \./([A-Za-z0-9_.-]+)", line)
            need(match is not None, "MANIFEST_FORMAT")
            digest, name = match.groups()
            need(name not in sums, "MANIFEST_DUPLICATE")
            sums[name] = digest
        need(set(sums) == allowed - {"SHA256SUMS"}, "MANIFEST_COVERAGE")
        for name, digest in sums.items():
            need(hashlib.sha256(z.read(name)).hexdigest() == digest,
                 "INNER_SHA256_" + name)
        for stage in STAGES:
            need(z.read(stage + "_EXIT.txt").strip() == b"0",
                 "STAGE_" + stage)
        need(z.read("HEAD.txt").decode().strip() == HEAD, "SOURCE_HEAD")
        need(b"CLEAN" in z.read("PRIVACY_RAW.log"), "PRIVACY")
        need(b"Ran 30 tests" in z.read("TEST_RAW.log")
             and b"\nOK\n" in z.read("TEST_RAW.log"), "SOFTWARE_TESTS")
        need(b"RUN36_DISJOINT_NATIVE_INCIDENCE_AGGREGATE_ONLY_NO_PROMOTION"
             in z.read("REPORT_CHECK_RAW.log"), "REPORT_CHECK")
        pins = {}
        for line in z.read("PINS_RAW.log").decode().splitlines():
            bits = line.split()
            need(len(bits) == 3 and bits[0] == bits[1]
                 and re.fullmatch("[0-9a-f]{40}", bits[0]), "PIN_FORMAT")
            need(bits[2] not in pins, "PIN_DUPLICATE")
            pins[bits[2]] = bits[0]
        need(pins == PINS, "SOURCE_PINS")
        r = json.loads(z.read("REPORT.json"),
                       parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
        need(r.get("schema") == "v13.run36.ag12_native_finite_confidence_incidence.v1"
             and r.get("revision") == "run36-ag12-native-confidence-incidence-shadow-v1"
             and r.get("evidence_kind") == "LINUX_NATIVE_AG12_SAME_OUTPUT_CONFIDENCE_SHADOW",
             "REPORT_IDENTITY")
        need(r.get("suite_seed") == 17 and r.get("generation_seed") == 17,
             "SEED")
        need(r.get("roles") == list(MODELS)
             and r.get("language_order") == ["de", "en"], "ROLE_ORDER")
        need(r.get("model_sha256") == MODELS, "MODEL_PINS")
        need(r.get("runner_tar_sha256") == "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
             and r.get("runner_binary_sha256") == "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39",
             "RUNNER_PINS")
        for key in ("runtime_closed", "process_reaped", "exclusive_native_residency",
                    "no_events", "no_messages"):
            need(r.get(key) is True, key)
        need(r.get("status") == "DONE" and r.get("native_role_calls") == 528
             and r.get("voted_items") == 176, "NATIVE_COMPLETION")
        need(r.get("age0") == "RECORD_ONLY" and r.get("step2") == "UTILITY_FAIL"
             and r.get("b3") == "NO_PROMOTION" and r.get("body_jepa") == "UNAVAILABLE"
             and r.get("jepa_weight") == 0 and r.get("world_jepa_authority") == "SHADOW",
             "NEGATIVE_GATES")
        for key in ("redmi_measured", "learned_german_transfer_proven",
                    "live_jef_fusion_proven", "whole_system_complete"):
            need(r.get(key) is False, key)
        need(set(r.get("per_language", {})) == set(SUITES), "LANGUAGES")
        result = {"original_sha256": expected_sha, "original_head": HEAD,
                  "inner_hashes": len(sums), "zero_exit_stages": len(STAGES),
                  "native_calls": 528, "rows": 176, "promotion": False,
                  "languages": {}}
        for lang, suite in SUITES.items():
            v = r["per_language"][lang]
            need(v.get("suite_hash") == suite
                 and v.get("native_roles") == list(MODELS), "SUITE_" + lang)
            a = v.get("aggregate")
            need(type(a) is dict and a.get("items") == 88
                 and a.get("role_calls") == 264, "ROLE_COUNT_" + lang)
            need(set(a.get("by_role", {})) == set(MODELS), "ROLE_KEYS")
            invalid = 0
            for role in MODELS:
                role_data = a["by_role"][role]
                sources = role_data.get("source_counts")
                need(type(sources) is dict
                     and all(type(n) is int and n >= 0 for n in sources.values()),
                     "SOURCE_TYPES")
                need(set(sources) <= {"field_min_prob", "invalid:field_min_prob", "none"}
                     and sum(sources.values()) == role_data.get("native_calls") == 88,
                     "SOURCE_COUNT")
                need(role_data.get("invalid_present") == sources.get("invalid:field_min_prob", 0)
                     and role_data.get("missing_confidence") == sources.get("none", 0)
                     and role_data.get("legacy_errors") == 0, "SOURCE_CLASSIFICATION")
                invalid += role_data["invalid_present"]
            need(a.get("legacy_comparable_rows") == 88
                 and a.get("legacy_incomparable_rows") == 0, "COMPARABILITY")
            for key in ("legacy_correct_on_comparable", "finite_correct_on_comparable",
                        "finite_correct_all", "same_output_changed_votes"):
                need(type(a.get(key)) is int and 0 <= a[key] <= 88, "COUNT_" + key)
            changed = a["same_output_changed_votes"]
            need(a["finite_correct_on_comparable"] == a["finite_correct_all"]
                 and abs(a["legacy_correct_on_comparable"]
                         - a["finite_correct_on_comparable"]) <= changed,
                 "SAME_OUTPUT_CORRECTNESS")
            need(calibration(a["legacy_calibration_on_comparable"], 88)
                 == a["legacy_correct_on_comparable"], "LEGACY_CALIBRATION")
            need(calibration(a["finite_calibration_on_comparable"], 88)
                 == a["finite_correct_on_comparable"], "FINITE_CALIBRATION")
            result["languages"][lang] = {
                "invalid_present_role_calls": invalid, "changed_votes": changed,
                "legacy_correct": a["legacy_correct_on_comparable"],
                "finite_correct": a["finite_correct_all"]}
        tail = z.read("NATIVE_RAW.log").decode().strip().splitlines()[-1]
        need(json.loads(tail) == {
            "evidence_kind": r["evidence_kind"],
            "native_role_calls": 528, "voted_items": 176}, "NATIVE_LOG")
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", required=True, type=Path)
    args = p.parse_args()
    print(json.dumps(audit_bytes(args.zip.read_bytes()), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
