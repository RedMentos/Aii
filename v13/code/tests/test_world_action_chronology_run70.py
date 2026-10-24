"""Run70: SQLite action-to-ActionSelection temporal binding regression."""
import json
import sqlite3
import unittest
from v13.world_model import transitions


class Store:
    def __init__(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.executescript("""CREATE TABLE actions(id TEXT,event_id TEXT,status TEXT,expected TEXT,outcome TEXT,created REAL);
           CREATE TABLE packets(kind TEXT,event_id TEXT,payload TEXT,created REAL);""")
    def rows(self,q,args=()):return [dict(x) for x in self.db.execute(q,args)]
    def one(self,q,args=()):
        x=self.db.execute(q,args).fetchone()
        return dict(x) if x else None
    def action(self,id,when,event='e1'):
        self.db.execute('INSERT INTO actions VALUES (?,?,?,?,?,?)',(id,event,'FINAL',json.dumps({'forecast':{'input_chars':50,'profile':{'role':'C3_LANGUAGE'}}}),json.dumps({'action_duration_s':2,'characters':5,'role':'C3_LANGUAGE'}),when))
    def selection(self,route,when,event='e1'):
        self.db.execute('INSERT INTO packets VALUES (?,?,?,?)',('ActionSelection',event,json.dumps({'route_hint':route}),when))
    def close(self):self.db.close()


class WorldActionChronology(unittest.TestCase):
    def setUp(self):self.s=Store()
    def tearDown(self):self.s.close()

    def test_two_actions_bind_respective_prior_selection(self):
        self.s.selection('simple',9);self.s.action('a1',10)
        self.s.selection('gist',19);self.s.action('a2',20)
        self.assertEqual([(x['action_id'],x['a']) for x in transitions(self.s)],[('a1','simple'),('a2','gist')])

    def test_future_selection_must_not_label_past_action(self):
        self.s.action('a1',8);self.s.selection('gist',9)
        self.assertEqual(transitions(self.s),[])

    def test_tied_created_times_choose_latest_rowid(self):
        self.s.selection('simple',9);self.s.selection('detail',9);self.s.action('a1',10)
        self.assertEqual(transitions(self.s)[0]['a'],'detail')

    def test_unrelated_event_does_not_supply_selection(self):
        self.s.selection('simple',9,'other');self.s.action('a1',10)
        self.assertEqual(transitions(self.s),[])

    def test_selection_after_one_action_before_another(self):
        self.s.selection('simple',5);self.s.action('a1',10);self.s.selection('both',15);self.s.action('a2',20)
        self.assertEqual([x['a'] for x in transitions(self.s)],['simple','both'])


if __name__=='__main__':unittest.main()
