"""Run638 preregistered 32-step C3 source-only negative controls; no model calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run632_c3_lfm350_native as R
from scripts import run638_c3_dose_response as S

ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "docs/proofs/continuation-20261027/run638-c3-dose-response/COHORT.json"
ORIGINAL = ROOT / "docs/proofs/continuation-20261027/run632-c3-lfm350-native/COHORT_V2.json"


class Run638SourceContract(unittest.TestCase):
    def setUp(self):
        self.source = json.loads(COHORT.read_text())

    def _mutate(self, edit, message):
        data = copy.deepcopy(self.source)
        edit(data)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutated.json"
            path.write_text(json.dumps(data, indent=2) + "\n")
            # Rebind the candidate blob solely inside the negative-control test
            # so schema/field guards must reject even a recomputed SHA.
            with patch.object(S, "COHORT_BLOB", R.git_blob_sha(path.read_bytes())):
                with self.assertRaisesRegex(ValueError, message):
                    S.verify_cohort(path)

    def test_exact_prospective_cohort_and_unchanged_run632(self):
        self.assertEqual(S.verify_cohort(COHORT)["config"]["max_steps"], 32)
        self.assertEqual(R.verify_cohort(ORIGINAL)["config"]["max_steps"], 2)
        self.assertEqual(S.CONFIG["seed"], R.CFG["seed"])
        self.assertEqual(S.CONFIG["targets"], R.CFG["targets"])
        self.assertEqual(S.CONFIG["jepa_weight"], 0)
        self.assertEqual(S.CONFIG["anchor_weight"], 0)

    def test_bytes_changed_without_rebinding_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "cohort.json"
            p.write_bytes(COHORT.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "blob"):
                S.verify_cohort(p)

    def test_model_master_revision_refused(self):
        self._mutate(lambda c: c["master"].update(revision="main"), "master")

    def test_model_master_license_refused(self):
        self._mutate(lambda c: c["master"].update(license="unknown"), "master")

    def test_deployed_model_refused(self):
        self._mutate(lambda c: c["deployed_reference"].update(sha256="0" * 64), "deployed")

    def test_deployed_equivalence_promotion_refused(self):
        self._mutate(lambda c: c["deployed_reference"].update(equivalence_proven=True), "deployed")

    def test_seed_tamper_refused(self):
        self._mutate(lambda c: c["config"].update(seed=14), "configuration")

    def test_jepa_promotion_refused(self):
        self._mutate(lambda c: c["config"].update(jepa_weight=0.1), "configuration")

    def test_steps_tamper_refused(self):
        self._mutate(lambda c: c["config"].update(max_steps=48), "configuration")

    def test_train_row_tamper_refused(self):
        self._mutate(lambda c: c["train_rows"][0].update(target="blue"), "rows")

    def test_heldout_row_tamper_refused(self):
        self._mutate(lambda c: c["heldout_rows"][0].update(target="five"), "rows")

    def test_near_miss_row_tamper_refused(self):
        self._mutate(lambda c: c["near_miss_rows"][0].update(target="red"), "rows")

    def test_baseline_artifact_refused(self):
        self._mutate(lambda c: c["baseline"].update(adapter_sha256="0" * 64), "comparator")

    def test_age_promotion_refused(self):
        self._mutate(lambda c: c.update(age_change=True), "authority")

    def test_weight_authority_refused(self):
        self._mutate(lambda c: c.update(production_weight_authority=1), "authority")

    def test_negative_gates_refused(self):
        self._mutate(lambda c: c["negative_gates"].update(STEP2="GREEN"), "negative gates")

    def test_source_overlap_refused(self):
        self._mutate(lambda c: c["near_miss_rows"][0].update(
            prompt=c["train_rows"][0]["prompt"]), "rows")

    @staticmethod
    def valid_result():
        return {
            "artifact": "/tmp/synthetic-only",
            "files": {"gguf": "/tmp/synthetic-only", "safetensors": "/tmp/synthetic-only"},
            "metrics": {
                "steps": 32, "jepa_weight": 0, "anchor_weight": 0,
                "rank": 2, "alpha": 4, "targets": ["v_proj", "out_proj"],
                "trainable_parameter_count": 83968,
                "loss_history": [{"step": 32, "ce": 1.5}],
                "final_ce": 1.5, "master_kl_to_base": 0.01,
                "seconds": 100.0, "peak_rss_mb": 2400.0,
            },
        }

    def test_valid_synthetic_shape_has_no_production_authority(self):
        result = self.valid_result()
        self.assertEqual(S.verify_training_result(result)["steps"], 32)
        self.assertEqual(S.GATES["STEP2"], "UTILITY_FAIL")

    def test_training_incomplete_or_missing_refused(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            S.verify_training_result({})
        result = self.valid_result()
        result["metrics"]["steps"] = 31
        with self.assertRaisesRegex(ValueError, "config"):
            S.verify_training_result(result)

    def test_nonfinite_and_missing_final_step_refused(self):
        result = self.valid_result()
        result["metrics"]["final_ce"] = float("nan")
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            S.verify_training_result(result)
        result = self.valid_result()
        result["metrics"]["loss_history"][-1]["step"] = 31
        with self.assertRaisesRegex(ValueError, "final optimizer"):
            S.verify_training_result(result)


if __name__ == "__main__":
    unittest.main()
