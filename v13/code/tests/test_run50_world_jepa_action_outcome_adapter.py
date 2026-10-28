"""Run50 read-only real-schema digital action/outcome adapter tests; software only."""
import json
import unittest

import numpy as np

from v13 import world_model
from v13 import world_jepa_action_outcome_adapter as adapter


class FakeReadOnlyView:
    def __init__(self, n=128):
        self.routes = {}
        self._rows = []
        self.read_calls = 0
        for i in range(n):
            event_id = 'ev-%04d' % i
            self.routes[event_id] = world_model.ACTIONS[i % 4]
            self._rows.append({
                'id': 'action-%04d' % i, 'event_id': event_id,
                'status': 'FINAL',
                'expected': json.dumps({'forecast': {
                    'input_chars': 100 + i, 'resource_state': 'NORMAL'}}),
                'outcome': json.dumps({
                    'action_duration_s': 1. + (i % 4) * .1,
                    'characters': 20 + i % 11}),
                'created': 1700000000. + i,
            })

    def rows(self, sql, args=()):
        self.read_calls += 1
        if not sql.lstrip().upper().startswith('SELECT '):
            raise AssertionError('read-only SELECT expected')
        return list(reversed(self._rows))

    def one(self, sql, args=()):
        self.read_calls += 1
        if not sql.lstrip().upper().startswith('SELECT '):
            raise AssertionError('read-only SELECT expected')
        return {'payload': json.dumps({'route_hint': self.routes[args[0]]})}

    def __getattr__(self, name):
        if name in ('set_state', 'log', 'execute', 'commit', 'write'):
            raise AssertionError('mutation not allowed')
        raise AttributeError(name)


class Run50ActionOutcomeAdapter(unittest.TestCase):
    def setUp(self):
        self.view = FakeReadOnlyView()
        self.records = world_model.transitions(self.view)

    def test_real_world_model_transition_schema_to_jepa_arrays(self):
        self.assertEqual(len(self.records), 128)
        out = adapter.build(self.records)
        meta = out['manifest']
        self.assertEqual(meta['n_total'], 128)
        self.assertGreaterEqual(meta['n_train'], 8)
        self.assertGreaterEqual(meta['n_holdout'], 8)
        self.assertFalse(meta['training_executed'])
        self.assertFalse(meta['source_verified'])
        self.assertFalse(meta['real_world_causality_proven'])
        self.assertFalse(meta['learning_gate_pass'])
        self.assertEqual(meta['age_authority'], 0)
        x, a, x2 = out['train']
        self.assertEqual(x.shape[1], 7)
        self.assertEqual(a.shape[1], 4)
        self.assertEqual(x2.shape, x.shape)
        np.testing.assert_array_equal(x[:, 4:], np.zeros((len(x), 3)))
        np.testing.assert_array_equal(x2[:, :4], x[:, :4])
        self.assertTrue((x2[:, 4:] >= 0).all())
        self.assertTrue(np.all(a.sum(axis=1) == 1))
        self.assertFalse(set(out['train_action_ids']) & set(out['holdout_action_ids']))

    def test_reordering_does_not_change_split_or_source_digests(self):
        a = adapter.build(self.records)
        b = adapter.build(list(reversed(self.records)))
        self.assertEqual(a['manifest'], b['manifest'])
        self.assertEqual(a['train_action_ids'], b['train_action_ids'])
        self.assertEqual(a['holdout_action_ids'], b['holdout_action_ids'])
        for side in ('train', 'holdout'):
            for left, right in zip(a[side], b[side]):
                np.testing.assert_array_equal(left, right)

    def test_invalid_duplicates_routes_and_nonfinite_values_fail_closed(self):
        duplicate = [dict(r) for r in self.records]
        duplicate[-1]['action_id'] = duplicate[0]['action_id']
        with self.assertRaisesRegex(ValueError, 'DUPLICATE'):
            adapter.build(duplicate)
        bad_route = [dict(r) for r in self.records]
        bad_route[0]['a'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'ACTION_ID'):
            adapter.build(bad_route)
        bad_state = [dict(r) for r in self.records]
        bad_state[0]['s'] = [float('nan'), 0., 0., 0.]
        with self.assertRaisesRegex(ValueError, 'NONFINITE'):
            adapter.build(bad_state)
        bad_outcome = [dict(r) for r in self.records]
        bad_outcome[0]['y'] = [True, 0., 0.]
        with self.assertRaisesRegex(ValueError, 'INVALID_VECTOR'):
            adapter.build(bad_outcome)

    def test_same_transition_content_under_distinct_ids_cannot_leak(self):
        # Distinct action IDs alone do not guarantee distinct transition
        # content. A held-out copy of a training row must be rejected.
        rows = [dict(r) for r in self.records]
        train_index = next(i for i, r in enumerate(rows)
                           if adapter._partition(r['action_id']) == 'train')
        holdout_index = next(i for i, r in enumerate(rows)
                             if adapter._partition(r['action_id']) == 'holdout')
        rows[holdout_index]['s'] = list(rows[train_index]['s'])
        rows[holdout_index]['a'] = rows[train_index]['a']
        rows[holdout_index]['y'] = list(rows[train_index]['y'])
        with self.assertRaisesRegex(ValueError, 'CONTENT_OVERLAP'):
            adapter.build(rows)

    def test_short_or_single_action_cohort_refused(self):
        with self.assertRaisesRegex(ValueError, 'RECORD_COUNT'):
            adapter.build(self.records[:12])
        same_action = [dict(r, a='simple') for r in self.records]
        with self.assertRaisesRegex(ValueError, 'ACTION_SUPPORT'):
            adapter.build(same_action)


if __name__ == '__main__':
    unittest.main()
