"""Offline STEP12 semantic scorer tests; no model weights or native execution."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.step2_currentchain_native_semantic_gap_20261030 import (
    EXPECTED_CANON, EXPECTED_CATALOG, EXPECTED_HEAD, EXPECTED_PROOFS_SHA,
    EXPECTED_TOOLS, audit, score_output,
)


class NativeSemanticGap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def archive(self, output, *, corrupt_inner=False, structural=True):
        jef = {"status": "JEF_MODES_PASS"}
        step = {
            "proof_kind": "STEP12_VERTICAL_INTERMEDIATE",
            "status": "VERTICAL_CHECKS_PASS",
            "source_hashes": {"v13/proofs.py": EXPECTED_PROOFS_SHA},
            "cycles": 1, "step2_observed_both_roles": structural,
            "full_runner_proof": False, "complementarity_proven": False,
            "turns": [
                {"output": "First C3 test"},
                {"output": output,
                 "checks": {"final_output": True, "actual_model_output": True},
                 "output_metadata": {
                     "runner": {"role": "B1_DETAIL"},
                     "effective_config": {
                         "learning_mode": "RECORD_ONLY",
                         "system_stage": 0, "jepa_weight": 0,
                         "latents_enabled": False}}},
            ],
        }
        raw = {
            "HEAD.txt": (EXPECTED_HEAD + "\n").encode(),
            "CANON_BLOB.txt": (EXPECTED_CANON + "\n").encode(),
            "CATALOG_BLOB.txt": (EXPECTED_CATALOG + "\n").encode(),
            "TOOLS_BLOB.txt": (EXPECTED_TOOLS + "\n").encode(),
            "proofs/jef-modes-proof.json": json.dumps(jef).encode(),
            "proofs/step12-proof.json": json.dumps(step).encode(),
        }
        manifest = []
        for name, payload in sorted(raw.items()):
            digest = hashlib.sha256(payload).hexdigest()
            if corrupt_inner and name == "proofs/step12-proof.json":
                digest = "0" * 64
            manifest.append(f"{digest}  ./{name}")
        raw["SHA256SUMS.txt"] = ("\n".join(manifest) + "\n").encode()
        path = self.root / "evidence.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for name, payload in raw.items():
                z.writestr(name, payload)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_positive_bound_remainders(self):
        for answer in (
                "Option Rot has 40 Euro left; Option Blau has 10 Euro left.",
                "For Rot, 40 Euro remain. For Blau, 10 EUR remain.",
                "Rot: 40 Euro Rest. Blau: 10 Euro Rest."):
            with self.subTest(answer=answer):
                self.assertEqual(score_output(answer)["correct_remainders"], 2)

    def test_cost_echo_swapped_values_and_unsupported_preference_are_not_credit(self):
        for answer in (
                "Option Rot costs 80 Euro; Option Blau costs 110 Euro.",
                "Rot has 10 Euro left; Blau has 40 Euro left.",
                "Rot costs 40 Euro; Blau costs 10 Euro.",
                "The 110 euro option is more advantageous.",
                "The budget is 120 euros. Rot costs 80 and Blau costs 110."):
            with self.subTest(answer=answer):
                self.assertEqual(score_output(answer)["correct_remainders"], 0)

    def test_exact_closed_zip_positive_is_diagnostic_not_gate(self):
        path, digest = self.archive(
            "Rot has 40 Euro left; Blau has 10 Euro left.")
        r = audit(path, expected_zip_sha=digest)
        self.assertEqual(r["score"]["correct_remainders"], 2)
        self.assertEqual(r["semantic_status"], "REQUIREMENTS_PRESENT_DIAGNOSTIC_ONLY")
        self.assertFalse(r["comparative_utility_proven"])
        self.assertFalse(r["native_executed_here"])
        self.assertFalse(r["step2_gate_promoted"])

    def test_missing_remainders_are_negative_even_with_structural_pass(self):
        path, digest = self.archive(
            "The budget is 120 euros. Rot costs 80, Blau costs 110.")
        r = audit(path, expected_zip_sha=digest)
        self.assertEqual(r["semantic_status"], "SEMANTIC_REQUIREMENT_FAIL")
        self.assertEqual(r["score"]["correct_remainders"], 0)
        self.assertEqual(r["step12_structural_status"], "VERTICAL_CHECKS_PASS")

    def test_outer_inner_and_scope_tampering_fail_closed(self):
        path, digest = self.archive("Rot has 40 Euro left.")
        with self.assertRaisesRegex(ValueError, "ZIP_SHA256_MISMATCH"):
            audit(path)
        path, digest = self.archive("Rot has 40 Euro left.", corrupt_inner=True)
        with self.assertRaisesRegex(ValueError, "INNER_SHA256_MISMATCH"):
            audit(path, expected_zip_sha=digest)
        path, digest = self.archive("Rot has 40 Euro left.", structural=False)
        with self.assertRaisesRegex(ValueError, "PROOF_SCOPE_MISMATCH"):
            audit(path, expected_zip_sha=digest)


if __name__ == "__main__":
    unittest.main()
