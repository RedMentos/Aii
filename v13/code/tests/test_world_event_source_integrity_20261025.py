"""WP-T8 source lineage: real Store-shaped event/source check, synthetic SQLite.

RED against Run222 world_model.py. No native model, external action, or authority.
"""
import json
import sqlite3
import unittest
from v13 import world_model as W


class SourceStore:
    def __init__(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          CREATE TABLE events(id TEXT PRIMARY KEY,source_id TEXT,packet TEXT);
          CREATE TABLE actions(id TEXT,event_id TEXT,status TEXT,expected TEXT,outcome TEXT,created REAL);
          CREATE TABLE packets(kind TEXT,event_id TEXT,payload TEXT,created REAL);
        """)
        self.deleted = False
        self.read_failure = False
        self.ref = {'source_id':'src-1','sha256':'sha-1','char_start':0,
                    'char_end':6,'modality':'text'}
        self.db.execute('INSERT INTO events VALUES (?,?,?)',
                        ('event-1','src-1',json.dumps({'source_ref':self.ref,'event_id':'event-1',
                                    'kind':'USER_TEXT','authority':'AUTHORITATIVE',
                                    'provenance':[self.ref]})))
        self.db.execute('INSERT INTO packets VALUES (?,?,?,?)',
                        ('ActionSelection','event-1',json.dumps({'route_hint':'simple'}),9.))
        self.db.execute('INSERT INTO actions VALUES (?,?,?,?,?,?)',
                        ('action-1','event-1','FINAL',
                         json.dumps({'forecast':{'input_chars':6,
                                                'profile':{'role':'C3_LANGUAGE'}}}),
                         json.dumps({'action_duration_s':2.0,'characters':7,
                                     'role':'C3_LANGUAGE'}),10.))
        self.db.commit()

    def rows(self,sql,args=()):
        return [dict(row) for row in self.db.execute(sql,args)]
    def one(self,sql,args=()):
        row = self.db.execute(sql,args).fetchone()
        return dict(row) if row else None
    def state(self,key,default=None):
        return default,0
    def read_source(self,ref):
        if self.deleted or self.read_failure:
            raise ValueError('Source revoked or unreadable')
        if ref != self.ref:
            raise ValueError('SourceRef mismatch')
        return 'source'
    def close(self):
        self.db.close()


class WorldEventSourceIntegrity(unittest.TestCase):
    def setUp(self):
        self.s = SourceStore()
    def tearDown(self):
        self.s.close()

    def assert_refused(self):
        self.assertEqual(W.transitions(self.s),[])
        report = W.for_event(self.s,'event-1','simple')
        self.assertEqual(report['reason'],'INVALID_EVENT_SOURCE',report)
        self.assertEqual(report['label'],'SIMULATION_UNCERTAIN')
        self.assertEqual(report['authority'],'HYPOTHESIS')
        self.assertEqual(report['confidence'],0.)
        self.assertIsNone(report['prediction'])

    def test_intact_event_source_preserves_observation(self):
        rows=W.transitions(self.s)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['a'],'simple')
        self.assertEqual(rows[0]['y'][1],1.)
        report=W.for_event(self.s,'event-1','simple')
        self.assertEqual(report['reason'],'NO_WORLD_MODEL')

    def test_deleted_source_rejected(self):
        self.s.deleted=True
        self.assert_refused()

    def test_missing_event_rejected(self):
        self.s.db.execute('DELETE FROM events WHERE id=?',('event-1',))
        self.assert_refused()

    def test_cross_source_event_id_rejected(self):
        self.s.db.execute('UPDATE events SET source_id=? WHERE id=?',
                          ('src-foreign','event-1'))
        self.assert_refused()

    def test_tampered_event_envelope_rejected(self):
        for bad in ('{not-json',json.dumps({'source_ref':{'source_id':'src-foreign'}}),
                    json.dumps({'source_ref':'not-a-ref'}),
                    json.dumps({'source_ref':self.s.ref,'event_id':'wrong-event',
                                'kind':'USER_TEXT','authority':'AUTHORITATIVE',
                                'provenance':[self.s.ref]}),
                    json.dumps({'source_ref':self.s.ref,'event_id':'event-1',
                                'kind':'USER_TEXT','authority':'PROVISIONAL',
                                'provenance':[self.s.ref]}),
                    json.dumps({'source_ref':self.s.ref,'event_id':'event-1',
                                'kind':'USER_TEXT','authority':'AUTHORITATIVE',
                                'provenance':[]})):
            with self.subTest(packet=bad):
                self.s.db.execute('UPDATE events SET packet=? WHERE id=?',
                                  (bad,'event-1'))
                self.assert_refused()

    def test_unreadable_source_rejected(self):
        self.s.read_failure=True
        self.assert_refused()


if __name__=='__main__':
    unittest.main()
