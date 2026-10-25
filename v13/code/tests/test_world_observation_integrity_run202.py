"""Run202: WorldModel must not turn missing observed counts into synthetic zero targets.

Synthetic SQLite with actual world_model.transitions. No native or learned utility.
"""
import json
import math
import sqlite3
import unittest

from v13.world_model import transitions


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
    def add(self, observed, input_chars=50, status='FINAL'):
        expected = {'forecast':{'input_chars':input_chars,'profile':{'role':'C3_LANGUAGE'}}}
        self.db.execute('INSERT INTO packets VALUES (?,?,?,?)',
                        ('ActionSelection','event',json.dumps({'route_hint':'simple'}),9.))
        self.db.execute('INSERT INTO actions VALUES (?,?,?,?,?,?)',
                        ('action','event',status,json.dumps(expected),json.dumps(observed),10.))
    def close(self):self.db.close()


class WorldObservationIntegrityRun202(unittest.TestCase):
    def trial(self, observed, input_chars=50, status='FINAL'):
        store=Store()
        try:
            store.add(observed,input_chars,status)
            return transitions(store)
        finally:store.close()

    def test_missing_or_untyped_output_characters_cannot_become_zero(self):
        base={'action_duration_s':2.,'role':'C3_LANGUAGE'}
        for label, value in (
            ('missing', 'MISSING'),('null', None),('boolean', False),
            ('empty_string', ''),('float_count', 0.0),('negative', -1),
            ('nan', float('nan')),('infinity', float('inf')),
        ):
            with self.subTest(case=label):
                observed=dict(base)
                if value != 'MISSING':observed['characters']=value
                self.assertEqual(self.trial(observed),[])

    def test_nonfinal_observation_also_requires_actual_characters(self):
        observed={'action_duration_s':2.}
        self.assertEqual(self.trial(observed,status='ERROR'),[])

    def test_fractional_input_character_count_not_a_valid_observed_state(self):
        observed={'action_duration_s':2.,'characters':7,'role':'C3_LANGUAGE'}
        self.assertEqual(self.trial(observed,input_chars=50.5),[])

    def test_explicit_zero_and_positive_integer_counts_are_preserved(self):
        for n in (0,7):
            with self.subTest(chars=n):
                observed={'action_duration_s':2.,'characters':n,'role':'C3_LANGUAGE'}
                rows=self.trial(observed)
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]['y'][1],1.)
                self.assertEqual(rows[0]['y'][2],math.log1p(n)/8)


if __name__=='__main__':unittest.main()
