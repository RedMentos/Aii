"""Real SQLite migrations, admission transactions and process-death recovery."""
import concurrent.futures
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest
from v13.backup import backup,restore
from v13.common import dumps,file_hash
from v13.config import initialize
from v13.store import Store,DDL,SCHEMA_VERSION,audit_schema,migrate_database

class StoreFixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);initialize(self.home)
        self.path=self.home/'data/db/brain.sqlite3';self.store=None
    def tearDown(self):
        if self.store:self.store.close()
        self.tmp.cleanup()
    def open(self):self.store=Store(self.home);return self.store

class Migrations(StoreFixture):
    def legacy(self):
        s=self.open();sid=s.new_session();event=s.event(sid,'Unverändert: Budget 120 Euro');manifest=s.generation();s.close();self.store=None
        db=sqlite3.connect(self.path,isolation_level=None)
        db.executescript('DROP TABLE accepted_turns;DROP TABLE schema_migrations;PRAGMA user_version=1;');db.close()
        return sid,event,manifest
    def test_fresh_two_migrations_restart_and_immutable_history(self):
        s=self.open();journal=s.rows('SELECT * FROM schema_migrations ORDER BY version');self.assertEqual([(r['from_version'],r['version']) for r in journal],[(0,1),(1,2)])
        sid=s.new_session();event=s.event(sid,'Genau dieser Text');manifest=s.generation();s.close();s=self.open()
        self.assertEqual(s.db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
        self.assertEqual(s.rows('SELECT * FROM schema_migrations ORDER BY version'),journal);self.assertEqual(s.generation(),manifest)
        self.assertEqual(s.read_source(event['source_ref']),'Genau dieser Text');self.assertEqual(s.history(sid)[0]['text'],'Genau dieser Text');self.assertEqual(s.integrity(True),[])
    def test_legacy_one_data_is_upgraded_without_rewriting_generation(self):
        sid,event,manifest=self.legacy();s=self.open()
        self.assertEqual(s.generation(),manifest);self.assertEqual(s.read_source(event['source_ref']),'Unverändert: Budget 120 Euro')
        self.assertEqual(s.history(sid)[0]['text'],'Unverändert: Budget 120 Euro');self.assertEqual(s.pending_turns(),[])
        self.assertEqual([(r['from_version'],r['version']) for r in s.rows('SELECT * FROM schema_migrations')],[(1,2)])
    def test_failed_actual_ddl_rolls_back_and_retry_resumes_last_committed_version(self):
        db=sqlite3.connect(self.path,isolation_level=None)
        def authorizer(action,arg1,arg2,database,source):
            return sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_CREATE_INDEX and arg1=='accepted_turn_state' else sqlite3.SQLITE_OK
        db.set_authorizer(authorizer)
        with self.assertRaises(sqlite3.DatabaseError):migrate_database(db)
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],1)
        self.assertEqual(db.execute('SELECT version FROM schema_migrations').fetchall(),[(1,)])
        self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='accepted_turns'").fetchone());self.assertFalse(db.in_transaction)
        db.set_authorizer(None);migrate_database(db);db.close();s=self.open();self.assertEqual(len(s.rows('SELECT * FROM schema_migrations')),2)
    def test_future_version_rejection_changes_no_database_and_releases_lock(self):
        s=self.open();s.close();self.store=None
        db=sqlite3.connect(self.path);db.execute('PRAGMA user_version=3');db.close();before=file_hash(self.path)
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError,'neuer'):Store(self.home)
            self.assertEqual(file_hash(self.path),before)
        db=sqlite3.connect(self.path);db.execute('PRAGMA user_version=2');db.close();self.open()
    def test_malformed_one_and_two_are_rejected_without_silent_repair(self):
        self.legacy();db=sqlite3.connect(self.path);db.execute('DROP INDEX message_session');db.close()
        with self.assertRaisesRegex(RuntimeError,'indexes'):Store(self.home)
        db=sqlite3.connect(self.path);self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],1);self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='accepted_turns'").fetchone());db.execute('CREATE INDEX message_session ON messages(session_id,id)');db.close()
        s=self.open();s.close();self.store=None;db=sqlite3.connect(self.path);db.execute('DROP INDEX accepted_turn_state');db.close()
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError,'indexes'):Store(self.home)
    def test_migration_journal_corruption_rejected_by_doctor_and_startup(self):
        s=self.open();self.assertEqual(s.schema_audit()['migrations'],[1,2])
        s.db.execute("UPDATE schema_migrations SET ddl_sha256=? WHERE version=2",('f'*64,))
        self.assertTrue(any('Migrationsjournal' in error for error in s.integrity(True)))
        s.close();self.store=None
        with self.assertRaisesRegex(RuntimeError,'Migrationsjournal'):Store(self.home)
    def test_version_one_backup_verified_then_upgraded_before_restore(self):
        s=self.open();sid=s.new_session();event=s.event(sid,'Alte Version bleibt lesbar');archive=backup(s);s.event(sid,'Später');s.close();self.store=None
        stage=self.home/'tmp/legacy-archive';stage.mkdir()
        with tarfile.open(archive) as t:t.extractall(stage,filter='data')
        db=sqlite3.connect(stage/'data/db/brain.sqlite3');db.executescript('DROP TABLE accepted_turns;DROP TABLE schema_migrations;PRAGMA user_version=1;');db.close()
        manifest=json.loads((stage/'backup_manifest.json').read_text());manifest['hashes']['data/db/brain.sqlite3']=file_hash(stage/'data/db/brain.sqlite3');(stage/'backup_manifest.json').write_text(dumps(manifest))
        legacy=self.home/'old-v1.tar.gz'
        with tarfile.open(legacy,'w:gz') as t:
            for p in stage.rglob('*'):
                if p.is_file():t.add(p,arcname=str(p.relative_to(stage)))
        restore(self.home,legacy);s=self.open();self.assertEqual(s.db.execute('PRAGMA user_version').fetchone()[0],2)
        self.assertEqual([r['text'] for r in s.history(sid)],['Alte Version bleibt lesbar']);self.assertEqual(s.read_source(event['source_ref']),'Alte Version bleibt lesbar');self.assertEqual(s.integrity(True),[])

