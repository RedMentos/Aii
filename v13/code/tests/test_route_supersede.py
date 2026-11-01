from pathlib import Path
import tempfile
import time
import unittest

from v13 import route_supersede as RS
from v13.operator import Operator
from v13.runtime import Runtime


class RouteSupersedeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.r = Runtime(Path(self.tmp.name))
    def tearDown(self):
        self.r.close(); self.tmp.cleanup()

    def test_only_older_contradicting_labels_with_the_words_are_dropped(self):
        t0 = time.time() - 10
        rows = [('Wie viel ist die Hälfte von 120 Euro?', ({'value': 'detail', 'created': t0, 'source_id': 'a'}, {})),
                ('Wie viel ist die Hälfte von 80 Euro?', ({'value': 'simple', 'created': t0, 'source_id': 'b'}, {})),
                ('Rechne 12 mal 3 aus.', ({'value': 'detail', 'created': t0, 'source_id': 'c'}, {}))]
        rule = RS.add(self.r.store, 'simple', ['Hälfte', 'halbiere'])
        later = ('Halbiere bitte 60 Euro.', ({'value': 'detail', 'created': time.time() + 5, 'source_id': 'd'}, {}))
        kept, dropped = RS.apply(self.r.store, rows + [later])
        self.assertEqual([d['feedback_source_id'] for d in dropped], ['a'])  # newer label after the rule stays
        self.assertEqual(len(kept), 3); self.assertEqual(dropped[0]['rule'], rule['id'])
        RS.remove(self.r.store, rule['id']); self.assertEqual(RS.apply(self.r.store, rows)[1], [])

    def test_operator_command_and_validation(self):
        op = Operator(self.r)
        out = op.run(':ersetze route simple Hälfte,halbiere --notiz neue Vorliebe')
        self.assertIn('Rücknahme', out); rid = RS.rules(self.r.store)[0]['id']
        self.assertEqual(RS.rules(self.r.store)[0]['words'], ['halbiere', 'hälfte'])
        with self.assertRaises(ValueError): RS.add(self.r.store, 'quatsch', ['wort'])
        with self.assertRaises(ValueError): RS.add(self.r.store, 'simple', ['ab'])
        op.run(':ersetze undo ' + rid); self.assertEqual(RS.rules(self.r.store), [])

    def test_sofort_rule_routes_at_answer_time_and_undo_restores(self):
        from v13.episodic_route import for_turn
        op = Operator(self.r); q = 'Wie viel ist die Hälfte von 120 Euro?'
        op.run(':ersetze route simple hälfte')  # without --sofort: training only
        self.assertIsNone(RS.rule_route(self.r.store, q))
        op.run(':ersetze route simple hälfte,halbiere --sofort'); rid = RS.rules(self.r.store)[-1]['id']
        route, info = for_turn(self.r.store, q, self.r.session)
        self.assertEqual((route, info['source']), ('simple', 'HUMAN_ROUTE_RULE'))
        self.assertIsNone(for_turn(self.r.store, 'Rechne 12 mal 3 aus.', self.r.session)[0])
        e = self.r.store.event(self.r.session, q)
        self.assertEqual(self.r._route(q, e, time.monotonic()+5)[0], 'simple')
        op.run(':ersetze undo ' + rid); self.assertIsNone(RS.rule_route(self.r.store, q))


if __name__ == '__main__':
    unittest.main()
