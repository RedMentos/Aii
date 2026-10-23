import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import z7_residency_bench as Z


class JournalRecovery(unittest.TestCase):
    def test_sigkill_retains_completed_row_and_refuses_silent_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'residency.json'
            code = """import sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from z7_residency_bench import ProgressJournal
j=ProgressJournal(sys.argv[2],{'sha256':'test-bound-input'})
j.row('arm',{'fixture':'first','pass':True})
print('durable',flush=True)
time.sleep(60)
"""
            p = subprocess.Popen([sys.executable, '-c', code, str(Path(Z.__file__).parent), str(output)], stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(p.stdout.readline().strip(), 'durable')
                p.kill(); p.wait(timeout=5)
            finally:
                if p.poll() is None: p.kill(); p.wait(timeout=5)
                p.stdout.close()
            dirs = list(output.with_name(output.name+'.attempts').iterdir())
            rows = [json.loads(x) for x in (dirs[0]/'progress.jsonl').read_text().splitlines()]
            self.assertEqual(rows[-1]['row']['fixture'], 'first')
            self.assertEqual(json.loads((dirs[0]/'state.json').read_text())['completed_rows'], 1)
            with self.assertRaisesRegex(ValueError, 'Previous residency evidence'):
                Z.ProgressJournal(output, {'sha256':'test-bound-input'})
            next_attempt = Z.ProgressJournal(output, {'sha256':'test-bound-input'}, new_attempt=True)
            self.assertNotEqual(next_attempt.directory, dirs[0])
            self.assertEqual((dirs[0]/'progress.jsonl').read_text().splitlines()[-1], json.dumps(rows[-1], sort_keys=True))

    def test_explicit_new_attempt_preserves_previous_final_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'r.json'; output.write_text('{"old":"measured"}')
            j = Z.ProgressJournal(output, {'sha256':'new'}, new_attempt=True)
            saved = list(j.root.glob('previous-report-*.json'))
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].read_bytes(), output.read_bytes())

    def test_interruption_in_next_turn_preserves_prior_real_path_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'r.json'; j = Z.ProgressJournal(output, {'sha256':'test'})
            runtime = mock.Mock(home=Path(tmp), cfg={})
            row = {'pass': True, 'answer_s': 1., 'wall_s': 2.}
            tasks = [('first', 'first prompt', [], {}), ('second', 'second prompt', [], {})]
            with mock.patch.object(Z, 'selected_tasks', return_value=tasks), mock.patch.object(Z, 'fresh_runtime', return_value=runtime), \
                 mock.patch.object(Z, 'device_state', return_value={}), mock.patch.object(Z, 'turn', side_effect=[row, KeyboardInterrupt]):
                with self.assertRaises(KeyboardInterrupt): Z.run_schedules(Path(tmp), ['A_THEN_B_SEQUENTIAL'], 1, j)
            records = [json.loads(x) for x in j.path.read_text().splitlines()]
            self.assertEqual([x['row']['fixture'] for x in records if x['kind']=='ROW'], ['first'])
            runtime.close.assert_called_once()

    def test_binding_changes_with_manifest_or_benchmark_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp); (home/'config').mkdir(); model = home/'config/models.json'; model.write_text('{}')
            a = Z.input_binding(home, 'schedules', [Z.SCHEDULES[0]], 1, 2)
            model.write_text('{"revision":"changed"}')
            b = Z.input_binding(home, 'schedules', [Z.SCHEDULES[0]], 1, 2)
            c = Z.input_binding(home, 'schedules', [Z.SCHEDULES[0]], 2, 2)
            self.assertNotEqual(a['sha256'], b['sha256']); self.assertNotEqual(b['sha256'], c['sha256'])


class MeasurementIntegrity(unittest.TestCase):
    def test_unknown_values_do_not_become_zero(self):
        dev = {'mem_available_mb': None, 'battery_temp_c': None, 'battery_percent': None}
        row = {'pass': False, 'answer_s': None, 'first_offer_s': None, 'wall_s': 3., 'processes': [], 'device_before': dev, 'device_after': dev}
        s = Z.summarize([row, dict(row, answer_s=4.), dict(row, answer_s=0.)])
        self.assertEqual(s['answer_s'], 2.); self.assertEqual(s['answer_samples'], 2); self.assertEqual(s['answer_missing'], 1)
        self.assertIsNone(s['mem_available_min_mb']); self.assertEqual(s['mem_available_samples'], 0)
        self.assertIsNone(Z.summarize([row])['answer_s'])
        with mock.patch('v13.resources.snapshot', return_value={'mem_available_bytes': None, 'battery_temperature_c': None, 'battery_percent': None, 'charging': None}):
            self.assertIsNone(Z.device_state(Path('.'))['mem_available_mb'])

    def test_already_idle_terminal_turn_is_sampled_and_error_cannot_pass(self):
        r = mock.Mock(); r.submit.return_value = 'event'; r.idle.return_value = True; r.store.rows.return_value = []
        def one(query, params): return {'status': self.status} if 'messages' in query else {'exists':1}
        r.store.one.side_effect = one
        audit = {'output': 'correct text', 'output_metadata': {}, 'offers': []}
        with mock.patch('v13.proofs.audit_event', return_value=audit), mock.patch.object(Z.U, 'score', return_value=({'ok':True},{})), \
             mock.patch.object(Z, 'proc_children', return_value=[]):
            self.status = 'FINAL'; final = Z.turn(r, 'prompt', [], {})
            self.assertTrue(final['pass']); self.assertIsNotNone(final['answer_s']); self.assertIsNotNone(final['first_offer_s'])
            self.status = 'ERROR'; failed = Z.turn(r, 'prompt', [], {})
            self.assertFalse(failed['pass']); self.assertIsNone(failed['answer_s']); self.assertEqual(failed['status'], 'ERROR')

    def test_child_residency_uses_namespace_correct_pid(self):
        p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            self.assertIn(p.pid, Z.proc_children())
            st = Z.proc_stats(p.pid)
            self.assertIsNotNone(st); self.assertEqual(st['pid'], p.pid)
            self.assertGreater(st['rss_mb'], 0)
        finally:
            p.terminate(); p.wait(timeout=5)

    def test_simultaneous_same_executable_processes_are_not_collapsed(self):
        r = mock.Mock(); r.submit.return_value = 'event'; r.idle.return_value = True; r.store.rows.return_value = []
        r.store.one.side_effect = lambda query, params: {'status':'FINAL'} if 'messages' in query else None
        stats = lambda pid: {'pid':pid, 'name':'llama-server', 'rss_mb':float(pid), 'hwm_mb':float(pid)+1, 'majflt':0, 'minflt':0}
        with mock.patch('v13.proofs.audit_event', return_value={'output':'ok','offers':[]}), \
             mock.patch.object(Z.U, 'score', return_value=({'ok':True},{})), \
             mock.patch.object(Z, 'proc_children', return_value=[10,20]), mock.patch.object(Z, 'proc_stats', side_effect=stats):
            row = Z.turn(r, 'prompt', [], {})
        self.assertEqual(len(row['processes']), 2)
        self.assertEqual(row['children_rss_peak_mb'], 30.)
        self.assertEqual(row['children_rss_samples'], 1)


if __name__ == '__main__': unittest.main()
