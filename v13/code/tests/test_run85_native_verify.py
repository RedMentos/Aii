"""Run85 verifier adversarial software tests; no native execution."""
import copy
import unittest

from scripts.run85_real_bodies_jef_c3_verify import verify
from scripts.run85_real_bodies_jef_c3_native import SCHEMA, MODELS
from scripts import jef_body_c3_interference_fixture_839 as f


class Run85VerifierTests(unittest.TestCase):
    def fixture(self):
        row = f.fixtures()[0]
        return {
            "schema": SCHEMA, "seed": f.SEED,
            "table_sha256": f.TABLE_SHA256, "fixture_index": 0,
            "project_sha256": f.sha(row["project"].encode()),
            "source_sha256": row["source_sha256"],
            "expected": row["expected"],
            "runner_sha256_required": f.RUNNER_SHA256,
            "runner_sha256_observed": f.RUNNER_SHA256,
            "models_required": {role: {"file": name, "sha256": digest}
                                for role, (name, digest) in MODELS.items()},
            "models_observed": {role: {"file": name, "sha256": digest}
                                for role, (name, digest) in MODELS.items()},
            "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "world_jepa": "SHADOW", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False,
            "delivery_authority": 0, "learning_authority": 0,
            "tool_dispatches": 0, "tty_approved": False,
            "output_committed": False, "independent_reasoning_proven": False,
            "native_body": False, "native_body_calls": 0,
            "native_c3_calls": 0, "no_live_output": False,
            "closed_store_ok": False, "body_offers": [], "c3": [],
        }

    def red(self, value):
        with self.assertRaises(ValueError):
            verify(value)

    def test_no_fake_native_completion(self):
        self.red(self.fixture())

    def test_wrong_source_hash_rejected(self):
        x = self.fixture()
        x["source_sha256"]["current"] = "0" * 64
        self.red(x)

    def test_model_pin_tamper_rejected(self):
        x = self.fixture()
        x["models_observed"]["B2_GIST"]["sha256"] = "0" * 64
        self.red(x)

    def test_authority_promotion_rejected(self):
        for key, value in (("step2", "PASS"),
                           ("jepa_weight", 0.01),
                           ("delivery_authority", 1),
                           ("whole_system_complete", True)):
            with self.subTest(key=key):
                x = self.fixture()
                x[key] = value
                self.red(x)

    def test_claiming_native_without_offers_rejected(self):
        x = self.fixture()
        x["native_body"] = True
        x["native_body_calls"] = 2
        x["native_c3_calls"] = 2
        x["no_live_output"] = True
        x["closed_store_ok"] = True
        self.red(x)

    def test_source_pin_immutable_across_test_objects(self):
        a = self.fixture()
        b = copy.deepcopy(a)
        b["source_sha256"]["current"] = "1" * 64
        self.assertNotEqual(a["source_sha256"], b["source_sha256"])


if __name__ == "__main__":
    unittest.main()
