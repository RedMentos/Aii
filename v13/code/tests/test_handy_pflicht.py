import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import handy_pflicht as H  # noqa: E402
import z7_residency_bench as Z  # noqa: E402


def fake_commands(step, stage, home, out):
    if step == 'training':
        return None, 0
    if step == 'langlauf':
        return [sys.executable, '-c', 'import time; time.sleep(30)'], 1
    code = "import json,sys; open(sys.argv[1],'w').write(json.dumps({'step': sys.argv[2]}))"
    return [sys.executable, '-c', code, str(out/(step+'.json')), step], 60


class HandyPflichtTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.base = Path(self.tmp.name)
        self.home = self.base/'home'; (self.home/'exports').mkdir(parents=True); self.target = self.base/'dl'

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *extra):
        check = {'installed': True, 'problems': [], 'warnings': [], 'chat_running': False, 'mem': {}, 'cpu_count': 4}
        with mock.patch.object(H.W, 'precheck', return_value=check), mock.patch.object(H, 'commands', fake_commands), \
             mock.patch.object(H.W, 'wake_lock', return_value=False):
            return H.main(['kurz', '--installed-home', str(self.home), '--target-dir', str(self.target), *extra])

    def test_steps_run_resume_and_honest_training(self):
        rc = self.run_main()
        self.assertEqual(rc, 1)  # langlauf hit its deadline
        state = json.loads((self.home/'exports/handy-pflicht-kurz/zustand.json').read_text())['steps']
        self.assertEqual(state['ram']['status'], 'DONE'); self.assertEqual(state['langlauf']['status'], 'DEADLINE')
        self.assertEqual(state['training']['status'], 'NOT_BUILT')
        zips = sorted(self.target.glob('V13-Pflicht-Ergebnis-kurz-*.zip')); self.assertEqual(len(zips), 1)
        with zipfile.ZipFile(zips[0]) as z:
            names = z.namelist(); text = z.read('KURZ.txt').decode()
        self.assertIn('lauf/ram/ram.json', names); self.assertIn('noch nicht gebaut', text)
        os.remove(zips[0])
        with mock.patch.object(H, 'run_step', wraps=H.run_step) as spy:
            self.run_main('--nur', 'ram,residenz')
            self.assertEqual(spy.call_count, 0)  # both already DONE -> skipped
        with mock.patch.object(H, 'run_step', wraps=H.run_step) as spy:
            self.run_main('--nur', 'ram', '--neu')
            self.assertEqual(spy.call_count, 1)

    def test_unknown_step_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_main('--nur', 'quatsch')


class ResidencyHelpersTest(unittest.TestCase):
    def test_proc_stats_and_summary(self):
        st = Z.proc_stats(os.getpid())
        self.assertGreater(st['rss_mb'], 0); self.assertIn('majflt', st)
        dev = {'mem_available_mb': 100, 'battery_temp_c': None, 'battery_percent': None, 'charging': None}
        rows = [{'pass': True, 'answer_s': 2., 'first_offer_s': 1., 'wall_s': 3., 'processes': [dict(st, name='llama-server')],
                 'device_before': dev, 'device_after': dev}]
        s = Z.summarize(rows)
        self.assertEqual(s['passed'], 1); self.assertEqual(s['hwm_mb_by_process']['llama-server'], st['hwm_mb'])
        self.assertIsNone(s['battery_drop_percent'])


if __name__ == '__main__':
    unittest.main()
