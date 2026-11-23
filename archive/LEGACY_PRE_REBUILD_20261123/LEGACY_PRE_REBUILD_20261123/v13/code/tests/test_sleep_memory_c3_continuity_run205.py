"""Run205: manual Age-0 Sleep A/B/C preserves source-bound corrections without promotion.

Actual Runtime/SleepCycle and deterministic C3 test double; no native inference.
"""
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from v13.age import BUILD_CEILING
from v13.operator import Operator
from v13.runtime import Runtime

QUERY='Projekt Alpha Budget?'
CORRECTION='120 Euro'
PHASES=('SLEEP_A','SLEEP_A_OFFLINE','SLEEP_B','SLEEP_C')


class SleepMemoryC3ContinuityRun205(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.r=Runtime(Path(self.tmp.name))
        Operator(self.r).run(':observers off')
        self.r.sleep.cycle.set_policy('enabled','off')
        self.r.cfg.update(route_override='simple',history_turns=0)
        self.captured=[]
        def generate(messages,*args,**kwargs):
            self.captured.append(messages)
            context=' '.join(m['content'] for m in messages if m['role']=='system')
            return iter([CORRECTION if CORRECTION in context else 'unknown'])
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'test_seam':True},generate=generate))
        self.r.learner.output_delta=Mock(return_value=None)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def correct(self):
        e=self.r.store.event(self.r.session,QUERY)
        return self.r.memory.feedback(e['event_id'],'fact',CORRECTION,key=QUERY)

    def sleep(self):
        before=self.r.store.generation_id
        report=self.r.sleep.cycle.run('full',origin='USER')
        self.assertEqual(report['status'],'DONE',report)
        self.assertEqual(tuple(x['phase'] for x in report['phases']),PHASES)
        self.assertTrue(all(x['status']=='DONE' for x in report['phases']))
        self.assertEqual(report['fact_write_authority'],0)
        self.assertFalse(report['weight_updates'])
        self.assertEqual(self.r.store.generation_id,before)
        self.assertEqual(BUILD_CEILING,0)
        return report

    def ask(self):
        self.r.submit(QUERY)
        until=time.monotonic()+15
        while not self.r.idle() and time.monotonic()<until:time.sleep(.01)
        self.assertTrue(self.r.idle())
        ans=self.r.last_answer()
        self.assertEqual(ans['status'],'FINAL',ans)
        return ans['text']

    def test_full_sleep_keeps_exact_human_correction_available_to_c3(self):
        mid=self.correct()
        self.sleep()
        self.assertEqual([m['id'] for m in self.r.memory.recall(QUERY,self.r.session)],[mid])
        self.assertEqual(self.ask(),CORRECTION)
        self.assertTrue(any(CORRECTION in m['content'] for m in self.captured[-1] if m['role']=='system'))
        self.assertEqual(self.r.cfg['learning_mode'],'RECORD_ONLY')

    def test_full_sleep_cannot_resurrect_a_forgotten_correction(self):
        mid=self.correct()
        self.r.memory.forget(mid)
        self.sleep()
        self.assertEqual(self.r.memory.recall(QUERY,self.r.session),[])
        self.assertEqual(self.ask(),'unknown')
        self.assertFalse(any(CORRECTION in m['content'] for m in self.captured[-1] if m['role']=='system'))

    def test_repeated_sleep_keeps_one_human_record_and_no_weight_change(self):
        mid=self.correct()
        before=self.r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='MemoryRecord'")['n']
        self.sleep()
        self.sleep()
        after=self.r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='MemoryRecord'")['n']
        self.assertEqual(after,before)
        self.assertEqual([m['id'] for m in self.r.memory.recall(QUERY,self.r.session)],[mid])


if __name__=='__main__':unittest.main()
