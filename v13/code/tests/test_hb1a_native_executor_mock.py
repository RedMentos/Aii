"""HB1a synthetic 54-call orchestration and RED-retention test; NO native weights."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scripts import hb1a_native_executor as native
from scripts import hb1a_two_body_native_pilot as plan


class FakeModels:
    def __init__(self, home):
        self.home = Path(home)

    def verify(self, deep=False):
        return {k: {"ok": True, "hash_checked": deep}
                for k in ("body", "gist", "language")}

    def revision(self, role):
        return plan.MODEL_REVISIONS[role]

    def path_for(self, role):
        return self.home / "models" / (role + ".gguf")


class FakePool:
    calls = []
    fail_at = None
    closed = False

    def __init__(self, home, models, cfg):
        type(self).calls = []
        type(self).closed = False

    def get(self, role):
        class Runner:
            last_metrics = {"status": "FINAL"}
            def generate(self, messages, cancel, deadline, max_tokens, seed, schema=None):
                FakePool.calls.append((role, max_tokens, seed, schema))
                if FakePool.fail_at == len(FakePool.calls):
                    raise RuntimeError("SYNTHETIC_INJECTED_RED")
                yield '{"action":"UNKNOWN"}' if role == "C3_LANGUAGE" else "SOURCE QUOTE ONLY"
        return Runner()

    def unload(self):
        type(self).closed = True
        return {"process_reaped": True}


class HB1AOrchestrationSoftware(unittest.TestCase):
    def setup_home(self, root):
        home = root / "home"
        (home / "config").mkdir(parents=True)
        (home / "bin").mkdir()
        (home / "models").mkdir()
        (home / "config/models.json").write_text("{}")
        (home / "bin/llama-server").write_bytes(b"FAKE_NON_NATIVE_TEST")
        for role in plan.MODEL_SHAS:
            (home / "models" / (role + ".gguf")).write_bytes(b"FAKE_MODEL")
        return home

    def fake_hash(self, path):
        path = Path(path)
        if path.name == "llama-server":
            return "f" * 64
        for role, digest in plan.MODEL_SHAS.items():
            if path.name == role + ".gguf":
                return digest
        raise AssertionError("unexpected hash path")

    def run_with_mocks(self, home, out):
        with patch.object(native, "admit"), \
             patch.object(native, "file_sha", side_effect=self.fake_hash), \
             patch("v13.config.initialize", return_value={
                 "system_stage": 0, "learning_mode": "RECORD_ONLY",
                 "latents_enabled": False, "jepa_weight": 0}), \
             patch("v13.models.ModelManager", FakeModels), \
             patch("v13.runners.RunnerPool", FakePool):
            return native.run_native(home, out, plan.FIXTURE)

    def test_all_54_synthetic_calls_checkpointed_without_gate(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = self.setup_home(root)
            FakePool.fail_at = None
            receipt = self.run_with_mocks(home, root / "evidence")
            self.assertEqual(receipt["body_recorded"], 24)
            self.assertEqual(receipt["c3_recorded"], 30)
            self.assertTrue(receipt["process_reaped"])
            self.assertTrue(FakePool.closed)
            self.assertEqual(len(FakePool.calls), 54)
            self.assertEqual(sum(role == "B1_DETAIL" for role, *_ in FakePool.calls), 18)
            self.assertEqual(sum(role == "B2_GIST" for role, *_ in FakePool.calls), 6)
            self.assertEqual(sum(role == "C3_LANGUAGE" for role, *_ in FakePool.calls), 30)
            self.assertTrue(all(schema is not None for role, _, _, schema in FakePool.calls
                                if role == "C3_LANGUAGE"))
            raw = json.loads((root / "evidence/RAW.json").read_text())
            score = json.loads((root / "evidence/SCORE.json").read_text())
            self.assertEqual(len(raw["body_rows"]), 24)
            self.assertEqual(len(raw["c3_rows"]), 30)
            self.assertEqual(sum(v["unknown"] for v in score["per_arm"].values()), 30)
            self.assertFalse(score["canonical_gate_pass"])
            self.assertFalse(receipt["whole_system_complete"])
            self.assertEqual(receipt["jepa_weight"], 0)
            self.assertFalse(receipt["redmi_measured"])

    def test_injected_failure_keeps_original_partial_raw(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = self.setup_home(root)
            FakePool.fail_at = 7
            try:
                with self.assertRaisesRegex(RuntimeError, "SYNTHETIC_INJECTED_RED"):
                    self.run_with_mocks(home, root / "evidence")
                raw = json.loads((root / "evidence/RAW.json").read_text())
                receipt = json.loads((root / "evidence/RECEIPT.json").read_text())
                self.assertEqual(raw["status"], "FAIL_RETAIN_RAW")
                self.assertEqual(len(raw["body_rows"]), 6)
                self.assertEqual(len(raw["c3_rows"]), 0)
                self.assertEqual(receipt["error_type"], "RuntimeError")
                self.assertTrue(receipt["process_reaped_on_exit"])
                self.assertTrue(FakePool.closed)
            finally:
                FakePool.fail_at = None


if __name__ == "__main__":
    unittest.main()
