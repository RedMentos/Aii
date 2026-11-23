"""Fixed paired STEP2 pilot fixture/scorer software tests, no native models."""
import unittest

from scripts.step2_budget_paired_native_v2_20261030 import (
    ARMS, B1_CANDIDATE, B2_CANDIDATE, FIXTURES,
    fixture_hash, prompt, score_pair, validate_fixtures, route_evidence, FIXTURE_SHA256, SEED,
)


class PairedNativeBudgetPilot(unittest.TestCase):
    def test_fixed_disjoint_fixtures_and_no_answer_leak(self):
        self.assertTrue(validate_fixtures())
        self.assertEqual(len(FIXTURES), 4)
        self.assertEqual(len(ARMS), 3)
        self.assertEqual(fixture_hash(), FIXTURE_SHA256)
        self.assertEqual(SEED, 29)
        self.assertNotIn("55 Euro", B1_CANDIDATE)
        self.assertNotIn("18 Euro", B2_CANDIDATE)
        for f in FIXTURES:
            with self.subTest(project=f["project"]):
                q = prompt(f)
                self.assertIn(f["project"], q)
                self.assertIn("local, no cloud", q)
                self.assertIn("remaining budget", q)

    def test_correct_remainders_score_two_per_fixture(self):
        for f in FIXTURES:
            with self.subTest(project=f["project"]):
                ra = f["budget"] - f["a_cost"]
                rb = f["budget"] - f["b_cost"]
                answer = (f"{f['a']} has {ra} Euro left; "
                          f"{f['b']} has {rb} Euro remaining.")
                self.assertEqual(score_pair(f, answer)["correct"], 2)

    def test_swapped_and_cost_echo_not_credited(self):
        for f in FIXTURES:
            with self.subTest(project=f["project"]):
                ra = f["budget"] - f["a_cost"]
                rb = f["budget"] - f["b_cost"]
                swapped = (f"{f['a']} has {rb} Euro left; "
                           f"{f['b']} has {ra} Euro left.")
                echoed = (f"{f['a']} costs {f['a_cost']} Euro; "
                          f"{f['b']} costs {f['b_cost']} Euro.")
                self.assertEqual(score_pair(f, swapped)["correct"], 0)
                self.assertEqual(score_pair(f, echoed)["correct"], 0)

    def test_leaves_and_contradiction_veto(self):
        f = FIXTURES[0]
        a = f["budget"] - f["a_cost"]
        b = f["budget"] - f["b_cost"]
        good = f'{f["a"]} leaves {a} Euro; {f["b"]} leaves {b} Euro.'
        self.assertEqual(score_pair(f, good)["correct"], 2)
        contradiction = (
            f'{f["a"]} leaves {a} Euro; {f["a"]} has 999 Euro remaining. '
            f'{f["b"]} leaves {b} Euro.')
        result = score_pair(f, contradiction)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["diagnostic"]["a"]["status"], "CONTRADICTORY")

    def test_route_override_evidence_not_c2_native_promotion(self):
        for arm in ARMS:
            packet_route = "simple" if arm == ARMS[0] else "both"
            meta = {"route": {"source": "OPERATOR_ROUTE_OVERRIDE"},
                    "c2_packet": {"route": packet_route}}
            self.assertTrue(route_evidence(meta, arm))
            self.assertFalse(route_evidence(
                {**meta, "c2_packet": {"route": "invalid"}}, arm))
            self.assertFalse(route_evidence(
                {**meta, "route": {"native_control": {}}}, arm))
            self.assertFalse(route_evidence(
                {**meta, "c2_packet": {}}, arm))

    def test_one_correct_is_not_two(self):
        f = FIXTURES[0]
        answer = f"{f['a']} has 55 Euro left. {f['b']} costs 149 Euro."
        self.assertEqual(score_pair(f, answer)["correct"], 1)


if __name__ == "__main__":
    unittest.main()
