import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import os
import stat

import numpy as np

from v13.runtime import Runtime
from v13.b3train import train_l1_shadow, _source_disjoint_split, _secure_shadow_output_dir


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
        self.assertTrue(report["weight_evidence"]["numeric_updates_verified_all_seeds"])
        self.assertTrue(report["weight_evidence"]["nonzero_gradient_norm_all_seeds"])
        self.assertEqual(report["weight_evidence"]["role_retention_status"],
                         "NOT_MEASURED_NO_OLD_TASK_ROLE_HOLDOUT")
        self.assertTrue(report["weight_evidence"]["master_weights_untouched"])
        for seed in report["seed_reports"]:
            self.assertTrue(seed["reload_identical"])
            self.assertTrue(seed["numeric_weight_update_verified"])
            self.assertGreater(seed["bridge_parameter_delta_l2"], 0.0)
            self.assertGreater(seed["gradient_norm_last"], 0.0)
            self.assertNotEqual(seed["initial_bridge_parameter_sha256"],
                                seed["final_bridge_parameter_sha256"])
            self.assertTrue(seed["no_message_identity"])
            self.assertEqual(seed["role_retention_status"],
                             "NOT_MEASURED_NO_OLD_TASK_ROLE_HOLDOUT")
            self.assertTrue(seed["master_weights_untouched"])
            self.assertGreater(seed["bridge_parameter_delta_by_tensor_l2"]["Wu"], 0.0)
            manifest = json.loads((self.r.home / seed["candidate_manifest"]).read_text())
            evidence = manifest["bridge_parameter_evidence"]
            self.assertGreater(evidence["delta_l2"], 0.0)
            self.assertGreater(evidence["gradient_norm_last"], 0.0)
            self.assertTrue(evidence["numeric_update_verified"])
            self.assertEqual(manifest["latent_authority"], 0)
            self.assertEqual(manifest["receiver_injection_authority"], 0)
            self.assertEqual(manifest["body_learning_authority"], 0)
            self.assertTrue((self.r.home / seed["candidate_manifest"]).is_file())
            self.assertTrue((self.r.home / seed["candidate_weights"]).is_file())
        self.assertTrue((self.r.home / report["report_path"]).is_file())

    def test_source_pinned_l0_evidence_can_open_only_l2_shadow_gate(self):
        pairs, batch = self._pairs_and_batch()
        train_indices, test_indices, train_hashes, test_hashes = _source_disjoint_split(
            batch["source_refs"], batch["y"], 20261122
        )
        l0 = {
            "schema": "v13.b3-l0-baselines/2",
            "split_policy": "SOURCE_SHA256_GROUPED_STRATIFIED_20PCT_MIN2_V1",
            "train_indices": train_indices.tolist(),
            "test_indices": test_indices.tolist(),
            "train_source_hashes": train_hashes,
            "test_source_hashes": test_hashes,
            "task_id": "binary-outcome", "direction": "B1_TO_B2",
            "label_source": "verified-test-outcome",
            "labels": [i % 2 for i in range(64)],
            "label_provenance": [f"feedback-{i}" for i in range(64)],
            "body_pair_ids": batch["body_pair_ids"],
            "source_hashes": [x["sha256"] for x in batch["source_refs"]],
            "seed_ids": ["3", "7", "11"],
            "acc": {"EXACT": [0.5, 0.5, 0.5], "CONTROL": [0.5, 0.5, 0.5], "SYMBOLIC": [0.5, 0.5, 0.5]},
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
                seeds=(3, 7, 11), epochs=2, head_steps=5, l0_evidence=l0,
            )
        self.assertEqual(report["l1_gate"], gate)
        self.assertEqual(report["l1_utility_gate"], "PASS_L2_PREFIX_SHADOW_ALLOWED_NO_NATIVE_AUTHORITY")
        self.assertEqual(report["status"], "L1_SHADOW_PASSED_L2_SHADOW_ALLOWED_NOT_PROMOTED")
        self.assertTrue(report["run_key"])
        self.assertEqual(report["latent_authority"], 0)
        task = gate_call.call_args.args[0]
        self.assertEqual(task["seed_ids"]["LATENT"], ["3", "7", "11"])
        self.assertEqual(task["acc"]["EXACT"], [0.5, 0.5, 0.5])
        self.assertEqual(task["role_drop"], 0.0)
        for seed in report["seed_reports"]:
            manifest = json.loads((self.r.home / seed["candidate_manifest"]).read_text())
            self.assertEqual(manifest["l1_gate"]["verdict"], "PASS")
            self.assertEqual(len(manifest["body_pair_ids"]), 64)
            self.assertEqual(len(manifest["label_provenance"]), 64)
            self.assertEqual(manifest["receiver_injection_authority"], 0)


    def test_source_disjoint_holdout_keeps_all_spans_of_each_source_together(self):
        source_refs = []
        labels = []
        for group in range(32):
            label = group % 2
            digest = f"{group:064x}"
            for span in range(2):
                source_refs.append({
                    "source_id": f"source-{group}",
                    "sha256": digest,
                    "char_start": span * 8,
                    "char_end": span * 8 + 8,
                })
                labels.append(label)
        train, test, train_hashes, test_hashes = _source_disjoint_split(
            source_refs, np.asarray(labels, dtype=np.int64), 20261122
        )
        train_set, test_set = set(train.tolist()), set(test.tolist())
        self.assertFalse(set(train_hashes) & set(test_hashes))
        self.assertEqual(set(train_hashes) | set(test_hashes),
                         {ref["sha256"] for ref in source_refs})
        for digest in {ref["sha256"] for ref in source_refs}:
            indices = {i for i, ref in enumerate(source_refs) if ref["sha256"] == digest}
            self.assertTrue(indices <= train_set or indices <= test_set)
            self.assertFalse(indices & train_set and indices & test_set)

    def test_source_disjoint_holdout_keeps_two_test_groups_per_class(self):
        refs = []
        labels = []
        for group in range(8):
            refs.append({
                "source_id": f"source-{group}",
                "sha256": f"{group:064x}",
                "char_start": 0,
                "char_end": 8,
            })
            labels.append(group % 2)
        train, test, train_hashes, test_hashes = _source_disjoint_split(
            refs, np.asarray(labels, dtype=np.int64), 13
        )
        label_by_hash = {ref["sha256"]: labels[i] for i, ref in enumerate(refs)}
        self.assertEqual(len(train_hashes), 4)
        self.assertEqual(len(test_hashes), 4)
        for label in (0, 1):
            self.assertEqual(sum(label_by_hash[x] == label for x in train_hashes), 2)
            self.assertEqual(sum(label_by_hash[x] == label for x in test_hashes), 2)
        self.assertEqual(len(train) + len(test), 8)

    def test_source_disjoint_holdout_rejects_conflicting_labels_for_same_source(self):
        refs = [
            {"source_id": "source-a", "sha256": "a" * 64, "char_start": 0, "char_end": 4},
            {"source_id": "source-b", "sha256": "a" * 64, "char_start": 4, "char_end": 8},
        ]
        with self.assertRaisesRegex(ValueError, "conflicting task labels"):
            _source_disjoint_split(refs, np.asarray([0, 1], dtype=np.int64), 7)

    def test_legacy_per_example_l0_evidence_is_rejected(self):
        pairs, batch = self._pairs_and_batch()
        with patch("v13.b3train.training_batch", return_value=batch):
            with self.assertRaisesRegex(ValueError, "L0 baseline evidence"):
                train_l1_shadow(
                    self.r.cognition, pairs, [i % 2 for i in range(64)],
                    [f"feedback-{i}" for i in range(64)], "binary-outcome",
                    "verified-test-outcome", direction="B1_TO_B2",
                    seeds=(3, 7, 11), epochs=1, head_steps=1,
                    l0_evidence={"schema": "v13.b3-l0-baselines/1"},
                )

    def test_refuses_less_than_sixty_four_pairs(self):
        with self.assertRaisesRegex(ValueError, "at least 64"):
            train_l1_shadow(self.r.cognition, [{}] * 63, [0] * 63,
                            [f"label-{i}" for i in range(63)],
                            "task", "human_feedback")



    def test_shadow_output_directory_is_private_and_descriptor_anchored(self):
        home = Path(self.tmp.name) / "secure-home"
        home.mkdir(mode=0o700)
        output_dir, relative_dir, output_fd = _secure_shadow_output_dir(
            home, Path("b3/shadow/B1_TO_B2/task/run-a")
        )
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "probe.txt").write_text("inside", encoding="utf-8")
            self.assertEqual((home / relative_dir / "probe.txt").read_text(encoding="utf-8"), "inside")
            self.assertEqual(stat.S_IMODE((home / relative_dir).stat().st_mode), 0o700)
        finally:
            os.close(output_fd)

    def test_shadow_output_rejects_top_level_and_nested_symlink_parents(self):
        home = Path(self.tmp.name) / "symlink-home"
        home.mkdir(mode=0o700)
        outside = Path(self.tmp.name) / "outside-shadow"
        outside.mkdir()

        (home / "b3").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            _secure_shadow_output_dir(home, Path("b3/shadow/B1_TO_B2/task/run-top"))
        self.assertEqual(list(outside.iterdir()), [])

        (home / "b3").unlink()
        (home / "b3").mkdir()
        (home / "b3" / "shadow").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            _secure_shadow_output_dir(home, Path("b3/shadow/B1_TO_B2/task/run-nested"))
        self.assertEqual(list(outside.iterdir()), [])

if __name__ == "__main__":
    unittest.main()
