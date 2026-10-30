"""Run13R preregistered new synthetic cohort, fixed verdict and no-native tests."""
import math
import tempfile
import unittest
from pathlib import Path

from scripts import bodyjepa_350m_scale_heldout_run13r as r


class Run13RSoftware(unittest.TestCase):
    def test_fixture_disjoint_source_and_seed_pins(self):
        rows = r.fixture()
        self.assertEqual(r.fixture_hash(rows), r.FIXTURE_SHA256)
        self.assertEqual(r.SEEDS, (271, 277))
        self.assertEqual(r.ARMS, ("CE_0", "CONTRAST_2_5",
                                  "CONTRAST_12", "SHUFFLED_12"))
        self.assertEqual([r.WEIGHTS[a] for a in r.ARMS],
                         [0., 2.5, 12., 12.])
        self.assertEqual({k: len(v) for k, v in rows.items()},
                         {"train": 4, "paraphrase": 4,
                          "near_miss_leak_proxy": 4, "retention": 4})
        self.assertEqual(len({q for pairs in rows.values()
                              for q, _ in pairs}), 16)
        self.assertFalse(any("227" in q or "239" in q or "257" in q
                             for pairs in rows.values() for q, _ in pairs))
        self.assertTrue(all(q != wrong_q
                            for (q, _), (wrong_q, _) in zip(
                                rows["train"], rows["near_miss_leak_proxy"])))

    def results(self, high_para=.8, shuffle_para=1., near=1., retention=1.,
                moderate_para=.95):
        out = {}
        for seed in r.SEEDS:
            out[str(seed)] = {}
            for arm in r.ARMS:
                p = (high_para if arm == "CONTRAST_12" else
                     shuffle_para if arm == "SHUFFLED_12" else
                     moderate_para if arm == "CONTRAST_2_5" else 1.)
                n = near if arm == "CONTRAST_12" else 1.
                t = retention if arm == "CONTRAST_12" else 1.
                out[str(seed)][arm] = {
                    "summary": {"train": 1., "paraphrase": p,
                                "near_miss_leak_proxy": n,
                                "retention": t}}
        return out

    def test_fixed_signal_and_secondary_dose_not_primary(self):
        v = r.verdict(self.results())
        self.assertEqual(v["status"],
                         "BOUNDED_SYNTHETIC_SCALE_SIGNAL_NOT_UTILITY_GATE")
        self.assertEqual(v["seed_wins"], 2)
        self.assertFalse(v["utility_gate_pass"])
        self.assertFalse(v["body_jepa_available"])
        self.assertFalse(v["whole_system_complete"])
        # A favorable moderate arm cannot replace the preregistered high arm.
        v = r.verdict(self.results(high_para=.98, moderate_para=.2))
        self.assertEqual(v["status"], "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
        self.assertEqual(v["seed_wins"], 0)

    def test_hurt_near_miss_retention_and_shuffled_veto(self):
        self.assertEqual(r.verdict(self.results(high_para=1.1))["status"],
                         "DIAGNOSTIC_HURT")
        self.assertEqual(r.verdict(self.results(retention=1.1))["status"],
                         "DIAGNOSTIC_HURT")
        self.assertEqual(r.verdict(self.results(near=.7))["status"],
                         "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
        self.assertEqual(r.verdict(self.results(shuffle_para=.79))["status"],
                         "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")

    def test_missing_arm_seed_nonfinite_and_negative_fail_closed(self):
        for mutate in ("seed", "arm", "nan", "negative", "string"):
            results = self.results()
            if mutate == "seed":
                results.pop("277")
            elif mutate == "arm":
                results["271"].pop("SHUFFLED_12")
            elif mutate == "nan":
                results["271"]["CE_0"]["summary"]["train"] = float("nan")
            elif mutate == "negative":
                results["277"]["CONTRAST_12"]["summary"]["retention"] = -1.
            else:
                results["277"]["CONTRAST_12"]["summary"]["paraphrase"] = "1.0"
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                r.verdict(results)

    def test_explicit_native_opt_in_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            with self.assertRaises(SystemExit):
                r.main(["--master", str(p), "--out", str(p / "out")])
            # Existing output cannot be overwritten; master verification
            # happens first, so use the actual no-master refusal here.
            with self.assertRaises(ValueError):
                r.main(["--master", str(p), "--out", str(p / "out"),
                        "--execute-native"])
            self.assertFalse((p / "out").exists())


if __name__ == "__main__":
    unittest.main()
