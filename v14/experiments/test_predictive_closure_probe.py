import unittest

from predictive_closure_probe import (
    binary_entropy_bits,
    empirical_mutual_information_bits,
    evaluate_light_control,
    run_probe,
    simulate_light_control,
)


class PredictiveClosureProbeTests(unittest.TestCase):
    def test_independent_light_has_zero_self_prediction_at_every_q(self):
        for q in (0.0, 0.25, 0.5, 0.75, 1.0):
            self.assertEqual(
                evaluate_light_control(q)["light_self_predictive_information_bits"],
                0.0,
            )

    def test_partner_information_is_zero_without_control(self):
        result = evaluate_light_control(0.0)
        self.assertAlmostEqual(result["partner_prediction_information_bits"], 0.0)
        self.assertFalse(result["set_level_partner_signal_available"])

    def test_partner_information_reaches_one_bit_at_deterministic_control(self):
        result = evaluate_light_control(1.0)
        self.assertAlmostEqual(result["partner_prediction_information_bits"], 1.0)
        self.assertEqual(result["light_identifies_replaced_position_probability"], 1.0)

    def test_partner_information_increases_monotonically_with_q(self):
        values = [
            evaluate_light_control(q)["partner_prediction_information_bits"]
            for q in (0.0, 0.25, 0.5, 0.75, 1.0)
        ]
        self.assertEqual(values, sorted(values))
        self.assertGreater(values[-1], values[0])

    def test_light_entropy_cost_is_constant_and_reported_separately(self):
        for q in (0.0, 0.25, 0.5, 0.75, 1.0):
            self.assertEqual(evaluate_light_control(q)["light_entropy_cost_bits"], 1.0)

    def test_binary_entropy_boundaries_and_midpoint(self):
        self.assertEqual(binary_entropy_bits(0.0), 0.0)
        self.assertEqual(binary_entropy_bits(1.0), 0.0)
        self.assertAlmostEqual(binary_entropy_bits(0.5), 1.0)

    def test_rejects_invalid_probabilities(self):
        for bad in (-0.01, 1.01, float("nan"), float("inf"), True, "0.5"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    evaluate_light_control(bad)
        for bad in (-0.01, 1.01, float("nan"), True):
            with self.subTest(entropy_bad=bad):
                with self.assertRaises(ValueError):
                    binary_entropy_bits(bad)

    def test_seeded_simulation_matches_exact_partner_information(self):
        result = simulate_light_control(0.75, samples=200_000, seed=17)
        self.assertAlmostEqual(
            result["partner_information_bits_empirical"],
            evaluate_light_control(0.75)["partner_prediction_information_bits"],
            delta=0.01,
        )
        self.assertLess(result["light_self_information_bits_empirical"], 0.01)

    def test_empirical_mutual_information_rejects_empty_or_nonbinary_data(self):
        with self.assertRaises(ValueError):
            empirical_mutual_information_bits(())
        with self.assertRaises(ValueError):
            empirical_mutual_information_bits(((0, 2),))

    def test_report_labels_it_as_non_runtime_synthetic_evidence(self):
        result = run_probe()
        self.assertEqual(
            result["evidence_class"], "SYNTHETIC_ANALYTIC_INFORMATION_THEORY_ONLY"
        )
        self.assertFalse(result["trained_jepa"])
        self.assertFalse(result["runtime_integrated"])
        self.assertEqual(len(result["rows"]), 5)

    def test_rejects_empty_sweep(self):
        with self.assertRaises(ValueError):
            run_probe(())


if __name__ == "__main__":
    unittest.main()
