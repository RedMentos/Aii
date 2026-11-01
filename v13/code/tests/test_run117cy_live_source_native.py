"""Run117CY real SQLite structural native seam tests; fake C3 only."""
from pathlib import Path
import tempfile
import unittest

from scripts import run117cy_live_source_native as cy


class FakeProcess:
    def poll(self):
        return 0


class FakeNative:
    calls = 0
    output = '{"action":"A"}'
    interrupted = False

    def __init__(self, home, role, model, config):
        self.proc = None
        self.last_metrics = {}
        self.model = Path(model)
        self.role = role
        self.config = config
        FakeNative.calls += 1

    def generate(self, messages, cancel, deadline, tokens, schema, seed):
        self.proc = FakeProcess()
        if FakeNative.interrupted:
            yield '{"act'
            raise RuntimeError("SYNTHETIC_NATIVE_INTERRUPTED")
        self.last_metrics = {"status": "FINAL", "actual_model": cy.MODEL_FILE}
        yield FakeNative.output

    def unload(self):
        return {"process_reaped": True}


class Run117CYRealStoreSyntheticNative(unittest.TestCase):
    def setUp(self):
        FakeNative.calls = 0
        FakeNative.output = '{"action":"A"}'
        FakeNative.interrupted = False

    def run_fake(self, base):
        return cy.run(
            base / "not-installed", base / "home", base / "raw",
            runner_factory=FakeNative,
            pin_factory=lambda _: Path(cy.MODEL_FILE))

    def test_one_real_store_native_callback_structural_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = self.run_fake(root)
            self.assertEqual(report["status"],
                             "NATIVE_SOURCE_CALLBACK_STRUCTURAL_COMPLETE_NONPROMOTING",
                             report)
            self.assertEqual(report["native_c3_calls"], 1)
            self.assertEqual(FakeNative.calls, 1)
            self.assertTrue(report["native_final"])
            self.assertTrue(report["process_reaped"])
            self.assertTrue(report["source_rechecked"])
            self.assertTrue(report["closed_store_ok"])
            self.assertTrue(report["offline_exact"])
            self.assertTrue(report["no_live_output"])
            self.assertEqual(report["guard"]["shadow_action"], "A")
            self.assertFalse(report["guard"]["native_proof"])
            self.assertEqual(report["guard"]["delivery_authority"], 0)
            self.assertEqual(report["jepa_weight"], 0)
            self.assertEqual(report["step2"], "UTILITY_FAIL")
            self.assertEqual(report["b3"], "NO_PROMOTION")
            self.assertFalse(report["whole_system_complete"])
            self.assertTrue((root / "raw" / "report.json").is_file())

    def test_invalid_model_output_not_counted_as_utility(self):
        FakeNative.output = '{"action":"INVALID"}'
        with tempfile.TemporaryDirectory() as tmp:
            report = self.run_fake(Path(tmp))
            self.assertEqual(report["status"],
                             "NATIVE_SOURCE_CALLBACK_STRUCTURAL_COMPLETE_NONPROMOTING")
            self.assertEqual(report["guard"]["status"], "MODEL_OUTPUT_INVALID_RED")
            self.assertFalse(report["offline_exact"])
            self.assertNotIn("shadow_action", report["guard"])

    def test_partial_error_retained_no_native_promotion(self):
        FakeNative.interrupted = True
        with tempfile.TemporaryDirectory() as tmp:
            report = self.run_fake(Path(tmp))
            self.assertEqual(report["status"], "STRUCTURAL_RED")
            self.assertEqual(report["native_c3_calls"], 1)
            self.assertEqual(report["native_output"], '{"act')
            self.assertEqual(report["callback_error_type"], "RuntimeError")
            self.assertEqual(report["guard"]["status"], "MODEL_CALLBACK_ERROR_RED")
            self.assertFalse(report["native_final"])
            self.assertTrue(report["process_reaped"])
            self.assertTrue(report["closed_store_ok"])

    def test_missing_pinned_model_never_creates_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(Exception):
                cy.run(root / "missing-installed", root / "home", root / "raw")
            self.assertFalse((root / "home").exists())
            self.assertFalse((root / "raw").exists())
            self.assertEqual(FakeNative.calls, 0)

    def test_fresh_evidence_paths_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "raw").mkdir()
            with self.assertRaises(FileExistsError):
                self.run_fake(root)
            self.assertEqual(FakeNative.calls, 0)


if __name__ == "__main__":
    unittest.main()
