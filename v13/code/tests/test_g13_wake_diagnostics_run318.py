"""Run318 G13 diagnostics: source-only/SQLite fixtures, no native proof."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from scripts import g13_wake_diagnostics_run318 as D


class FakeRuntime:
    def __init__(self, idle=True):
        self._idle = idle
        self.jobs = SimpleNamespace(qsize=lambda: 2)
        self.guard = SimpleNamespace(state='NORMAL', update=lambda *_: (_ for _ in ()).throw(AssertionError('guard mutated')))
        self.sleep = SimpleNamespace(scheduler=SimpleNamespace(pending=lambda: [
            {'status': 'PENDING', 'kind': 'GOAL_WAKE'},
            {'status': 'PENDING', 'kind': 'GOAL_WAKE'},
        ]))
    def idle(self):
        return self._idle


class G13WakeDiagnosticsRun318(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_is_read_only_and_content_free(self):
        x = D.snapshot(FakeRuntime())
        self.assertTrue(x['idle'])
        self.assertEqual(x['jobs_qsize'], 2)
        self.assertEqual(x['guard_state_readonly'], 'NORMAL')
        self.assertEqual(x['pending_status_kind_counts'], {'PENDING:GOAL_WAKE': 2})
        self.assertNotIn('payload', json.dumps(x))

    def test_timeout_observed_without_changing_original_return(self):
        journal = D.Journal(self.root / 'trace.jsonl')
        original = D.L.wait_idle
        with patch.object(D.L, 'wait_idle', return_value=False):
            with D.instrument(journal):
                self.assertFalse(D.L.wait_idle(FakeRuntime(False), timeout=0.01))
        self.assertIs(D.L.wait_idle, original)
        self.assertEqual(journal.wait_timeouts, 1)
        row = json.loads(journal.path.read_text().splitlines()[0])
        self.assertEqual(row['kind'], 'wait_idle')
        self.assertFalse(row['success'])
        self.assertEqual(row['after']['pending_status_kind_counts']['PENDING:GOAL_WAKE'], 2)

    def test_busy_tick_none_recorded_and_method_restored(self):
        journal = D.Journal(self.root / 'trace.jsonl')
        original = D.SleepRuntime.tick
        with patch.object(D.SleepRuntime, 'tick', return_value=None):
            patched = D.SleepRuntime.tick
            with D.instrument(journal):
                fake = SimpleNamespace(r=FakeRuntime(False))
                self.assertIsNone(D.SleepRuntime.tick(fake, force=True))
            self.assertIs(D.SleepRuntime.tick, patched)
        self.assertIs(D.SleepRuntime.tick, original)
        self.assertEqual(journal.tick_none_busy, 1)

    def test_original_soak_exception_keeps_diagnostic_failure_and_restores_hooks(self):
        original_tick = D.SleepRuntime.tick
        original_wait = D.L.wait_idle
        with patch.object(D.L, 'soak', side_effect=RuntimeError('fixture forced')):
            report = D.run(self.root / 'home', self.root / 'out', native=False)
        self.assertEqual(report['status'], 'CAPTURE_INTERRUPTED')
        self.assertIsNone(report['soak_verdict'])
        self.assertEqual(report['error']['type'], 'RuntimeError')
        self.assertIs(D.SleepRuntime.tick, original_tick)
        self.assertIs(D.L.wait_idle, original_wait)
        self.assertTrue((self.root / 'out/RUN318_SUMMARY.json').is_file())

    def test_real_runtime_sqlite_fixture_keeps_original_g13_gates(self):
        report = D.run(self.root / 'home', self.root / 'out', native=False, days=2, turns=2)
        self.assertEqual(report['status'], 'CAPTURE_COMPLETE')
        self.assertEqual(report['evidence_level'], 'FIXTURE_ONLY')
        # The original soak has an observed timing flake even with a fixture
        # at this preregistered wall start: retain its exact PASS or FAIL.
        self.assertIn(report['soak_verdict'], ('PASS', 'FAIL'))
        self.assertEqual(len(report['days']), 2)
        original_checks_pass = all(all(day['checks'].values()) for day in report['days'])
        self.assertEqual(report['soak_verdict'], 'PASS' if original_checks_pass else 'FAIL')
        self.assertGreater(report['trace_rows'], 0)
        self.assertEqual(report['wait_idle_timeouts'], 0)
        self.assertTrue((self.root / 'out/RUN318_TRACE.jsonl').is_file())
        self.assertEqual(report['original_gates']['STEP2'], 'UTILITY_FAIL')

    def test_existing_raw_evidence_is_never_overwritten(self):
        out = self.root / 'out'
        out.mkdir()
        (out / 'RUN318_TRACE.jsonl').write_text('original')
        with self.assertRaises(FileExistsError):
            D.run(self.root / 'home', out, native=False)
        self.assertEqual((out / 'RUN318_TRACE.jsonl').read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
