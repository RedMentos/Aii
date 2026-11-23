"""Synthetic-only tests for the private raw ZIP aggregate auditor."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import run30_native_keldara_aggregate_audit as audit


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode()


class NativeAggregateAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "synthetic.zip"
        self.models = {"B1_DETAIL": "a" * 64,
                       "B2_GIST": "b" * 64,
                       "C3_LANGUAGE": "c" * 64}
        self.report = {
            "fixture_sha256": audit.FIXTURE_SHA256,
            "canonical_gate_pass": False,
            "phone_measured": False,
            "all_structural_checks_passed": True,
            "rows": [],
            "row_sha256": {},
        }
        for variant in audit.VARIANTS:
            checks = {key: True for key in audit.FIELDS}
            row = {
                "fixture": "Keldara", "variant": variant,
                "status": "RECORDED", "processes_reaped": True,
                "oracle_visible_to_native": False,
                "native_consumer_metrics": {"status": "FINAL"},
                "score": {
                    "field_checks": checks, "contradictions": [],
                    "contradiction_count": 0, "scored_fields": 12,
                    "exact": True, "utility": 1.0,
                },
            }
            self.report["rows"].append(row)
        self.receipt = {
            "schema": "v13.step2.run16.keldara.native_pilot.v1",
            "status": "PASS_SCOPED_ONE_FIXTURE_NATIVE_NO_UTILITY_GATE",
            "fixture_id": "Keldara", "fixture_limit": 1,
            "fixture_sha256": audit.FIXTURE_SHA256,
            "fixture_source_git_blob": audit.SOURCE_BLOB,
            "arm": "CQ", "seed": 20261114,
            "model_hashes_before": self.models,
            "model_hashes_after": dict(self.models),
            "model_hashes_unchanged": True,
            "runner_sha256_before": "d" * 64,
            "runner_sha256_after": "d" * 64,
            "runner_unchanged": True,
            "native_offer_counts": {"offers": 12, "with_question": 12},
            "rows": 7, "native_consumer_final": 7,
            "canonical_gate_pass": False,
            "whole_system_complete": False, "age_authority": 0,
            "jepa_weight": 0, "weight_updates": False,
            "redmi_measured": False,
        }

    def tearDown(self):
        self.temp.cleanup()

    def write_zip(self, stale_inner=False):
        self.report["row_sha256"] = {
            "Keldara:" + row["variant"]: sha(encode(row))
            for row in self.report["rows"]
        }
        raw = encode(self.report)
        self.receipt["raw_report_sha256"] = sha(raw)
        files = {
            "HEAD.txt": (audit.HEAD + "\n").encode(),
            "RECEIPT.json": encode(self.receipt),
            "STEP2_RAW.json": raw,
        }
        sums = "".join(sha(data) + "  ./" + name + "\n"
                       for name, data in sorted(files.items()))
        if stale_inner:
            sums = sums.replace(sha(files["STEP2_RAW.json"]), "0" * 64)
        with zipfile.ZipFile(self.path, "w") as z:
            for name, data in files.items():
                z.writestr(name, data)
            z.writestr("SHA256SUMS.txt", sums.encode())
        return {"expected_zip_sha": sha(self.path.read_bytes()),
                "expected_head": audit.HEAD,
                "expected_raw_sha": sha(raw)}

    def test_clean_synthetic_is_scoped_only(self):
        args = self.write_zip()
        result = audit.audit_zip(self.path, **args)
        self.assertTrue(result["all_variants_exact"])
        self.assertEqual(result["both_exact_minus_b1_only"], 0)
        self.assertFalse(result["canonical_gate_pass"])
        self.assertNotIn("raw_answer", json.dumps(result))

    def test_reject_modified_zip_and_inner_hash(self):
        args = self.write_zip()
        with self.assertRaisesRegex(ValueError, "native_zip_sha_mismatch"):
            audit.audit_zip(self.path)
        args = self.write_zip(stale_inner=True)
        with self.assertRaisesRegex(ValueError, "native_inner_sha_mismatch"):
            audit.audit_zip(self.path, **args)

    def test_reject_missing_variant_or_promoted_gate(self):
        self.report["rows"][0]["variant"] = self.report["rows"][1]["variant"]
        args = self.write_zip()
        with self.assertRaises(ValueError):
            audit.audit_zip(self.path, **args)
        self.report["rows"][0]["variant"] = audit.VARIANTS[0]
        self.receipt["canonical_gate_pass"] = True
        args = self.write_zip()
        with self.assertRaisesRegex(ValueError, "native_receipt_or_scope_mismatch"):
            audit.audit_zip(self.path, **args)

    def test_reject_inconsistent_field_score_and_changed_models(self):
        self.report["rows"][0]["score"]["utility"] = 0.5
        args = self.write_zip()
        with self.assertRaisesRegex(ValueError, "native_field_score_inconsistent"):
            audit.audit_zip(self.path, **args)
        self.report["rows"][0]["score"]["utility"] = 1.0
        self.receipt["model_hashes_after"]["B1_DETAIL"] = "f" * 64
        args = self.write_zip()
        with self.assertRaisesRegex(ValueError, "native_receipt_or_scope_mismatch"):
            audit.audit_zip(self.path, **args)


if __name__ == "__main__":
    unittest.main()
