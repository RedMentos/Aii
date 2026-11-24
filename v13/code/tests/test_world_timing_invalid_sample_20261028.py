"""World/Self timing evidence refuses boolean, negative and nonfinite durations."""
import json
import tempfile
from pathlib import Path
import unittest

from v13.runtime import Runtime
from v13.world import _valid_duration


class WorldTimingIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def action(self, duration, text='Timing sample'):
        r = self.r
        e = r.store.event(r.session, text)
        forecast = r.world.forecast(e, 'C3_LANGUAGE', native_prediction=False)
        aid = r.store.start_action(e['event_id'], r.store.generation_id, forecast=forecast)
        r.store.finish_action(aid, 'FINAL', {'action_duration_s': duration, 'role': 'C3_LANGUAGE'})
        observation = r.world.observe(aid)
        return e, forecast, aid, observation

    def test_valid_duration_rejects_bool_negative_nonfinite_and_huge_int(self):
        for bad in (True, False, -1, -0.01, float('nan'), float('inf'),
                    -float('inf'), 10**1000, None, '2'):
            with self.subTest(value=str(bad)[:30]):
                self.assertFalse(_valid_duration(bad))
        for good in (0, 0., 2, 2.5):
            self.assertTrue(_valid_duration(good))

    def test_invalid_completed_samples_never_influence_supported_median(self):
        self.action(-1)
        self.action(True)
        for value in (2., 3., 4.):
            self.action(value)
        e = self.r.store.event(self.r.session, 'Timing sample')
        f = self.r.world.forecast(e, 'C3_LANGUAGE', native_prediction=False)
        self.assertEqual(f['sample_count'], 3)
        self.assertEqual(f['invalid_timing_sample_count'], 2)
        self.assertEqual(f['duration_median_s'], 3.)
        self.assertEqual(f['observed_range_s'], [2., 4.])
        self.assertEqual(f['failed_action_count'], 0)

    def test_invalid_current_observation_is_unscored_not_silent_success(self):
        for value in (2., 3., 4.):
            self.action(value)
        for bad in (-1, True):
            _, forecast, _, outcome = self.action(bad)
            self.assertEqual(forecast['duration_median_s'], 3.)
            self.assertFalse(outcome['scored'])
            self.assertIsNone(outcome['timing_error_s'])
            self.assertIsNone(outcome['semantic_success'])
            self.assertEqual(outcome['observed']['action_duration_s'], bad)
        _, f, _, outcome = self.action(5.)
        self.assertEqual(f['invalid_timing_sample_count'], 2)
        self.assertEqual(outcome['timing_error_s'], 2.)
        self.assertTrue(outcome['scored'])

    def test_corrupt_expected_input_length_does_not_count_as_timing_support(self):
        _, _, aid, _ = self.action(2.)
        action = self.r.store.one('SELECT expected FROM actions WHERE id=?', (aid,))
        expected = json.loads(action['expected'])
        expected['forecast']['input_chars'] = True
        from v13.common import dumps
        with self.r.store.tx() as db:
            db.execute('UPDATE actions SET expected=? WHERE id=?', (dumps(expected), aid))
        e = self.r.store.event(self.r.session, 'Timing sample')
        f = self.r.world.forecast(e, 'C3_LANGUAGE', native_prediction=False)
        self.assertEqual(f['sample_count'], 0)
        self.assertEqual(f['invalid_timing_sample_count'], 1)
        self.assertIsNone(f['duration_median_s'])


if __name__ == '__main__':
    unittest.main()
