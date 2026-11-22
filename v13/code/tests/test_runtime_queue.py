"""Actual source-copy turns exercise durable coordinator behavior, no LM claims."""
import tempfile
import time
import unittest
from pathlib import Path
from v13.runtime import Runtime


class DurableRuntimeQueue(unittest.TestCase):
    def wait(self,r):
        end=time.monotonic()+5
        while not r.idle() and time.monotonic()<end:time.sleep(.01)
        self.assertTrue(r.idle())

    def test_paused_restart_preserves_pending_fifo_and_no_duplicate_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);r=Runtime(h);r.pause()
            first=r.submit('Kopiere exakt: eins');second=r.submit('Kopiere exakt: zwei')
            r.close();r=Runtime(h)
            try:
                self.assertTrue(r.paused);self.assertEqual(r.store.queue_stats()['count'],2)
                self.assertEqual(r.store.rows("SELECT * FROM messages WHERE role='assistant'"),[])
                r.resume();self.wait(r)
                rows=r.store.rows("SELECT event_id,text,status FROM messages WHERE role='assistant' ORDER BY id")
                self.assertEqual(rows,[{'event_id':first,'text':'eins','status':'FINAL'},{'event_id':second,'text':'zwei','status':'FINAL'}])
                self.assertEqual([row['state'] for row in r.store.rows('SELECT state FROM accepted_turns ORDER BY sequence')],['DONE','DONE'])
                r.close();r=Runtime(h);self.wait(r)
                self.assertEqual(len(r.store.rows("SELECT * FROM messages WHERE role='assistant'")),2)
            finally:r.close()

    def test_restart_queue_expiry_is_visible_and_never_generates_late_answer(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);r=Runtime(h);r.pause();eid=r.submit('Kopiere exakt: zu spät')
            with r.store.tx() as c:c.execute('UPDATE accepted_turns SET accepted_at=? WHERE event_id=?',(time.time()-r.cfg['queue_ttl_seconds']-2,eid))
            r.close();r=Runtime(h)
            try:
                r.resume();self.wait(r);row=r.last_answer()
                self.assertEqual(row['status'],'ERROR');self.assertIn('Warteschlangen-Zeitlimit',row['text'])
                self.assertEqual(r.store.one('SELECT state FROM accepted_turns WHERE event_id=?',(eid,))['state'],'ERROR')
            finally:r.close()

    def test_failed_turn_is_terminal_and_following_real_source_copy_runs(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d));r.pause();first=r.submit('Fehlgeschlagener Testauftrag');second=r.submit('Kopiere exakt: weiter')
            original=r._turn
            def fail_one(event):
                if event['event_id']==first:raise ValueError('Injected coordinator failure')
                return original(event)
            r._turn=fail_one
            try:
                r.resume();self.wait(r)
                self.assertEqual([row['state'] for row in r.store.rows('SELECT state FROM accepted_turns ORDER BY sequence')],['ERROR','DONE'])
                self.assertEqual(r.last_answer()['event_id'],second);self.assertEqual(r.last_answer()['text'],'weiter')
            finally:r.close()


if __name__=='__main__':unittest.main()
