import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import tool_forecast_bounded_phone_candidate as B


@unittest.skipUnless(os.name == 'posix', 'Owned POSIX process groups required')
class BoundedPhoneDriver(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out = self.root / 'proof'

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, text):
        return [sys.executable, '-u', '-c', text]

    def test_complete_preserves_child_and_log(self):
        child = self.out / 'device-check/report.json'
        code = 'from pathlib import Path; p=Path(%r); p.parent.mkdir(); p.write_text(%r); print("native-stub-only")' % (
            str(child), json.dumps({'status': 'PARITY_PASS_NO_LIVE', 'receiver_authority': 0}))
        r = B.run_driver(self.command(code), self.out, timeout_s=2, driver_report=child)
        self.assertEqual(r['status'], 'DRIVER_EXITED')
        self.assertEqual(r['child_report_sha256'], B.sha_file(child))
        self.assertIn('native-stub-only', (self.out / 'driver.log').read_text())
        self.assertFalse(r['native_quality_claimed'])
        self.assertEqual(r['signals'], [])

    def test_deadline_stops_soft_handler_and_keeps_partial(self):
        child = self.out / 'device-check/report.json'
        code = ('import signal,time; from pathlib import Path; '
                'signal.signal(signal.SIGTERM, lambda *_: None); p=Path(%r); p.parent.mkdir(); '
                'p.write_text(%r); print("retained pre-effect evidence"); time.sleep(30)') % (
                    str(child), json.dumps({'status': 'PARITY'}))
        r = B.run_driver(self.command(code), self.out, timeout_s=.3, grace_s=.1, driver_report=child)
        self.assertEqual(r['status'], 'DEADLINE')
        self.assertEqual(r['child_status_observed'], 'PARITY')
        self.assertEqual(json.loads(child.read_text())['status'], 'PARITY')
        self.assertTrue(r['leader_reaped'])
        self.assertEqual(r['signals'], ['SIGTERM', 'SIGKILL'])
        self.assertLess(r['elapsed_seconds'], 2.)
        self.assertIn('retained pre-effect', (self.out / 'driver.log').read_text())

    def test_cancel_stops_child_and_no_unrelated_process(self):
        unrelated = subprocess.Popen(self.command('import time; time.sleep(30)'), start_new_session=True)
        cancel = threading.Event()
        timer = threading.Timer(.3, cancel.set)
        timer.start()
        try:
            r = B.run_driver(self.command('import time; time.sleep(30)'), self.out,
                             timeout_s=10, grace_s=.1, cancel=cancel)
            self.assertEqual(r['status'], 'CANCELLED')
            self.assertTrue(r['leader_reaped'])
            self.assertIsNone(unrelated.poll())
        finally:
            timer.cancel()
            unrelated.terminate()
            unrelated.wait(timeout=2)

    def test_grandchild_stopped_when_leader_exits_on_term(self):
        marker = self.out / 'leaked.txt'
        ready = self.out / 'ready'
        grand = ('import signal,time; from pathlib import Path; '
                 'signal.signal(signal.SIGTERM, lambda *_: None); Path(%r).write_text("ready"); '
                 'time.sleep(.8); Path(%r).write_text("leak"); time.sleep(30)') % (str(ready), str(marker))
        code = ('import subprocess,time,sys; subprocess.Popen([sys.executable,"-u","-c",%r]); time.sleep(30)') % grand
        r = B.run_driver(self.command(code), self.out, timeout_s=.4, grace_s=.1)
        self.assertTrue(ready.exists(), 'Descendant must actually have started')
        self.assertEqual(r['status'], 'DEADLINE')
        time.sleep(.5)
        self.assertFalse(marker.exists(), 'TERM-resistant descendant must not survive group cleanup')

    def test_existing_output_never_replaced(self):
        self.out.mkdir()
        keep = self.out / 'report.json'
        keep.write_text('keep')
        with self.assertRaises(FileExistsError):
            B.run_driver(self.command('pass'), self.out, timeout_s=1)
        self.assertEqual(keep.read_text(), 'keep')

    def test_driver_error_receipt(self):
        r = B.run_driver(self.command('import sys; print("attempt"); sys.exit(7)'), self.out, timeout_s=2)
        self.assertEqual(r['status'], 'DRIVER_ERROR')
        self.assertEqual(r['driver_exit_code'], 7)
        self.assertEqual(json.loads((self.out / 'wrapper-report.json').read_text())['status'], 'DRIVER_ERROR')

    def test_start_failure_saved(self):
        r = B.run_driver([str(self.root / 'missing-executable')], self.out, timeout_s=1)
        self.assertEqual(r['status'], 'WRAPPER_ERROR')
        self.assertIn('FileNotFoundError', r['error'])

    def test_zero_exit_missing_report_does_not_pass(self):
        r = B.run_driver(self.command('pass'), self.out, timeout_s=2,
                         driver_report=self.out / 'missing-report.json')
        self.assertEqual(r['status'], 'DRIVER_REPORT_MISSING_OR_INVALID')

    def test_zero_exit_negative_gate_does_not_pass(self):
        child = self.out / 'device-check/report.json'
        code = 'from pathlib import Path; p=Path(%r); p.parent.mkdir(); p.write_text(%r)' % (
            str(child), json.dumps({'status': 'LIVE_PATH_NOT_CONFIRMED'}))
        r = B.run_driver(self.command(code), self.out, timeout_s=2, driver_report=child)
        self.assertEqual(r['status'], 'DRIVER_CHECKS_NOT_CONFIRMED')
        self.assertFalse(r['canonical_gate_pass'])

    def test_precancel_does_not_launch(self):
        cancel = threading.Event()
        cancel.set()
        r = B.run_driver(self.command('raise RuntimeError("must not launch")'), self.out,
                         timeout_s=1, cancel=cancel)
        self.assertEqual(r['status'], 'CANCELLED_BEFORE_START')
        self.assertNotIn('owned_pid', r)

    def test_nonfinite_budget_refused_without_output(self):
        for value in (0, -1, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                B.run_driver(self.command('pass'), self.out, timeout_s=value)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
