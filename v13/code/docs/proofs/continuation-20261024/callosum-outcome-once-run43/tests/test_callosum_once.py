import copy
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from callosum_once_candidate import credit_once, observation


class OnceTests(unittest.TestCase):
    def setUp(self):
        self.state = {'pending': {'event-A': [
            {'msg': 'm1', 'direction': 'B1_TO_B2', 'channel': 'SOURCE_EXACT', 'receiver': 'B2_GIST'},
            {'msg': 'm2', 'direction': 'B1_TO_B2', 'channel': 'CONTROL', 'receiver': 'B2_GIST'}]}}
        self.calls = []

    def update(self, state, direction, channel, util, parts):
        self.calls.append((direction, channel, util, dict(parts)))

    def obs(self, i=0, util=1.2):
        return observation('event-A', self.state['pending']['event-A'][i], util, {'task_gain': 1.})

    def credit(self, observations):
        return credit_once(self.state, 'event-A', observations, self.update)

    def test_first_observation_updates_once(self):
        self.assertEqual(len(self.credit([self.obs()])), 1)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.state['pending']['event-A'][0]['scored'])

    def test_replay_does_not_double_credit(self):
        evidence = [self.obs()]
        self.credit(evidence)
        self.assertEqual(self.credit(evidence), [])
        self.assertEqual(len(self.calls), 1)

    def test_stale_snapshot_after_first_commit_no_double_credit(self):
        stale = copy.deepcopy(self.obs())
        self.credit([self.obs()])
        self.assertEqual(self.credit([stale]), [])

    def test_duplicate_observation_single_credit(self):
        e = self.obs()
        self.assertEqual(len(self.credit([e, copy.deepcopy(e)])), 1)

    def test_duplicate_pending_message_id_is_refused(self):
        self.state['pending']['event-A'][1]['msg'] = 'm1'
        self.assertEqual(self.credit([self.obs()]), [])
        self.assertEqual(self.calls, [])

    def test_unobserved_message_remains_unscored_then_eligible(self):
        self.credit([self.obs()])
        self.assertNotIn('scored', self.state['pending']['event-A'][1])
        self.assertEqual(len(self.credit([self.obs(1)])), 1)
        self.assertEqual(len(self.calls), 2)

    def test_other_event_not_credited(self):
        other = self.obs(); other['event_id'] = 'event-B'
        self.assertEqual(self.credit([other]), [])

    def test_missing_event_does_not_create_pending(self):
        self.assertEqual(credit_once(self.state, 'absent', [self.obs()], self.update), [])
        self.assertNotIn('absent', self.state['pending'])

    def test_channel_receiver_direction_mismatch_refused(self):
        for field, value in [('channel', 'SYMBOLIC'), ('receiver', 'B1_DETAIL'), ('direction', 'B2_TO_B1')]:
            with self.subTest(field=field):
                e = self.obs(); e[field] = value
                self.assertEqual(self.credit([e]), [])
        self.assertEqual(self.calls, [])

    def test_nonfinite_and_bool_utility_refused(self):
        for value in [float('nan'), float('inf'), -float('inf'), True]:
            with self.subTest(value=value):
                self.assertEqual(self.credit([self.obs(util=value)]), [])
        self.assertEqual(self.calls, [])

    def test_nonfinite_parts_refused(self):
        e = self.obs(); e['parts'] = {'task_gain': float('nan')}
        self.assertEqual(self.credit([e]), [])

    def test_malformed_pending_rejected(self):
        e = self.obs()
        self.state['pending']['event-A'] = 'bad'
        with self.assertRaises(ValueError): self.credit([e])

    def test_no_age_action_or_latent_authority_fields(self):
        self.credit([self.obs()])
        self.assertNotIn('age', self.state)
        self.assertNotIn('latent', self.state)

    def test_legacy_replay_is_not_idempotent_synthetic_demonstration(self):
        # Mirror the current source's unguarded update loop; not a native run.
        legacy = copy.deepcopy(self.state)
        def legacy_apply():
            for _ in legacy['pending']['event-A'][:1]:
                self.update(legacy, 'B1_TO_B2', 'SOURCE_EXACT', 1.2, {'task_gain': 1.})
            for item in legacy['pending']['event-A']: item['scored'] = True
        legacy_apply(); legacy_apply()
        self.assertEqual(len(self.calls), 2)


if __name__ == '__main__': unittest.main()
