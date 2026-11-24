import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP / 'scripts'))
import werkzeug_handy as W

# Shape of docs/proofs/continuation-20261013/tool-forecast-device-learning-cloud/report.json (proofs are not in the
# phone ZIP, so the selftest carries its own copy of the fields the summary reads).
CLOUD = {
    'status': 'LIVE_PATH_CONFIRMED+CONTINUAL_LEARNING_CONFIRMED', 'parity_seconds': 132.6,
    'parity': {'gate': .98, 'status': 'PASS', 'worlds': {
        'calc_counter': {'pass': True, 'ratio_to_best_control': {'add_15': .0947, 'double': .1344, 'quarter': .1881, 'subtract_7': .0913}},
        'note_edit': {'pass': True, 'ratio_to_best_control': {'append_done': .06, 'undo': .11}}}},
    'live': {'verdict': 'LIVE_PATH_CONFIRMED', 'statuses': {'SCORED': 245}, 'seconds_per_call_median': 3.538,
             'tap_process_max_rss_mb': 924.9, 'arms': {
                 'calc_in_world': {'double': {'ratio_to_best_control': .223, 'pass': True}},
                 'calc_out_of_range': {'quarter': {'ratio_to_best_control': 1.1297, 'pass': False}}}},
    'learning': {'verdict': 'CONTINUAL_LEARNING_CONFIRMED', 'minutes': 37.1, 'statuses': {'SCORED': 610}, 'worlds': {
        'calc_counter': {'pass': True, 'shift_actions_improved': 4}, 'note_edit': {'pass': True, 'shift_actions_improved': 3}}}}


