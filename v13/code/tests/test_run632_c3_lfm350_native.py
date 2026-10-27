"""Run632 source-only immutable actual selected-C3 LFM2.5-350M preflight controls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import run632_c3_lfm350_native as R

ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "docs/proofs/continuation-20261027/run632-c3-lfm350-native/COHORT_V2.json"
V1 = ROOT / "docs/proofs/continuation-20261027/run632-c3-lfm350-native/COHORT.json"
SPECS = ROOT / "specs/models.json"


class Run632Contracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.master = self.home / "master"
        self.master.mkdir()
        (self.master / "model.safetensors").write_bytes(b"dummy")
        (self.master / "config.json").write_text(json.dumps({"model_type": "lfm2", "num_hidden_layers": 16}))
        (self.master / "LICENSE").write_text("LFM Open License v1.0\nTest fixture, not a model license.\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_v2_immutable_and_v1_never_executed(self):
        c = R.verify_cohort(COHORT)
        self.assertEqual(c["schema"], "V13_RUN632_C3_LFM350_NATIVE_COHORT_V2")
        self.assertEqual(c["config"]["targets"], ["v_proj", "out_proj"])
        self.assertEqual(c["config"]["jepa_weight"], 0)
        with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
            R.verify_cohort(V1)

    def test_any_cohort_edit_fails_before_training(self):
        c = json.loads(COHORT.read_text())
        for path, value in [
            (("config", "targets"), ["q_proj", "v_proj"]),
            (("config", "jepa_weight"), 0.2),
            (("train_rows", 0, "target"), "red"),
            (("production_weight_authority",), 1),
            (("master", "revision"), "main"),
        ]:
            with self.subTest(path=path):
                x = json.loads(json.dumps(c))
                y = x
                for k in path[:-1]:
                    y = y[k]
                y[path[-1]] = value
                p = self.home / "changed.json"
                p.write_text(json.dumps(x))
                with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                    R.verify_cohort(p)

    def test_master_sha_arch_license_and_deployed_manifest(self):
        def fake_sha(path):
            return R.MASTER_SHA if Path(path).name == "model.safetensors" else "a" * 64
        with patch.object(R, "sha256", side_effect=fake_sha):
            binding = R.verify_master(self.master, SPECS)
            self.assertFalse(binding["deployed_equivalence_proven"])
            self.assertEqual(binding["master_sha256"], R.MASTER_SHA)
        with self.assertRaisesRegex(ValueError, "safetensors SHA mismatch"):
            R.verify_master(self.master, SPECS)
        (self.master / "config.json").write_text(json.dumps({"model_type": "llama", "num_hidden_layers": 16}))
        with patch.object(R, "sha256", side_effect=fake_sha):
            with self.assertRaisesRegex(ValueError, "architecture"):
                R.verify_master(self.master, SPECS)
        (self.master / "config.json").write_text(json.dumps({"model_type": "lfm2", "num_hidden_layers": 16}))
        (self.master / "LICENSE").write_text("NOT THE LICENSE")
        with patch.object(R, "sha256", side_effect=fake_sha):
            with self.assertRaisesRegex(ValueError, "missing LFM Open License"):
                R.verify_master(self.master, SPECS)

    def test_no_training_when_source_or_master_invalid(self):
        with patch.object(R, "verify_cohort", side_effect=ValueError("blocked")):
            with self.assertRaisesRegex(ValueError, "blocked"):
                R.execute(COHORT, self.master, SPECS, self.home / "output")
        self.assertFalse((self.home / "output").exists())
        with patch.object(R, "verify_master", side_effect=ValueError("master blocked")):
            with self.assertRaisesRegex(ValueError, "master blocked"):
                R.execute(COHORT, self.master, SPECS, self.home / "output")
        self.assertFalse((self.home / "output").exists())

    def test_no_rope_qk_targets_and_separate_heldout(self):
        self.assertEqual(R.CFG["targets"], ["v_proj", "out_proj"])
        self.assertFalse({"q_proj", "k_proj"} & set(R.CFG["targets"]))
        self.assertFalse(set(x[0] for x in R.TRAIN) & set(x[0] for x in R.HELDOUT))
        self.assertEqual(R.GATES["STEP2"], "UTILITY_FAIL")
        self.assertEqual(R.GATES["Body_JEPA"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
