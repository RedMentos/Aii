"""Run150 synthetic SQLite and real Store integration, no native model calls."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.age0d_history_shadow_audit_run150 import audit

class Run150StoreAudit(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.home=Path(self.temp.name)
        (self.home/'data/db').mkdir(parents=True);(self.home/'data/blobs').mkdir(parents=True)
        self.db=self.home/'data/db/brain.sqlite3';self.conn=sqlite3.connect(self.db)
        self.conn.executescript('''CREATE TABLE events(id TEXT PRIMARY KEY,session_id TEXT,source_id TEXT,packet TEXT,created REAL);
        CREATE TABLE sources(id TEXT PRIMARY KEY,hash TEXT,deleted INTEGER);
        CREATE TABLE accepted_turns(event_id TEXT PRIMARY KEY,state TEXT);
        CREATE TABLE messages(id INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT,event_id TEXT,role TEXT,text TEXT,status TEXT,metadata TEXT);''')
        self.session='chat_a'

    def tearDown(self):self.conn.close();self.temp.cleanup()

    def add(self,question='Compute 2 plus 2.',answer='2 + 2 = 4\n\n',session=None,state='DONE',deleted=0):
        sid=session or self.session;idx=self.conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        event='evt_'+str(idx);source='src_'+str(idx);raw=question.encode();h=hashlib.sha256(raw).hexdigest()
        (self.home/'data/blobs'/h).write_bytes(raw)
        ref={'source_id':source,'sha256':h,'char_start':0,'char_end':len(question),'modality':'text'}
        self.conn.execute('INSERT INTO sources VALUES(?,?,?)',(source,h,deleted))
        self.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',(event,sid,source,json.dumps({'source_ref':ref}),idx))
        self.conn.execute('INSERT INTO accepted_turns VALUES(?,?)',(event,state))
        self.conn.execute('INSERT INTO messages(session_id,event_id,role,text,status,metadata) VALUES(?,?,?,?,?,?)',(sid,event,'user',question,'FINAL',json.dumps({'source_ref':ref})))
        self.conn.execute('INSERT INTO messages(session_id,event_id,role,text,status,metadata) VALUES(?,?,?,?,?,?)',(sid,event,'assistant',answer,'FINAL','{}'))
        self.conn.commit();return event,h

    def test_01_valid_correct_and_wrong_source_bound(self):
        self.add();self.add('Compute 3 plus 2.','5');self.add('Compute 4 times 5.','22')
        r=audit(self.home,self.session)
        self.assertEqual((r['considered'],r['source_verified']),(3,3))
        self.assertEqual(r['verdicts'],{'CORRECT':2,'MISMATCH':1,'ABSTAIN':0})
        self.assertEqual(r['gate'],'UNVERIFIED');self.assertFalse(r['may_deliver'])

    def test_02_other_session_never_mixed(self):
        self.add();self.add('Compute 3 plus 3.','6',session='chat_b')
        self.assertEqual(audit(self.home,'chat_a')['considered'],1)
        self.assertEqual(audit(self.home,'chat_b')['considered'],1)

    def test_03_pending_and_deadline_excluded(self):
        self.add(state='PENDING');self.add('Compute 3 plus 3.','6',state='DEADLINE')
        r=audit(self.home,self.session);self.assertEqual(r['source_verified'],0)
        self.assertEqual(r['skips'],{'not_done':2})

    def test_04_deleted_source_excluded(self):
        self.add(deleted=1);r=audit(self.home,self.session)
        self.assertEqual(r['skips'],{'missing_or_deleted_source':1})

    def test_05_tampered_user_text_excluded(self):
        event,_=self.add();self.conn.execute("UPDATE messages SET text='Compute 9 plus 9.' WHERE event_id=? AND role='user'",(event,));self.conn.commit()
        self.assertEqual(audit(self.home,self.session)['skips'],{'source_integrity_fail':1})

    def test_06_tampered_blob_excluded(self):
        _,h=self.add();(self.home/'data/blobs'/h).write_text('tampered')
        self.assertEqual(audit(self.home,self.session)['skips'],{'source_integrity_fail':1})

    def test_07_symlink_blob_excluded(self):
        _,h=self.add();p=self.home/'data/blobs'/h;p.unlink();p.symlink_to(self.db)
        self.assertEqual(audit(self.home,self.session)['skips'],{'source_integrity_fail':1})

    def test_08_duplicate_final_excluded(self):
        event,_=self.add();self.conn.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata) VALUES(?,?,?,?,?,?)",(self.session,event,'assistant','4','FINAL','{}'));self.conn.commit()
        self.assertEqual(audit(self.home,self.session)['skips'],{'missing_or_ambiguous_final':1})

    def test_09_cross_session_message_excluded(self):
        event,_=self.add();self.conn.execute("UPDATE messages SET session_id='chat_b' WHERE event_id=? AND role='assistant'",(event,));self.conn.commit()
        self.assertEqual(audit(self.home,self.session)['skips'],{'cross_session_message':1})

    def test_10_db_bytes_unchanged_and_no_raw_leak(self):
        self.add();before=hashlib.sha256(self.db.read_bytes()).hexdigest()
        report=json.dumps(audit(self.home,self.session));after=hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.assertEqual(before,after);self.assertNotIn('Compute 2 plus 2.',report);self.assertNotIn('chat_a',report)

    def test_11_bad_limits_and_missing_session(self):
        for limit in (0,1001,True):
            with self.assertRaises(ValueError):audit(self.home,self.session,limit)
        with self.assertRaises(ValueError):audit(self.home,'')

    def test_12_database_symlink_rejected(self):
        self.conn.close()
        target=self.home/'data/db/real.sqlite3';self.db.rename(target);self.db.symlink_to(target.name)
        with self.assertRaisesRegex(ValueError,'database_missing_or_symlink'):audit(self.home,self.session)
        self.db.unlink();target.rename(self.db)
        self.conn=sqlite3.connect(self.db)

    def test_13_parent_blob_symlink_rejected(self):
        self.add()
        original=self.home/'data/blobs';moved=self.home/'data/blob_storage';original.rename(moved);original.symlink_to(moved.name)
        self.assertEqual(audit(self.home,self.session)['skips'],{'source_integrity_fail':1})
        original.unlink();moved.rename(original)

    def test_14_read_only_live_wal_snapshot(self):
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.add();self.add('Compute 3 plus 4.','7')
        r=audit(self.home,self.session)
        self.assertEqual(r['source_verified'],2)
        self.assertEqual(r['verdicts']['CORRECT'],2)

    def test_15_real_v13_store_integration_if_available(self):
        try:
            from v13.config import initialize
            from v13.store import Store
        except ImportError:self.skipTest('full V13 Store unavailable in isolated local scratch')
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);initialize(home)
            store=Store(home)
            try:
                sid=store.new_session();p=store.accept_turn(sid,'Compute 2 plus 2.',4,64000,16000)
                eid=p['event_id'];self.assertTrue(store.claim_turn(eid))
                mid=store.message(sid,eid,'assistant','4','DRAFT',{})
                store.finish_message(mid,'FINAL',{});store.finish_turn(eid,'FINAL')
            finally:store.close()
            report=audit(home,sid)
            self.assertEqual(report['source_verified'],1)
            self.assertEqual(report['verdicts']['CORRECT'],1)

if __name__=='__main__':unittest.main()
