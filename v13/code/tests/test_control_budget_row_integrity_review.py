"""Review-only persisted WP-T14 control latency row integrity; synthetic store only."""
import json
import math
import unittest
from v13 import control_budget as cb

VALID_MARKS = {'ingress': 0., 'routing': .2, 'finished': 1.}


class _Store:
    def __init__(self, rows):
        self._rows = rows

    def rows(self, sql, args=()):
        return self._rows


def _row(metadata, created):
    return {'metadata': metadata, 'created': created}


def _valid():
    return _row(json.dumps({'stage_marks_s': VALID_MARKS}), 100.)


class ControlRowIntegrityReview(unittest.TestCase):
    def test_valid_json_wrong_container_excluded(self):
        for bad in ('null', '[]', '"bad"', '0', 'true'):
            with self.subTest(bad=bad):
                report = cb.latency(_Store([_row(bad, 10.), _valid()]))
                self.assertEqual(report['turns'], 1)
                self.assertEqual(report['control_p95_ms'], 1000.)
                self.assertIsNone(report['turns_per_hour'])

    def test_invalid_created_excluded_before_latency_accounting(self):
        for bad in (None, 'bad', True, float('nan'), float('inf'),
                    -float('inf'), -1.):
            with self.subTest(bad=repr(bad)):
                rows = [_row(json.dumps({'stage_marks_s': VALID_MARKS}), bad), _valid()]
                report = cb.latency(_Store(rows))
                self.assertEqual(report['turns'], 1)
                self.assertEqual(report['control_p95_ms'], 1000.)
                self.assertIsNone(report['turns_per_hour'])
                json.dumps(report, allow_nan=False)

    def test_valid_two_rows_still_report_finite_rate(self):
        rows = [_valid(), _row(json.dumps({'stage_marks_s': VALID_MARKS}), 110.)]
        report = cb.latency(_Store(rows))
        self.assertEqual(report['turns'], 2)
        self.assertEqual(report['control_p95_ms'], 1000.)
        self.assertTrue(math.isfinite(report['turns_per_hour']))
        self.assertEqual(report['inline_observer_rate'], 0.)


if __name__ == '__main__':
    unittest.main()
