"""WP-Z6i: word channel for the route head and the rule -> learned-head lifecycle (no native models needed)."""
import json
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np

from v13 import route_supersede as RS
from v13 import route_words as RW
from v13 import learning_worker as LW
from v13.operator import Operator
from v13.runtime import Runtime

CFG = {'learning_steps': 40, 'eligibility_decay': .95, 'learning_rate': .01, 'max_update_norm': .02, 'retention_max_delta': .02}


class RouteWordsTest(unittest.TestCase):
    def test_vector_is_fixed_and_ignores_numbers(self):
        a = RW.vector('Wie viel ist die Hälfte von 120 Euro?')
        self.assertEqual(a, RW.vector('Wie viel ist die Hälfte von 120 Euro?'))
        self.assertEqual(a, RW.vector('Wie viel ist die Hälfte von 480 Euro?'))  # digits fold to '#'
        self.assertEqual(len(a), RW.DIM); self.assertAlmostEqual(float(np.linalg.norm(a)), RW.SCALE, places=6)
        self.assertNotEqual(a, RW.vector('Wie viel ist ein Drittel von 120 Euro?'))
        self.assertEqual(float(np.linalg.norm(RW.vector('?!'))), 0.)

    def test_worker_trains_with_words_and_widens_an_old_head(self):
        rng = np.random.default_rng(0); texts = ['Frage %d %s' % (i, w) for i, w in enumerate(['hallo', 'rechne', 'kern', 'vergleiche'] * 6)]
        emb = rng.normal(size=(len(texts), 6)).tolist(); y = [i % 4 for i in range(len(texts))]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); old = d/'old'; old.mkdir()
            LW.train({'config': CFG, 'embeddings': emb, 'labels': y, 'scaffold_labels': y}, old)
            with np.load(old/'candidate.npz') as z:
                self.assertEqual(LW.word_dim(z), 0); w0 = z['route_w']; before = LW.route_logits(z, emb[0], texts[0])
            w1, t1 = LW.widen(w0, np.ones(w0.shape[0]), RW.DIM, .5)
            x = LW.features([emb[0]], [RW.vector(texts[0])])
            np.testing.assert_allclose((x@w1)[0], before)  # zero rows: same function before training
            self.assertEqual(t1.shape, (w0.shape[0]+RW.DIM,))
            new = d/'new'; new.mkdir()
            m = LW.train({'config': CFG, 'embeddings': emb, 'labels': y, 'scaffold_labels': y, 'words': [RW.vector(t) for t in texts],
                          'active_checkpoint': str(old/'candidate.npz')}, new)
            self.assertEqual(m['word_dim'], RW.DIM); self.assertIn('known_items_lost', m['held_out'])
            with np.load(new/'candidate.npz') as z:
                self.assertEqual(LW.word_dim(z), RW.DIM); self.assertEqual(LW.route_logits(z, emb[1], texts[1]).shape, (4,))


    def test_weighted_objective_gradient_matches_finite_differences(self):
        rng = np.random.default_rng(1); x = rng.normal(size=(9, 5)); y = rng.integers(0, 4, 9); w = rng.normal(size=(5, 4)); sw = rng.uniform(.2, 1., 9)
        _, g, _ = LW.objective(x, y, w, sw); eps = 1e-6
        for i, j in ((0, 0), (2, 3), (4, 1)):
            a = w.copy(); b = w.copy(); a[i, j] += eps; b[i, j] -= eps
            self.assertAlmostEqual((LW.objective(x, y, a, sw)[0]-LW.objective(x, y, b, sw)[0])/(2*eps), g[i, j], places=6)
        self.assertAlmostEqual(LW.objective(x, y, w, np.ones(9))[0], LW.objective(x, y, w)[0], places=12)

    def test_relative_gate_compares_with_the_active_head(self):
        rng = np.random.default_rng(3); texts = ['Frage %d %s' % (i, w) for i, w in enumerate(['hallo', 'rechne', 'kern', 'vergleiche'] * 6)]
        emb = rng.normal(size=(len(texts), 6)).tolist(); y = [i % 4 for i in range(len(texts))]; wv = [RW.vector(t) for t in texts]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); old = d/'old'; old.mkdir(); new = d/'new'; new.mkdir()
            LW.train({'config': CFG, 'embeddings': emb, 'labels': y, 'scaffold_labels': y, 'words': wv}, old)
            m = LW.train({'config': CFG, 'embeddings': emb, 'labels': y, 'scaffold_labels': y, 'words': wv, 'gate': 'relative',
                          'active_checkpoint': str(old/'candidate.npz')}, new)
            h = m['held_out']; self.assertEqual(h['gate'], 'relative')
            if not h['known_accuracy_after'] > h['known_accuracy_before']: self.assertFalse(m['commit_eligible'])

    def test_anchors_are_soft_targets_and_reported(self):
        rng = np.random.default_rng(2); texts = ['Frage %d %s' % (i, w) for i, w in enumerate(['hallo', 'rechne', 'kern', 'vergleiche'] * 6)]
        emb = rng.normal(size=(len(texts), 6)).tolist(); y = [i % 4 for i in range(len(texts))]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); old = d/'old'; old.mkdir(); new = d/'new'; new.mkdir()
            LW.train({'config': CFG, 'embeddings': emb, 'labels': y, 'scaffold_labels': y, 'words': [RW.vector(t) for t in texts]}, old)
            anchors = {'embeddings': rng.normal(size=(5, 6)).tolist(), 'words': [RW.vector('anker %d' % i) for i in range(5)], 'weight': .5, 'rule_routes': [0]}
            m = LW.train({'config': CFG, 'embeddings': emb, 'labels': y, 'scaffold_labels': y, 'words': [RW.vector(t) for t in texts],
                          'active_checkpoint': str(old/'candidate.npz'), 'anchors': anchors}, new)
            self.assertEqual(m['held_out']['anchors'], 5); self.assertIn('anchors_moved_into_rule_route', m['held_out'])
            self.assertTrue(m['deterministic_repeat'])


class RuleLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.r = Runtime(Path(self.tmp.name)); self.op = Operator(self.r)
    def tearDown(self):
        self.r.close(); self.tmp.cleanup()

    def _rule(self, extra=''):
        self.op.run(':ersetze route simple hälfte,halbiere --sofort' + extra); return RS.rules(self.r.store)[-1]['id']

    def test_handover_needs_eight_agreements_of_the_same_head_and_falls_back(self):
        rid = self._rule(); q = 'Wie viel ist die Hälfte von 120 Euro?'
        with self.assertRaises(ValueError): RS.set_handover(self.r.store, rid, True, 'upd_a')
        for i in range(RS.HANDOVER_N - 1):
            rule, info = RS.decide(self.r.store, q, head=lambda: ('simple', 'upd_a'))
            self.assertEqual(rule['id'], rid); self.assertTrue(info['head_shadow']['agree'])
        self.assertFalse(RS.status(self.r.store, rid, 'upd_a')['learned'])
        RS.decide(self.r.store, q, head=lambda: ('simple', 'upd_a'))
        st = RS.status(self.r.store, rid, 'upd_a'); self.assertTrue(st['learned']); self.assertEqual(st['agree_in_a_row'], RS.HANDOVER_N)
        self.assertFalse(RS.status(self.r.store, rid, 'upd_b')['learned'])
        RS.set_handover(self.r.store, rid, True, 'upd_a')
        rule, info = RS.decide(self.r.store, q, head=lambda: ('simple', 'upd_a'))
        self.assertIsNone(rule); self.assertEqual(info['source'], 'RULE_CARRIED_BY_HEAD')
        rule, _ = RS.decide(self.r.store, q, head=lambda: ('simple', 'upd_b'))  # new head without its own evidence
        self.assertEqual(rule['id'], rid)
        rule, info = RS.decide(self.r.store, q, head=lambda: ('detail', 'upd_a'))  # one disagreement: the rule is back
        self.assertEqual(rule['id'], rid); self.assertFalse(info['head_shadow']['agree'])
        rule, _ = RS.decide(self.r.store, q, head=lambda: (None, 'upd_a'))  # below the decision margin counts as disagreement
        self.assertEqual(rule['id'], rid)
        self.assertIsNone(RS.decide(self.r.store, 'Rechne 12 mal 3 aus.', head=lambda: ('detail', 'upd_a'))[0])
        RS.set_handover(self.r.store, rid, False)
        self.assertFalse(RS.rules(self.r.store)[-1]['handover'])

    def test_operator_check_and_handover(self):
        rid = self._rule()
        self.assertFalse(json.loads(self.op.run(':ersetze pruefe ' + rid))['learned'])
        with self.assertRaises(ValueError): self.op.run(':ersetze gelernt ' + rid)  # no active head, nothing shown
        self.assertIn('routet wieder', self.op.run(':ersetze zurueck ' + rid))

    def test_lehre_needs_sofort_and_collects_routed_questions(self):
        with self.assertRaises(ValueError): RS.add(self.r.store, 'simple', ['hälfte'], teach=True)
        self.assertIn('trainieren', self.op.run(':ersetze route simple hälfte --sofort --lehre'))
        from v13.episodic_route import for_turn
        q = 'Wie viel ist die Hälfte von 120 Euro?'; e = self.r.store.event(self.r.session, q)
        self.assertEqual(for_turn(self.r.store, q, self.r.session, event_id=e['event_id'])[0], 'simple')
        self.assertEqual([(ev, route) for ev, route, _ in RS.taught(self.r.store)], [(e['event_id'], 'simple')])
        e2 = self.r.store.event(self.r.session, q)
        self.assertEqual(self.r._route(q, e2, time.monotonic()+5)[0], 'simple')  # runtime passes the event id
        self.assertEqual(len(RS.taught(self.r.store)), 2)

    def test_rule_without_lehre_teaches_nothing(self):
        self._rule(); q = 'Wie viel ist die Hälfte von 120 Euro?'; e = self.r.store.event(self.r.session, q)
        self.r._route(q, e, time.monotonic()+5); self.assertEqual(RS.taught(self.r.store), [])


if __name__ == '__main__':
    unittest.main()
