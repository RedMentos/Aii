"""World recovery keeps malformed completed raw outcomes but grants no timing authority."""
import tempfile
from pathlib import Path
import unittest

from v13.runtime import Runtime


class WorldMalformedOutcomeRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def action(self, actual, observe=True):
        r = self.r
        e = r.store.event(r.session, 'World recovery input')
        forecast = r.world.forecast(e, 'C3_LANGUAGE', native_prediction=False)
        aid = r.store.start_action(e['event_id'], r.store.generation_id, forecast=forecast)
        r.store.finish_action(aid, 'FINAL', actual)
        return aid, r.world.observe(aid) if observe else None

    def test_non_dict_json_outcomes_are_unscored_but_exactly_preserved(self):
        values = ([], None, 'not a result', 42)
        for actual in values:
            with self.subTest(actual=actual):
                aid, observed = self.action(actual)
                self.assertEqual(observed['observed'], actual)
                self.assertFalse(observed['scored'])
                self.assertIsNone(observed['timing_error_s'])
                self.assertIsNone(observed['semantic_success'])
                self.assertFalse(observed['external_world_observation'])
        e = self.r.store.event(self.r.session, 'World recovery input')
        f = self.r.world.forecast(e, 'C3_LANGUAGE', native_prediction=False)
        self.assertEqual(f['sample_count'], 0)
        self.assertEqual(f['invalid_outcome_shape_count'], len(values))
        self.assertIsNone(f['duration_median_s'])

    def test_recover_unobserved_malformed_completed_action_after_restart(self):
        aid, observed = self.action(['invalid', 'payload'], observe=False)
        self.assertIsNone(observed)
        self.r.close()
        self.r = Runtime(self.home)
        packets = self.r.store.rows("SELECT payload FROM packets WHERE kind='PredictionOutcome'")
        self.assertEqual(len(packets), 1)
        recovered = self.r.world.observe(aid)
        self.assertEqual(recovered['observed'], ['invalid', 'payload'])
        self.assertFalse(recovered['scored'])
        self.assertEqual(self.r.world.world_state()['observed_action_count'], 1)

    def test_valid_followup_timing_still_works_after_malformed(self):
        self.action({'unexpected': ['not a duration']})
        for duration in (2., 3., 4.):
            self.action({'role': 'C3_LANGUAGE', 'action_duration_s': duration})
        e = self.r.store.event(self.r.session, 'World recovery input')
        f = self.r.world.forecast(e, 'C3_LANGUAGE', native_prediction=False)
        self.assertEqual(f['sample_count'], 3)
        self.assertEqual(f['duration_median_s'], 3.)
        self.assertEqual(f['invalid_outcome_shape_count'], 0)


if __name__ == '__main__':
    unittest.main()
