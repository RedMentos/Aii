"""Independent W7D D3 prereg integrity tests; software/synthetic only."""
import copy
import unittest

from scripts import w7d_world_jepa_delta_inverse_real as w7d


def fixture(delta_ranks=(True, True, True), baseline_ranks=(False, False, False),
            pooled_baseline=.2, pooled_delta=-.3):
    def row(seed, inverted, delta_arm):
        # Confidences strictly ordered: no tie artefact in these fixtures.
        return {
            "seed": seed,
            "_conf_err": [[float(i), float(3-i if inverted else i)]
                          for i in range(4)],
            "attribution": {
                "jepa": {"balanced": .6 if delta_arm else .4},
                "no_action": {"balanced": .4},
            },
        }
    seeds = w7d.SEEDS
    baseline = [row(seed, inverted, False)
                for seed, inverted in zip(seeds, baseline_ranks)]
    delta = [row(seed, inverted, True)
             for seed, inverted in zip(seeds, delta_ranks)]
    return {
        "balanced_slot": baseline,
        "delta_slot": delta,
        "balanced_slot_w7_summary": {
            "per_seed": [{"none_self_gap": .2} for _ in seeds],
        },
        "delta_slot_w7_summary": {
            "per_seed": [{"none_self_gap": .3} for _ in seeds],
        },
        "balanced_slot_summary": {
            "spearman_conf_err_covered": pooled_baseline,
        },
        "delta_slot_summary": {
            "spearman_conf_err_covered": pooled_delta,
        },
    }


class W7DPerSeedD3Review(unittest.TestCase):
    def test_registered_per_seed_positive(self):
        r = w7d.delta_exploratory(fixture())
        self.assertTrue(r["D3_w4_rho_improvement"])
        self.assertEqual(r["per_seed_w4_rho_delta"], [-2., -2., -2.])
        self.assertEqual(r["mean_per_seed_w4_rho_delta"], -2.)
        self.assertTrue(r["D3_per_seed_rho_measured"])
        self.assertTrue(r["D1_w6_margin_improvement"])
        self.assertTrue(r["D2_w7b_none_improvement"])

    def test_pooled_pass_must_not_hide_single_seed_regression(self):
        # Two seeds improve by -2; third regresses by +2. Mean passes
        # but the original preregistered each-seed limit fails.
        r = w7d.delta_exploratory(fixture(
            delta_ranks=(True, True, False),
            baseline_ranks=(False, False, True)))
        self.assertEqual(r["per_seed_w4_rho_delta"], [-2., -2., 2.])
        self.assertLessEqual(r["mean_per_seed_w4_rho_delta"], -.05)
        self.assertTrue(r["pooled_w4_rho_improvement_diagnostic"])
        self.assertFalse(r["D3_w4_rho_improvement"])

    def test_per_seed_pass_independent_of_pooled_diagnostic(self):
        r = w7d.delta_exploratory(fixture(
            pooled_baseline=-.5, pooled_delta=.1))
        self.assertTrue(r["D3_w4_rho_improvement"])
        self.assertFalse(r["pooled_w4_rho_improvement_diagnostic"])

    def test_missing_pooled_rho_does_not_fabricate_pooled_success(self):
        r = w7d.delta_exploratory(fixture(
            pooled_baseline=None, pooled_delta=None))
        self.assertIsNone(r["pooled_w4_rho_delta"])
        self.assertFalse(r["pooled_w4_rho_improvement_diagnostic"])
        self.assertTrue(r["D3_w4_rho_improvement"])

    def test_swapped_seed_identity_refused(self):
        r = fixture()
        r["delta_slot"][0]["seed"] = 703
        with self.assertRaisesRegex(ValueError, "SEEDS|SEED_IDENTITY"):
            w7d.delta_exploratory(r)

    def test_missing_or_insufficient_covered_raw_refused(self):
        for bad in (None, [], [[0., 0.]]):
            with self.subTest(bad=bad):
                r = fixture()
                r["delta_slot"][1]["_conf_err"] = bad
                with self.assertRaisesRegex(ValueError, "COVERED_SUPPORT"):
                    w7d.delta_exploratory(r)

    def test_nonfinite_and_invalid_raw_refused(self):
        for bad in ([0., float("nan")], [float("inf"), 1.],
                    [True, 1.], [0.], "not-a-pair"):
            with self.subTest(bad=bad):
                r = fixture()
                r["balanced_slot"][0]["_conf_err"][0] = bad
                with self.assertRaisesRegex(ValueError, "RAW_PAIRS"):
                    w7d.delta_exploratory(r)

    def test_missing_raw_refused(self):
        r = fixture()
        del r["balanced_slot"][2]["_conf_err"]
        with self.assertRaisesRegex(ValueError, "COVERED_SUPPORT"):
            w7d.delta_exploratory(r)

    def test_input_not_mutated_and_d1_d2_stable(self):
        r = fixture()
        original = copy.deepcopy(r)
        d = w7d.delta_exploratory(r)
        self.assertEqual(r, original)
        self.assertEqual(d["per_seed_w6_margin_delta"], [.2, .2, .2])
        self.assertEqual(d["per_seed_w7b_none_gap_delta"], [.1, .1, .1])


if __name__ == "__main__":
    unittest.main()
