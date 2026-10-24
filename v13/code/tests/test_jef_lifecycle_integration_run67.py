"""Actual JEF lifecycle + SQLite source lineage; full V13 checkout required."""
import json
import sqlite3
import unittest
from v13.jefoutcome import lifecycle


class Store:
    def __init__(self, manifest):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''CREATE TABLE events(id TEXT,source_id TEXT);
            CREATE TABLE packets(kind TEXT,event_id TEXT);
            CREATE TABLE feedback(event_id TEXT,source_id TEXT);
            CREATE TABLE telemetry(kind TEXT,event_id TEXT);
            CREATE TABLE updates(id TEXT,status TEXT,manifest TEXT);''')
        self.db.execute('INSERT INTO events VALUES (?,?)',('e1','input1'))
        self.db.execute('INSERT INTO packets VALUES (?,?)',('ExperienceRecord','e1'))
        self.db.execute('INSERT INTO feedback VALUES (?,?)',('e1','src1'))
        self.db.execute('INSERT INTO updates VALUES (?,?,?)',('u1','ACTIVE',manifest))
        self.db.commit()
    def one(self,sql,args=()):
        row=self.db.execute(sql,args).fetchone()
        return dict(row) if row else None
    def rows(self,sql,args=()):return [dict(x) for x in self.db.execute(sql,args).fetchall()]
    def state(self,key):return None,0
    def components(self):return {'route':{'update_id':'u1'}}


class Runtime:
    def __init__(self,manifest):self.store=Store(manifest)


class LifecycleIntegration(unittest.TestCase):
    def test_substring_collision_does_not_claim_promotion(self):
        r=Runtime(json.dumps({'source_ids':['src10']}))
        out=lifecycle(r,'e1')
        self.assertFalse(out['reached']['L4_UPDATE_PROPOSAL'])
        self.assertFalse(out['reached']['L9_PROMOTE'])
        r.store.db.close()

    def test_exact_lineage_can_claim_observed_update(self):
        r=Runtime(json.dumps({'source_ids':['src1']}))
        out=lifecycle(r,'e1')
        self.assertTrue(out['reached']['L4_UPDATE_PROPOSAL'])
        self.assertTrue(out['reached']['L9_PROMOTE'])
        r.store.db.close()

    def test_invalid_manifest_never_claims_promotion(self):
        r=Runtime('{bad')
        out=lifecycle(r,'e1')
        self.assertFalse(out['reached']['L4_UPDATE_PROPOSAL'])
        r.store.db.close()


if __name__=='__main__':unittest.main()
