"""Run496 frozen held-out10 pilot source-only adversarial tests; no model inference."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run491_step2_heldout10 as F
import run496_heldout10_native_pilot as P


def reports():
    rows = [{"fixture": fid, "variant": v, "score": {"utility": 0.5}}
            for fid in P.PILOT_IDS for v in F.VARIANTS]
    tool = {"installed_artifacts_unchanged": True, "rows": rows}
    summary = {"run": "C_s31", "arm": "C", "seed": 31,
               "tool_status": "UTILITY_FAIL", "step2_status": "UTILITY_FAIL",
               "tool_summary": {v: {"wrong_committed": 0} for v in F.VARIANTS}}
    return tool, summary


class PilotSourceOnly(unittest.TestCase):
    def test_exact_full_fixture_hash_and_two_pilot_ids(self):
        r = P.pilot_registration()
        self.assertEqual(r["full_fixture_sha256"], F.FIXTURE_SHA256)
        self.assertEqual(r["pilot_ids"], ["Vesper", "Willow"])
        self.assertEqual((r["arm"], r["seed"], r["expected_rows"]), ("C", 31, 14))
        self.assertEqual(r["variants"], list(F.VARIANTS))
        self.assertIs(r["native_executed"], False)
        self.assertEqual(r["step2_exit"], "UTILITY_FAIL")
        self.assertEqual(r["jepa_weight"], 0)

    def test_in_memory_fixture_and_arm_configuration_restored(self):
        import step2_z2_timescale as z2
        import step2_z2b_seeds as z2b
        before_fixtures = z2.FIXTURES
        before_arms = copy.deepcopy(z2b.ARMS)
        before_seeds = z2b.SEEDS
        with P.pilot_modules():
            self.assertEqual([f["id"] for f in z2.FIXTURES], ["Vesper", "Willow"])
            self.assertEqual(set(z2b.ARMS), set(F.ARMS))
            self.assertEqual(z2b.ARMS["C"], {"base": "C", "query": False})
            self.assertEqual(z2b.SEEDS, F.SEEDS)
        self.assertIs(z2.FIXTURES, before_fixtures)
        self.assertEqual(z2b.ARMS, before_arms)
        self.assertEqual(z2b.SEEDS, before_seeds)

    def test_valid_structural_rows_do_not_promote_step2(self):
        tool, summary = reports()
        result = P.verify_rows(tool, summary)
        self.assertEqual(result["rows_verified"], 14)
        self.assertIs(result["canonical_gate_pass"], False)
        self.assertEqual(result["step2_exit"], "UTILITY_FAIL")

    def test_duplicate_or_missing_variant_fails(self):
        tool, summary = reports()
        tool["rows"][-1] = copy.deepcopy(tool["rows"][0])
        with self.assertRaisesRegex(ValueError, "NATIVE_PILOT_VARIANT_COVERAGE"):
            P.verify_rows(tool, summary)
        tool, summary = reports()
        tool["rows"].pop()
        with self.assertRaisesRegex(ValueError, "NATIVE_PILOT_ROW_COUNT"):
            P.verify_rows(tool, summary)

    def test_wrong_arm_seed_or_committed_tool_fails(self):
        for mutate, reason in [
            (lambda t,s: s.update(seed=32), "NATIVE_PILOT_IDENTITY_CHANGED"),
            (lambda t,s: s["tool_summary"]["both_exact"].update(wrong_committed=1),
             "NATIVE_PILOT_WRONG_COMMITTED"),
            (lambda t,s: t.update(installed_artifacts_unchanged=False),
             "INSTALLED_ARTIFACTS_CHANGED"),
            (lambda t,s: s.update(tool_status="STRUCTURAL_FAIL"),
             "NATIVE_PILOT_STRUCTURAL_FAIL"),
        ]:
            tool, summary = reports()
            mutate(tool, summary)
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                P.verify_rows(tool, summary)

    def test_nonfinite_and_out_of_range_utility_fail(self):
        for bad in [float("nan"), float("inf"), -0.1, 1.1, "0.5"]:
            tool, summary = reports()
            tool["rows"][0]["score"]["utility"] = bad
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "NATIVE_PILOT_UTILITY_INVALID"):
                P.verify_rows(tool, summary)

    def test_preregistration_write_is_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "RUN496_PILOT_PREREG.json"
            P.write_new(path, P.pilot_registration())
            self.assertEqual(json.loads(path.read_text())["pilot_ids"], ["Vesper", "Willow"])
            with self.assertRaises(FileExistsError):
                P.write_new(path, P.pilot_registration())

    def test_frozen_model_and_runner_hashes_are_unchanged(self):
        r = P.pilot_registration()
        self.assertEqual(r["model_sha256_expected_not_retrieved"], F.MODEL_SHA256)
        self.assertEqual(r["runner_sha256_expected_not_retrieved"], F.RUNNER_SHA256)


if __name__ == "__main__":
    unittest.main()
