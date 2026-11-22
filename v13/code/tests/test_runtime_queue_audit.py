"""Durable-queue regression cases found by independent Runtime review."""
from pathlib import Path
import tempfile
import time
import unittest
from v13.config import initialize,save_config
from v13.runtime import Runtime
from v13.store import Store

class RuntimeQueueAudit(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);cfg=initialize(self.home);cfg['observer_mode']='off';save_config(self.home,cfg);self.r=None
    def tearDown(self):
        if self.r:self.r.close()
        self.tmp.cleanup()
    def wait(self,seconds=4):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if not self.r.worker.is_alive() or self.r.idle():break
            time.sleep(.02)
    def test_packet_write_error_before_turn_try_keeps_worker_live_and_next_turn_usable(self):
        self.r=Runtime(self.home);self.r.pause()
        self.r.store.db.execute("CREATE TRIGGER snapshot_reject BEFORE INSERT ON packets WHEN NEW.kind='OutputSnapshot' BEGIN SELECT RAISE(ABORT,'actual snapshot write failure'); END")
        eid=self.r.submit('Kopiere exakt: erstes');self.r.resume();self.wait()
        self.assertTrue(self.r.worker.is_alive(),'Prefinal SQLite failure killed coordinator')
        self.assertTrue(self.r.idle(),'Failed user turn kept coordinator busy')
        queue=self.r.store.one('SELECT state FROM accepted_turns WHERE event_id=?',(eid,));self.assertIn(queue['state'],{'ERROR','INTERRUPTED'})
        assistant=self.r.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant'",(eid,));self.assertIn(assistant['status'],{'ERROR','INTERRUPTED'})
        self.r.store.db.execute('DROP TRIGGER snapshot_reject');second=self.r.submit('Kopiere exakt: zweites');self.wait()
        self.assertTrue(self.r.idle());answer=self.r.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant'",(second,));self.assertEqual((answer['text'],answer['status']),('zweites','FINAL'))
    def test_restart_pending_original_session_never_writes_into_last_opened_chat(self):
        s=Store(self.home);first=s.new_session();e=s.accept_turn(first,'Kopiere exakt: gehört zu erstem Chat',4,64000,16000);second=s.new_session();s.set_queue_paused(True);s.close()
        self.r=Runtime(self.home);self.assertEqual(self.r.session,second);self.r.resume();self.wait()
        self.assertTrue(self.r.worker.is_alive());self.assertTrue(self.r.idle())
        answers=self.r.store.rows("SELECT * FROM messages WHERE event_id=? AND role='assistant'",(e['event_id'],))
        self.assertEqual(len(answers),1);self.assertEqual(answers[0]['session_id'],first)
        self.assertEqual((answers[0]['text'],answers[0]['status']),('gehört zu erstem Chat','FINAL'))
        self.assertEqual(self.r.session,second,'Execution changed selected chat')
