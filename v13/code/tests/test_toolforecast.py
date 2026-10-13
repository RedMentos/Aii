"""Thread M: SHADOW tool-consequence forecast in the live tool path (IH-H29 `predicted`). Fake taps unless a native encoder
is given through V13_TAP_TOOL + V13_TAP_MODEL (then the parity-checked install and one live round trip run for real)."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from v13 import toolforecast as F
from v13 import toolstep as T
from v13.agi import hub
from v13.runtime import Runtime
from v13.transaction import operator_command as tx_command, settle_turn

APP = Path(__file__).resolve().parents[1]


class FakeTaps:
    """Deterministic stand-in encoder: one fixed random 1024-vector per text."""
    def __init__(self):
        self.calls = []

    def tap(self, texts):
        self.calls.append(list(texts))
        return np.stack([np.random.default_rng(int(hashlib.sha256(t.encode()).hexdigest()[:12], 16)).normal(size=1024).astype(np.float32)
                         for t in texts])


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / 'data' / 'tool_sandbox').mkdir(parents=True)
        (self.home / 'data' / 'tool_sandbox' / 'todo.txt').write_text('Call the bank today.')

    def tearDown(self):
        self.tmp.cleanup()

    def test_calc_world_only_for_the_four_measured_actions(self):
        c = F.classify('calc', {'expression': '37*2'}, self.home)
        self.assertEqual((c['world'], c['action'], c['state_text'], c['in_world_range']), ('calc_counter', 'double', 'The counter shows 37.', True))
        self.assertEqual(F.classify('calc', {'expression': '4000-7'}, self.home)['in_world_range'], False)
        for expr in ('37*3', '2*37', '37+16', '(37)/4', '0*2', '1.5*2'):
            self.assertIn('unmapped', F.classify('calc', {'expression': expr}, self.home), expr)

    def test_note_world_needs_an_edit_of_an_existing_single_line_note(self):
        c = F.classify('sandbox_note', {'name': 'todo', 'text': 'Urgent: Call the bank today.'}, self.home)
        self.assertEqual((c['action'], c['state_text'], c['in_world_range']), ('prefix_urgent', 'The note reads: Call the bank today.', True))
        self.assertEqual(F.classify('sandbox_note', {'name': 'todo', 'text': 'CALL THE BANK TODAY.'}, self.home)['action'], 'uppercase')
        self.assertIn('unmapped', F.classify('sandbox_note', {'name': 'todo', 'text': 'Something else.'}, self.home))
        self.assertIn('unmapped', F.classify('sandbox_note', {'name': 'new', 'text': 'x Done.'}, self.home))
        self.assertIn('unmapped', F.classify('web', {}, self.home))

    def test_note_edit_proposals(self):
        read = lambda n: {'todo': 'Call the bank today.'}.get(n)
        self.assertEqual(T.propose_note_edit('Mark note todo as done', read)['args'], {'name': 'todo', 'text': 'Call the bank today. Done.'})
        self.assertEqual(T.propose_note_edit('please make the note "todo" urgent.', read)['args']['text'], 'Urgent: Call the bank today.')
        self.assertEqual(T.propose_note_edit('Uppercase note todo', read)['args']['text'], 'CALL THE BANK TODAY.')
        self.assertIsNone(T.propose_note_edit('Mark note other as done', read))
        self.assertIsNone(T.propose_note_edit('Mark the meeting as done', read))


class CheckpointTests(unittest.TestCase):
    def test_runtime_formula_equals_round6_predict_state(self):
        sys.path.insert(0, str(APP / 'scripts'))
        import action_jepa_round6_ridge as r6
        manifest = json.loads(F.MANIFEST.read_text())
        x = F.rms_normalize(np.random.default_rng(3).normal(size=(5, 1024)))
        for world in manifest['worlds']:
            ck = F.Checkpoint(world, manifest['worlds'][world])
            state = {'p': ck.p, 'mean_delta': ck.mean_delta, 'centre': ck.centre, 'weight': ck.weight, 'arm': ck.arm}
            for j, action in enumerate(ck.actions):
                want = r6.predict_state(x, np.full(5, j), state)
                got = np.stack([ck.predict(row, action)['forecast'] for row in x])
                np.testing.assert_allclose(got, want, rtol=0, atol=1e-12)

    def test_tampered_checkpoint_is_refused(self):
        manifest = json.loads(F.MANIFEST.read_text())
        entry = manifest['worlds']['calc_counter']
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for k in ('checkpoint', 'metrics'):
                (root / entry[k]).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(APP / entry[k], root / entry[k])
            with open(root / entry['checkpoint'], 'ab') as f:
                f.write(b'\0')
            with self.assertRaises(ValueError):
                F.Checkpoint('calc_counter', entry, root)

    def test_missing_or_failed_encoder_gives_no_forecast(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(F.load_encoder(d), (None, 'NO_ENCODER_INSTALLED'))
            p = Path(d) / 'data' / 'tool_forecast'
            p.mkdir(parents=True)
            (p / 'encoder.json').write_text(json.dumps({'schema': F.SCHEMA + '-encoder', 'parity': {'status': 'FAIL'}}))
            self.assertEqual(F.load_encoder(d), (None, 'ENCODER_PARITY_NOT_PASSED'))


class LivePathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.taps = FakeTaps()
        self.r.tool_forecast = F.ToolForecast(self.r.store, self.r.home, taps=self.taps)
        self.g = hub(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def ev(self, text):
        return self.r.store.event(self.r.session, text)

    def run_calc(self, text):
        self.g.tools.enable('calc')
        self.g.tools._policy = lambda spec, origin, args, confirmed=False: ('APPROVED', 'POLICY', [])
        e = self.ev(text)
        ts = T.ToolStep(self.r)
        p = ts.plan(e, text)
        return e, ts.execute(e, p)

    def test_off_by_default_no_tap_no_prediction(self):
        e, res = self.run_calc('What is 37 times 2?')
        self.assertEqual(res['result'], 74)
        self.assertEqual(self.taps.calls, [])
        self.assertIsNone(self.g.tools.box.load()[0]['calls'][-1]['predicted'])

    def test_calc_forecast_before_effect_scored_after_final(self):
        self.r.tool_forecast.set_mode('SHADOW')
        e, res = self.run_calc('What is 37 times 2?')
        tx = self.g.tools.box.load()[0]['calls'][-1]
        self.assertTrue(F.is_forecast(tx['predicted']))
        self.assertEqual(tx['predicted']['action'], 'double')
        self.assertEqual(tx['predicted']['authority'], 'LOCAL_PREDICTION_HYPOTHESIS')
        self.assertEqual(self.taps.calls, [['The counter shows 37.']])          # pre-state only, before the effect
        copy = json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='CorollaryCopy' AND event_id=?", (e['event_id'],))['payload'])
        self.assertEqual(copy['expected']['predicted']['forecast_id'], tx['predicted']['forecast_id'])  # committed before the effect
        settle_turn(self.r, e['event_id'], 'FINAL')                               # provisional outcome -> sinks
        self.assertEqual(self.taps.calls[-1], ['After doubling, the counter shows 74.'])
        rep = self.r.tool_forecast.report()
        self.assertEqual(rep['pending'], 0)
        self.assertEqual(rep['stats']['calc_counter:double']['n'], 1)
        self.assertEqual(rep['recent'][-1]['status'], 'SCORED')
        self.assertEqual(set(rep['recent'][-1]['mse']), {'forecast', 'copy', 'mean_delta'})
        grounded = self.g.grounding.box.load()[0]['closed'][-1]
        self.assertIsNone(grounded['predicted'])   # AG2 frequency baseline untouched by the latent forecast
        settle_turn(self.r, e['event_id'], 'FINAL')
        self.assertEqual(self.r.tool_forecast.report()['stats']['calc_counter:double']['n'], 1)  # idempotent

    def test_unmapped_calc_records_reason_without_tap(self):
        self.r.tool_forecast.set_mode('SHADOW')
        self.run_calc('What is 48 times 37?')
        self.assertEqual(self.taps.calls, [])
        self.assertEqual(self.r.tool_forecast.report()['counts'].get('CALC_EXPRESSION_NOT_IN_WORLD'), 1)

    def test_note_edit_proposed_approved_scored_and_survives_restart(self):
        self.g.tools.enable('sandbox_note')
        sandbox = self.r.home / 'data' / 'tool_sandbox'
        sandbox.mkdir(parents=True, exist_ok=True)
        (sandbox / 'todo.txt').write_text('Pay the dentist next week.')
        self.r.tool_forecast.set_mode('SHADOW')
        e = self.ev('Mark note todo as done')
        ts = T.ToolStep(self.r)
        p = ts.plan(e, 'Mark note todo as done')
        self.assertEqual(p['status'], 'PROPOSED')
        pending = ts.propose_call(e, p)
        self.assertEqual((sandbox / 'todo.txt').read_text(), 'Pay the dentist next week.')   # nothing happened yet
        self.assertEqual(self.r.tool_forecast.report()['pending'], 1)
        # restart between proposal and approval: forecast and call both persist
        home = self.r.home
        self.r.close()
        self.r = Runtime(home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.tool_forecast = F.ToolForecast(self.r.store, self.r.home, taps=self.taps)
        self.g = hub(self.r)
        self.assertEqual(self.r.tool_forecast.report()['pending'], 1)
        out = json.loads(tx_command(self.r, ['approve', pending['call_id']]))
        self.assertEqual(out['status'], 'EXECUTED')
        self.assertEqual((sandbox / 'todo.txt').read_text(), 'Pay the dentist next week. Done.')
        self.assertEqual(self.taps.calls[-1], ['After appending, the note reads: Pay the dentist next week. Done.'])
        rep = self.r.tool_forecast.report()
        self.assertEqual((rep['pending'], rep['stats']['note_edit:append_done']['n'], rep['stats']['note_edit:append_done']['in_range']), (0, 1, 1))

    def test_operator_command_and_no_active_mode(self):
        from v13.toolforecast import operator_command
        self.assertEqual(json.loads(operator_command(self.r, ['shadow']))['mode'], 'SHADOW')
        self.assertEqual(json.loads(operator_command(self.r, ['status']))['mode'], 'SHADOW')
        self.assertEqual(json.loads(operator_command(self.r, ['off']))['mode'], 'OFF')
        with self.assertRaises(ValueError):
            operator_command(self.r, ['active'])


class DeviceScriptTests(unittest.TestCase):
    def test_build_reuses_pinned_worker_command_with_tap_source(self):
        sys.path.insert(0, str(APP / 'scripts'))
        import test_tool_forecast_phone as P
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            (home / 'bin').mkdir()
            (home / 'config').mkdir()
            worker = str(APP / 'scripts/native_prefill_worker.cpp')
            seen = {}

            def prepare(h, identity, runner, cancel, out):
                return None, {'identity_key': {'k': 1}, 'command': ['c++', '-O2', worker, 'sha.o', '-o', str(h / 'bin/native-prefill-worker.new')]}

            def bounded(command, log, cancel, seconds):
                seen['command'] = command
                Path(command[-1]).write_bytes(b'bin')
                log.write_text('')
                return {'exit_code': 0, 'stop_reason': None}
            old = P.port.prepare_worker, P.port.bounded_process
            P.port.prepare_worker, P.port.bounded_process = prepare, bounded
            try:
                binary, info = P.build_taps(home, {}, {}, None, home)
                self.assertEqual(seen['command'][2], str(P.SOURCE))
                self.assertEqual(binary, home / 'bin/native-layer-taps')
                again, _ = P.build_taps(home, {}, {}, None, home)      # cached by identity + binary hash
                self.assertEqual(again, binary)
                P.port.prepare_worker = lambda *a: (None, {'identity_key': {'k': 2}, 'command': ['c++', 'other.cpp']})
                with self.assertRaises(RuntimeError):
                    P.build_taps(home, {}, {}, None, home)
            finally:
                P.port.prepare_worker, P.port.bounded_process = old

    def test_fixed_live_plan_matches_preregistration(self):
        plan = json.loads((APP / 'specs/tool_forecast/live-plan.json').read_text())['plan']
        prereg = APP / 'docs/proofs/continuation-20261012/tool-forecast-live/preregistration.json'
        if prereg.exists():   # not shipped in the phone package
            self.assertEqual(plan, json.loads(prereg.read_text())['plan'])
        self.assertEqual((len(plan['calc_in_world']), len(plan['note_in_world'])), (25, 25))


@unittest.skipUnless(os.environ.get('V13_TAP_TOOL') and os.environ.get('V13_TAP_MODEL'), 'native tap tool + Qwen3.5 GGUF not given')
class NativeEncoderTests(unittest.TestCase):
    def test_install_parity_and_live_round_trip(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            proc = subprocess.run([sys.executable, str(APP / 'scripts' / 'install_tool_forecast.py'), 'install', '--home', d,
                                   '--tool', os.environ['V13_TAP_TOOL'], '--model', os.environ['V13_TAP_MODEL']], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
            r = Runtime(Path(d))
            try:
                r.sleep.cycle.set_policy('enabled', 'off')
                g = hub(r)
                F.for_runtime(r).set_mode('SHADOW')
                g.tools.enable('calc')
                g.tools._policy = lambda spec, origin, args, confirmed=False: ('APPROVED', 'POLICY', [])
                e = r.store.event(r.session, 'What is 412 minus 7?')
                ts = T.ToolStep(r)
                ts.execute(e, ts.plan(e, 'What is 412 minus 7?'))
                settle_turn(r, e['event_id'], 'FINAL')
                rec = F.for_runtime(r).report()['recent'][-1]
                self.assertEqual((rec['status'], rec['action']), ('SCORED', 'subtract_7'))
                self.assertTrue(rec['beats_controls'])
            finally:
                r.close()


if __name__ == '__main__':
    unittest.main()
