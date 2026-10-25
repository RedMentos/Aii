"""Run261 RED-first: terminal non-FINAL outcomes are real WorldModel training evidence.

Production Store + synthetic action outcomes; no native model or Redmi. Does not
modify the actively owned WorldModel source on PR259.
"""
import json
from pathlib import Path
import tempfile
import time
import unittest

from v13.runtime import Runtime
from v13 import world_model as W


class TerminalFailureLineage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.failed = []
        for i in range(24):
            ev = self.r.store.event(self.r.session, f'Observed action {i}')
            eid = ev['event_id']
            generation = ev['brain_generation_id']
            route = W.ACTIONS[i % len(W.ACTIONS)]
            with self.r.store.tx() as c:
                c.execute('INSERT INTO packets VALUES (?,?,?,?,?,?)',
                          (f'run261-selection-{i}', 'ActionSelection', eid,
                           generation, json.dumps({'route_hint': route}), time.time()))
            aid = self.r.store.start_action(
                eid, generation,
                forecast={'input_chars': 30+i, 'resource_state': 'NORMAL',
                          'profile': {'role': 'C3_LANGUAGE'}})
            status = 'ERROR' if i % 6 == 0 else 'FINAL'
            self.r.store.finish_action(
                aid, status,
                {'action_duration_s': 0.3+i*0.05,
                 'characters': 12+i, 'role': 'C3_LANGUAGE'})
            if status == 'ERROR':
                self.failed.append(aid)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_observed_failure_is_not_erased_from_transitions(self):
        transitions = W.transitions(self.r.store)
        self.assertEqual(len(transitions), 24)
        self.assertEqual(sum(t['y'][1] == 0 for t in transitions), 4)
        self.assertEqual(sum(t['y'][1] == 1 for t in transitions), 20)

    def test_fitted_world_retains_valid_terminal_failures(self):
        st = W.fit(self.r.store, rng_seed=17)
        self.assertEqual(st['status'], 'FITTED',
                         'A valid ERROR outcome must not invalidate all training data')
        self.assertEqual(st['n'], 24)
        self.assertEqual(st['evidence_scope'], 'SOURCE_BOUND_STORE')
        self.assertEqual(len(st['training_bindings']), 24)
        self.assertIsNotNone(W.load(self.r.store))

    def test_nonterminal_dispatched_with_outcome_is_not_observed(self):
        ev = self.r.store.event(self.r.session, 'Unfinished action is not an outcome')
        eid = ev['event_id']
        generation = ev['brain_generation_id']
        with self.r.store.tx() as c:
            c.execute('INSERT INTO packets VALUES (?,?,?,?,?,?)',
                      ('run261-unfinished-selection', 'ActionSelection', eid,
                       generation, json.dumps({'route_hint': 'simple'}), time.time()))
        aid = self.r.store.start_action(
            eid, generation,
            forecast={'input_chars': 33, 'resource_state': 'NORMAL',
                      'profile': {'role': 'C3_LANGUAGE'}})
        # Corrupted/incomplete write: an outcome payload is present but the
        # lifecycle still says DISPATCHED. No terminal ActionOutcome exists.
        with self.r.store.tx() as c:
            c.execute('UPDATE actions SET outcome=? WHERE id=?',
                      (json.dumps({'action_duration_s': 0.5,
                                   'characters': 20, 'role': 'C3_LANGUAGE'}), aid))
        observed = W.transitions(self.r.store)
        self.assertEqual(len(observed), 24,
                         'Nonterminal DISPATCHED is not a grounded outcome')
        self.assertNotIn(aid, [t['action_id'] for t in observed])

    def test_error_outcome_mutation_invalidates_bound_fit(self):
        st = W.fit(self.r.store, rng_seed=17)
        self.assertEqual(st['status'], 'FITTED')
        with self.r.store.tx() as c:
            c.execute("UPDATE actions SET outcome=? WHERE id=?",
                      (json.dumps({'action_duration_s': 999,
                                   'characters': 100, 'role': 'C3_LANGUAGE'}),
                       self.failed[0]))
        self.assertIsNone(W.load(self.r.store),
                          'Revocation/tamper guard must cover failures as well as successes')


if __name__ == '__main__':
    unittest.main()
