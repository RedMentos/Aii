import json
from pathlib import Path
import unittest

from scripts.tool_forecast_learning_integrity_candidate import expected_grid

ROOT = Path(__file__).resolve().parents[1]


class RecoveredCohortPlan(unittest.TestCase):
    def test_new_shifted_states_are_disjoint_but_retention_repeat_is_explicit(self):
        old = json.loads((ROOT / 'specs/tool_forecast/learning-plan-20261016.json').read_text())
        new = json.loads((ROOT / 'specs/tool_forecast/learning-plan-20261016-evening.json').read_text())
        a, b = old['plan'], new['plan']
        self.assertEqual(len(expected_grid(new)), 610)
        self.assertEqual(new['gates'], old['gates'])
        self.assertEqual(new['mode'], 'region')
        for family in ('calc', 'note'):
            old_shift = set(a[family+'_shift_exp']) | set(a[family+'_shift_test'])
            new_shift = set(b[family+'_shift_exp']) | set(b[family+'_shift_test'])
            self.assertFalse(old_shift & new_shift)
            self.assertEqual(a[family+'_in_test'], b[family+'_in_test'])
        self.assertIn('repeat', new['retention_controls'].lower())
        self.assertIn('not a fresh retention cohort', new['claim_limit'])


if __name__ == '__main__':
    unittest.main()
