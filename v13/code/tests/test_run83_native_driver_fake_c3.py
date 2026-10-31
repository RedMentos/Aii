"""Run83 driver fake-C3 software rehearsal; absolutely no native proof."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_run52_b1b2_cross_turn import FakeRuntime
from scripts import jef_body_c3_interference_fixture_839 as f
from scripts import run83_jef_body_c3_interference_native as native
from scripts import run83_jef_body_c3_interference_verify as verify
from v13.common import dumps


class FakeC3:
    last_metrics = {
        "status": "FINAL",
        "actual_model": native.C3_MODEL,
        "generated_tokens": 5,
        "synthetic": True,
    }

    def generate(self, messages, *args, **kwargs):
        payload = json.loads(messages[1]["content"])
        yield dumps({"action": payload["typed_jef_action"]})


class DryRuntime(FakeRuntime):
    def __init__(self, home):
        super().__init__(home)
        # Synthetic C3 path seam ONLY: the driver hashes a model path before
        # its fake generator runs. Keep ModelManager.path_for strict in reality.
        real_path_for = self.models.path_for
        self.models.path_for = lambda role: (
            Path(home) / "synthetic-only-c3.gguf"
            if role == "C3_LANGUAGE" else real_path_for(role))

    def _body(self, role):
        if role == "C3_LANGUAGE":
            return FakeC3()
        return super()._body(role)

    def _unload(self):
        self.pool.release_history.append({
            "before": 1234, "process_reaped": True, "synthetic": True})


class DriverFakeC3Tests(unittest.TestCase):
    def test_real_missing_model_gate_is_not_relaxed_by_fake_seam(self):
        from v13.common import Unavailable
        from v13.models import ModelManager
        with tempfile.TemporaryDirectory() as d:
            runtime = DryRuntime(Path(d))
            try:
                with self.assertRaises(Unavailable):
                    ModelManager.path_for(runtime.models, "C3_LANGUAGE")
                self.assertEqual(runtime.models.path_for("C3_LANGUAGE"),
                                 Path(d) / "synthetic-only-c3.gguf")
            finally:
                runtime.close()

    def test_twelve_calls_full_store_pipeline_synthetic_only(self):
        with tempfile.TemporaryDirectory() as d, \
                patch.object(native.cli, "Runtime", DryRuntime), \
                patch.object(native, "file_hash", side_effect=[
                    f.MODEL_SHA256, f.RUNNER_SHA256]):
            report = native.run(Path(d) / "home", Path(d) / "raw")
        self.assertEqual(report["status"],
                         "DUAL_FORMATTER_NONINFERIOR_SMALL_SHADOW", report)
        self.assertEqual(report["native_call_count"], 12)
        self.assertEqual(report["body_native_call_count"], 0)
        self.assertTrue(report["body_observations_synthetic"])
        self.assertEqual(report["scores"],
                         {"TYPED_ONLY": 6, "DUAL_SOURCE": 6})
        self.assertTrue(report["no_live_output"])
        self.assertTrue(report["closed_store_ok"])
        self.assertEqual(verify.verify(report)["scores"], report["scores"])
        self.assertFalse(report["whole_system_complete"])


if __name__ == "__main__":
    unittest.main()
