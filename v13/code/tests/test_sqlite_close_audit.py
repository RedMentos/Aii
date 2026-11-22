"""Close-boundary SQLite audit: checkpoint result, read-only integrity probe, sidecar preservation."""
from pathlib import Path
import importlib.util
import tempfile
import unittest
from v13.common import file_hash
from v13.config import initialize
from v13.store import Store,audit_closed,preserve_sqlite

APP=Path(__file__).resolve().parents[1]

class CloseAudit(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);initialize(self.home)
        self.db=self.home/'data/db/brain.sqlite3'
        s=Store(self.home);sid=s.new_session()
        for i in range(200):s.event(sid,'Zeile '+str(i)+' '+'x'*400)
        s.close();self.checkpoint=s.last_checkpoint
    def tearDown(self):self.tmp.cleanup()
    def test_clean_close_passes_without_mutation(self):
        self.assertEqual(self.checkpoint[0],0)
        before=file_hash(self.db);audit=audit_closed(self.home)
        self.assertTrue(audit['ok']);self.assertEqual(audit['page_count']*audit['page_size'],audit['file_bytes'])
        self.assertEqual(file_hash(self.db),before)
    def test_truncated_tail_is_detected_and_preserved(self):
        data=self.db.read_bytes();self.db.write_bytes(data[:len(data)//2])
        audit=audit_closed(self.home);self.assertFalse(audit['ok'])
        out=self.home/'kept';copied=preserve_sqlite(self.home,out)
        self.assertEqual(copied['brain.sqlite3']['sha256'],file_hash(self.db))
        with self.assertRaises(FileExistsError):preserve_sqlite(self.home,out)
    def test_collector_guard_stops_at_first_failing_boundary(self):
        spec=importlib.util.spec_from_file_location('lifecycle',APP/'tests/integration_causal_output_lifecycle.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        row={'index':8};m.guard_closed(self.home,self.home,row,'runtime-close')
        self.assertTrue(row['sqlite_boundaries'][0]['ok'])
        data=self.db.read_bytes();self.db.write_bytes(data[:len(data)//2]);damaged=file_hash(self.db)
        with self.assertRaises(ValueError):m.guard_closed(self.home,self.home,row,'export-close')
        kept=self.home/'sqlite-boundary-failure-row-8-export-close'
        self.assertEqual(file_hash(kept/'brain.sqlite3'),damaged);self.assertEqual(file_hash(self.db),damaged)

if __name__=='__main__':unittest.main()
