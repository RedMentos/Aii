"""Age-based diagnostic expiry excludes sources, chats and proof artifacts."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from v13.config import initialize
from v13.runtime import Runtime
from v13.resources import prune_runner_logs
from v13.operator import Operator

class LogRetention(unittest.TestCase):
    def test_restart_expires_diagnostics_and_preserves_exact_history_and_proofs(self):
        with tempfile.TemporaryDirectory() as td:
            h=Path(td);r=Runtime(h);e=r.store.event(r.session,'Retained original input');r.store.message(r.session,e['event_id'],'assistant','Retained output','FINAL')
            r.store.log('test',e['event_id'],{'count':1});r.store.log('test',e['event_id'],{'count':2});old=time.time()-15*86400
            with r.store.tx() as c:c.execute('UPDATE telemetry SET created=? WHERE id=(SELECT MIN(id) FROM telemetry)',(old,))
            for name in ('logs/B1_DETAIL.log','logs/B1_DETAIL.previous.log','exports/proof.json','logs/user-notes.txt'):
                p=h/name;p.write_text('retained unless diagnostic');os.utime(p,(old,old))
            fresh=h/'logs/C3_LANGUAGE.log';fresh.write_text('fresh');session=r.session;r.close();r=Runtime(h)
            try:
                self.assertEqual(len(r.store.rows('SELECT * FROM telemetry')),1);self.assertEqual(r.session,session)
                self.assertFalse((h/'logs/B1_DETAIL.log').exists());self.assertFalse((h/'logs/B1_DETAIL.previous.log').exists());self.assertTrue(fresh.exists())
                self.assertTrue((h/'exports/proof.json').exists());self.assertTrue((h/'logs/user-notes.txt').exists())
                self.assertEqual(r.store.read_source(e['source_ref']),'Retained original input');self.assertEqual(r.last_answer()['text'],'Retained output')
            finally:r.close()
    def test_old_symlink_does_not_delete_target(self):
        with tempfile.TemporaryDirectory() as td:
            h=Path(td);initialize(h);target=h/'exports/proof.json';target.write_text('proof');old=time.time()-20*86400;os.utime(target,(old,old));(h/'logs/C2_CONTROL.log').symlink_to(target)
            self.assertEqual(prune_runner_logs(h,14),0);self.assertTrue(target.exists());self.assertTrue((h/'logs/C2_CONTROL.log').is_symlink())
    def test_operator_budget_applies_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as td:
            h=Path(td);r=Runtime(h)
            try:
                r.store.log('test',None,{'count':1})
                with r.store.tx() as c:c.execute('UPDATE telemetry SET created=?',(time.time()-3*86400,))
                Operator(r).run(':budget log_retention_days 2');self.assertEqual(r.store.rows('SELECT * FROM telemetry'),[])
            finally:r.close()
            r=Runtime(h)
            try:self.assertEqual(r.store.log_retention_days,2)
            finally:r.close()

if __name__=='__main__':unittest.main()
