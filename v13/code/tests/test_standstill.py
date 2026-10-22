"""Full standstill (:stillstand, WP-SAFE2): tools, job queue (turns, learning, background), scheduler tick and Age
promotion stop together, the running job is confirmed stopped or reported, a restart stays still, release only undoes
what the command itself switched on. No models."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import prohibitions as P
from v13 import standstill as S
from v13 import age as agectl
from v13.agi.tools import ToolRegistry


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off');self.op=Operator(self.r)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def wait(self,cond,limit=5.):
        end=time.monotonic()+limit
        while not cond() and time.monotonic()<end:time.sleep(.01)
        return cond()


class EngageTests(Base):
    def test_all_parts_stop_and_idle_runtime_is_confirmed_still(self):
        out=self.op.run(':stillstand')
        self.assertIn('STILLSTAND AN',out);self.assertIn('Bestätigt',out);self.assertNotIn('NICHT angehalten',out)
        s=S.status(self.r);self.assertTrue(s['on'] and s['all_parts_on'] and s['confirmed_still'])
        self.assertTrue(self.r.paused and self.r.store.queue_paused());self.assertTrue(agectl.controller(self.r).view()['frozen'])
        reg=ToolRegistry(self.r.store);reg.enable('calc')
        self.assertEqual(reg.call('calc',{'expression':'1+1'},origin='USER')['reason'],'HARD_BLOCK:NOTAUS')

    def test_scheduler_tick_and_background_do_not_run_during_standstill(self):
        self.r.sleep.tick=Mock(return_value=None)
        self.assertTrue(self.wait(lambda:self.r.sleep.tick.call_count>0))  # baseline: the idle worker ticks
        S.engage(self.r);time.sleep(.3);n=self.r.sleep.tick.call_count;time.sleep(.6)
        self.assertEqual(self.r.sleep.tick.call_count,n)
        S.release(self.r);self.assertTrue(self.wait(lambda:self.r.sleep.tick.call_count>n))

    def test_queued_turn_is_not_answered_while_still(self):
        S.engage(self.r);self.r.submit('Hallo');time.sleep(.5)
        self.assertEqual(self.r.store.queue_stats()['count'],1);self.assertIsNone(self.r.current)

    def test_running_job_that_honours_cancel_is_confirmed_stopped(self):
        started=threading.Event()
        def dream():
            started.set()
            while not self.r.cancel_event.is_set():time.sleep(.01)
        self.r._dream=dream;self.r.enqueue('dream');self.assertTrue(started.wait(3))
        s=S.engage(self.r,wait=3)
        self.assertIsNone(s['running_job']);self.assertTrue(s['confirmed_still'])

    def test_job_that_ignores_cancel_is_reported_never_claimed_stopped(self):
        started=threading.Event();go=threading.Event()
        def dream():started.set();go.wait(3)
        self.r._dream=dream;self.r.enqueue('dream');self.assertTrue(started.wait(3))
        s=S.engage(self.r,wait=.1)
        self.assertEqual(s['running_job'],'dream');self.assertFalse(s['confirmed_still'])
        self.assertIn('ACHTUNG',S.text(s));go.set()
        self.assertTrue(self.wait(lambda:S.status(self.r)['confirmed_still']))


class ReleaseTests(Base):
    def test_release_only_undoes_what_standstill_set(self):
        self.op.run(':age freeze on')
        S.engage(self.r);self.assertEqual(S.status(self.r)['set_by_standstill'],{'notaus':True,'queue':True,'age':False})
        out=self.op.run(':stillstand aus')
        self.assertIn('aufgehoben',out);self.assertIn('Alterung',out)
        self.assertTrue(agectl.controller(self.r).view()['frozen']);self.assertFalse(self.r.paused)
        self.assertFalse(P.report(self.r.store)['notaus'])

    def test_user_notaus_before_standstill_survives_release(self):
        self.op.run(':notaus');S.engage(self.r);S.release(self.r)
        self.assertTrue(P.report(self.r.store)['notaus'])

    def test_repeated_engage_keeps_first_record(self):
        S.engage(self.r);S.engage(self.r)
        self.assertEqual(S.status(self.r)['set_by_standstill'],{'notaus':True,'queue':True,'age':True})
        S.release(self.r);self.assertFalse(any(S.parts(self.r).values()))

    def test_release_reports_background_that_resumes(self):
        S.engage(self.r);self.r.sleep.scheduler.post('TIMER',action='growth_consolidate',dedup='t')
        s=S.release(self.r);self.assertGreaterEqual(s['background_resumes'],1)
        self.assertIn('laufen jetzt wieder an',S.text(s))

    def test_release_without_standstill_changes_nothing(self):
        self.op.run(':pause');s=S.release(self.r);self.assertTrue(self.r.paused);self.assertFalse(s['on'])


class RestartTests(unittest.TestCase):
    def test_restart_stays_still(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d));r.sleep.cycle.set_policy('enabled','off');S.engage(r);r.close()
            r2=Runtime(Path(d))
            try:
                s=S.status(r2);self.assertTrue(s['on'] and s['all_parts_on']);self.assertTrue(r2.paused)
                S.release(r2);self.assertFalse(any(S.parts(r2).values()))
            finally:r2.close()


class TextTests(Base):
    def test_notaus_says_learning_continues_and_points_to_standstill(self):
        self.assertIn(':stillstand',self.op.run(':notaus'))
    def test_bad_argument(self):
        with self.assertRaises(ValueError):S.operator_command(self.r,['jetzt'])


if __name__=='__main__':unittest.main()