@unittest.skipUnless(os.name == 'posix', 'POSIX locks and process groups required')
class WerkzeugHandy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        (self.home / 'data').mkdir(parents=True)
        (self.home / 'bin').mkdir()
        (self.home / 'bin/v13').write_text('#!/bin/sh\n')

    def tearDown(self):
        self.tmp.cleanup()

    def test_meminfo_parses_megabytes(self):
        p = self.root / 'meminfo'
        p.write_text('MemTotal:        5822000 kB\nMemFree:  1 kB\nMemAvailable:    2048000 kB\nSwapTotal: 0 kB\n')
        self.assertEqual(W.meminfo(p), {'MemTotal': 5685, 'MemAvailable': 2000, 'SwapTotal': 0})
        self.assertEqual(W.meminfo(self.root / 'missing'), {})

    def test_precheck_stops_on_low_ram_and_running_chat(self):
        with mock.patch.object(W, 'meminfo', return_value={'MemTotal': 5600, 'MemAvailable': 900}), \
                mock.patch.object(W, 'installed', return_value=(True, '/m/b2.gguf')):
            c = W.precheck(self.home, 'kurz')
        self.assertTrue(any('RAM frei' in p for p in c['problems']))
        import fcntl
        with (self.home / 'data/coordinator.lock').open('a+') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            pid = os.fork()   # flock is per open file description: probe from another process
            if pid == 0:
                os._exit(0 if W.chat_running(self.home) else 1)
            _, status = os.waitpid(pid, 0)
        self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        self.assertFalse(W.chat_running(self.home))

    def test_precheck_missing_install_is_warning_not_problem(self):
        (self.home / 'bin/v13').unlink()
        with mock.patch.object(W, 'meminfo', return_value={'MemAvailable': 4000}):
            c = W.precheck(self.home, 'kurz')
        self.assertFalse(c['installed'])
        self.assertIn('nicht eingerichtet', c['warnings'][-1])

    def test_summary_reads_cloud_report_without_deciding(self):
        child = json.loads(json.dumps(CLOUD))
        text = W.summarize('voll', {'mem': {'MemTotal': 5600, 'MemAvailable': 3000}, 'cpu_count': 8, 'termux': True},
                           {'status': 'DRIVER_EXITED', 'driver_exit_code': 0, 'elapsed_seconds': 3000},
                           child, {'mem_available_min_mb': 1800, 'battery_temp_max_c': 39.5})
        self.assertIn('Gesamtstatus: LIVE_PATH_CONFIRMED+CONTINUAL_LEARNING_CONFIRMED', text)
        self.assertIn('calc_counter: PASS', text)
        self.assertIn('quarter 1.13', text)          # out-of-range arm stays visible as worse than control
        self.assertIn('Kleinster freier RAM während der Prüfung: 1800 MB', text)
        self.assertIn('Integrität fehlt', text)       # 13.10 report predates the integrity gate
        child['learning']['integrity'] = {'pass': True}
        self.assertIn('Integrität PASS', W.summarize('voll', {}, {}, child, {}))
        child['learning']['integrity'] = {'pass': False}
        self.assertIn('Integrität FAIL', W.summarize('voll', {}, {}, child, {}))
        self.assertIn('KEIN_BERICHT', W.summarize('kurz', {}, {}, None, {}))

    def test_collect_keeps_reports_drops_models_and_large_files(self):
        out = self.root / 'run'
        (out / 'device-check').mkdir(parents=True)
        (out / 'device-check/report.json').write_text('{"status":"X"}')
        (out / 'driver.log').write_text('log')
        (out / 'taps.npz').write_bytes(b'0' * 10)
        (out / 'big.log').write_bytes(b'0' * (W.COLLECT_MAX_BYTES + 1))
        z = W.collect(out, self.root / 'dl/r.zip', {'KURZ.txt': 'hallo'})
        with zipfile.ZipFile(z) as a:
            self.assertEqual(sorted(a.namelist()), ['KURZ.txt', 'lauf/device-check/report.json', 'lauf/driver.log'])
        self.assertFalse((self.root / 'dl/r.zip.part').exists())

    def fake_bounded(self, status):
        script = self.root / 'fake_bounded.py'
        script.write_text(
            'import json,sys\nfrom pathlib import Path\n'
            'out=Path(sys.argv[sys.argv.index("--out-dir")+1]);(out/"device-check").mkdir(parents=True)\n'
            '(out/"device-check/report.json").write_text(json.dumps({"status":%r,"argv":sys.argv[1:]}))\n'
            '(out/"wrapper-report.json").write_text(json.dumps({"status":"DRIVER_EXITED","driver_exit_code":0,"elapsed_seconds":1}))\n'
            % status)
        return script

    def run_main(self, status, *extra):
        with mock.patch.object(W, 'BOUNDED', self.fake_bounded(status)), \
                mock.patch.object(W, 'installed', return_value=(True, '/m/b2.gguf')), \
                mock.patch.object(W, 'meminfo', return_value={'MemTotal': 5600, 'MemAvailable': 3000}), \
                mock.patch.object(W, 'wake_lock', return_value=False), \
                mock.patch('sys.stdout', new=io.StringIO()):
            rc = W.main(['--installed-home', str(self.home), '--target-dir', str(self.root / 'dl'), *extra])
        zips = sorted((self.root / 'dl').glob('V13-Werkzeug-Ergebnis-*.zip'))
        self.assertEqual(len(zips), 1)
        with zipfile.ZipFile(zips[0]) as a:
            receipt = json.loads(a.read('paket-bericht.json'))
            child = json.loads(a.read('lauf/device-check/report.json'))
            self.assertIn('Gesamtstatus: ' + status, a.read('KURZ.txt').decode())
        return rc, receipt, child

    def test_main_kurz_confirmed(self):
        rc, receipt, child = self.run_main('LIVE_PATH_CONFIRMED')
        self.assertEqual(rc, 0)
        self.assertTrue(receipt['device_checks_confirmed'])
        self.assertEqual((receipt['receiver_authority'], receipt['learn_authority']), (0, 0))
        self.assertNotIn('--with-learning', child['argv'])
        self.assertNotIn('--skip-live', child['argv'])

    def test_main_voll_failure_is_nonzero_and_passes_learning_flag(self):
        rc, receipt, child = self.run_main('LIVE_PATH_CONFIRMED+NOT_CONFIRMED', 'voll')
        self.assertEqual(rc, 1)
        self.assertFalse(receipt['device_checks_confirmed'])
        self.assertIn('--with-learning', child['argv'])
        self.assertEqual(child['argv'][child['argv'].index('--timeout-seconds') + 1], str(10 * 3600))

    def test_main_refuses_without_setup_when_not_installed(self):
        (self.home / 'bin/v13').unlink()
        with mock.patch.object(W, 'meminfo', return_value={'MemAvailable': 3000}), \
                mock.patch.object(W, 'run_setup') as setup, mock.patch('sys.stdout', new=io.StringIO()):
            self.assertEqual(W.main(['--installed-home', str(self.home), '--no-setup']), 2)
        setup.assert_not_called()

    def test_launcher_is_packaged_for_phone(self):
        import package_source
        names = {p.relative_to(APP).as_posix() for p in package_source.inventory(APP, True)}
        self.assertTrue({'WERKZEUG_TESTEN.sh', 'WERKZEUG_ANLEITUNG.txt', 'scripts/werkzeug_handy.py',
                         'scripts/tool_forecast_bounded_phone_candidate.py', 'specs/tool_forecast/live-plan.json'} <= names)


if __name__ == '__main__':
    unittest.main()
