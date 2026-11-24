"""Preregistered v3 counterbalanced nine-task native pilot source-only guards."""
import unittest

from scripts import step2_budget_paired_native_v3_20261030 as v3


class PairedNativeV3Software(unittest.TestCase):
    def test_frozen_seed_fixture_hash_and_disjoint_names(self):
        self.assertEqual(v3.SEED, 41)
        self.assertEqual(v3.SCHEMA, "v13.step2.budget_paired_native_pilot.v3")
        self.assertEqual(v3.fixture_hash(),
                         "fe9b86fdf561778ad540dd4767111f04c10a147a8a44cf783fa16f0d2c8a45ca")
        self.assertEqual(len(v3.FIXTURES), 9)
        self.assertTrue(v3.validate_fixtures())
        names = {f["project"] for f in v3.FIXTURES}
        self.assertEqual(len(names), 9)
        self.assertFalse(names & {"Solace", "Tundra", "Harbor", "Atlas",
                                  "Vega", "Lyra", "Nadir", "Orion"})

    def test_latin_square_balances_all_positions_and_rows(self):
        self.assertEqual(len(v3.ARM_ORDER), 3)
        self.assertTrue(all(set(order) == set(v3.ARMS) for order in v3.ARM_ORDER))
        ordered = [v3.ARM_ORDER[i % 3] for i in range(len(v3.FIXTURES))]
        for arm in v3.ARMS:
            for position in range(3):
                self.assertEqual(sum(order[position] == arm for order in ordered), 3)
        self.assertEqual(sum(len(order) for order in ordered), 27)

    def test_all_expected_remainders_and_cost_echo_not_credited(self):
        for fixture in v3.FIXTURES:
            a = fixture["budget"] - fixture["a_cost"]
            b = fixture["budget"] - fixture["b_cost"]
            answer = (f'Option {fixture["a"]} leaves {a} Euro; '
                      f'Option {fixture["b"]} leaves {b} Euro.')
            score = v3.score_pair(fixture, answer)
            self.assertEqual(score["correct"], 2, fixture["project"])
            self.assertTrue(score["a"])
            self.assertTrue(score["b"])
            bare = (f'Option {fixture["a"]} costs {fixture["a_cost"]} Euro. '
                    f'Option {fixture["b"]} costs {fixture["b_cost"]} Euro.')
            self.assertEqual(v3.score_pair(fixture, bare)["correct"], 0)

    def test_contradiction_veto_and_swapped_values(self):
        f = v3.FIXTURES[0]
        a, b = f["budget"] - f["a_cost"], f["budget"] - f["b_cost"]
        contradiction = (f'Option {f["a"]} leaves {a} Euro. '
                         f'Option {f["a"]} leaves {a+1} Euro. '
                         f'Option {f["b"]} leaves {b} Euro.')
        score = v3.score_pair(f, contradiction)
        self.assertFalse(score["a"])
        self.assertTrue(score["b"])
        swapped = (f'Option {f["a"]} leaves {b} Euro. '
                   f'Option {f["b"]} leaves {a} Euro.')
        self.assertEqual(v3.score_pair(f, swapped)["correct"], 0)

    def test_native_c2_not_inferred_from_route_override(self):
        self.assertTrue(v3.route_evidence(
            {"route": {"source": "OPERATOR_ROUTE_OVERRIDE"},
             "c2_packet": {"route": "both"}}, v3.ARMS[1]))
        self.assertFalse(v3.route_evidence(
            {"route": {"source": "NATIVE_NEEDLE"},
             "c2_packet": {"route": "both"}}, v3.ARMS[1]))
        self.assertFalse(v3.route_evidence(
            {"route": {"source": "OPERATOR_ROUTE_OVERRIDE"},
             "c2_packet": {"route": "simple"}}, v3.ARMS[2]))

    def test_pilot_signal_is_bounded_and_not_a_gate(self):
        a, b, c = v3.ARMS
        self.assertTrue(v3.pilot_signal({a: 7, b: 9, c: 12}, True))
        self.assertFalse(v3.pilot_signal({a: 7, b: 9, c: 11}, True))
        self.assertFalse(v3.pilot_signal({a: 7, b: 9, c: 12}, False))
        self.assertFalse(v3.pilot_signal({a: 7, b: 9, c: 19}, True))
        self.assertFalse(v3.pilot_signal({a: 7, b: 9, c: 12.0}, True))
        self.assertFalse(v3.pilot_signal({a: 7, b: 9}, True))


if __name__ == "__main__":
    unittest.main()
