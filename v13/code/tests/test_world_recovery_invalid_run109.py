"""Run109: malformed durable World outcomes must not prevent Runtime restart."""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime


class WorldRecoveryInvalidRun109(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.s = self.r.store

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def action(self, duration=2.):
        e = self.s.event(self.r.session, 'World restart timing')
        f = self.r.world.forecast(e, 'SOURCE_COPY', native_prediction=False)
        aid = self.s.start_action(e['event_id'], self.s.generation_id, forecast=f)
        self.s.finish_action(aid, 'FINAL', {'role': 'SOURCE_COPY', 'action_duration_s': duration})
        return aid

    def change(self, aid, field, raw):
        assert field in ('expected', 'outcome')
        with self.s.tx() as c:
            c.execute('UPDATE actions SET ' + field + '=? WHERE id=?', (raw, aid))

    def restart(self):
        self.r.close()
        self.r = Runtime(self.home)
        self.s = self.r.store

    def outcomes(self, aid):
        return self.s.rows("SELECT payload FROM packets WHERE kind='PredictionOutcome' "
                           "AND json_extract(payload,'$.action_id')=?", (aid,))

    def test_nan_duration_does_not_brick_restart_or_create_observation(self):
        aid = self.action()
        self.change(aid, 'outcome', '{"role":"SOURCE_COPY","action_duration_s":NaN}')
        self.restart()
        self.assertEqual(self.outcomes(aid), [])
        self.assertEqual(self.r.world.world_state()['observed_action_count'], 0)

    def test_infinite_or_nested_nonfinite_outcome_refused(self):
        for raw in ('{"role":"SOURCE_COPY","action_duration_s":Infinity}',
                    '{"role":"SOURCE_COPY","action_duration_s":2.0,"debug":NaN}'):
            with self.subTest(raw=raw):
                aid = self.action()
                self.change(aid, 'outcome', raw)
                self.restart()
                self.assertEqual(self.outcomes(aid), [])

    def test_malformed_outcome_and_expected_do_not_brick_restart(self):
        a = self.action()
        b = self.action()
        self.change(a, 'outcome', '{malformed')
        self.change(b, 'expected', '{"forecast":not-json}')
        self.restart()
        self.assertEqual(self.outcomes(a), [])
        self.assertEqual(self.outcomes(b), [])

    def test_negative_and_boolean_duration_not_accepted_as_world_observation(self):
        a = self.action(-5.)
        b = self.action(True)
        self.restart()
        self.assertEqual(self.outcomes(a), [])
        self.assertEqual(self.outcomes(b), [])

    def test_invalid_first_row_does_not_block_valid_sibling_or_second_restart(self):
        invalid = self.action()
        self.change(invalid, 'outcome', '{"role":"SOURCE_COPY","action_duration_s":NaN}')
        valid = self.action(3.)
        self.restart()
        self.assertEqual(self.outcomes(invalid), [])
        self.assertEqual(len(self.outcomes(valid)), 1)
        self.assertEqual(self.r.world.world_state()['observed_action_count'], 1)
        self.restart()
        self.assertEqual(len(self.outcomes(valid)), 1)
        self.assertEqual(self.r.world.world_state()['observed_action_count'], 1)

    def test_valid_finite_prediction_error_and_authority_unchanged(self):
        for duration in (2., 3., 4.):
            self.action(duration)
        aid = self.action(5.)
        observed = self.r.world.observe(aid)
        self.assertTrue(observed['scored'])
        self.assertEqual(observed['timing_error_s'], 2.)
        self.assertTrue(observed['self_caused'])
        self.assertIsNone(observed['semantic_success'])
        self.assertFalse(observed['causal_claim'])
        self.restart()
        self.assertEqual(len(self.outcomes(aid)), 1)
        self.assertEqual(self.r.world.world_state()['observed_action_count'], 4)


if __name__ == '__main__':
    unittest.main()
