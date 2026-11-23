"""RED-first four-arm causal-control identity tests; synthetic only, no native proof."""
import unittest

from scripts.step2_longnote_fourarm_analysis import ARMS, SEEDS, analyze
from tests.test_step2_longnote_fourarm_analysis_20261028 import IDS, fixture


class CrossArmB1Identity(unittest.TestCase):
    def test_original_paired_fixture_remains_accepted(self):
        report = analyze(fixture(), IDS)
        self.assertTrue(report['candidate_supported'])
        self.assertFalse(report['canonical_gate_pass'])
        self.assertEqual(report['jepa_weight'], 0)

    def test_shared_body_arms_cannot_swap_b1_for_all_seeds(self):
        rows = fixture()
        for row in rows:
            if row['arm'] in ('SC', 'SP'):
                row['model_sha256']['B1_DETAIL'] = 'e' * 64
                row['model_sha256']['B2_GIST'] = 'e' * 64
        self.assertEqual(len(rows), len(ARMS) * len(SEEDS))
        with self.assertRaisesRegex(ValueError, 'B1.*across.*arm'):
            analyze(rows, IDS)

    def test_distinct_body_arms_cannot_swap_b1_for_all_seeds(self):
        rows = fixture()
        for row in rows:
            if row['arm'] in ('TC', 'TP'):
                row['model_sha256']['B1_DETAIL'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'B1.*across.*arm'):
            analyze(rows, IDS)


if __name__ == '__main__':
    unittest.main()
