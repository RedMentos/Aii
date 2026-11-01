"""Independent review of Claude M 1941d07. Synthetic taps; no native inference.

Tests exercise the actual newly integrated module, never the Oct13 candidate.
The source-change window was reproduced against M's original 1941d07 and then
fixed with a narrow before/after observation snapshot in the actual module.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from v13 import toolforecast as F


class MemoryStore:
    """Persisted JSON snapshots for the real StateBox, with controlled write failure."""
    def __init__(self):
        self.values = {}
        self.logs = []
        self.fail_writes = False

    def state(self, key, default):
        return copy.deepcopy(self.values.get(key, (default, None)))

    def set_state(self, key, value, expected=None):
        if self.fail_writes:
            raise ValueError('synthetic persistence failure')
        old = self.values.get(key, (None, None))[1]
        if old != expected:
            raise ValueError('concurrent writer')
        self.values[key] = (copy.deepcopy(value), (old or 0) + 1)

    def log(self, kind, event, payload):
        self.logs.append((kind, event, payload))


class ToolForecastReview20261016(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.store = MemoryStore()
        self.tool, self.model = self.home / 'tap-tool', self.home / 'model.gguf'
        self.tool.write_bytes(b'synthetic encoder A')
        self.model.write_bytes(b'synthetic model fixture; never loaded')
        manifest = json.loads(F.MANIFEST.read_text())
        manifest['encoder']['model_sha256'] = F.sha_file(self.model)
        self.manifest = self.home / 'manifest.json'
        self.manifest.write_text(json.dumps(manifest))
        self.enc_path = self.home / 'data/tool_forecast/encoder.json'
        self.enc = {'schema': F.SCHEMA + '-encoder', 'parity': {'status': 'PASS'},
                    'tool_path': str(self.tool), 'tool_sha256': F.sha_file(self.tool),
                    'model_path': str(self.model), 'model_sha256': F.sha_file(self.model),
                    'layer': manifest['encoder']['layer'], 'pooling': manifest['encoder']['pooling']}
        self.write_encoder()
        owner = self

        class NativeStandIn:
            # Only the subprocess encoder is replaced. load_encoder, encoder(),
            # checkpoints, StateBox, disk buffers, prediction and scoring are real.
            calls = []
            after_before_effect_check = None

            def __init__(self, enc, *args, **kwargs):
                self.enc = enc

            def tap(self, texts):
                if texts[0].startswith('After ') and NativeStandIn.after_before_effect_check is not None:
                    NativeStandIn.after_before_effect_check()
                sha = F.sha_file(owner.tool)
                NativeStandIn.calls.append({'texts': list(texts), 'actual_tool_sha256': sha,
                                           'declared_tool_sha256': self.enc['tool_sha256']})
                return np.stack([np.random.default_rng(int(hashlib.sha256((sha + t).encode()).hexdigest()[:10], 16))
                                 .normal(size=1024).astype(np.float32) for t in texts])

            def tap_both(self, texts):
                x = self.tap(texts)
                return x, x[:, ::-1].copy()

        self.native = NativeStandIn
        self.patch = patch.object(F, 'NativeLayerTaps', NativeStandIn)
        self.patch.start()
        self.tf = self.runtime()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def write_encoder(self):
        F.atomic_write(self.enc_path, json.dumps(self.enc))

    def replace_encoder_binary(self):
        self.tool.write_bytes(b'synthetic encoder B changed in the source-change window')
        self.enc['tool_sha256'] = F.sha_file(self.tool)
        self.write_encoder()

    def runtime(self):
        tf = F.ToolForecast(self.store, self.home, manifest=self.manifest)
        tf.set_mode('SHADOW')
        return tf

    def predict(self, n=37):
        pred = self.tf.predict('calc', {'expression': '%d*2' % n})
        self.assertIsNotNone(pred)
        return pred

    def transaction(self, pred, n=37):
        return {'id': 'tx', 'predicted': pred, 'status': 'EXECUTED', 'result': n * 2}

    def test_bound_pending_restart_scores_once_and_retains_correct_encoder_binding(self):
        pred = self.predict()
        self.tf = self.runtime()    # the same persisted StateBox/disk, fresh checkpoint cache
        got = self.tf.observe(self.transaction(pred))
        self.assertEqual(got['status'], 'SCORED')
        self.assertIsNone(self.tf.observe(self.transaction(pred)))
        exp = F.Experience(self.home).load('calc_counter')
        self.assertEqual(exp['binding']['tool_sha256'], F.sha_file(self.tool))
        self.assertEqual(len(exp['x']), 1)

    def test_encoder_change_before_observe_closes_without_outcome_tap(self):
        pred = self.predict()
        self.replace_encoder_binary()
        self.tf = self.runtime()
        before = len(self.native.calls)
        got = self.tf.observe(self.transaction(pred))
        self.assertEqual(got['status'], 'ENCODER_CHANGED_SINCE_FORECAST')
        self.assertEqual(len(self.native.calls), before)
        self.assertIsNone(F.Experience(self.home).load('calc_counter'))

    def test_checkpoint_change_before_observe_closes_without_outcome_tap(self):
        pred = self.predict()
        self.tf.box.mutate(lambda st: st['pending'][pred['forecast_id']].update(checkpoint_sha256='old checkpoint'))
        self.tf = self.runtime()
        before = len(self.native.calls)
        got = self.tf.observe(self.transaction(pred))
        self.assertEqual(got['status'], 'CHECKPOINT_CHANGED_SINCE_FORECAST')
        self.assertEqual(len(self.native.calls), before)
        self.assertIsNone(F.Experience(self.home).load('calc_counter'))

    def test_66_predictions_keep_64_matching_context_files(self):
        self.tf.pending_dir.mkdir(parents=True)
        unrelated = self.tf.pending_dir / 'keep.txt'
        unrelated.write_bytes(b'keep')
        ids = [self.predict(n)['forecast_id'] for n in range(10, 76)]
        pending = self.tf.box.load()[0]['pending']
        files = {p.stem for p in self.tf.pending_dir.glob('*.npy')}
        self.assertEqual(len(pending), 64)
        self.assertEqual(set(pending), files)
        self.assertEqual(files, set(ids[-64:]))
        self.assertEqual(unrelated.read_bytes(), b'keep')

    def test_capacity_state_write_failure_preserves_old_pending_context_bytes(self):
        for n in range(10, 74):
            self.predict(n)
        state = self.tf.box.load()[0]
        original = {p.name: p.read_bytes() for p in self.tf.pending_dir.glob('*.npy')}
        self.store.fail_writes = True
        self.assertIsNone(self.tf.predict('calc', {'expression': '74*2'}))
        self.assertEqual(state, self.tf.box.load()[0])
        self.assertEqual(len(original), 64)
        for name, data in original.items():
            self.assertEqual((self.tf.pending_dir / name).read_bytes(), data)

    def test_stale_region_adaptation_rejected_after_real_competence_reference_change(self):
        ck = self.tf.checkpoint('calc_counter')
        ret = self.home / 'retention.npz'
        F.save_npz(ret, texts=np.asarray(['synthetic retention']), taps=np.ones((1, ck.width)))
        self.enc['retention'] = {ck.world: {'path': str(ret), 'sha256': F.sha_file(ret)}}
        self.write_encoder()
        npz, js = F.adapted_paths(self.home, ck.world)
        F.save_npz(npz, weight=ck.weight + .01)
        # A synthetic passing receipt is a loader fixture, not an empirical utility claim.
        report = {'pass': True, 'mode': 'region', 'checkpoint_sha256': ck.entry['checkpoint_sha256'],
                  'adapted_sha256': F.sha_file(npz), 'binding': F.adaptation_binding(ck, self.enc, 'region')}
        F.atomic_write(js, json.dumps(report))
        self.assertIsNotNone(F.load_adapted(self.home, ck, self.enc))
        data = json.loads(self.manifest.read_text())
        with np.load(F.APP / ck.entry['competence'], allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
        arrays['threshold_mean'] = arrays['threshold_mean'] * 1.5
        changed = self.home / 'changed-competence.npz'
        F.save_npz(changed, **arrays)
        data['worlds'][ck.world].update(competence=str(changed), competence_sha256=F.sha_file(changed))
        self.manifest.write_text(json.dumps(data))
        self.tf = self.runtime()
        new = self.tf.checkpoint(ck.world)
        self.assertIsNone(F.load_adapted(self.home, new, self.enc))
        # Raw observations depend on the encoder, not the competence classifier.
        self.assertEqual(F.experience_binding(new, self.enc), F.experience_binding(ck, self.enc))

    def test_foreign_encoder_experience_is_archived_without_losing_old_bytes(self):
        self.tf.observe(self.transaction(self.predict()))
        exp = F.Experience(self.home)
        old = exp.path('calc_counter').read_bytes()
        self.replace_encoder_binary()
        self.tf = self.runtime()
        self.tf.observe(self.transaction(self.predict(38), 38))
        archived = list(exp.dir.glob('calc_counter-unbound-*.npz'))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_bytes(), old)
        got = exp.load('calc_counter')
        self.assertEqual(got['binding']['tool_sha256'], self.enc['tool_sha256'])
        self.assertEqual(len(got['x']), 1)

    def test_outcome_encoder_change_after_initial_guard_must_not_score_or_append(self):
        """Regression: actual source B outcome must never be labelled as A."""
        pred = self.predict()
        self.native.after_before_effect_check = self.replace_encoder_binary
        got = self.tf.observe(self.transaction(pred))
        # Baseline 1941d07 returns SCORED and appends A-bound experience whose
        # outcome was produced by B. Correct behavior would close/refuse it.
        self.assertEqual(got['status'], 'SOURCE_CHANGED_DURING_OBSERVE')
        self.assertIsNone(F.Experience(self.home).load('calc_counter'))
        self.assertEqual(self.tf.report()['stats'], {})
        self.assertFalse((self.tf.pending_dir / (pred['forecast_id'] + '.npy')).exists())

    def private_asset(self, name):
        entry = self.tf.manifest['worlds']['calc_counter']
        path = self.home / ('private-' + name + '.npz')
        shutil.copyfile(F.APP / entry[name], path)
        entry[name] = str(path)
        return path

    def test_outcome_competence_asset_change_is_discarded_before_score(self):
        asset = self.private_asset('competence')
        pred = self.predict()
        def changed():
            with asset.open('ab') as stream:
                stream.write(b'synthetic competence source change')
        self.native.after_before_effect_check = changed
        done = self.tf.observe(self.transaction(pred))
        self.assertEqual(done['status'], 'SOURCE_CHANGED_DURING_OBSERVE')
        self.assertIsNone(F.Experience(self.home).load('calc_counter'))
        self.assertEqual(self.tf.report()['stats'], {})

    def test_outcome_checkpoint_asset_change_is_discarded_before_score(self):
        asset = self.private_asset('checkpoint')
        pred = self.predict()
        def changed():
            with asset.open('ab') as stream:
                stream.write(b'synthetic checkpoint source change')
        self.native.after_before_effect_check = changed
        done = self.tf.observe(self.transaction(pred))
        self.assertEqual(done['status'], 'SOURCE_CHANGED_DURING_OBSERVE')
        self.assertIsNone(F.Experience(self.home).load('calc_counter'))

    def test_outcome_source_discard_preserves_context_when_state_commit_fails(self):
        pred = self.predict()
        path = self.tf.pending_dir / (pred['forecast_id'] + '.npy')
        original = path.read_bytes()
        def changed():
            self.replace_encoder_binary()
            self.store.fail_writes = True
        self.native.after_before_effect_check = changed
        # The surrounding caller already catches persistence failures from the
        # best-effort telemetry path. This regression focuses on data safety.
        with self.assertRaises(ValueError):
            self.tf.observe(self.transaction(pred))
        self.assertEqual(path.read_bytes(), original)
        self.assertIn(pred['forecast_id'], self.tf.box.load()[0]['pending'])
        self.assertIsNone(F.Experience(self.home).load('calc_counter'))


def reproduce_outcome_encoder_window():
    """Machine-readable concrete evidence, no expected-failure traceback needed."""
    case = ToolForecastReview20261016()
    case.setUp()
    try:
        pred = case.predict()
        old = case.enc['tool_sha256']
        case.native.after_before_effect_check = case.replace_encoder_binary
        done = case.tf.observe(case.transaction(pred))
        exp = F.Experience(case.home).load('calc_counter')
        return {'status': done['status'], 'before_tool_sha256': old,
                'actual_outcome_tool_sha256': case.native.calls[-1]['actual_tool_sha256'],
                'experience_tool_sha256': exp['binding']['tool_sha256'] if exp else None,
                'experience_rows': len(exp['x']) if exp else 0, 'encoder_after': F.load_encoder(case.home)[0]['tool_sha256']}
    finally:
        case.tearDown()


if __name__ == '__main__':
    unittest.main()
