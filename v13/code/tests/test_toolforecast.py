"""Thread M: SHADOW tool-consequence forecast in the live tool path (IH-H29 `predicted`). Fake taps unless a native encoder
is given through V13_TAP_TOOL + V13_TAP_MODEL (then the parity-checked install and one live round trip run for real)."""
import contextlib
import hashlib
import io
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

    def test_competence_reference_flags_states_unlike_training_contexts(self):
        manifest = json.loads(F.MANIFEST.read_text())
        for world, entry in manifest['worlds'].items():
            ck = F.Checkpoint(world, entry)
            ref = ck.reference['taps']
            typical = ref[int(np.argmin([ck.competence(r)['distance'] for r in ref[:20]]))]
            near = typical + 1e-3 * np.random.default_rng(1).normal(size=ck.width)
            self.assertTrue(ck.competence(near)['in_domain'])
            far = F.rms_normalize(np.random.default_rng(2).normal(size=ck.width))
            c = ck.competence(far)
            self.assertFalse(c['in_domain'])
            self.assertEqual((c['signal'], c['threshold']), ('knn5_cosine_distance', round(entry['competence_reference']['threshold'], 8)))
            i = int(np.argmin([ck.competence(r)['distance'] for r in ref[:20]]))
            both = ck.competence(ref[i], ck.reference['taps_mean'][i])           # v2: last-token and token-mean tests
            self.assertEqual(both['signal'], 'knn5_cosine_last_or_mean')
            self.assertTrue(both['in_domain'])
            odd_mean = ck.competence(ref[i], F.rms_normalize(np.random.default_rng(4).normal(size=ck.width)))
            self.assertFalse(odd_mean['in_domain'])                             # either test alone flags the state
            self.assertGreater(odd_mean['score'], 1)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            entry = manifest['worlds']['note_edit']
            for k in ('checkpoint', 'metrics', 'competence'):
                (root / entry[k]).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(APP / entry[k], root / entry[k])
            with open(root / entry['competence'], 'ab') as f:
                f.write(b'\0')
            with self.assertRaisesRegex(ValueError, 'competence'):
                F.Checkpoint('note_edit', entry, root)
            self.assertIsNone(F.Checkpoint('note_edit', {k: v for k, v in entry.items() if k != 'competence'}, root).competence(far))

    def test_competence_check_scores_states_not_calls(self):
        sys.path.insert(0, str(APP / 'scripts'))
        import tool_forecast_competence_check as cc
        rows = []
        for arm, dist in (('calc_in_world', [.01, .02, .05]), ('calc_out_of_range', [.04, .2, .3]),
                          ('note_in_world', [.01, .01, .02]), ('note_free', [.3, .4, .5])):
            for i, d in enumerate(dist):
                for _ in range(3):   # several actions share one pre-effect state
                    rows.append({'arm': arm, 'state': i, 'status': 'SCORED', 'ratio_to_best_control': .5 if d < .035 else 2.,
                                 'competence': {'distance': d, 'in_domain': d <= .035, 'threshold': .035}})
        rep = cc.analyze(rows)
        calc, note = rep['worlds']['calc_counter'], rep['worlds']['note_edit']
        self.assertEqual(calc['states'], {'calc_in_world': 3, 'calc_out_of_range': 3})
        self.assertAlmostEqual(calc['auroc'], 8 / 9, places=4)
        self.assertAlmostEqual(calc['in_world_flag_rate'], 1 / 3, places=4)
        self.assertFalse(calc['pass'])
        self.assertTrue(note['pass'])
        self.assertEqual(note['report_only_ratio_geo_mean'], {'unflagged': .5, 'flagged': 2.})
        self.assertEqual(rep['verdict'], 'COMPETENCE_SIGNAL_NOT_CONFIRMED')
        plan = cc.plan('/root/native/restore') if Path('/root/native/restore/round8-note-tool-raw').exists() else None
        if plan:
            earlier = json.loads((APP / 'specs/tool_forecast/live-plan.json').read_text())['plan']
            for k in plan:
                self.assertEqual(len(plan[k]), cc.N)
                self.assertFalse(set(plan[k]) & set(earlier[k]))

    def synthetic_world(self, home, shift, law_for_retention):
        """calc checkpoint; experience follows W0 + shift; retention taps follow the given law."""
        manifest = json.loads(F.MANIFEST.read_text())
        ck = F.Checkpoint('calc_counter', manifest['worlds']['calc_counter'])
        rng = np.random.default_rng(5)
        lift = ck.p @ np.linalg.inv(ck.p.T @ ck.p)

        def outcome(x, j, w):
            target = x @ ck.p + ck.mean_delta[j] + (ck.features(x) - ck.centre[j]) @ w[j]
            return x + (target - x @ ck.p) @ lift.T
        w_new = ck.weight + shift
        exp = F.Experience(home)
        enc = {'tool_sha256': 'T', 'model_sha256': 'M', 'layer': 11, 'pooling': 'last'}
        for j in range(len(ck.actions)):
            for i in range(24):
                x = F.rms_normalize(rng.normal(size=ck.width))
                exp.add('calc_counter', x, outcome(x, j, w_new), j, 'f%d_%d' % (j, i), binding=F.experience_binding(ck, enc))
        rows = json.loads((APP / ck.entry['parity']).read_text())['rows']
        law = w_new if law_for_retention == 'shifted' else ck.weight
        taps = {}
        for r in rows:
            taps.setdefault(r['input'], F.rms_normalize(rng.normal(size=ck.width)))
        for r in rows:
            taps[r['outcome']] = outcome(taps[r['input']], ck.actions.index(r['action']), law)
        ret = Path(home) / 'ret.npz'
        F.save_npz(ret, texts=np.asarray(list(taps)), taps=np.stack(list(taps.values())).astype(np.float32))
        return ck, enc | {'retention': {'calc_counter': {'path': str(ret), 'sha256': F.sha_file(ret)}}}

    def test_learn_adapts_only_with_holdout_gain_and_retention(self):
        with tempfile.TemporaryDirectory() as d:
            ck0 = F.Checkpoint('calc_counter', json.loads(F.MANIFEST.read_text())['worlds']['calc_counter'])
            shift = np.random.default_rng(9).normal(scale=.02, size=ck0.weight.shape)
            ck, enc = self.synthetic_world(d, shift, 'shifted')
            self.assertEqual(F.learn(d, ck, {k: v for k, v in enc.items() if k != 'retention'})['reason'], 'NO_RETENTION_REFERENCE')
            region = F.learn(d, ck, enc)
            self.assertEqual((region['mode'], region['replay_pairs'], region['experience_out_of_domain']), ('region', 0, 96))
            self.assertTrue(region['pass'])
            rep = F.learn(d, ck, enc, 'mixed')
            self.assertEqual(rep['replay_pairs'], 800)          # the candidate's own training pairs are replayed
            self.assertTrue(rep['pass'])
            self.assertEqual(rep['adapted_actions'], ck.actions)
            got = F.load_adapted(d, ck, enc)
            self.assertEqual(got['mode'], 'mixed')
            w = got['weight']
            self.assertLess(np.abs(w - (ck.weight + shift)).mean(), np.abs(shift).mean())   # moved toward the new law
            npz, js = F.adapted_paths(d, ck.world)
            with open(npz, 'ab') as f:
                f.write(b'\0')
            self.assertIsNone(F.load_adapted(d, ck, enc))                                   # bytes bound by the report
        with tempfile.TemporaryDirectory() as d:
            ck, enc = self.synthetic_world(d, shift, 'measured')   # old world still holds on the retention set
            rep = F.learn(d, ck, enc, 'mixed')
            self.assertFalse(rep['pass'])
            self.assertEqual({v['kept'] for v in rep['actions'].values()}, {'MEASURED_RETENTION_FAIL'})
            self.assertFalse(F.adapted_paths(d, ck.world)[0].exists())
        with tempfile.TemporaryDirectory() as d:   # region mode ignores experience the reference calls in-domain
            ck, enc = self.synthetic_world(d, shift, 'shifted')
            exp = F.Experience(d)
            for i, x in enumerate(ck.reference['taps'][:40]):
                exp.add('calc_counter', x, x, 0, 'in%d' % i, binding=F.experience_binding(ck, enc))
            rep = F.learn(d, ck, enc)
            self.assertLessEqual(rep['experience_out_of_domain'], 96 + 4)    # edge training contexts may sit past the threshold
            self.assertLessEqual(rep['actions']['add_15']['rows'], 24 + 4)

    def test_adaptation_bound_to_competence_encoder_and_retention(self):
        """Codex review bdeb4f6, defect 1: a passing receipt is reused only against what it was validated on."""
        with tempfile.TemporaryDirectory() as d:
            ck0 = F.Checkpoint('calc_counter', json.loads(F.MANIFEST.read_text())['worlds']['calc_counter'])
            ck, enc = self.synthetic_world(d, np.random.default_rng(9).normal(scale=.02, size=ck0.weight.shape), 'shifted')
            rep = F.learn(d, ck, enc)
            self.assertTrue(rep['pass'])
            self.assertEqual(rep['binding'], F.adaptation_binding(ck, enc, 'region'))
            self.assertIsNotNone(F.load_adapted(d, ck, enc))
            self.assertIsNone(F.load_adapted(d, ck, enc | {'tool_sha256': 'T2'}))           # rebuilt tap tool
            self.assertIsNone(F.load_adapted(d, ck, enc | {'model_sha256': 'M2'}))
            ret = dict(enc['retention']['calc_counter'], sha256='0' * 64)
            self.assertIsNone(F.load_adapted(d, ck, enc | {'retention': {'calc_counter': ret}}))   # other retention taps
            ck.entry = dict(ck.entry, competence_sha256='1' * 64)                            # e.g. the v2 reference
            self.assertIsNone(F.load_adapted(d, ck, enc))
            ck.entry = ck0.entry
            npz, js = F.adapted_paths(d, ck.world)
            legacy = json.loads(js.read_text())
            del legacy['binding']                                                            # receipt from before bindings
            js.write_text(json.dumps(legacy))
            self.assertIsNone(F.load_adapted(d, ck, enc))
            js.write_text('{"pass": tr')
            self.assertIsNone(F.load_adapted(d, ck, enc))

    def test_experience_never_mixes_encoders(self):
        with tempfile.TemporaryDirectory() as d:
            ck = F.Checkpoint('calc_counter', json.loads(F.MANIFEST.read_text())['worlds']['calc_counter'])
            a = F.experience_binding(ck, {'tool_sha256': 'A', 'model_sha256': 'M', 'layer': 11, 'pooling': 'last'})
            b = dict(a, tool_sha256='B')
            exp, x = F.Experience(d), np.ones(ck.width)
            exp.add('calc_counter', x, x, 0, 'f1')                      # legacy, unbound
            exp.add('calc_counter', x, x, 0, 'f2', binding=a)
            exp.add('calc_counter', x, x, 0, 'f3', binding=a)
            got = exp.load('calc_counter')
            self.assertEqual((got['binding'], got['id'].tolist()), (a, ['f2', 'f3']))
            exp.add('calc_counter', x, x, 0, 'f4', binding=b)
            self.assertEqual(exp.load('calc_counter')['id'].tolist(), ['f4'])
            self.assertEqual(len(list(exp.dir.glob('calc_counter-unbound-*.npz'))), 2)   # set aside, not deleted
            rep = F.learn(d, ck, {'tool_sha256': 'A', 'model_sha256': 'M', 'layer': 11, 'pooling': 'last'})
            self.assertEqual(rep['reason'], 'EXPERIENCE_BINDING_MISMATCH')

    def test_learning_check_verdict(self):
        sys.path.insert(0, str(APP / 'scripts'))
        import tool_forecast_learning_check as lc
        def rows(arm, actions, adapted):
            return [{'arm': arm, 'action': a, 'status': 'SCORED',
                     'mse': {'forecast': 1., 'adapted': adapted(a), 'copy': 2., 'mean_delta': 1.5}} for a in actions for _ in range(2)]
        calc, note = ['double', 'add_15', 'quarter', 'subtract_7'], ['append_done', 'prefix_urgent', 'uppercase']
        learn = {w: {'pass': True, 'adapted_actions': ['x']} for w in lc.WORLDS}
        good = (rows('calc_shift_test', calc, lambda a: .5 if a != 'quarter' else 1.) + rows('calc_in_test', calc, lambda a: 1.01)
                + rows('note_shift_test', note, lambda a: .8) + rows('note_in_test', note, lambda a: 1.))
        rep = lc.analyze(good, learn)
        self.assertEqual(rep['verdict'], 'CONTINUAL_LEARNING_CONFIRMED')
        self.assertEqual(rep['worlds']['calc_counter']['shift_actions_improved'], 3)
        forgot = [dict(r, mse=dict(r['mse'], adapted=1.05)) if r['arm'] == 'note_in_test' else r for r in good]
        self.assertFalse(lc.analyze(forgot, learn)['worlds']['note_edit']['pass'])
        self.assertFalse(lc.analyze(good, dict(learn, calc_counter={'pass': False}))['worlds']['calc_counter']['pass'])

    def test_missing_or_failed_encoder_gives_no_forecast(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(F.load_encoder(d), (None, 'NO_ENCODER_INSTALLED'))
            p = Path(d) / 'data' / 'tool_forecast'
            p.mkdir(parents=True)
            (p / 'encoder.json').write_text(json.dumps({'schema': F.SCHEMA + '-encoder', 'parity': {'status': 'FAIL'}}))
            self.assertEqual(F.load_encoder(d), (None, 'ENCODER_PARITY_NOT_PASSED'))
            # Codex review bdeb4f6, defect 4: a partial or incomplete pointer is reported, never raised
            for bad in ('{"schema": "v13-tool', '[]', json.dumps({'schema': F.SCHEMA + '-encoder', 'parity': {'status': 'PASS'}})):
                (p / 'encoder.json').write_text(bad)
                self.assertEqual(F.load_encoder(d), (None, 'ENCODER_CONFIG_INVALID'), bad)


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
        self.assertFalse(tx['predicted']['competence']['in_domain'])   # a random fake tap is unlike every training context
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
        self.assertEqual(rep['recent'][-1]['competence'], tx['predicted']['competence'])
        self.assertEqual(rep['stats']['calc_counter:double']['in_domain'], 0)
        self.assertEqual(rep['experience_rows'], {'calc_counter': 1})                   # scored call joins the experience
        self.assertEqual(list(self.r.tool_forecast.pending_dir.iterdir()), [])
        self.assertEqual(self.r.tool_forecast.learn(['calc_counter'])['calc_counter']['reason'], 'NO_RETENTION_REFERENCE')
        grounded = self.g.grounding.box.load()[0]['closed'][-1]
        self.assertIsNone(grounded['predicted'])   # AG2 frequency baseline untouched by the latent forecast
        settle_turn(self.r, e['event_id'], 'FINAL')
        self.assertEqual(self.r.tool_forecast.report()['stats']['calc_counter:double']['n'], 1)  # idempotent

    def test_damaged_encoder_config_status_and_no_forecast(self):
        tf = F.ToolForecast(self.r.store, self.r.home)
        tf.set_mode('SHADOW')
        p = self.r.home / 'data' / 'tool_forecast'
        p.mkdir(parents=True, exist_ok=True)
        (p / 'encoder.json').write_text('{"schema": "v13-tool-forecast-v1-encoder", "par')
        self.assertEqual(tf.report()['encoder'], 'ENCODER_CONFIG_INVALID')
        self.assertIsNone(tf.predict('calc', {'expression': '37*2'}))
        self.assertEqual(tf.report()['counts'].get('ENCODER_CONFIG_INVALID'), 1)

    def test_checkpoint_changed_since_forecast_is_not_scored(self):
        """Codex review bdeb4f6, defect 3: a pending forecast is scored only by the checkpoint that made it."""
        tf = self.r.tool_forecast
        tf.set_mode('SHADOW')
        e, res = self.run_calc('What is 37 times 2?')
        fid = self.g.tools.box.load()[0]['calls'][-1]['predicted']['forecast_id']
        tf.box.mutate(lambda st: st['pending'][fid].update(checkpoint_sha256='0' * 64))
        settle_turn(self.r, e['event_id'], 'FINAL')
        rep = tf.report()
        self.assertEqual((rep['pending'], rep['recent'][-1]['status']), (0, 'CHECKPOINT_CHANGED_SINCE_FORECAST'))
        self.assertEqual(rep['experience_rows'], {})
        self.assertEqual(rep['stats'], {})

    def test_pending_capacity_removes_evicted_context_taps(self):
        """Codex review bdeb4f6, defect 5: the cap holds for the context files too; other files survive."""
        tf = self.r.tool_forecast
        tf.set_mode('SHADOW')
        tf.pending_dir.mkdir(parents=True, exist_ok=True)
        (tf.pending_dir / 'unrelated.txt').write_text('keep')
        old, F.PENDING_MAX = F.PENDING_MAX, 3
        try:
            ids = [tf.predict('calc', {'expression': '%d*2' % n})['forecast_id'] for n in range(10, 15)]
        finally:
            F.PENDING_MAX = old
        pending = tf.box.load()[0]['pending']
        self.assertEqual(sorted(pending), sorted(ids[-3:]))
        self.assertEqual(sorted(f.name for f in tf.pending_dir.iterdir()), sorted([i + '.npy' for i in ids[-3:]] + ['unrelated.txt']))
        self.assertEqual(tf.report()['counts']['EXPIRED_CAPACITY'], 2)

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


class InstallLifecycleTests(unittest.TestCase):
    """Codex review bdeb4f6, defect 2: a failed or interrupted reinstall keeps the passing encoder and its retention."""
    def setUp(self):
        sys.path.insert(0, str(APP / 'scripts'))
        import install_tool_forecast as I
        self.I = I
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / 'tool').write_bytes(b'tap tool')
        (self.d / 'model.gguf').write_bytes(b'gguf')
        manifest = json.loads(F.MANIFEST.read_text())
        manifest['encoder']['model_sha256'] = F.sha_file(self.d / 'model.gguf')
        (self.d / 'manifest.json').write_text(json.dumps(manifest))
        self.saved = F.MANIFEST, F.NativeLayerTaps, I.gate
        F.MANIFEST = self.d / 'manifest.json'
        self.fail_after = None
        test = self

        class Taps:
            calls = 0

            def __init__(self, enc, threads=4, timeout_s=0):
                pass

            def tap_both(self, texts):
                Taps.calls += 1
                if test.fail_after is not None and Taps.calls > test.fail_after:
                    raise RuntimeError('native tap tool exit 9')
                v = FakeTaps().tap(texts)
                return v, v[:, ::-1].copy()
        F.NativeLayerTaps = Taps
        self.Taps = Taps

    def tearDown(self):
        F.MANIFEST, F.NativeLayerTaps, self.I.gate = self.saved
        self.tmp.cleanup()

    def install(self, passing):
        self.I.gate = lambda per: passing
        self.Taps.calls = 0
        args = type('A', (), {'home': str(self.d / 'home'), 'tool': str(self.d / 'tool'), 'model': str(self.d / 'model.gguf'),
                              'threads': 1, 'backend_dir': None})()
        with contextlib.redirect_stdout(io.StringIO()):
            return self.I.install(args)

    def live(self):
        out = self.d / 'home' / 'data' / 'tool_forecast'
        enc = json.loads((out / 'encoder.json').read_text())
        for v in enc['retention'].values():
            self.assertEqual(F.sha_file(v['path']), v['sha256'])
        self.assertEqual(sorted(f.name for f in out.glob('retention-*.npz')), sorted(Path(v['path']).name for v in enc['retention'].values()))
        return (out / 'encoder.json').read_bytes()

    def test_failed_or_interrupted_reinstall_keeps_previous_generation(self):
        self.assertEqual(self.install(True), 0)
        first = self.live()
        self.assertEqual(self.install(False), 1)          # parity fails: nothing live changes, no files left behind
        self.assertEqual(self.live(), first)
        failed = json.loads((self.d / 'home/data/tool_forecast/encoder-parity-failed.json').read_text())
        self.assertEqual({v['written'] for v in failed['retention'].values()}, {False})
        self.fail_after = 1                               # the second world's tap run dies mid-install
        with self.assertRaises(RuntimeError):
            self.install(True)
        self.assertEqual(self.live(), first)
        self.fail_after = None
        self.assertEqual(self.install(True), 0)           # a passing reinstall switches generation and drops the old one
        self.assertNotEqual(self.live(), first)
        self.assertEqual(F.load_encoder(self.d / 'home', verify=False)[1], None)


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
        doc = json.loads((APP / 'specs/tool_forecast/learning-plan.json').read_text())
        prereg = APP / doc['source']
        if prereg.exists():
            self.assertEqual(hashlib.sha256(prereg.read_bytes()).hexdigest(), doc['preregistration_sha256'])
            self.assertEqual(doc['plan'], json.loads(prereg.read_text())['plan'])
        self.assertEqual((doc['round'], doc['mode'], len(doc['plan']['calc_shift_exp'])), (2, 'region', 40))


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
