"""Software-only static contract for same-run QAD train+V2 workflow; no native execution."""
import os
from pathlib import Path
import unittest

import yaml

WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/bp1-qad-train-plus-v2-samejob.yml"
SOURCE = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"


class TrainV2WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = WORKFLOW.read_text()
        cls.workflow = yaml.safe_load(cls.raw)

    def test_exact_registered_activation_and_serial_heavy_owner(self):
        wf = self.workflow
        trigger = wf.get("on", wf.get(True))
        self.assertEqual(trigger["push"]["branches"], ["codex/gpt6-bp1-qad-train-plus-v2-20261027"])
        self.assertEqual(trigger["push"]["paths"], [
            "v13/code/docs/proofs/continuation-20261027/bp1-qad-train-v2-samejob/ACTIVATE.txt"])
        self.assertEqual(wf["concurrency"]["group"], "v13-bp1-qad-native-smoke-heavy-serial")
        self.assertFalse(wf["concurrency"]["cancel-in-progress"])
        self.assertEqual(wf["permissions"], {"contents": "read", "actions": "read"})

    def test_immutable_native_train_source_and_separate_heldout(self):
        s = self.raw
        for token in (
            SOURCE,
            "1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079",
            "9f356917911983e887f80aaadd8b58365fe43ecbf6632bb5e9e0a1aa8628ff86",
            "7238a0220255cbccbcf1f9ccfad8dc03febfc37f7bc1d9d0aa645618f006508c",
            "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
            "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39",
            "12a66c12019ee267cac12defd0b281f34fbcac5dc1f2e941236ae4ebf9a5f56c",
            "bp1_qad_lora_eval.py --mode collect",
            "bp1_qad_lora_eval.py --mode score",
            "E.verify_train_proof(b,proof)",
            "--serial-owner-confirmed",
        ):
            with self.subTest(token=token):
                self.assertIn(token, s)
        self.assertLess(s.index("TRAIN_EXIT.txt"), s.index("V2_HELDOUT_EXIT.txt"))
        self.assertNotIn("force: true", s)
        self.assertNotIn("upload adapter.gguf", s.lower())

    def test_public_artifact_scope_excludes_adapter_weights(self):
        steps = self.workflow["jobs"]["native"]["steps"]
        uploads = [step for step in steps if "actions/upload-artifact" in step.get("uses", "")]
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0]["with"]["path"], "${{ runner.temp }}/bp1-native-train/")
        self.assertNotIn("bp1-train-output", uploads[0]["with"]["path"])
        self.assertIn("NO_UTILITY_PROMOTION_OR_REDMi", self.raw)
        self.assertIn("for n in BUDGET DATASET_FETCH DEPS GGUF_SOURCE MASTER_FETCH TRAIN V2_MODEL V2_HELDOUT V2; do", self.raw)


if __name__ == "__main__":
    unittest.main()
