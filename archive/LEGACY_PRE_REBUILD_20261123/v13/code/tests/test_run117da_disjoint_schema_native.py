"""Run117DA synthetic software tests; never native model proof."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117da_disjoint_schema_native as da
from scripts import run117da_source_only_preflight as pre


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
            raise RuntimeError("SYNTHETIC_NATIVE_INTERRUPT")
        self.last_metrics = {"status": "FINAL", "actual_model": self.model.name}
        yield '{"action":"NONE"}'

    def unload(self):
        return {"process_reaped": True}


class Run117DANativeSoftware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preflight = pre.preflight()

    def setUp(self):
        FakeNative.calls = []
        FakeNative.interrupt_first = False

    def fake_run(self, root):
        paths = {
            da.cv.MODELS[0]: Path("LFM2.5-350M-QAD-Q4_0.gguf"),
            da.cv.MODELS[1]: Path("Qwen3.5-0.8B-Q4_0.gguf"),
        }
        with patch.object(da, "source_pins", wraps=da.source_pins) as pins:
            result = da.run(
                root / "missing-installed", root / "missing-qwen", root / "raw",
                runner_factory=FakeNative,
                pin_factory=lambda installed, qwen: paths,
                preflight_factory=lambda: self.preflight)
            self.assertGreaterEqual(pins.call_count, 2)
        return result

    def test_48_serial_calls_are_synthetic_and_nonpromoting(self):
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
            self.assertEqual([schema for _, schema in FakeNative.calls[:4]],
                             [True, False, False, True])
            self.assertEqual(r["summary"]["strict_scores"],
                             {m: {"SCHEMA": 4, "UNCONSTRAINED": 4}
                              for m in da.cv.MODELS})
            self.assertEqual(r["summary"]["none_output_count"],
                             {m: {"SCHEMA": 12, "UNCONSTRAINED": 12}
                              for m in da.cv.MODELS})
            self.assertEqual(r["jepa_weight"], 0)
            self.assertEqual(r["step2"], "UTILITY_FAIL")
            self.assertEqual(r["b3"], "NO_PROMOTION")
            self.assertFalse(r["whole_system_complete"])

    def test_partial_failure_keeps_raw_and_is_red(self):
        FakeNative.interrupt_first = True
        with tempfile.TemporaryDirectory() as tmp:
            r = self.fake_run(Path(tmp))
            self.assertEqual(r["status"], "STRUCTURAL_RED")
            self.assertEqual(r["model_callback_attempts"], 48)
            self.assertFalse(r["native_proof"])
            self.assertEqual(r["native_calls_verified"], 0)
            first = r["rows"][0]["arms"][0]
            self.assertEqual(first["native_output"], '{"act')
            self.assertEqual(first["error_type"], "RuntimeError")
            self.assertEqual(first["status"], "STRUCTURAL_RED")

    def test_bad_envelope_rejected_before_runner(self):
        rows = __import__("json").loads(__import__("json").dumps(self.preflight["rows"]))
        rows[0]["messages_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "ENVELOPE_RED"):
            da.validate(rows)
        self.assertEqual(FakeNative.calls, [])

    def test_no_model_pin_never_creates_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(Exception):
                da.run(root / "missing", root / "qwen", root / "raw")
            self.assertFalse((root / "raw").exists())

    def test_immutable_source_blobs_and_arm_map(self):
        pins = da.source_pins()
        self.assertEqual(len(pins), 6)
        self.assertEqual(da._arm("LFM_SCHEMA"), ("lfm25_350m", "SCHEMA"))
        self.assertEqual(da._arm("QWEN_UNCONSTRAINED"),
                         ("qwen35_0p8b", "UNCONSTRAINED"))
        with self.assertRaises(ValueError):
            da._arm("QWEN_ORACLE")


if __name__ == "__main__":
    unittest.main()
