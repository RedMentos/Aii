"""Run71: FINAL World Model transitions require forecast/observed role agreement."""
import json
import sqlite3
import unittest
from v13.world_model import transitions


class Store:
    def __init__(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        self.db.executescript("""CREATE TABLE actions(id TEXT,event_id TEXT,status TEXT,expected TEXT,outcome TEXT,created REAL);
            CREATE TABLE packets(kind TEXT,event_id TEXT,payload TEXT,created REAL);""")
    def rows(self,q,args=()):return [dict(x) for x in self.db.execute(q,args)]
    def one(self,q,args=()):
        x=self.db.execute(q,args).fetchone()
        return dict(x) if x else None
    def add(self,id,expected_role='C3_LANGUAGE',actual_role='C3_LANGUAGE',status='FINAL'):
        fc={'input_chars':60,'resource_state':'NORMAL'}
        if expected_role is not None:fc['profile']={'role':expected_role}
        actual={'action_duration_s':2,'characters':10}
        if actual_role is not None:actual['role']=actual_role
        self.db.execute('INSERT INTO packets VALUES (?,?,?,?)',('ActionSelection','e'+id,json.dumps({'route_hint':'simple'}),9))
        self.db.execute('INSERT INTO actions VALUES (?,?,?,?,?,?)',(id,'e'+id,status,json.dumps({'forecast':fc}),json.dumps(actual),10))
    def close(self):self.db.close()


class WorldRole(unittest.TestCase):
    def setUp(self):self.s=Store()
    def tearDown(self):self.s.close()
    def test_valid_role_admitted(self):
        self.s.add('a');self.assertEqual(len(transitions(self.s)),1)
    def test_mismatched_final_role_rejected(self):
        self.s.add('a',actual_role='B1_DETAIL');self.assertEqual(transitions(self.s),[])
    def test_missing_forecast_role_rejected(self):
        self.s.add('a',expected_role=None);self.assertEqual(transitions(self.s),[])
    def test_missing_observed_role_rejected(self):
        self.s.add('a',actual_role=None);self.assertEqual(transitions(self.s),[])
    def test_nonfinal_failure_without_role_remains_failure(self):
        self.s.add('a',expected_role=None,actual_role=None,status='ERROR')
        t=transitions(self.s);self.assertEqual(len(t),1);self.assertEqual(t[0]['y'][1],0.)
    def test_other_valid_role_supported(self):
        self.s.add('a',expected_role='B2_GIST',actual_role='B2_GIST')
        self.assertEqual(len(transitions(self.s)),1)


if __name__=='__main__':unittest.main()
