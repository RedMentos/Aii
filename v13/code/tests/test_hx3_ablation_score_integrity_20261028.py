"""HX3 evaluator score integrity: preregistered synthetic adversarial checks.

Software only. No native, learning, Redmi, age, or gate promotion.
"""
import unittest

from v13.agi.experience import ablation


class FakeLibrary:
    def lookup(self, task_type, k=3, enabled=True):
        return ['lesson'] if enabled else []


class HX3ScoreIntegrity(unittest.TestCase):
    def setUp(self):
        self.lib = FakeLibrary()
        self.tasks = [{'task_type': 'list_arith'}]

    def run_scores(self, on, off):
        return ablation(
            self.tasks,
            lambda task, lessons: on if lessons else off,
            self.lib,
        )

    def test_nonfinite_or_out_of_range_scores_refused_on_both_arms(self):
        invalid = [float('nan'), float('inf'), -float('inf'), -0.01, 1.01]
        for bad in invalid:
            for side in ('with', 'without'):
                with self.subTest(bad=repr(bad), side=side):
                    with self.assertRaises(ValueError):
                        self.run_scores(bad, 0.5) if side == 'with' else self.run_scores(0.5, bad)

    def test_boolean_and_numeric_text_are_not_measured_scores(self):
        for bad in (True, False, '0.7', '1'):
            for side in ('with', 'without'):
                with self.subTest(bad=repr(bad), side=side):
                    with self.assertRaises(ValueError):
                        self.run_scores(bad, 0.5) if side == 'with' else self.run_scores(0.5, bad)

    def test_valid_endpoints_and_ordinary_delta_unchanged(self):
        row = self.run_scores(1, 0)
        self.assertEqual((row['n'], row['with'], row['without'], row['mean_delta'], row['worse']), (1, 1, 0, 1, 0))
        row = self.run_scores(0.5, 0.8)
        self.assertEqual((row['n'], row['mean_delta'], row['worse']), (1, -0.3, 1))
        self.assertEqual(row['rows'][0]['delta'], -0.3)

    def test_empty_tasks_still_report_no_evidence(self):
        out = ablation([], lambda *_: self.fail('solver should not be called'), self.lib)
        self.assertEqual((out['n'], out['mean_delta'], out['rows']), (0, 0, []))


if __name__ == '__main__':
    unittest.main()
