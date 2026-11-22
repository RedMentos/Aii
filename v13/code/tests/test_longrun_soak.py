"""G13 long-run soak (scripts/longrun_soak.py) + the wake-replay starvation it found (fixture speaker, no models)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import longrun_soak as soak  # noqa: E402
from v13.runtime import Runtime  # noqa: E402
from v13.sleep import SleepRuntime  # noqa: E402

class Soak(unittest.TestCase):
    def test_three_days_with_restarts_pass_every_g13_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            rep=soak.soak(Path(tmp)/'home',days=3,turns=3,log=lambda *a:None)
            self.assertEqual(rep['verdict'],'PASS',json.dumps([d['checks'] for d in rep['days']]))
            self.assertEqual(rep['evidence_level'],'LINUX_SOFTWARE_FIXTURE_SPEAKER')
            for d in rep['days']:
                self.assertEqual((d['sleep']['mode'],d['sleep']['status']),('full','DONE'))
                self.assertEqual(d['recall']['recalled'],d['recall']['facts'])
                self.assertTrue(d['checks']['wake_priority']);self.assertTrue(d['checks']['carried_wakes_survive_restart'])
            self.assertEqual(rep['facts'],9);self.assertTrue(Path(rep['artifact']).is_file())

    def test_native_needs_separate_home(self):
        import contextlib,io
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):soak.main(['--home','/tmp/x','--native'])
            with self.assertRaises(SystemExit):soak.main(['--home','/tmp/x','--models-from','/tmp/x'])

class WakeReplayOncePerIdlePeriod(unittest.TestCase):
    def test_second_tick_in_same_idle_period_posts_no_new_wake_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Runtime(Path(tmp))
            try:
                clock=soak.Clock(2_000_000_000.)
                with soak.SimulatedWall(clock):
                    r.sleep=SleepRuntime(r,clock=clock);r.sleep.cycle.set_policy('sleep_idle_s','86400')
                    for i in range(3):
                        e=r.store.event(r.session,'Project W%d budget?'%i);r.memory.feedback(e['event_id'],'fact','%d euro'%i)
                    q=r.sleep.cycle.queue;st,v=q.load();q.sync(st,r.sleep.cycle.policy());q.save(st,v)  # rows known to the replay schedule
                    def actions(n=6):
                        out=[]
                        for _ in range(n):
                            e=r.sleep.tick(force=True);soak.wait_idle(r)
                            if e:out.append(e['action'])
                            clock.t+=10
                        return out
                    clock.t+=r.sleep.cycle.policy()['wake_replay_idle_s']+1
                    self.assertEqual(actions().count('wake_replay'),1)  # items stay due (Age-0: one per wake), still one per idle period
                    r.submit('new input');soak.wait_idle(r);clock.t+=r.sleep.cycle.policy()['wake_replay_idle_s']+1
                    self.assertEqual(actions().count('wake_replay'),1)  # the next idle period gets its own
            finally:r.close()

if __name__=='__main__':unittest.main()
