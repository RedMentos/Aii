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
    def _body(self, role):
        if role == "C3_LANGUAGE":
            return FakeC3()
        return super()._body(role)

    def _unload(self):
        self.pool.release_history.append({
            "before": 1234, "process_reaped": True, "synthetic": True})


class DriverFakeC3Tests(unittest.TestCase):
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
