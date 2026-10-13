"""Inactive candidate: synthetic lifecycle tests; no native inference or quality claim."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np

from v13 import toolforecast as F
from scripts import toolforecast_binding_candidate as C


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.manifest = json.loads(F.MANIFEST.read_text())
        self.ck = F.Checkpoint('calc_counter', self.manifest['worlds']['calc_counter'])
        self.ck.entry = copy.deepcopy(self.ck.entry)
        self.tool, self.model = self.home / 'tool', self.home / 'model'
        self.tool.write_bytes(b'synthetic tool, never executed')
        self.model.write_bytes(b'synthetic model, never loaded')
        self.ck.entry['model_sha256'] = F.sha_file(self.model)
        self.manifest['encoder']['model_sha256'] = F.sha_file(self.model)
        self.manifest['worlds'][self.ck.world]['model_sha256'] = F.sha_file(self.model)
        p = self.home / 'manifest.json'
        p.write_text(json.dumps(self.manifest))
        self.manifest_patch = patch.object(F, 'MANIFEST', p)
        self.manifest_patch.start()
        self.ret = self.home / 'staged-retention.npz'
        F.save_npz(self.ret, texts=np.asarray(['synthetic']), taps=np.ones((1, self.ck.width)))
        self.enc = {'schema': F.SCHEMA + '-encoder', 'model_path': str(self.model), 'model_sha256': F.sha_file(self.model),
                    'tool_path': str(self.tool), 'tool_sha256': F.sha_file(self.tool), 'layer': 11, 'pooling': 'last',
                    'parity': {'status': 'PASS', 'worlds': {self.ck.world: {'pass': True}}},
                    'retention': {self.ck.world: {'path': str(self.ret), 'sha256': F.sha_file(self.ret)}}}

    def tearDown(self):
        self.manifest_patch.stop()
        self.tmp.cleanup()

    def write_adaptation(self, ck=None):
        ck = ck or self.ck
        p, j = F.adapted_paths(self.home, ck.world)
        F.save_npz(p, weight=ck.weight + .01)
        rep = {'schema': F.SCHEMA + '-learn', 'world': ck.world,
               'pass': True, 'mode': 'region', 'checkpoint_sha256': ck.entry['checkpoint_sha256'],
               'adapted_sha256': F.sha_file(p), 'tool_sha256': self.enc['tool_sha256']}
        bound = C.learning_binding(ck, self.enc)
        rep = C.stamp_new_learning_report(rep, bound, ck, self.enc)
        j.write_text(json.dumps(rep))
        return p, j, rep

    def changed_competence(self):
        changed = copy.copy(self.ck)
        changed.entry = dict(self.ck.entry)
        p = self.home / 'prior-v1-reference.npz'
        # The exact lifecycle change from v1->v2: token-mean reference absent.
        F.save_npz(p, train_taps=self.ck.reference['taps'], k=np.asarray(self.ck.reference['k']),
                   threshold=np.asarray(self.ck.reference['threshold']))
        changed.entry.update(competence=str(p), competence_sha256=F.sha_file(p))
        changed.reference = {k: v for k, v in self.ck.reference.items() if k not in ('taps_mean', 'threshold_mean')}
        return changed

    def test_fresh_bound_receipt_reloads_without_inference(self):
        self.write_adaptation()
        got = C.load_bound_adapted(self.home, self.ck, self.enc)
        self.assertIsNotNone(got)
        self.assertEqual(got['mode'], 'region')
        np.testing.assert_array_equal(got['weight'], self.ck.weight + .01)

    def test_legacy_receipt_is_not_retroactively_promoted(self):
        p, j, rep = self.write_adaptation()
        del rep['binding']
        j.write_text(json.dumps(rep))
        self.assertIsNotNone(F.load_adapted(self.home, self.ck))   # BEFORE behavior
        self.assertIsNone(C.load_bound_adapted(self.home, self.ck, self.enc))

    def test_v1_region_receipt_cannot_activate_under_new_mean_gate(self):
        old = self.changed_competence()
        x = min(old.reference['taps'][:20], key=lambda r: old.competence(r)['distance'])
        xm = F.rms_normalize(np.random.default_rng(41).normal(size=old.width))
        self.assertTrue(old.competence(x, xm)['in_domain'])
        self.assertFalse(self.ck.competence(x, xm)['in_domain'])
        self.write_adaptation(old)
        self.assertIsNotNone(C.load_bound_adapted(self.home, old, self.enc))
        self.assertIsNotNone(F.load_adapted(self.home, self.ck))   # BEFORE behavior
        self.assertIsNone(C.load_bound_adapted(self.home, self.ck, self.enc))

    def test_tool_change_with_new_valid_file_hash_invalidates_fit(self):
        self.write_adaptation()
        self.tool.write_bytes(b'new device tool, never executed')
        replacement = dict(self.enc, tool_sha256=F.sha_file(self.tool))
        self.assertIsNone(C.load_bound_adapted(self.home, self.ck, replacement))

    def test_retention_change_with_new_valid_hash_invalidates_fit(self):
        self.write_adaptation()
        F.save_npz(self.ret, texts=np.asarray(['replacement']), taps=np.zeros((1, self.ck.width)))
        changed = copy.deepcopy(self.enc)
        changed['retention'][self.ck.world]['sha256'] = F.sha_file(self.ret)
        self.assertIsNone(C.load_bound_adapted(self.home, self.ck, changed))

    def test_receipt_stamp_refuses_asset_change_during_fit(self):
        _, _, rep = self.write_adaptation()
        before = C.learning_binding(self.ck, self.enc)
        with self.assertRaisesRegex(ValueError, 'CHANGED_DURING_FIT'):
            C.stamp_new_learning_report(rep, before, self.changed_competence(), self.enc)

    def test_pending_checkpoint_change_rejected_before_score(self):
        rec = {'checkpoint_sha256': self.ck.entry['checkpoint_sha256'], 'binding': C.forecast_binding(self.ck, self.enc)}
        self.assertEqual(C.validate_pending_record(rec, self.ck, self.enc), (True, None))
        changed = copy.copy(self.ck)
        changed.entry = dict(self.ck.entry, checkpoint_sha256='new checkpoint')
        self.assertEqual(C.validate_pending_record(rec, changed, self.enc), (False, 'CHECKPOINT_CHANGED_SINCE_FORECAST'))

    def test_pending_gate_change_and_legacy_snapshot_rejected(self):
        rec = {'checkpoint_sha256': self.ck.entry['checkpoint_sha256'], 'binding': C.forecast_binding(self.ck, self.enc)}
        self.assertFalse(C.validate_pending_record(rec, self.changed_competence(), self.enc)[0])
        del rec['binding']
        self.assertFalse(C.validate_pending_record(rec, self.ck, self.enc)[0])

    def test_corrupt_report_and_nonfinite_weight_fail_closed(self):
        p, j, rep = self.write_adaptation()
        j.write_text('{')
        self.assertIsNone(C.load_bound_adapted(self.home, self.ck, self.enc))
        weight = self.ck.weight.copy()
        weight[0, 0, 0] = np.nan
        F.save_npz(p, weight=weight)
        rep['adapted_sha256'] = F.sha_file(p)
        j.write_text(json.dumps(rep))
        self.assertIsNone(C.load_bound_adapted(self.home, self.ck, self.enc))


class LifecycleTests(BindingTests):
    def store(self):
        class Store:
            def __init__(self):
                self.values = {}
                self.logs = []
            def state(self, key, default):
                return copy.deepcopy(self.values.get(key, (default, None)))
            def set_state(self, key, value, expected=None):
                old = self.values.get(key, (None, None))[1]
                if expected != old:
                    raise ValueError('concurrent state change')
                self.values[key] = (copy.deepcopy(value), (old or 0) + 1)
            def log(self, kind, event, payload):
                self.logs.append([kind, event, payload])
        return Store()

    def taps(self):
        ck = self.ck
        x = min(ck.reference['taps'][:20], key=lambda v: ck.competence(v)['distance'])
        xm = F.rms_normalize(np.random.default_rng(41).normal(size=ck.width))
        class Taps:
            calls = 0
            def tap_both(self, texts):
                self.calls += 1
                return np.stack([x] * len(texts)), np.stack([xm] * len(texts))
            def tap(self, texts):
                return self.tap_both(texts)[0]
        return Taps()

    def instance(self, module, store, taps):
        tf = module.ToolForecast(store, self.home, manifest=F.MANIFEST, taps=taps)
        tf.encoder = lambda world: (taps, self.enc)
        tf.set_mode('SHADOW')
        return tf

    def test_actual_candidate_predict_rejects_old_region_adaptation_after_restart(self):
        old = self.changed_competence()
        self.write_adaptation(old)
        store, taps = self.store(), self.taps()
        original = self.instance(F, store, taps)
        original_forecast = original.predict('calc', {'expression': '37*2'})
        self.assertTrue(original_forecast['adapted_forecast'])     # BEFORE
        candidate = self.instance(C.materialize_runtime(), store, taps)
        result = candidate.predict('calc', {'expression': '38*2'})
        self.assertIsNotNone(result)
        self.assertFalse(result['adapted_forecast'])               # AFTER real predict path
        self.assertFalse(result['used_for_decision'])

    def test_actual_candidate_pending_survives_restart_and_scores_once(self):
        module, store, taps = C.materialize_runtime(), self.store(), self.taps()
        first = self.instance(module, store, taps)
        pred = first.predict('calc', {'expression': '37*2'})
        restarted = self.instance(module, store, taps)
        tx = {'predicted': pred, 'status': 'EXECUTED', 'result': 74, 'id': 'tx'}
        got = restarted.observe(tx)
        self.assertEqual(got['status'], 'SCORED')
        self.assertIsNone(restarted.observe(tx))
        exp = module.Experience(self.home).load(self.ck.world)
        self.assertEqual(len(exp['x']), 1)
        self.assertEqual(json.loads(str(exp['binding'])), C.forecast_binding(self.ck, self.enc))

    def test_actual_candidate_pending_checkpoint_change_closes_without_outcome_tap(self):
        module, store, taps = C.materialize_runtime(), self.store(), self.taps()
        first = self.instance(module, store, taps)
        pred = first.predict('calc', {'expression': '37*2'})
        # Represent a new measured checkpoint without requiring new native inference.
        restarted = self.instance(module, store, taps)
        changed = copy.copy(self.ck)
        changed.entry = dict(self.ck.entry, checkpoint_sha256='NEW-CHECKPOINT')
        restarted._checkpoints[self.ck.world] = changed
        calls_before = taps.calls
        got = restarted.observe({'predicted': pred, 'status': 'EXECUTED', 'result': 74, 'id': 'tx'})
        self.assertEqual(got['status'], 'CHECKPOINT_CHANGED_SINCE_FORECAST')
        self.assertEqual(taps.calls, calls_before)
        self.assertIsNone(module.Experience(self.home).load(self.ck.world))

    def test_actual_candidate_learn_refuses_legacy_experience_and_preserves_original_gates(self):
        from test_toolforecast import CheckpointTests
        module = C.materialize_runtime()
        shift = np.random.default_rng(9).normal(scale=.02, size=self.ck.weight.shape)
        _, synthetic = CheckpointTests().synthetic_world(self.home, shift, 'shifted')
        self.enc['retention'] = synthetic['retention']
        refused = module.learn(self.home, self.ck, self.enc)
        self.assertFalse(refused['pass'])
        self.assertEqual(refused['reason'], 'EXPERIENCE_BINDING_MISSING_OR_CHANGED')
        # This NEW synthetic dataset has known provenance. No historical artifact is relabelled.
        data = F.Experience(self.home).load(self.ck.world)
        F.Experience(self.home).path(self.ck.world).unlink()
        fresh = module.Experience(self.home)
        bound = C.forecast_binding(self.ck, self.enc)
        for x, y, action, fid in zip(data['x'], data['y'], data['action'], data['id']):
            fresh.add(self.ck.world, x, y, int(action), str(fid), binding=bound)
        passed = module.learn(self.home, self.ck, self.enc)
        self.assertTrue(passed['pass'])
        self.assertEqual(passed['binding'], C.learning_binding(self.ck, self.enc))
        self.assertIsNotNone(module.load_adapted(self.home, self.ck, self.enc))
        for action in passed['adapted_actions']:
            a = passed['actions'][action]
            self.assertLess(a['holdout_adapted_mse'], a['holdout_measured_mse'])
            self.assertLessEqual(a['retention_adapted'], F.RETENTION_MAX * a['retention_measured'])

    def test_outcome_tap_asset_change_refused_before_score_or_experience(self):
        module, store, taps = C.materialize_runtime(), self.store(), self.taps()
        tf = self.instance(module, store, taps)
        local = self.changed_competence()   # owned temporary reference; never alters M's file
        tf._checkpoints[self.ck.world] = local
        pred = tf.predict('calc', {'expression': '37*2'})
        original_tap = taps.tap
        def changing_tap(texts):
            value = original_tap(texts)
            with open(local.entry['competence'], 'ab') as f:
                f.write(b'synthetic source change during outcome prefill')
            return value
        taps.tap = changing_tap
        got = tf.observe({'predicted': pred, 'status': 'EXECUTED', 'result': 74, 'id': 'tx'})
        self.assertEqual(got['status'], 'FORECAST_BINDING_UNAVAILABLE')
        self.assertIsNone(module.Experience(self.home).load(self.ck.world))
        self.assertEqual(tf.report()['counts'].get('SCORED', 0), 0)

    def test_source_hash_mismatch_prevents_materialization(self):
        with self.assertRaisesRegex(ValueError, 'RUNTIME_SOURCE_NOT_PINNED'):
            C.materialize_runtime(expected_sha256='unowned future source')

    def test_corrupted_encoder_status_returns_unavailable_without_taps(self):
        module, store = C.materialize_runtime(), self.store()
        tf = module.ToolForecast(store, self.home, manifest=F.MANIFEST)
        path = self.home / 'data/tool_forecast/encoder.json'
        path.parent.mkdir(parents=True)
        for bad in ('{', '[1]', json.dumps({'schema': F.SCHEMA + '-encoder', 'parity': {'status': 'PASS'}})):
            path.write_text(bad)
            status = json.loads(module.operator_command(SimpleNamespace(tool_forecast=tf), ['status']))
            self.assertEqual(status['encoder'], 'ENCODER_CONFIG_INVALID')
            self.assertEqual(status['mode'], 'OFF')
            tf.set_mode('SHADOW')
            self.assertIsNone(tf.predict('calc', {'expression': '37*2'}))
            tf.set_mode('OFF')

    def test_capacity_commit_evicts_exact_old_context_files(self):
        module, store, taps = C.materialize_runtime(), self.store(), self.taps()
        tf = self.instance(module, store, taps)
        ids = []
        unrelated = tf.pending_dir / 'not-owned.txt'
        tf.pending_dir.mkdir(parents=True)
        unrelated.write_bytes(b'unrelated file survives capacity cleanup')
        for i in range(module.PENDING_MAX + 2):
            pred = tf.predict('calc', {'expression': '37*2'}, str(i))
            self.assertIsNotNone(pred)
            ids.append(pred['forecast_id'])
        pending = tf.box.load()[0]['pending']
        files = {p.stem for p in tf.pending_dir.glob('*.npy')}
        self.assertEqual(len(pending), 64)
        self.assertEqual(files, set(pending))
        self.assertEqual(files, set(ids[2:]))
        self.assertEqual(unrelated.read_bytes(), b'unrelated file survives capacity cleanup')

    def test_failed_capacity_persistence_preserves_every_pending_context(self):
        module, store, taps = C.materialize_runtime(), self.store(), self.taps()
        tf = self.instance(module, store, taps)
        for i in range(module.PENDING_MAX):
            self.assertIsNotNone(tf.predict('calc', {'expression': '37*2'}, str(i)))
        state_before = tf.box.load()[0]
        bytes_before = {p.name: p.read_bytes() for p in tf.pending_dir.glob('*.npy')}
        def failing_state(*args, **kwargs):
            raise ValueError('synthetic failure before state persistence')
        store.set_state = failing_state
        self.assertIsNone(tf.predict('calc', {'expression': '38*2'}, 'fail'))
        self.assertEqual(tf.box.load()[0], state_before)
        self.assertEqual(len(bytes_before), 64)
        for name, value in bytes_before.items():
            self.assertEqual((tf.pending_dir / name).read_bytes(), value)

    def test_cleanup_refuses_filenames_outside_forecast_namespace(self):
        owned = self.home / 'pending'
        owned.mkdir()
        outside = self.home / 'outside.npy'
        outside.write_bytes(b'must never delete')
        failures = C.unlink_evicted_contexts(owned, ['../outside', 'not-a-forecast'])
        self.assertEqual(len(failures), 2)
        self.assertTrue(outside.exists())


class PublicationTests(BindingTests):
    # Inherit setup helpers, not binding tests, through an explicit suite below.
    def publication_fixture(self):
        data = self.home / 'data/tool_forecast'
        data.mkdir(parents=True)
        old_ret = data / 'retention-calc_counter.npz'
        old_ret.write_bytes(b'previous measured retention')
        old = copy.deepcopy(self.enc)
        old['retention'][self.ck.world] = {'path': str(old_ret), 'sha256': F.sha_file(old_ret)}
        pointer = data / 'encoder.json'
        pointer.write_text(json.dumps(old))
        return pointer, pointer.read_bytes(), old_ret, old_ret.read_bytes(), {self.ck.world: C.source_binding(self.ck)}

    def test_failed_parity_preserves_encoder_and_retention(self):
        pointer, prior, old_ret, prior_ret, before = self.publication_fixture()
        bad = copy.deepcopy(self.enc)
        bad['parity']['status'] = 'FAIL'
        got = C.publish_verified_encoder(self.home, bad, before_assets=before, checkpoint_of=lambda _: self.ck)
        self.assertFalse(got['published'])
        self.assertEqual(pointer.read_bytes(), prior)
        self.assertEqual(old_ret.read_bytes(), prior_ret)
        self.assertFalse((pointer.parent / 'generations').exists())

    def test_passing_install_publishes_new_generation_then_pointer(self):
        pointer, prior, old_ret, prior_ret, before = self.publication_fixture()
        got = C.publish_verified_encoder(self.home, self.enc, before_assets=before, checkpoint_of=lambda _: self.ck)
        self.assertTrue(got['published'])
        new = json.loads(pointer.read_text())
        ret = new['retention'][self.ck.world]
        self.assertIn('/generations/', ret['path'])
        self.assertEqual(F.sha_file(ret['path']), ret['sha256'])
        self.assertEqual(old_ret.read_bytes(), prior_ret)
        self.assertEqual(new['install_source_binding'], before)

    def test_interruption_before_pointer_commit_preserves_last_pass(self):
        pointer, prior, old_ret, prior_ret, before = self.publication_fixture()
        def interruption(*args):
            raise OSError('synthetic crash before encoder-pointer commit')
        with self.assertRaisesRegex(OSError, 'synthetic crash'):
            C.publish_verified_encoder(self.home, self.enc, before_assets=before, checkpoint_of=lambda _: self.ck,
                                       replace_pointer=interruption)
        self.assertEqual(pointer.read_bytes(), prior)
        self.assertEqual(old_ret.read_bytes(), prior_ret)
        orphan = list((pointer.parent / 'generations').iterdir())
        self.assertEqual(len(orphan), 1)   # sealed unreferenced bytes; original generation is intact
        self.assertEqual(F.sha_file(orphan[0] / 'retention-calc_counter.npz'), self.enc['retention'][self.ck.world]['sha256'])

    def test_staged_tap_corruption_changes_no_live_bytes(self):
        pointer, prior, old_ret, prior_ret, before = self.publication_fixture()
        self.ret.write_bytes(b'corrupt staged file')
        with self.assertRaisesRegex(ValueError, 'STAGED_RETENTION_CHANGED'):
            C.publish_verified_encoder(self.home, self.enc, before_assets=before, checkpoint_of=lambda _: self.ck)
        self.assertEqual(pointer.read_bytes(), prior)
        self.assertEqual(old_ret.read_bytes(), prior_ret)
        self.assertFalse((pointer.parent / 'generations').exists())

    def test_changed_competence_during_parity_cannot_publish(self):
        pointer, prior, old_ret, prior_ret, before = self.publication_fixture()
        with self.assertRaisesRegex(ValueError, 'INSTALL_SOURCE_CHANGED_DURING_PARITY'):
            C.publish_verified_encoder(self.home, self.enc, before_assets=before, checkpoint_of=lambda _: self.changed_competence())
        self.assertEqual(pointer.read_bytes(), prior)
        self.assertEqual(old_ret.read_bytes(), prior_ret)


def load_tests(loader, tests, pattern):
    # Avoid repeating BindingTests inherited by PublicationTests.
    suite = unittest.TestSuite([loader.loadTestsFromTestCase(BindingTests)])
    suite.addTests(PublicationTests(name) for name in PublicationTests.__dict__ if name.startswith('test_'))
    suite.addTests(LifecycleTests(name) for name in LifecycleTests.__dict__ if name.startswith('test_'))
    return suite


if __name__ == '__main__':
    unittest.main()
