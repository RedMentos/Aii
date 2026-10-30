"""Run14A preregistered disjoint moderate Body-JEPA dose software-only tests."""
import tempfile
import unittest
from pathlib import Path

from scripts import bodyjepa_350m_moderate_heldout_run14a as r
from scripts import bodyjepa_350m_scale_heldout_run13r as frozen


class Run14AModerateSoftware(unittest.TestCase):
    def test_new_fixture_seed_arms_and_original_cohort_frozen(self):
        rows = r.fixture()
        self.assertEqual(r.fixture_hash(rows), r.FIXTURE_SHA256)
        self.assertEqual(r.FIXTURE_SHA256,
                         "0a376a829dfca1679df783d8e580004c193a534d18dc8f56a5bc4f7fc7181a09")
        self.assertEqual(r.SEEDS, (291, 293))
        self.assertEqual(r.ARMS, ("CE_0", "CONTRAST_2_5", "SHUFFLED_2_5"))
        self.assertEqual([r.WEIGHTS[a] for a in r.ARMS], [0., 2.5, 2.5])
        self.assertEqual(len(r.SEEDS) * len(r.ARMS), 6)
        self.assertEqual({k: len(v) for k, v in rows.items()},
                         {"train": 4, "paraphrase": 4,
                          "near_miss_leak_proxy": 4, "retention": 4})
        questions = {q for pairs in rows.values() for q, _ in pairs}
        self.assertEqual(len(questions), 16)
        self.assertFalse(any("271" in q or "277" in q or "257" in q
                             for q in questions))
        self.assertEqual(frozen.SEEDS, (271, 277))
        self.assertEqual(frozen.fixture_hash(frozen.fixture()),
                         frozen.FIXTURE_SHA256)
        self.assertNotEqual(frozen.FIXTURE_SHA256, r.FIXTURE_SHA256)
        self.assertEqual(r.LICENSE_SHA256, frozen.LICENSE_SHA256)

    def results(self, moderate=.8, shuffled=1., near=1., retention=1.):
        out = {}
        for seed in r.SEEDS:
            out[str(seed)] = {}
            for arm in r.ARMS:
                p = moderate if arm == "CONTRAST_2_5" else (
                    shuffled if arm == "SHUFFLED_2_5" else 1.)
                n = near if arm == "CONTRAST_2_5" else 1.
                t = retention if arm == "CONTRAST_2_5" else 1.
                out[str(seed)][arm] = {
                    "summary": {"train": 1., "paraphrase": p,
                                "near_miss_leak_proxy": n, "retention": t}}
        return out

    def test_precommitted_moderate_signal_never_promotes(self):
        v = r.verdict(self.results())
        self.assertEqual(v["status"],
                         "BOUNDED_MODERATE_SYNTHETIC_SIGNAL_NOT_UTILITY_GATE")
        self.assertEqual(v["seed_wins"], 2)
        self.assertFalse(v["utility_gate_pass"])
        self.assertFalse(v["body_jepa_available"])
        self.assertFalse(v["redmi_measured"])
        self.assertFalse(v["whole_system_complete"])

    def test_hurt_retention_near_miss_and_shuffled_veto(self):
        self.assertEqual(r.verdict(self.results(moderate=1.1))["status"],
                         "DIAGNOSTIC_HURT")
        self.assertEqual(r.verdict(self.results(retention=1.1))["status"],
                         "DIAGNOSTIC_HURT")
        self.assertEqual(r.verdict(self.results(near=.7))["status"],
                         "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
        self.assertEqual(r.verdict(self.results(shuffled=.79))["status"],
                         "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
        self.assertEqual(r.verdict(self.results(moderate=.98))["status"],
                         "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")

    def test_missing_arm_seed_nonfinite_negative_and_string_fail_closed(self):
        for mutate in ("seed", "arm", "nan", "negative", "string"):
            results = self.results()
            if mutate == "seed":
                results.pop("293")
            elif mutate == "arm":
                results["291"].pop("SHUFFLED_2_5")
            elif mutate == "nan":
                results["291"]["CE_0"]["summary"]["train"] = float("nan")
            elif mutate == "negative":
                results["293"]["CONTRAST_2_5"]["summary"]["retention"] = -1.
            else:
                results["293"]["CONTRAST_2_5"]["summary"]["paraphrase"] = "1.0"
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                r.verdict(results)

    def test_native_opt_in_and_no_master_refuse_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            with self.assertRaises(SystemExit):
                r.main(["--master", str(p), "--out", str(p / "out")])
            with self.assertRaises(ValueError):
                r.main(["--master", str(p), "--out", str(p / "out"),
                        "--execute-native"])
            self.assertFalse((p / "out").exists())


if __name__ == "__main__":
    unittest.main()
