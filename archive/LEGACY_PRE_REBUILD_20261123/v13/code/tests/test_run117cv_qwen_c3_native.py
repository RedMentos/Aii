"""Run117CV software-only tests. Fake native outputs are NEVER native evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117cv_qwen_c3_native as cv
from scripts import run117cu_qwen_c3_source_only_preflight as cu
from v13.common import dumps


class FakeProcess:
    def poll(self):
        return 0


class FakeNative:
    calls = []
    fail_first = False

    def __init__(self, home, role, model, config):
        self.model = Path(model)
        self.proc = None
        self.last_metrics = {}
        self.calls.append(self.model.name)

    def generate(self, messages, cancel, deadline, tokens, schema, seed):
        self.proc = FakeProcess()
        self.last_metrics = {"status": "FINAL", "actual_model": self.model.name}
        if self.fail_first and len(self.calls) == 1:
            yield '{"act'
            raise RuntimeError("SYNTHETIC_INTERRUPTED")
        yield '{}'

    def unload(self):
        return {"process_reaped": True}


class Run117CVSoftwareOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preflight = cu.preflight()

    def setUp(self):
        FakeNative.calls = []
        FakeNative.fail_first = False

    def test_exact_source_and_model_pins(self):
        self.assertEqual(len(cv.source_pins()), 4)
        self.assertEqual(cv.MODELS, ("lfm25_350m", "qwen35_0p8b"))
        self.assertEqual(cv.SEED, 117041)
        self.assertEqual(cv.RUNNER_SHA,
                         "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39")
        self.assertTrue(cv.validate_envelopes(self.preflight["rows"]))
        self.assertEqual(cv.model_order(0), cv.MODELS)
        self.assertEqual(cv.model_order(1), cv.MODELS[::-1])

    def test_rehashed_oracle_and_foreign_source_rejected(self):
        rows = json.loads(json.dumps(self.preflight["rows"]))
        payload = json.loads(rows[0]["messages"][1]["content"])
        payload["oracle"] = "A"
        rows[0]["messages"][1]["content"] = dumps(payload)
        rows[0]["messages_sha256"] = cv.sha(dumps(rows[0]["messages"]).encode())
        with self.assertRaisesRegex(ValueError, "ORACLE_OR_SOURCE_RED"):
            cv.validate_envelopes(rows)
        rows = json.loads(json.dumps(self.preflight["rows"]))
        rows[0]["source_sha256"]["current"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_ENVELOPE_RED"):
            cv.validate_envelopes(rows)

    def test_no_weights_no_output_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fresh"
            with self.assertRaises(Exception):
                cv.run(Path(tmp) / "not-installed", Path(tmp) / "qwen.gguf", out)
            self.assertFalse(out.exists())

    def test_synthetic_18_arms_serial_and_nonpromoting(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fresh"
            paths = {cv.MODELS[0]: Path("LFM2.5-350M-QAD-Q4_0.gguf"),
                     cv.MODELS[1]: Path("Qwen3.5-0.8B-Q4_0.gguf")}
            with patch.object(cv, "pinned_paths", return_value=paths):
                result = cv.run(Path(tmp), Path(tmp) / "qwen", out,
                                runner_factory=FakeNative,
                                preflight_factory=lambda: self.preflight)
            self.assertEqual(result["status"], "NO_EXPLORATORY_CAPACITY_SIGNAL")
            self.assertEqual(result["native_c3_calls"], 18)
            self.assertEqual(result["summary"]["native_final"], 18)
            self.assertEqual(result["summary"]["process_reaped"], 18)
            self.assertTrue(result["summary"]["complete_native_receipts"])
            self.assertEqual(result["summary"]["exact_by_model"],
                             {name: 0 for name in cv.MODELS})
            self.assertEqual(FakeNative.calls[:4], [
                paths[cv.MODELS[0]].name, paths[cv.MODELS[1]].name,
                paths[cv.MODELS[1]].name, paths[cv.MODELS[0]].name])
            self.assertEqual(result["jepa_weight"], 0)
            self.assertEqual(result["step2"], "UTILITY_FAIL")
            self.assertEqual(result["b3"], "NO_PROMOTION")
            self.assertFalse(result["whole_system_complete"])
            self.assertFalse(result["output_committed"])
            self.assertEqual(json.loads((out / "report.json").read_text())["status"],
                             result["status"])

    def test_synthetic_partial_native_failure_is_preserved_and_red(self):
        FakeNative.fail_first = True
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fresh"
            paths = {cv.MODELS[0]: Path("LFM2.5-350M-QAD-Q4_0.gguf"),
                     cv.MODELS[1]: Path("Qwen3.5-0.8B-Q4_0.gguf")}
            with patch.object(cv, "pinned_paths", return_value=paths):
                result = cv.run(Path(tmp), Path(tmp) / "qwen", out,
                                runner_factory=FakeNative,
                                preflight_factory=lambda: self.preflight)
            self.assertEqual(result["status"], "STRUCTURAL_RED")
            self.assertEqual(result["native_c3_calls"], 18)
            first = result["rows"][0]["arms"][0]
            self.assertEqual(first["native_output"], '{"act')
            self.assertEqual(first["error_type"], "RuntimeError")
            self.assertEqual(first["status"], "STRUCTURAL_RED")
            self.assertEqual(json.loads((out / "report.json").read_text())["rows"][0]["arms"][0]["native_output"], '{"act')

    def test_changed_oracle_and_early_bad_preflight_never_launch(self):
        bad = json.loads(json.dumps(self.preflight))
        bad["rows"][0]["messages_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fresh"
            paths = {cv.MODELS[0]: Path("LFM2.5-350M-QAD-Q4_0.gguf"),
                     cv.MODELS[1]: Path("Qwen3.5-0.8B-Q4_0.gguf")}
            with patch.object(cv, "pinned_paths", return_value=paths):
                with self.assertRaisesRegex(ValueError, "SOURCE_ENVELOPE_RED"):
                    cv.run(Path(tmp), Path(tmp) / "qwen", out,
                           runner_factory=FakeNative,
                           preflight_factory=lambda: bad)
            self.assertFalse(out.exists())
            self.assertEqual(FakeNative.calls, [])


if __name__ == "__main__":
    unittest.main()
