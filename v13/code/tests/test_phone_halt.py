"""Home-screen stop buttons (WP-UI1): a request file in <home>/control/ switches Notaus/Stillstand on in the running
chat with the same functions as the typed commands, only ever ON, applied at start, never twice. No models."""
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from v13.runtime import Runtime
from v13 import phone_halt as H
from v13 import prohibitions as P
from v13 import standstill as S
from v13.agi.tools import ToolRegistry

APP=Path(__file__).resolve().parents[1]


class ButtonTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off');self.seen=[]
    def tearDown(self):self.r.stop.set();self.r.close();self.tmp.cleanup()
    def press(self,name):(H.control_dir(self.home)/name).touch()
    def wait(self,cond,limit=5.):
        end=time.monotonic()+limit
        while not cond() and time.monotonic()<end:time.sleep(.02)
        return cond()

    def test_notaus_button_blocks_tools_in_running_chat(self):
        H.watch(self.r,self.seen.append,poll=.05);self.press('NOTAUS')
        self.assertTrue(self.wait(lambda:P.report(self.r.store)['notaus']))
        reg=ToolRegistry(self.r.store);reg.enable('calc')
        self.assertEqual(reg.call('calc',{'expression':'1+1'},origin='USER')['reason'],'HARD_BLOCK:NOTAUS')
        self.assertTrue(self.wait(lambda:any('NOTAUS AN' in t for t in self.seen)))
        self.assertEqual(H.pending(self.home),[])

    def test_stillstand_button_waiting_at_start_is_applied_before_first_input(self):
        self.press('STILLSTAND');self.press('NOTAUS')
        H.watch(self.r,self.seen.append,poll=10)  # long poll: only the start check can have applied it
        s=S.status(self.r);self.assertTrue(s['on'] and s['all_parts_on'])
        self.assertEqual(len(self.seen),1);self.assertIn('STILLSTAND AN',self.seen[0])
        self.assertEqual(H.pending(self.home),[])  # NOTAUS was covered by the standstill, not applied twice

    def test_button_never_releases_and_handled_file_does_not_reapply(self):
        self.press('STILLSTAND');H.apply_once(self.r,self.seen.append)
        S.release(self.r);self.assertFalse(S.status(self.r)['on'])
        H.apply_once(self.r,self.seen.append)  # renamed file must not count again
        self.assertFalse(S.status(self.r)['on']);self.assertFalse(P.report(self.r.store)['notaus'])
        done=[p.name for p in H.control_dir(self.home).iterdir()]
        self.assertTrue(any(n.startswith('STILLSTAND.erledigt-') for n in done))
        for name in ('AUS','NOTAUS_AUS','stillstand aus'):self.press(name)  # unknown names are ignored
        self.assertEqual(H.apply_once(self.r),[]);self.assertFalse(P.report(self.r.store)['notaus'])


class InstallerTests(unittest.TestCase):
    def test_installer_writes_four_buttons_that_only_drop_request_files(self):
        with tempfile.TemporaryDirectory() as t:
            env=dict(os.environ,HOME=t,PREFIX='/usr',V13_HOME=t+'/v13')
            subprocess.run(['bash',str(APP/'KNOEPFE_EINRICHTEN.sh')],env=env,check=True,capture_output=True)
            sc=Path(t)/'.shortcuts'
            for n in ('V13 Chat','V13 Status','tasks/V13 Notaus','tasks/V13 Stillstand'):
                self.assertTrue((sc/n).is_file(),n);self.assertEqual((sc/n).stat().st_mode&0o777,0o700)
            subprocess.run(['bash',str(sc/'tasks/V13 Stillstand')],env=env,check=True,capture_output=True)
            self.assertEqual(H.pending(Path(t)/'v13'),['STILLSTAND'])
            for n in ('tasks/V13 Notaus','tasks/V13 Stillstand'):
                self.assertNotIn(' aus',(sc/n).read_text().split('msg=')[0])  # a button cannot lift a stop
            subprocess.run(['bash',str(APP/'KNOEPFE_EINRICHTEN.sh'),'weg'],env=env,check=True,capture_output=True)
            self.assertFalse((sc/'V13 Chat').exists())


if __name__=='__main__':unittest.main()
