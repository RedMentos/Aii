"""Run209: WorldModel.for_event must not simulate unobserved fractional char counts.

Actual world_model.for_event with synthetic SQLite action rows, no model fit/native run.
"""
import json
import sqlite3
import unittest

from v13.world_model import for_event, transitions


class Store:
    def __init__(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE actions(id TEXT,event_id TEXT,status TEXT,expected TEXT,outcome TEXT,created REAL);
            CREATE TABLE packets(kind TEXT,event_id TEXT,payload TEXT,created REAL);
        ''')
    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]
    def one(self, sql, args=()):
        row = self.db.execute(sql, args).fetchone()
        return dict(row) if row else None
    def state(self, key, default=None):
        return default, 0
    def add(self, chars):
        self.db.execute('INSERT INTO packets VALUES (?,?,?,?)',
                        ('ActionSelection', 'event', json.dumps({'route_hint':'simple'}), 9.))
        self.db.execute('INSERT INTO actions VALUES (?,?,?,?,?,?)',
                        ('action', 'event', 'FINAL',
                         json.dumps({'forecast': {'input_chars':chars, 'profile': {'role':'C3_LANGUAGE'}}}),
                         json.dumps({'action_duration_s':2.,'characters':7,'role':'C3_LANGUAGE'}),10.))
    def close(self):self.db.close()


class WorldCounterfactualInputIntegrityRun209(unittest.TestCase):
    def trial(self, chars):
        s = Store()
        try:
            s.add(chars)
            return for_event(s,'event','simple'),transitions(s)
        finally:
            s.close()

    def test_fractional_or_float_character_counts_are_not_observed_states(self):
        for label, chars in (('fractional',50.5),('float_zero',0.0),('float_integer',50.0)):
            with self.subTest(label=label):
                cf, rows = self.trial(chars)
                self.assertEqual(rows,[])
                self.assertEqual(cf['reason'],'INVALID_OBSERVED_STATE')
                self.assertEqual(cf['confidence'],0.)
                self.assertIsNone(cf['prediction'])

    def test_non_numeric_and_nonfinite_counts_fail_closed(self):
        for chars in (None,True,-1,'50',float('nan'),float('inf')):
            with self.subTest(chars=str(chars)):
                cf, rows = self.trial(chars)
                self.assertEqual(rows,[])
                self.assertEqual(cf['reason'],'INVALID_OBSERVED_STATE')

    def test_genuine_integer_counts_preserve_existing_counterfactual_path(self):
        for chars in (0,50):
            with self.subTest(chars=chars):
                cf, rows = self.trial(chars)
                self.assertEqual(len(rows),1)
                self.assertEqual(cf['reason'],'NO_WORLD_MODEL')
                self.assertEqual(cf['authority'],'HYPOTHESIS')


if __name__=='__main__':
    unittest.main()