class PersistentQueue(StoreFixture):
    def accept(self,s,text='Wartende Eingabe',**kwargs):
        return s.accept_turn(self.sid,text,kwargs.get('queue_count',4),kwargs.get('queue_bytes',64000),kwargs.get('input_bytes',16000),kwargs.get('request_key'))
    def start(self):s=self.open();self.sid=s.new_session();return s
    def test_atomic_bounds_no_event_or_source_when_admission_rejected(self):
        s=self.start();self.accept(s,'ää',queue_count=1,queue_bytes=4,input_bytes=4)
        before={t:s.rows('SELECT * FROM '+t) for t in ['sources','events','messages','accepted_turns']}
        for text,kwargs in [('x',{'queue_count':1}),('too long',{'input_bytes':2}),(' ',{})]:
            with self.assertRaises((ValueError,RuntimeError)):self.accept(s,text,**kwargs)
        self.assertEqual({t:s.rows('SELECT * FROM '+t) for t in before},before);self.assertEqual(s.queue_stats()['bytes'],4)
    def test_actual_sql_abort_leaves_no_accepted_event(self):
        s=self.start()
        s.db.execute("CREATE TRIGGER queue_reject BEFORE INSERT ON accepted_turns BEGIN SELECT RAISE(ABORT,'injected disk/write failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.accept(s)
        for table in ('sources','events','messages','accepted_turns'):self.assertEqual(s.rows('SELECT * FROM '+table),[])
        s.db.execute('DROP TRIGGER queue_reject');self.accept(s);self.assertEqual(s.queue_stats()['count'],1)
    def test_concurrent_admission_capacity_and_duplicate_retry(self):
        s=self.start()
        def accept(i):
            try:return self.accept(s,str(i),queue_count=4,request_key='key-'+str(i))['event_id']
            except RuntimeError:return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(accept,range(8)))
        self.assertEqual(sum(r is not None for r in results),4);self.assertEqual(len(s.rows('SELECT * FROM events')),4)
        accepted=next(i for i,r in enumerate(results) if r);event=self.accept(s,str(accepted),request_key='key-'+str(accepted))
        self.assertEqual(event['event_id'],results[accepted]);self.assertEqual(len(s.rows('SELECT * FROM events')),4)
        with self.assertRaisesRegex(ValueError,'anders'):self.accept(s,'different',request_key='key-'+str(accepted))
    def test_fifo_pause_finish_and_dedup_survive_restart(self):
        s=self.start();first=self.accept(s,'eins',request_key='first');second=self.accept(s,'zwei');s.set_queue_paused(True);s.close();s=self.open()
        self.assertTrue(s.queue_paused());self.assertFalse(s.claim_turn(first['event_id']));s.set_queue_paused(False)
        self.assertFalse(s.claim_turn(second['event_id']));self.assertTrue(s.claim_turn(first['event_id']));self.assertFalse(s.claim_turn(first['event_id']))
        s.message(self.sid,first['event_id'],'assistant','Tatsächlicher gespeicherter Testtext','FINAL');self.assertTrue(s.finish_turn(first['event_id'],'FINAL'));self.assertFalse(s.finish_turn(first['event_id'],'FINAL'))
        self.assertTrue(s.claim_turn(second['event_id']));s.finish_turn(second['event_id'],'CANCELLED');s.close();s=self.open()
        self.assertEqual(s.pending_turns(),[]);self.assertEqual(self.accept(s,'eins',request_key='first')['event_id'],first['event_id']);self.assertFalse(s.claim_turn(first['event_id']))
    def test_process_exit_preserves_pending_pause_and_partial_without_reexecution(self):
        script="""from pathlib import Path
import os,sys
from v13.config import initialize
from v13.store import Store
h=Path(sys.argv[1]);initialize(h);s=Store(h);sid=s.new_session();a=s.accept_turn(sid,'erste',4,64000,16000);b=s.accept_turn(sid,'zweite',4,64000,16000);s.claim_turn(a['event_id']);mid=s.message(sid,a['event_id'],'assistant');s.append_message(mid,'partial bleibt');s.set_queue_paused(True);os._exit(23)
"""
        result=subprocess.run([sys.executable,'-c',script,str(self.home)],capture_output=True,text=True);self.assertEqual(result.returncode,23,result.stderr)
        s=self.open();rows=s.rows('SELECT * FROM accepted_turns ORDER BY sequence');self.assertEqual([r['state'] for r in rows],['INTERRUPTED','PENDING']);self.assertTrue(s.queue_paused())
        answer=s.one("SELECT * FROM messages WHERE role='assistant'");self.assertEqual((answer['text'],answer['status']),('partial bleibt','INTERRUPTED'))
        self.assertEqual(len(s.pending_turns()),1);self.assertFalse(s.claim_turn(rows[0]['event_id']));s.close();s=self.open();self.assertEqual(len(s.pending_turns()),1);self.assertEqual(s.integrity(True),[])
    def test_completed_output_crash_window_not_reexecuted(self):
        s=self.start();e=self.accept(s);self.assertTrue(s.claim_turn(e['event_id']));s.message(self.sid,e['event_id'],'assistant','persistiert','FINAL');s.close();s=self.open()
        self.assertEqual(s.one('SELECT state FROM accepted_turns')['state'],'DONE');self.assertEqual(s.pending_turns(),[]);self.assertFalse(s.claim_turn(e['event_id']))
    def test_source_revoked_cannot_be_claimed(self):
        s=self.start();e=self.accept(s)
        with s.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(e['source_ref']['source_id'],))
        self.assertFalse(s.claim_turn(e['event_id']));self.assertEqual(s.one('SELECT state FROM accepted_turns')['state'],'CANCELLED')
