import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from v13.runtime import Runtime
from v13.b3train import train_l1_shadow


class L1ShadowTrainingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _pairs_and_batch(self):
        revs = {
            "B1_DETAIL": self.r.models.revision("B1_DETAIL"),
            "B2_GIST": self.r.models.revision("B2_GIST"),
        }
        pairs = []
        refs = []
        for i in range(64):
            source = {"source_id": f"src-{i}", "sha256": f"{i:064x}",
                      "char_start": 0, "char_end": 8}
            refs.append(source)
            pairs.append({"body_pair_id": f"pair-{i}", "model_revisions": revs,
                          "source_ref": source})
        rng = np.random.default_rng(7)
        y = np.asarray([i % 2 for i in range(64)], dtype=np.int64)
        H = rng.normal(0, .2, size=(64, 4, 8)).astype(np.float32)
        H[:, :, 0] += y[:, None] * 1.5
        mask = np.ones((64, 4), dtype=np.float32)
        Xr = rng.normal(0, .2, size=(64, 6)).astype(np.float32)
        Xr[:, 0] += y * 1.5
        batch = {
            "H": H, "mask": mask, "Xr": Xr, "y": y,
            "body_pair_ids": [p["body_pair_id"] for p in pairs],
            "source_refs": refs,
            "sender_revision": revs["B1_DETAIL"],
            "receiver_revision": revs["B2_GIST"],
        }
        return pairs, batch

    def test_trains_and_persists_shadow_candidate_without_authority(self):
        pairs, batch = self._pairs_and_batch()
        with patch("v13.b3train.training_batch", return_value=batch):
            report = train_l1_shadow(
                self.r.cognition, pairs, [i % 2 for i in range(64)],
                [f"feedback-{i}" for i in range(64)], "binary-outcome",
                "verified-test-outcome", direction="B1_TO_B2",
                seeds=(3, 7), epochs=2, head_steps=5,
            )
        self.assertEqual(report["status"], "L1_SHADOW_CANDIDATES_SAVED_NOT_PROMOTED")
        self.assertEqual(len(report["seed_reports"]), 2)
        self.assertEqual(report["latent_authority"], 0)
        self.assertEqual(report["receiver_injection_authority"], 0)
        self.assertEqual(report["body_learning_authority"], 0)
        self.assertIn("NOT_RUN_MISSING_L0_CHANNEL_BASELINES", report["l1_utility_gate"])
        for seed in report["seed_reports"]:
            self.assertTrue(seed["reload_identical"])
            self.assertTrue((self.r.home / seed["candidate_manifest"]).is_file())
            self.assertTrue((self.r.home / seed["candidate_weights"]).is_file())
        self.assertTrue((self.r.home / report["report_path"]).is_file())

    def test_source_pinned_l0_evidence_can_open_only_l2_shadow_gate(self):
        pairs, batch = self._pairs_and_batch()
        split_rng = np.random.default_rng(20261122)
        test_indices = []
        for label in range(2):
            members = np.flatnonzero(batch["y"] == label)
            members = split_rng.permutation(members)
            test_indices.extend(int(x) for x in members[:6])
        test_indices = sorted(test_indices)
        l0 = {
            "schema": "v13.b3-l0-baselines/1",
            "body_pair_ids": batch["body_pair_ids"],
            "source_hashes": [x["sha256"] for x in batch["source_refs"]],
            "test_indices": test_indices,
            "seed_ids": ["3", "7"],
            "acc": {"EXACT": [0.5, 0.5], "CONTROL": [0.5, 0.5], "SYMBOLIC": [0.5, 0.5]},
            "bytes": {"EXACT": 0, "CONTROL": 16, "SYMBOLIC": 32},
            "role_drop": 0.0,
        }
        gate = {"verdict": "PASS", "reason": "test-only stub; no runtime authority"}
        with patch("v13.b3train.training_batch", return_value=batch), \
             patch("v13.b3train.l1_gate", return_value=gate) as gate_call:
            report = train_l1_shadow(
                self.r.cognition, pairs, [i % 2 for i in range(64)],
                [f"feedback-{i}" for i in range(64)], "binary-outcome",
                "verified-test-outcome", direction="B1_TO_B2",
                seeds=(3, 7), epochs=2, head_steps=5, l0_evidence=l0,
            )
        self.assertEqual(report["l1_gate"], gate)
        self.assertEqual(report["l1_utility_gate"], "PASS_L2_PREFIX_SHADOW_ALLOWED_NO_NATIVE_AUTHORITY")
        self.assertEqual(report["status"], "L1_SHADOW_PASSED_L2_SHADOW_ALLOWED_NOT_PROMOTED")
        self.assertEqual(report["latent_authority"], 0)
        task = gate_call.call_args.args[0]
        self.assertEqual(task["seed_ids"]["LATENT"], ["3", "7"])
        self.assertEqual(task["acc"]["EXACT"], [0.5, 0.5])
        self.assertEqual(task["role_drop"], 0.0)
        for seed in report["seed_reports"]:
            manifest = json.loads((self.r.home / seed["candidate_manifest"]).read_text())
            self.assertEqual(manifest["l1_gate"]["verdict"], "PASS")
            self.assertEqual(manifest["receiver_injection_authority"], 0)

    def test_refuses_less_than_sixty_four_pairs(self):
        with self.assertRaisesRegex(ValueError, "at least 64"):
            train_l1_shadow(self.r.cognition, [{}] * 63, [0] * 63,
                            [f"label-{i}" for i in range(63)],
                            "task", "human_feedback")


if __name__ == "__main__":
    unittest.main()
