"""Run204: actual Age-0 Runtime source -> memory -> C3 context -> restart -> forget.

C3 is a deterministic test double, not native inference or proof of learning utility.
The double emits a correction only if the actual Runtime system context contains it.
"""
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from v13.operator import Operator
from v13.runtime import Runtime

QUERY='Projekt Alpha Budget?'
CORRECTION='120 Euro'


class SecondTurnC3MemoryPipelineRun204(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.captures=[]
        self.r=Runtime(self.home)
        self.wire()

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def wire(self):
        Operator(self.r).run(':observers off')
        self.r.sleep.cycle.set_policy('enabled','off')
        self.r.cfg.update(route_override='simple',history_turns=0)
        def generate(messages,*args,**kwargs):
            self.captures.append(messages)
            system=' '.join(m['content'] for m in messages if m['role']=='system')
            return iter([CORRECTION if CORRECTION in system else 'unknown'])
        fake=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'test_seam':True},generate=generate)
        self.r.pool.get=Mock(return_value=fake)
        self.r.learner.output_delta=Mock(return_value=None)

    def ask(self,text=QUERY):
        self.r.submit(text)
        deadline=time.monotonic()+15
        while not self.r.idle() and time.monotonic()<deadline:
            time.sleep(.01)
        self.assertTrue(self.r.idle(),'Runtime did not finish test turn')
        answer=self.r.last_answer()
        self.assertEqual(answer['status'],'FINAL',answer)
        return answer

    def has_correction_in_system(self):
        self.assertTrue(self.captures,'C3 test double was not called')
        return any(CORRECTION in m['content'] for m in self.captures[-1] if m['role']=='system')

    def test_second_turn_uses_persisted_human_correction_after_restart_then_forget(self):
        first=self.ask()
        self.assertEqual(first['text'],'unknown')
        self.assertFalse(self.has_correction_in_system())
        mid=self.r.memory.feedback(first['event_id'],'fact',CORRECTION,key=QUERY)
        original_session=self.r.session
        self.r.close()
        self.r=Runtime(self.home)
        self.wire()
        self.assertEqual(self.r.session,original_session)
        second=self.ask()
        self.assertEqual(second['text'],CORRECTION)
        self.assertTrue(self.has_correction_in_system())
        self.assertEqual(self.r.cfg['learning_mode'],'RECORD_ONLY')
        self.r.memory.forget(mid)
        third=self.ask()
        self.assertEqual(third['text'],'unknown')
        self.assertFalse(self.has_correction_in_system())

    def test_session_only_correction_does_not_enter_another_chat_context(self):
        first=self.ask()
        self.r.memory.feedback(first['event_id'],'fact',CORRECTION,key=QUERY,scope='session')
        other=self.r.store.new_session()
        self.r.session=other
        self.assertEqual(self.ask()['text'],'unknown')
        self.assertFalse(self.has_correction_in_system())

    def test_corrupted_key_does_not_retarget_human_value_to_other_project(self):
        first=self.ask()
        mid=self.r.memory.feedback(first['event_id'],'fact',CORRECTION,key=QUERY)
        with self.r.store.tx() as conn:
            conn.execute('UPDATE memories SET key_text=? WHERE id=?',('Projekt Beta Budget?',mid))
        self.assertEqual(self.ask('Projekt Beta Budget?')['text'],'unknown')
        self.assertFalse(self.has_correction_in_system())


if __name__=='__main__':unittest.main()
