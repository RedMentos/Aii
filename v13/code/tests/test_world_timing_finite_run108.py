"""Run108: real SQLite, synthetic timing only; no native/Redmi claim."""
import json
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime


class WorldTimingFiniteRun108(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.s = self.r.store

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def sample(self, duration=2., text='Timing baseline'):
        e = self.s.event(self.r.session, text)
        forecast = self.r.world.forecast(e, 'SOURCE_COPY', native_prediction=False)
        aid = self.s.start_action(e['event_id'], self.s.generation_id, forecast=forecast)
        self.s.finish_action(aid, 'FINAL', {'role': 'SOURCE_COPY', 'action_duration_s': duration})
        return aid

    def mutate(self, aid, field, value):
        assert field in ('expected', 'outcome')
        with self.s.tx() as c:
            c.execute('UPDATE actions SET ' + field + '=? WHERE id=?', (value, aid))

    def forecast(self):
        e = self.s.event(self.r.session, 'Timing baseline')
        return self.r.world.forecast(e, 'SOURCE_COPY', native_prediction=False)

    def test_negative_and_boolean_durations_do_not_count_as_measurements(self):
        good = [self.sample(2.), self.sample(3.)]
        self.sample(-100.)
        flag = self.sample(1.)
        self.mutate(flag, 'outcome', '{"role":"SOURCE_COPY","action_duration_s":true}')
        good.append(self.sample(4.))
        f = self.forecast()
        self.assertEqual(f['sample_count'], 3)
        self.assertEqual(set(f['sample_action_ids']), set(good))
        self.assertEqual(f['duration_median_s'], 3.)
        self.assertEqual(f['observed_range_s'], [2., 4.])

    def test_nonfinite_nan_and_infinity_durations_fail_closed(self):
        good = [self.sample(2.), self.sample(3.), self.sample(4.)]
        nan = self.sample(1.)
        inf = self.sample(1.)
        self.mutate(nan, 'outcome', '{"role":"SOURCE_COPY","action_duration_s":NaN}')
        self.mutate(inf, 'outcome', '{"role":"SOURCE_COPY","action_duration_s":Infinity}')
        f = self.forecast()
        self.assertEqual(f['sample_count'], 3)
        self.assertEqual(set(f['sample_action_ids']), set(good))
        self.assertEqual(f['duration_median_s'], 3.)

    def test_malformed_expected_and_outcome_are_skipped_not_crashes(self):
        good = [self.sample(2.), self.sample(3.), self.sample(4.)]
        bad_expected = self.sample(9.)
        bad_outcome = self.sample(9.)
        self.mutate(bad_expected, 'expected', '{malformed')
        self.mutate(bad_outcome, 'outcome', '{malformed')
        f = self.forecast()
        self.assertEqual(set(f['sample_action_ids']), set(good))
        self.assertEqual(f['sample_count'], 3)

    def test_invalid_historical_input_lengths_are_not_coverage_evidence(self):
        good = [self.sample(2.), self.sample(3.), self.sample(4.)]
        for bad in (-3, True, float('nan'), None):
            aid = self.sample(9.)
            row = self.s.one('SELECT expected FROM actions WHERE id=?', (aid,))
            expected = json.loads(row['expected'])
            expected['forecast']['input_chars'] = bad
            self.mutate(aid, 'expected', json.dumps(expected, allow_nan=True))
        f = self.forecast()
        self.assertEqual(f['sample_count'], 3)
        self.assertEqual(set(f['sample_action_ids']), set(good))
        self.assertTrue(f['covered'])
        self.assertEqual(f['duration_median_s'], 3.)

    def test_valid_three_samples_and_restart_unchanged(self):
        ids = [self.sample(2.), self.sample(3.), self.sample(4.)]
        f = self.forecast()
        self.assertEqual(f['sample_count'], 3)
        self.assertEqual(set(f['sample_action_ids']), set(ids))
        self.assertEqual(f['duration_median_s'], 3.)
        self.assertEqual(f['observed_range_s'], [2., 4.])
        self.r.close()
        self.r = Runtime(self.home)
        self.s = self.r.store
        after = self.forecast()
        self.assertEqual(after['duration_median_s'], 3.)
        self.assertEqual(set(after['sample_action_ids']), set(ids))


if __name__ == '__main__':
    unittest.main()
