"""Run117DG synthetic 48-arm native seam tests, no native proof."""
import copy
from pathlib import Path
import tempfile
import unittest

from scripts import run117dg_normalized_source_native as dg
from scripts import run117df_paired_source_preflight as pre


class FakeProcess:
    def poll(self):
        return 0


class FakeNative:
    calls = []
    interrupt_first = False

    def __init__(self, home, role, model, config):
        self.model = Path(model)
        self.proc = None
        self.last_metrics = {}
        self.calls.append((self.model.name, None))

    def generate(self, messages, cancel, deadline, tokens, schema, seed):
        self.proc = FakeProcess()
        self.calls[-1] = (self.model.name, schema is not None)
        if self.interrupt_first and len(self.calls) == 1:
            yield '{"act'
            raise RuntimeError("SYNTHETIC_NATIVE_INTERRUPTED")
        self.last_metrics = {"status": "FINAL", "actual_model": self.model.name}
        yield '{"action":"NONE"}'

    def unload(self):
        return {"process_reaped": True}


class Run117DGNativeSoftware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admission = pre.preflight()

    def setUp(self):
        FakeNative.calls = []
        FakeNative.interrupt_first = False

    def fake_run(self, root):
        paths = {
            dg.cv.MODELS[0]: Path("LFM2.5-350M-QAD-Q4_0.gguf"),
            dg.cv.MODELS[1]: Path("Qwen3.5-0.8B-Q4_0.gguf"),
        }
        return dg.run(root / "no-installed", root / "no-qwen", root / "raw",
                      runner_factory=FakeNative,
                      pin_factory=lambda installed, qwen: paths,
                      preflight_factory=lambda: self.admission)

    def test_48_serial_synthetic_calls_schema_both_arms_no_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.fake_run(Path(tmp))
            self.assertEqual(r["status"], "SYNTHETIC_SOFTWARE_ONLY")
            self.assertEqual(r["evidence_class"], "SYNTHETIC_SOFTWARE_ONLY")
            self.assertEqual(r["model_callback_attempts"], 48)
            self.assertEqual(r["native_calls_verified"], 0)
            self.assertFalse(r["native_proof"])
            self.assertEqual(r["summary"]["native_final"], 48)
            self.assertEqual(r["summary"]["process_reaped"], 48)
            self.assertTrue(r["summary"]["complete_native_receipts"])
            self.assertEqual(len(FakeNative.calls), 48)
            self.assertEqual([x[1] for x in FakeNative.calls], [True] * 48)
            self.assertEqual(r["summary"]["strict_scores"],
                             {m: {"RAW": 4, "NORMALIZED": 4} for m in dg.cv.MODELS})
            self.assertEqual(r["summary"]["none_output_count"],
                             {m: {"RAW": 12, "NORMALIZED": 12} for m in dg.cv.MODELS})
            self.assertEqual(r["jepa_weight"], 0)
            self.assertEqual(r["step2"], "UTILITY_FAIL")
            self.assertEqual(r["b3"], "NO_PROMOTION")
            self.assertFalse(r["whole_system_complete"])

    def test_partial_failure_preserves_raw_and_never_proves_native(self):
        FakeNative.interrupt_first = True
        with tempfile.TemporaryDirectory() as tmp:
            r = self.fake_run(Path(tmp))
            self.assertEqual(r["status"], "STRUCTURAL_RED")
            self.assertEqual(r["model_callback_attempts"], 48)
            self.assertFalse(r["native_proof"])
            self.assertEqual(r["native_calls_verified"], 0)
            arm = r["rows"][0]["arms"][0]
            self.assertEqual(arm["native_output"], '{"act')
            self.assertEqual(arm["error_type"], "RuntimeError")
            self.assertEqual(arm["status"], "STRUCTURAL_RED")

    def test_mutated_source_message_rejected_before_runner(self):
        rows = copy.deepcopy(self.admission["rows"])
        rows[0]["normalized_messages_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "MESSAGE_HASH_RED"):
            dg.validate(rows)
        self.assertEqual(FakeNative.calls, [])
        rows = copy.deepcopy(self.admission["rows"])
        rows[0]["source_sha256"]["policy_source"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_ENVELOPE_RED"):
            dg.validate(rows)

    def test_forged_normalized_worksheet_rejected_even_if_hash_recomputed(self):
        rows = copy.deepcopy(self.admission["rows"])
        import json
        from v13.common import dumps
        data = json.loads(rows[0]["normalized_messages"][1]["content"])
        data["worksheet_without_eligibility_or_action"]["policy"]["required_sealed"] = False
        rows[0]["normalized_messages"][1]["content"] = dumps(data)
        rows[0]["normalized_messages_sha256"] = dg.sha(
            dumps(rows[0]["normalized_messages"]).encode())
        with self.assertRaisesRegex(ValueError, "ORACLE_OR_SOURCE_RED"):
            dg.validate(rows)

    def test_fresh_output_required_and_no_pins_no_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(Exception):
                dg.run(root / "missing", root / "qwen", root / "raw")
            self.assertFalse((root / "raw").exists())

    def test_frozen_source_blobs_and_arms(self):
        pins = dg.source_pins()
        self.assertGreaterEqual(len(pins), 7)
        self.assertEqual(dg._arm("LFM_NORMALIZED"), ("lfm25_350m", "NORMALIZED"))
        self.assertEqual(dg._arm("QWEN_RAW"), ("qwen35_0p8b", "RAW"))
        with self.assertRaises(ValueError):
            dg._arm("QWEN_ORACLE")


if __name__ == "__main__":
    unittest.main()
