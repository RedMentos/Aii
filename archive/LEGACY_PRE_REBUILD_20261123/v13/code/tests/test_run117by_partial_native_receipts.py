"""Run117BY future-only failed native stream receipts; software stubs, never native proof."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117bu_disjoint_budget_native as m

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/RUN117BS_C3_DISJOINT_BUDGET_SEED1103.json")


class FakeRunner:
    def __init__(self, fail_typed=False, fail_raw=False):
        self.fail_typed = fail_typed
        self.fail_raw = fail_raw
        self.last_metrics = {"status": "NOT_STARTED"}

    def generate(self, messages, *_args, **_kw):
        typed = "typed_jef_candidate" in messages[1]["content"]
        if (typed and self.fail_typed) or (not typed and self.fail_raw):
            self.last_metrics = {"status": "STREAM_INTERRUPTED"}
            yield '{"choice":'
            raise RuntimeError("synthetic stream interrupted")
        if typed:
            packet = json.loads(messages[1]["content"])
            value = packet["typed_jef_candidate"]
        else:
            value = {"choice": "UNKNOWN", "remaining": None}
        self.last_metrics = {"status": "FINAL"}
        yield json.dumps(value, separators=(",", ":"))


class FakePool:
    def __init__(self, runner):
        self.runner = runner
        self.release_history = []

    def get(self, _role):
        return self.runner

    def unload(self):
        self.release_history.append({"synthetic_reap_only": True})


class FailureReceipts(unittest.TestCase):
    def row(self, index, runner):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "home"
            fixture = m.fixture(FIXTURE)["fixtures"][index]
            pool = FakePool(runner)
            with patch.object(m, "installed_links"), \
                 patch.object(m, "ModelManager", return_value=object()), \
                 patch.object(m, "RunnerPool", return_value=pool), \
                 patch.object(m, "_reaped", return_value=True):
                result = m.run_row(home, Path(d) / "no-model", fixture, index)
            return result

    def test_raw_first_stream_exception_keeps_partial_bytes_and_release(self):
        result = self.row(1, FakeRunner(fail_raw=True))
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertTrue(result["closed_store_ok"])
        self.assertEqual(len(result["arms"]), 1)
        arm = result["arms"][0]
        self.assertEqual(arm["arm"], "RAW_SOURCE")
        self.assertEqual(arm["native_output"], '{"choice":')
        self.assertEqual(arm["error_type"], "RuntimeError")
        self.assertEqual(arm["native_metrics"]["status"], "STREAM_INTERRUPTED")
        self.assertEqual(arm["status"], "STRUCTURAL_RED")
        self.assertTrue(arm["process_reaped"])
        self.assertTrue(arm["process_releases"])
        self.assertFalse(arm["score"]["exact"])
        self.assertFalse(arm["native_final"])

    def test_typed_callback_failure_kept_and_next_raw_arm_not_promoted(self):
        result = self.row(0, FakeRunner(fail_typed=True))
        self.assertEqual(result["status"], "STRUCTURAL_RED")
        self.assertEqual(len(result["arms"]), 2)
        typed, raw = result["arms"]
        self.assertEqual(typed["arm"], "TYPED_JEF")
        self.assertEqual(typed["native_output"], '{"choice":')
        self.assertEqual(typed["guard"]["status"], "CALLBACK_RED")
        self.assertEqual(typed["status"], "STRUCTURAL_RED")
        self.assertFalse(typed["source_rechecked"])
        self.assertTrue(typed["process_reaped"])
        self.assertEqual(raw["arm"], "RAW_SOURCE")
        self.assertEqual(raw["status"], "RECORDED")
        self.assertFalse(result["closed_store_ok"] is False)
        self.assertFalse(typed["native_final"])


if __name__ == "__main__":
    unittest.main()
