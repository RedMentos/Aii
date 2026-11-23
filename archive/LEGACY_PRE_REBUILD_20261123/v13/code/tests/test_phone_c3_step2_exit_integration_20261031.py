"""Integrated phone-source negative-gate integrity; Linux software only.

This does not execute native weights or promote any gate. Original Z2 result
files and registered scorer remain immutable.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from scripts import package_source
from v13 import gates
from v13.common import APP


NEGATIVE = (
    "bench-results/step2-z2b-seeds-20261021/z2b_result.json",
    "bench-results/step2-z2c-b2-rule-20261021/z2c_result.json",
    "bench-results/step2-z2-timescale-20261021/z2_result.json",
)
CANONICAL = NEGATIVE[:2]


class PhoneC3Step2ExitIntegration(unittest.TestCase):
    def test_native_negative_results_required_for_phone_inventory(self):
        for relative in NEGATIVE:
            with self.subTest(relative=relative):
                self.assertIn(relative, package_source.PHONE_REQUIRED_FIXTURES)
                self.assertTrue(package_source.phone_needed(Path(relative)))
                self.assertTrue((APP / relative).is_file())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in NEGATIVE[:-1]:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("{}")
            with patch.object(package_source, "PHONE_REQUIRED_FIXTURES", set(NEGATIVE)):
                with self.assertRaisesRegex(ValueError, "Phone-install required fixture missing"):
                    package_source.inventory(root, True)

    def test_immutable_original_native_verdicts_still_false(self):
        for relative in CANONICAL:
            with self.subTest(relative=relative):
                report = json.loads((APP / relative).read_text())
                self.assertIs(report["gate"]["canonical_gate_pass"], False)
        result = gates.evaluate()
        self.assertEqual(result["STEP2_EXIT"]["status"], "EVIDENCE_NOT_PASSING")
        self.assertEqual(len(result["STEP2_EXIT"]["verdict_failures"]), 2)
        for name in ("STEP6", "G-B-TIMESCALE-DIVERGENCE-001",
                     "G-FOCAL-CAPACITY-003"):
            self.assertNotEqual(result[name]["status"], "GREEN")

    def test_actual_phone_zip_contains_exact_original_negative_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "phone.zip"
            receipt = package_source.package(APP, output, phone_install=True)
            self.assertFalse(receipt["native_models_launched"])
            self.assertFalse(receipt["phone_measured"])
            self.assertFalse(receipt["canonical_gate_pass"])
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read("V13-Phone/WORKSPACE_FILES.json"))
                files = manifest["files"]
                for relative in NEGATIVE:
                    with self.subTest(relative=relative):
                        raw = (APP / relative).read_bytes()
                        self.assertEqual(archive.read("V13-Phone/" + relative), raw)
                        self.assertEqual(files[relative], hashlib.sha256(raw).hexdigest())
                for relative in ("v13/gates.py", "specs/gate-graph.json",
                                 "tests/test_step2_exit_gate_split_20261031.py",
                                 "tests/test_b2_c3_context_plan_20261031.py",
                                 "v13/context_os.py", "v13/safe_tar.py",
                                 "scripts/install_selftest.py"):
                    self.assertIn(relative, files)


if __name__ == "__main__":
    unittest.main()
