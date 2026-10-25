"""Run306 RED-first: heldout WorldModel must not reuse identical user source bytes.

Actual production Runtime/Store SQLite, synthetic durations, no native model.
"""
import json
from pathlib import Path
import tempfile
import time
import unittest

from v13.runtime import Runtime
from v13.store import Store
from v13 import world_model as W


class WorldSourceDisjointRun306(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.temp.cleanup()

    def build(self, texts, actions_per_event=2, cross_sessions=False):
        hashes = []
        for i, text in enumerate(texts):
            if cross_sessions and i == len(texts)//2:
                self.r.session = self.r.store.new_session('RUN306 second session')
            event = self.r.store.event(self.r.session, text)
            hashes.append(event['source_ref']['sha256'])
            for j in range(actions_per_event):
                route = W.ACTIONS[(i * actions_per_event + j) % len(W.ACTIONS)]
                with self.r.store.tx() as c:
                    c.execute(
                        'INSERT INTO packets VALUES (?,?,?,?,?,?)',
                        (f'run306-route-{i}-{j}', 'ActionSelection', event['event_id'],
                         event['brain_generation_id'],
                         json.dumps({'route_hint': route}), time.time()),
                    )
                aid = self.r.store.start_action(
                    event['event_id'], event['brain_generation_id'],
                    forecast={'input_chars': len(text), 'resource_state': 'NORMAL',
                              'profile': {'role': 'C3_LANGUAGE'}},
                )
                self.r.store.finish_action(
                    aid, 'FINAL',
                    {'action_duration_s': .5 + i * .12 + j * .03,
                     'characters': 30 + i + j, 'role': 'C3_LANGUAGE'},
                )
        return hashes

    def test_identical_text_across_distinct_events_cannot_forge_independent_holdout(self):
        hashes = self.build(['RUN306 identical source with two observed actions'] * 12,
                            cross_sessions=True)
        self.assertEqual(len(set(hashes)), 1)
        rows = W.transitions(self.r.store)
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({r['event_id'] for r in rows}), 12)
        state = W.fit(self.r.store, rng_seed=306)
        self.assertEqual(state['status'], 'INSUFFICIENT_INDEPENDENT_GROUPS', state)
        self.assertIsNone(W.load(self.r.store))
        self.assertIsNone(self.r.store.state(W.KEY, None)[0])

    def test_two_repeated_source_groups_are_disjoint_and_restart_valid(self):
        a = 'RUN306 source alpha with observed actions'
        b = 'RUN306 source beta with observed actions'
        hashes = self.build([a, b] * 6, cross_sessions=True)
        self.assertEqual(len(set(hashes)), 2)
        rows = W.transitions(self.r.store)
        self.assertEqual(len(rows), 24)
        state = W.fit(self.r.store, rng_seed=306)
        self.assertEqual(state['status'], 'FITTED', state.get('status'))
        metrics = state['metrics']
        self.assertEqual(metrics['group_split'], 'SOURCE_HASH_DISJOINT')
        self.assertTrue(metrics['group_disjoint'])
        self.assertEqual(metrics['train_group_count'] + metrics['held_out_group_count'], 2)
        groups = [self.r.store.one(
            'SELECT s.hash AS hash FROM events e JOIN sources s ON s.id=e.source_id WHERE e.id=?',
            (row['event_id'],))['hash'] for row in rows]
        tr, te = W._split(len(rows), groups)
        self.assertFalse(set(groups[i] for i in tr) & set(groups[i] for i in te))
        self.assertEqual(metrics['held_out'], len(te))
        self.assertIsNotNone(W.load(self.r.store))
        self.r.close()
        self.r = None
        fresh = Store(self.home)
        try:
            self.assertIsNotNone(W.load(fresh))
        finally:
            fresh.close()

    def test_unique_source_events_preserve_run301_split_and_metrics(self):
        hashes = self.build([f'RUN306 unique user source {i}' for i in range(12)])
        self.assertEqual(len(set(hashes)), 12)
        rows = W.transitions(self.r.store)
        groups = [r['event_id'] for r in rows]
        tr, te = W._split(len(rows), groups)
        state = W.fit(self.r.store, rng_seed=306)
        self.assertEqual(state['status'], 'FITTED')
        self.assertEqual(state['metrics']['group_split'], 'EVENT_DISJOINT')
        self.assertEqual(state['metrics']['held_out'], len(te))
        self.assertEqual(state['metrics']['train_group_count'] + state['metrics']['held_out_group_count'], 12)
        self.assertTrue(state['metrics']['group_disjoint'])
        self.assertIsNotNone(W.load(self.r.store))


if __name__ == '__main__':
    unittest.main()
