"""Adversarial tests against the exact pinned Run531 raw real-file artifact."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run534_independent_z12a_audit import independently_score, audit_file, RAW_SHA256


class IndependentRawAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = os.environ.get("RUN534_RAW_JSON")
        if source is None:
            raise unittest.SkipTest(
                "Run534 pinned Run531 raw artifact not bundled with phone source; "
                "exact-head Actions audit requires RUN534_RAW_JSON")
        cls.path = Path(source)
        if not cls.path.is_file():
            raise FileNotFoundError("RUN534_RAW_JSON was provided but pinned raw file is missing")
        cls.raw = json.loads(cls.path.read_text())

    def test_exact_raw_independent_pass(self):
        result = audit_file(self.path)
        self.assertEqual(result["status"], "INDEPENDENT_RAW_AUDIT_PASS")
        self.assertEqual(result["metrics"]["n_observations"], 509)
        self.assertEqual(result["metrics"]["unknown_truth"], 0)
        self.assertFalse(result["phone_measured"])
        self.assertFalse(result["canonical_gate_promoted"])

    def reject(self, mutate):
        data = copy.deepcopy(self.raw)
        mutate(data)
        with self.assertRaisesRegex(ValueError, "RUN534_AUDIT_FAIL"):
            independently_score(data)

    def test_wrong_sha_refused(self):
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            audit_file(self.path, "0" * 64)

    def test_modified_report_row_refused(self):
        self.reject(lambda d: d["rows"][0].update(truth="unknown"))

    def test_modified_raw_class_refused(self):
        self.reject(lambda d: d["runs"][0]["observations"][0].update(cls="EXTERNAL"
                    if d["runs"][0]["observations"][0]["cls"] != "EXTERNAL" else "SELF"))

    def test_modified_metric_refused(self):
        self.reject(lambda d: d["metrics"].update(n_observations=510))

    def test_modified_criterion_refused(self):
        self.reject(lambda d: d["criteria"].update(K1_false_self_on_world_le_5pct=False))

    def test_false_verdict_refused(self):
        self.reject(lambda d: d.update(verdict="Z12A_SELF_WORLD_REAL_FAIL"))

    def test_changed_seed_refused(self):
        self.reject(lambda d: d["runs"][1].update(seed=999))

    def test_missing_world_log_refused(self):
        self.reject(lambda d: d["runs"][0]["world_log"].pop())

    def test_missing_observation_refused(self):
        self.reject(lambda d: d["runs"][0]["observations"].pop())

    def test_nonfinite_time_refused(self):
        self.reject(lambda d: d["runs"][0]["observations"][0]["obs"].update(t=float("nan")))

    def test_phone_claim_refused(self):
        self.reject(lambda d: d.update(phone_measured=True))

    def test_wrong_episode_balance_refused(self):
        self.reject(lambda d: d["runs"][0]["kinds"].__setitem__(0, "own" if d["runs"][0]["kinds"][0] != "own" else "world"))


if __name__ == "__main__":
    unittest.main()
