"""WP-T14 finite cumulative stage-mark RED: invalid timing evidence must abstain."""
import json
import math
import unittest
from v13 import control_budget as cb


class FiniteMarksReview(unittest.TestCase):
    def test_invalid_known_stage_mark_invalidates_entire_turn(self):
        for bad in (True, float('nan'), float('inf'), -float('inf'), -1., '0.2', None):
            with self.subTest(bad=repr(bad)):
                marks = {'ingress': 0., 'routing': bad, 'finished': 1.}
                self.assertEqual(cb.durations(marks), {})

    def test_invalid_container_fails_closed(self):
        for marks in (None, [], 'ingress', 42):
            with self.subTest(marks=repr(marks)):
                self.assertEqual(cb.durations(marks), {})

    def test_valid_finite_marks_preserve_durations(self):
        out = cb.durations({'ingress': 0., 'routing': .2, 'finished': 1.})
        self.assertAlmostEqual(out['ingress'], .2)
        self.assertAlmostEqual(out['routing'], .8)
        self.assertNotIn('finished', out)
        self.assertEqual(cb.durations({'unrelated': float('nan'), 'ingress': 0.,
                                       'finished': 1.}), {'ingress': 1.})

    def test_invalid_rows_excluded_from_latency_denominator(self):
        class Store:
            def rows(self, sql, args=()):
                return [
                    {'metadata': json.dumps({'stage_marks_s': {
                        'ingress': 0., 'routing': float('nan'), 'finished': 1.}}),
                     'created': 10.},
                    {'metadata': json.dumps({'stage_marks_s': {
                        'ingress': 0., 'routing': .2, 'finished': 1.}}),
                     'created': 20.},
                ]
        report = cb.latency(Store())
        self.assertEqual(report['turns'], 1)
        self.assertAlmostEqual(report['control_p95_ms'], 1000.)
        self.assertEqual(report['inline_observer_rate'], 0.)


if __name__ == '__main__':
    unittest.main()
