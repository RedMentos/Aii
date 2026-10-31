"""Run37 independent native receipt audit: synthetic and negative controls only."""
import hashlib
import io
import json
import unittest
import zipfile

from scripts.run37_audit_run36_native_zip import (
    HEAD, MODELS, PINS, STAGES, SUITES, audit_bytes,
)


def make_report():
    cal = {"brier": .25, "ece": 0., "bins": [
        {"lo": 0., "hi": 1., "n": 88, "accuracy": .5, "confidence": .5}]}
    by_role = {role: {"native_calls": 88, "source_counts": {"field_min_prob": 88},
                      "invalid_present": 0, "missing_confidence": 0, "legacy_errors": 0}
               for role in MODELS}
    agg = {"items": 88, "role_calls": 264, "by_role": by_role,
           "legacy_comparable_rows": 88, "legacy_incomparable_rows": 0,
           "legacy_correct_on_comparable": 44, "finite_correct_on_comparable": 44,
           "finite_correct_all": 44, "same_output_changed_votes": 0,
           "legacy_calibration_on_comparable": cal,
           "finite_calibration_on_comparable": cal}
    return {
        "schema": "v13.run36.ag12_native_finite_confidence_incidence.v1",
        "revision": "run36-ag12-native-confidence-incidence-shadow-v1",
        "evidence_kind": "LINUX_NATIVE_AG12_SAME_OUTPUT_CONFIDENCE_SHADOW",
        "suite_seed": 17, "generation_seed": 17,
        "roles": list(MODELS), "language_order": ["de", "en"],
        "model_sha256": dict(MODELS),
        "runner_tar_sha256": "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443",
        "runner_binary_sha256": "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39",
        "runtime_closed": True, "process_reaped": True,
        "exclusive_native_residency": True, "no_events": True, "no_messages": True,
        "status": "DONE", "native_role_calls": 528, "voted_items": 176,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL", "b3": "NO_PROMOTION",
        "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "world_jepa_authority": "SHADOW", "redmi_measured": False,
        "learned_german_transfer_proven": False, "live_jef_fusion_proven": False,
        "whole_system_complete": False,
        "per_language": {
            lang: {"suite_hash": sha, "native_roles": list(MODELS),
                   "aggregate": json.loads(json.dumps(agg))}
            for lang, sha in SUITES.items()},
    }


def make_zip(report=None, tamper=None, corrupt_manifest=False):
    report = make_report() if report is None else report
    files = {
        "HEAD.txt": (HEAD + "\n").encode(),
        "PINS.txt": b"frozen pins",
        "PINS_RAW.log": "\n".join(
            f"{sha} {sha} {path}" for path, sha in PINS.items()).encode(),
        "REPORT.json": json.dumps(report).encode(),
        "REPORT_CHECK_RAW.log":
            b"RUN36_DISJOINT_NATIVE_INCIDENCE_AGGREGATE_ONLY_NO_PROMOTION",
        "PRIVACY_RAW.log": b"privacy CLEAN",
        "TEST_RAW.log": b"Ran 30 tests in 0.415s\n\nOK\n",
        "NATIVE_RAW.log": (
            b'{"evidence_kind":"LINUX_NATIVE_AG12_SAME_OUTPUT_CONFIDENCE_SHADOW",'
            b'"native_role_calls":528,"voted_items":176}\n'),
    }
    for stage in STAGES:
        files[stage + "_EXIT.txt"] = b"0\n"
        files.setdefault(stage + "_RAW.log", b"")
    if tamper:
        files[tamper[0]] = tamper[1]
    manifest = "".join(
        f"{hashlib.sha256(value).hexdigest()}  ./{name}\n"
        for name, value in sorted(files.items())).encode()
    if corrupt_manifest:
        manifest = manifest.replace(b"0", b"1", 1)
    files["SHA256SUMS"] = manifest
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, value in files.items():
            z.writestr(name, value)
    data = out.getvalue()
    return data, hashlib.sha256(data).hexdigest()


class Run37IndependentAudit(unittest.TestCase):
    def audit(self, report=None, tamper=None, corrupt_manifest=False):
        data, digest = make_zip(report, tamper, corrupt_manifest)
        return audit_bytes(data, expected_sha=digest)

    def test_complete_synthetic_receipt(self):
        r = self.audit()
        self.assertEqual(r["inner_hashes"], 21)
        self.assertEqual(r["zero_exit_stages"], 9)
        self.assertFalse(r["promotion"])

    def test_outer_hash_mismatch(self):
        data, _ = make_zip()
        with self.assertRaisesRegex(ValueError, "OUTER_SHA256"):
            audit_bytes(data)

    def test_manifest_tamper(self):
        with self.assertRaisesRegex(ValueError, "MANIFEST"):
            self.audit(corrupt_manifest=True)

    def test_native_exit_red_even_with_new_manifest(self):
        with self.assertRaisesRegex(ValueError, "STAGE_NATIVE"):
            self.audit(tamper=("NATIVE_EXIT.txt", b"1\n"))

    def test_wrong_model_pin(self):
        r = make_report()
        r["model_sha256"]["B1_DETAIL"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "MODEL_PINS"):
            self.audit(r)

    def test_incomplete_role(self):
        r = make_report()
        r["per_language"]["de"]["aggregate"]["by_role"]["B1_DETAIL"]["source_counts"]["field_min_prob"] = 87
        with self.assertRaisesRegex(ValueError, "SOURCE_COUNT"):
            self.audit(r)

    def test_calibration_mismatch(self):
        r = make_report()
        r["per_language"]["de"]["aggregate"]["finite_calibration_on_comparable"]["bins"][0]["accuracy"] = .125
        with self.assertRaisesRegex(ValueError, "FINITE_CALIBRATION"):
            self.audit(r)

    def test_negative_gate_tamper(self):
        r = make_report()
        r["step2"] = "PASS"
        with self.assertRaisesRegex(ValueError, "NEGATIVE_GATES"):
            self.audit(r)

    def test_impossible_correctness_change(self):
        r = make_report()
        a = r["per_language"]["en"]["aggregate"]
        a["finite_correct_all"] = a["finite_correct_on_comparable"] = 50
        with self.assertRaisesRegex(ValueError, "SAME_OUTPUT_CORRECTNESS"):
            self.audit(r)

    def test_unexpected_raw_private_member(self):
        with self.assertRaisesRegex(ValueError, "MEMBER_SET"):
            self.audit(tamper=("PROMPTS.txt", b"private"))


if __name__ == "__main__":
    unittest.main()
