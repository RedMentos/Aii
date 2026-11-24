"""Run44 disk-backed SQLite immutable read-only CLI, no native inference."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zlib

from scripts import run44_b2_shadow_readonly_cli as c
from tests.test_run40_b2_store_history_readonly import Store
from tests.test_run42_b2_eligibility_source_shadow import RULE, SHEET, CURRENT


class OfflineViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / 'installed'
        (self.home/'data/db').mkdir(parents=True)
        (self.home/'data/blobs').mkdir(parents=True)
        (self.home/'data/coordinator.lock').touch()
        self.s = Store()
        self.rule = self.s.event(RULE); self.s.offer(self.rule)
        for _ in range(5):
            e=self.s.event(SHEET);self.s.offer(e)
        self.cur=self.s.event(CURRENT)
        self.dbfile=self.home/'data/db/brain.sqlite3'
        self.s.db.commit()  # sqlite backup waits indefinitely on an open writer transaction
        with sqlite3.connect(self.dbfile) as disk:
            self.s.db.backup(disk)
        for text in self.s.sources.values():
            h=hashlib.sha256(text.encode()).hexdigest()
            (self.home/'data/blobs'/h).write_bytes(text.encode())

    def tearDown(self):
        self.s.db.close()
        self.tmp.cleanup()

    def snapshot(self):
        return {str(p.relative_to(self.home)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.home.rglob('*') if p.is_file()}

    def test_diagnose_no_home_writes(self):
        before=self.snapshot()
        result=c.diagnose(self.home,self.cur['event_id'],'m')
        self.assertEqual(result['decision']['action'],'A')
        self.assertEqual(result['decision']['options'][0]['remaining'],45)
        self.assertEqual(result['authority'],'SHADOW_NO_AUTHORITY')
        self.assertEqual(before,self.snapshot())
        self.assertFalse(result['canonical_gate_pass'])

    def test_cli_output_outside_home_and_no_overwrite(self):
        out=Path(self.tmp.name)/'result.json'
        c.main(['--installed-home',str(self.home),'--event-id',self.cur['event_id'],
                '--model-revision','m','--out',str(out)])
        result=json.loads(out.read_text())
        self.assertEqual(result['decision']['action'],'A')
        self.assertEqual(os.stat(out).st_mode & 0o777,0o600)
        with self.assertRaisesRegex(ValueError,'RUN44_OUTPUT_PATH_REFUSED'):
            c.main(['--installed-home',str(self.home),'--event-id',self.cur['event_id'],
                    '--model-revision','m','--out',str(out)])

    def test_output_inside_installed_home_refused(self):
        with self.assertRaisesRegex(ValueError,'RUN44_OUTPUT_PATH_REFUSED'):
            c.main(['--installed-home',str(self.home),'--event-id',self.cur['event_id'],
                    '--model-revision','m','--out',str(self.home/'result.json')])

    def test_active_coordinator_refused(self):
        with (self.home/'data/coordinator.lock').open('rb') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,'RUN44_ACTIVE_COORDINATOR'):
                c.diagnose(self.home,self.cur['event_id'],'m')

    def test_nonempty_wal_refused(self):
        wal=self.dbfile.with_name('brain.sqlite3-wal');wal.write_bytes(b'not checkpointed')
        with self.assertRaisesRegex(ValueError,'RUN44_NOT_QUIESCENT_OR_INVALID_HOME'):
            c.diagnose(self.home,self.cur['event_id'],'m')

    def test_archived_rule_blob_read_with_hash_check(self):
        h=self.rule['source_ref']['sha256'];plain=self.home/'data/blobs'/h
        plain.with_name(h+'.z').write_bytes(zlib.compress(plain.read_bytes()))
        plain.unlink()
        self.assertEqual(c.diagnose(self.home,self.cur['event_id'],'m')['decision']['action'],'A')

    def test_tampered_old_rule_refused(self):
        h=self.rule['source_ref']['sha256'];(self.home/'data/blobs'/h).write_bytes(b'changed')
        self.assertEqual(c.diagnose(self.home,self.cur['event_id'],'m')['status'],'ABSTAIN_RULE_SOURCE')

    def test_symlink_old_rule_refused(self):
        h=self.rule['source_ref']['sha256'];plain=self.home/'data/blobs'/h
        copy=Path(self.tmp.name)/'outside.txt';copy.write_bytes(plain.read_bytes())
        plain.unlink();plain.symlink_to(copy)
        self.assertEqual(c.diagnose(self.home,self.cur['event_id'],'m')['status'],'ABSTAIN_RULE_SOURCE')

    def test_missing_event_refused(self):
        with self.assertRaisesRegex(ValueError,'RUN44_EVENT_NOT_FOUND'):
            c.diagnose(self.home,'evt_missing','m')


if __name__=='__main__':unittest.main()
