"""Phone/learning orchestration regressions with explicit model/runner stubs.

Real gates, strict grid checking, journals and NPZ snapshot bytes are exercised.
The synthetic tap rows establish no learned utility or device/model result.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from scripts import tool_forecast_learning_check as learning
from scripts import tool_forecast_bounded_phone_candidate as bounded
from scripts import tool_forecast_bound_learning_candidate as bound
from scripts import test_tool_forecast_phone as phone
from tests.test_tool_forecast_learning_integrity_candidate import fixture
from tests.test_toolforecast import FakeTaps


class LearningRunIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.encoder_home = self.root / 'installed'
        enc = self.encoder_home / 'data/tool_forecast/encoder.json'
        enc.parent.mkdir(parents=True)
        enc.write_text(json.dumps({'tool_sha256': 'a'*64, 'model_sha256': 'b'*64}))
        self.doc = json.loads((learning.APP / 'specs/tool_forecast/learning-plan.json').read_text())
        self.rows, self.learn, _ = fixture(self.doc)
        self.plan = self.root / 'plan.json'
        self.plan.write_text(json.dumps(self.doc))
        self.out = self.root / 'out'
        self.args = type('Args', (), {'plan': str(self.plan), 'round': 2, 'out': str(self.out),
                                    'encoder_home': str(self.encoder_home)})()
        self.runtime = Mock()
        self.tf = Mock()
        self.tf.report.return_value = {'mode': 'SHADOW', 'stub_taps': True}

    def write_buffer(self, home, rows):
        for world, arm in zip(('calc_counter', 'note_edit'), learning.EXP_ARMS):
            part = [r for r in rows if r['arm'] == arm]
            path = learning.F.Experience(home).path(world)
            path.parent.mkdir(parents=True, exist_ok=True)
            n = len(part)
            np.savez(path, x=np.ones((n, 2), dtype=np.float32), y=np.ones((n, 2), dtype=np.float32),
                     xm=np.ones((n, 2), dtype=np.float32), action=np.zeros(n, dtype=np.int64),
                     id=np.asarray([r['forecast_id'] for r in part]),
                     binding=np.asarray(json.dumps({'checkpoint_sha256': 'stub-only', 'model_sha256': 'b'*64})))

    def execute(self, *, partial=False, interrupt=False, improve=True):
        test_home = self.out / 'home'
        def arms(runtime, g, tf, plan, selected, rows):
            phase_a = tuple(selected) == learning.EXP_ARMS
            part = [copy.deepcopy(row) for row in self.rows if row['arm'] in selected]
            if phase_a:
                if interrupt:
                    rows.append(part[0]); rows.append(part[1])
                    raise RuntimeError('synthetic native interruption')
                for row in part:
                    rows.append(row)
                self.write_buffer(test_home, part)
            else:
                if partial:
                    part = [row for row in part if row['action'] in ('double', 'append_done')][:]
                if not improve:
                    for row in part:
                        row['mse']['adapted'] = row['mse']['forecast']
                for row in part:
                    rows.append(row)
                # The real buffer is mutable after learning. Keep the frozen copy exact.
                for world in ('calc_counter', 'note_edit'):
                    learning.F.Experience(test_home).add(world, [9., 8.], [7., 6.], 0,
                                                        'tfc_' + 'f'*32, binding={'new': 'held-out'})
        def learn(**kwargs):
            got = copy.deepcopy(self.learn)
            for world in got:
                got[world]['experience_sha256'] = learning._sha(learning.F.Experience(test_home).path(world))
            return got
        self.tf.learn.side_effect = learn
        with patch.object(learning, 'Runtime', return_value=self.runtime), \
             patch.object(learning, 'hub', return_value=Mock()), \
             patch.object(learning.F, 'for_runtime', return_value=self.tf), \
             patch.object(learning.live, 'run_arms', side_effect=arms), \
             patch.object(learning.live, 'verdict', return_value={'stub_only': True}), \
             contextlib.redirect_stdout(io.StringIO()):
            rc = learning.run(self.args)
        return rc, json.loads((self.out / 'report.json').read_text())

    def test_partial_test_rows_cannot_pass_original_run(self):
        # The low-level old analysis accepts this shortened action denominator.
        partial = [r for r in self.rows if r['arm'] not in learning.EXP_ARMS
                   and r['action'] in ('double', 'append_done')]
        self.assertEqual(learning.analyze(partial, self.learn)['verdict'], 'CONTINUAL_LEARNING_CONFIRMED')
        rc, report = self.execute(partial=True)
        self.assertEqual(rc, 1)
        self.assertFalse(report['analysis_ran'])
        self.assertFalse(report['integrity']['pass'])
        self.assertEqual(report['verdict'], 'CONTINUAL_LEARNING_NOT_CONFIRMED')

    def test_interrupted_phase_a_preserves_journal_and_partial_json(self):
        rc, report = self.execute(interrupt=True)
        self.assertEqual(rc, 1)
        journal = [json.loads(line) for line in (self.out / 'rows.jsonl').read_text().splitlines()]
        self.assertEqual(len(journal), 2)
        self.assertEqual(json.loads((self.out / 'rows.json').read_text()), journal)
        self.assertFalse(report['analysis_ran'])
        self.assertIn('synthetic native interruption', report['error'])
        self.tf.learn.assert_not_called()
        self.runtime.close.assert_called_once()

    def test_shutdown_failure_still_closes_partial_rows_and_negative_report(self):
        self.runtime.close.side_effect = RuntimeError('synthetic shutdown failure')
        with self.assertRaisesRegex(RuntimeError, 'synthetic shutdown failure'):
            self.execute(interrupt=True)
        report = json.loads((self.out / 'report.json').read_text())
        self.assertEqual(len(json.loads((self.out / 'rows.json').read_text())), 2)
        self.assertEqual(report['verdict'], 'CONTINUAL_LEARNING_NOT_CONFIRMED')
        self.assertIn('synthetic shutdown failure', report['shutdown_error'])

    def test_old_journal_is_not_appended_or_overwritten(self):
        self.out.mkdir()
        path = self.out / 'rows.jsonl'
        path.write_bytes(b'old evidence\n')
        with self.assertRaisesRegex(SystemExit, 'fresh output folder required'):
            learning.run(self.args)
        self.assertEqual(path.read_bytes(), b'old evidence\n')

    def test_complete_grid_passes_and_exact_160_90_snapshot_survives_phase_b(self):
        rc, report = self.execute()
        self.assertEqual(rc, 0)
        self.assertTrue(report['integrity']['pass'])
        self.assertTrue(report['analysis_ran'])
        self.assertEqual(report['integrity']['observed_rows'], 610)
        snapshot = report['phase_a_experience']
        self.assertEqual([v['rows'] for v in snapshot['manifest']['worlds'].values()], [160, 90])
        learned = json.loads((self.out / 'learn.json').read_text())
        self.assertTrue(learning.verify_experience_snapshot(self.out, snapshot, learned))
        for world, item in snapshot['manifest']['worlds'].items():
            old = self.out / snapshot['directory'] / item['file']
            current = learning.F.Experience(self.out / 'home').path(world)
            self.assertEqual(learning._sha(old), learned[world]['experience_sha256'])
            self.assertNotEqual(old.read_bytes(), current.read_bytes())
        # Changed frozen bytes fail closed even if their file name is retained.
        old.write_bytes(old.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'PHASE_A_SNAPSHOT_BYTES_CHANGED'):
            learning.verify_experience_snapshot(self.out, snapshot, learned)

    def test_complete_grid_numeric_negative_returns_nonzero(self):
        rc, report = self.execute(improve=False)
        self.assertEqual(rc, 1)
        self.assertTrue(report['integrity']['pass'])
        self.assertTrue(report['analysis_ran'])
        self.assertEqual(report['verdict'], 'CONTINUAL_LEARNING_NOT_CONFIRMED')

    def test_learner_hash_must_bind_exact_snapshot_input(self):
        rows = [r for r in self.rows if r['arm'] in learning.EXP_ARMS]
        self.out.mkdir()
        self.write_buffer(self.encoder_home, rows)
        snapshot = learning.snapshot_experience(self.encoder_home, self.out, rows, self.doc)
        learned = copy.deepcopy(self.learn)
        for world in learned:
            learned[world]['experience_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'LEARN_INPUT_SNAPSHOT_MISMATCH'):
            learning.verify_experience_snapshot(self.out, snapshot, learned)

    def test_real_runtime_tool_paths_write_snapshot_with_only_tap_provider_stubbed(self):
        # Complement orchestration controls with actual Runtime/ToolStep/approval,
        # checkpoint prediction/scoring, SQLite state and Experience persistence.
        _, _, small = fixture()
        self.plan.write_text(json.dumps(small))
        real_runtime = learning.Runtime
        taps = FakeTaps()
        def runtime(home):
            r = real_runtime(home)
            r.tool_forecast = learning.F.ToolForecast(r.store, r.home, taps=taps)
            return r
        with patch.object(learning, 'Runtime', side_effect=runtime), contextlib.redirect_stdout(io.StringIO()):
            rc = learning.run(self.args)
        report = json.loads((self.out / 'report.json').read_text())
        rows = json.loads((self.out / 'rows.json').read_text())
        self.assertEqual(rc, 1)  # No native retention installation: no learned-utility assertion.
        self.assertEqual(len(rows), 7)
        self.assertEqual({r['tool_status'] for r in rows}, {'EXECUTED'})
        self.assertEqual({r['status'] for r in rows}, {'SCORED'})
        snapshot = report['phase_a_experience']
        self.assertEqual([v['rows'] for v in snapshot['manifest']['worlds'].values()], [4, 3])
        self.assertTrue(learning.verify_experience_snapshot(self.out, snapshot))
        self.assertGreater(len(taps.calls), 0)
        self.assertFalse(report['analysis_ran'])

    def test_bound_worker_closes_snapshot_before_learning_and_preserves_it_after_test(self):
        installed = self.encoder_home
        n = {'tool_path': 'native-stub-only', 'model_path': 'model-stub-only', 'library_directory': 'stub-only'}
        prereg = self.root / 'prereg.json'
        prereg.write_text(json.dumps({'schema': bound.SCHEMA, 'gates': learning.GATES, 'rule': bound.F.LEARN_RULE,
                                     'native': n, 'numerical_runtime': {}, 'plan': self.doc,
                                     'plan_path': str(self.plan), 'plan_sha256': bound.sha_file(self.plan), 'threads': 4}))
        test_home = self.out / 'home'
        def install(args):
            enc = installed / 'data/tool_forecast/encoder.json'
            enc.write_text(json.dumps({'parity': {'pass': True}}))
            return 0
        def arms(runtime, g, tf, plan, selected, rows):
            part = [copy.deepcopy(row) for row in self.rows if row['arm'] in selected]
            for row in part:
                rows.append(row)
            if tuple(selected) == learning.EXP_ARMS:
                self.write_buffer(test_home, part)
            else:
                for world in ('calc_counter', 'note_edit'):
                    learning.F.Experience(test_home).add(world, [9., 8.], [7., 6.], 0,
                                                        'tfc_' + 'f'*32, binding={'new': 'held-out'})
        def learn(**kwargs):
            # This is reached after the snapshot is durably closed, before Phase B.
            manifest = self.out / 'phase-a-experience/manifest.json'
            self.assertTrue(manifest.is_file())
            got = copy.deepcopy(self.learn)
            for world, item in json.loads(manifest.read_text())['worlds'].items():
                got[world]['experience_sha256'] = item['sha256']
            return got
        self.tf.learn.side_effect = learn
        with patch.object(bound, 'verify_sources'), patch.object(bound, 'native_binding', return_value=n), \
             patch.object(bound, 'numerical_runtime_binding', return_value={}), \
             patch.object(bound.installer, 'install', side_effect=install), \
             patch.object(bound, 'Runtime', return_value=self.runtime), \
             patch.object(bound, 'hub', return_value=Mock()), \
             patch.object(bound.F, 'for_runtime', return_value=self.tf), \
             patch.object(bound.original.live, 'run_arms', side_effect=arms), contextlib.redirect_stdout(io.StringIO()):
            rc = bound.worker(installed, prereg, self.out)
        report = json.loads((self.out / 'report.json').read_text())
        self.assertEqual(rc, 0, report)
        self.assertTrue(report['phase_a_snapshot_verified_after'])
        self.assertTrue(report['analysis']['integrity']['pass'])
        self.assertEqual(report['analysis']['integrity']['observed_rows'], 610)
        self.assertEqual(report['status'], bound.CONFIRMED)
        self.assertEqual(len((self.out / 'rows.jsonl').read_text().splitlines()), 610)
        self.assertTrue(learning.verify_experience_snapshot(self.out, report['phase_a_experience'],
                        json.loads((self.out / 'learn.json').read_text())))


class PhoneExitIntegrity(unittest.TestCase):
    def call_driver(self, *, live_verdict='LIVE_PATH_CONFIRMED', learning_verdict='CONTINUAL_LEARNING_CONFIRMED',
                    integrity=True, analysis=True, live_rc=0, learning_rc=0, with_learning=True):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); home = root / 'home'; (home / 'data').mkdir(parents=True)
            out = root / 'proof'
            want = json.loads(phone.tf.MANIFEST.read_text())['encoder']['model_sha256']
            def install(args):
                enc = home / 'data/tool_forecast/encoder.json'; enc.parent.mkdir()
                enc.write_text(json.dumps({'parity': {'pass': True}}))
                return 0
            def live(args, **kwargs):
                target = Path(args.out); target.mkdir()
                (target / 'report.json').write_text(json.dumps({'verdict': live_verdict, 'statuses': {},
                    'seconds_per_call_median': 0, 'tap_process_max_rss_mb': 0, 'arms': {}}))
                return live_rc
            def learn(args):
                target = Path(args.out); target.mkdir()
                (target / 'report.json').write_text(json.dumps({'verdict': learning_verdict, 'minutes': 0,
                    'statuses': {}, 'worlds': {}, 'integrity': {'pass': integrity}, 'analysis_ran': analysis}))
                return learning_rc
            argv = ['driver', '--installed-home', str(home), '--out-dir', str(out)]
            if with_learning: argv.append('--with-learning')
            with patch.object(sys, 'argv', argv), patch.object(phone, 'device', return_value={'stub': True}), \
                 patch.object(phone, 'catalog', return_value={'runner': {}}), \
                 patch.object(phone, 'ModelManager') as mm, patch.object(phone, 'file_hash', return_value=want), \
                 patch.object(phone.port, 'installed_identity', return_value={'library_directory': 'stub-only'}), \
                 patch.object(phone, 'build_taps', return_value=(root/'native-stub', {'binary_sha256': 'stub', 'identity_key': {}})), \
                 patch.object(phone.installer, 'install', side_effect=install), \
                 patch.object(phone.live, 'run', side_effect=live), \
                 patch.object(phone.learning, 'run', side_effect=learn), contextlib.redirect_stdout(io.StringIO()):
                mm.return_value.path_for.return_value = root/'model-stub'
                rc = phone.main()
            return rc, json.loads((out / 'report.json').read_text())

    def test_full_confirmed_status_and_integrity_are_preserved(self):
        rc, report = self.call_driver()
        self.assertEqual(rc, 0)
        self.assertEqual(report['status'], 'LIVE_PATH_CONFIRMED+CONTINUAL_LEARNING_CONFIRMED')
        self.assertTrue(report['learning']['integrity']['pass'])
        self.assertTrue(report['learning']['analysis_ran'])

    def test_each_negative_or_missing_gate_propagates_nonzero(self):
        for kwargs in ({'live_verdict': 'LIVE_PATH_NOT_CONFIRMED'},
                       {'learning_verdict': 'CONTINUAL_LEARNING_NOT_CONFIRMED'},
                       {'integrity': False}, {'analysis': False}, {'live_rc': 1}, {'learning_rc': 1},
                       {'live_verdict': 'LIVE_PATH_NOT_CONFIRMED', 'with_learning': False}):
            with self.subTest(kwargs=kwargs):
                rc, _ = self.call_driver(**kwargs)
                self.assertEqual(rc, 1)

    def test_bounded_wrapper_rejects_short_fake_suffix_and_accepts_actual_full_verdict(self):
        for suffix, expected in (('CONFIRMED', 'DRIVER_CHECKS_NOT_CONFIRMED'),
                                 ('CONTINUAL_LEARNING_CONFIRMED', 'DRIVER_EXITED')):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as d:
                out = Path(d)/'out'; child = out/'report.json'
                code = 'from pathlib import Path; Path(%r).write_text(%r)' % (
                    str(child), json.dumps({'status': 'LIVE_PATH_CONFIRMED+' + suffix}))
                report = bounded.run_driver([sys.executable, '-c', code], out, timeout_s=5, driver_report=child)
                self.assertEqual(report['status'], expected)


if __name__ == '__main__':
    unittest.main()
