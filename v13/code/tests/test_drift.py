import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from v13 import drift, guards
from v13.common import dumps
from v13.runtime import Runtime

class FakeEvaluator:
    def __init__(self, value): self.value = value; self.seen = None
    def kl(self, prompts): self.seen = list(prompts); return self.value

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off'); self.s = self.r.store; self.d = drift.Drift(self.s, self.r.cfg)
    def tearDown(self): self.r.close(); self.tmp.cleanup()

class Measures(unittest.TestCase):
    def test_kl_and_flip_rate(self):
        self.assertAlmostEqual(drift.kl({'a': .5, 'b': .5}, {'a': .5, 'b': .5}), 0., places=9)
        self.assertGreater(drift.kl({'a': .9, 'b': .1}, {'a': .1, 'b': .9}), .5)
        self.assertGreater(drift.kl({'a': 1.}, {'b': 1.}), 1.)  # missing support is smoothed, not infinite
        self.assertEqual(drift.flip_rate(['x', 'y', 'z', 'x'], ['x', 'y', 'x', 'x']), .25)
        with self.assertRaises(ValueError): drift.flip_rate(['x'], [])

    def test_gate_caps_come_from_config(self):
        cfg = {'drift_kl_max': .05, 'drift_flip_max': .1, 'drift_required': 0}
        self.assertEqual(drift.gate({}, cfg), [])
        self.assertEqual(drift.gate({}, cfg | {'drift_required': 1}), ['DRIFT_NOT_MEASURED'])
        self.assertEqual(drift.gate({'drift': {'measure': 'LM_KL', 'value': .2, 'cap': 1.}}, cfg), ['DRIFT_ABOVE_CAP'])
        self.assertEqual(drift.gate({'drift': {'measure': 'DECISION_FLIP', 'value': .05}}, cfg), [])
        self.assertEqual(drift.gate({'drift': {'measure': 'OTHER', 'value': 0}}, cfg), ['DRIFT_INVALID'])
        self.assertIn('DRIFT_ABOVE_CAP', guards.stability_envelope({'drift': {'measure': 'LM_KL', 'value': .5}}, cfg))

class Probes(Base):
    def test_lm_probes_freeze_and_refuse_silent_change(self):
        prompts, sha = self.d.lm_probes(); self.assertGreaterEqual(len(prompts), 24)
        ev = FakeEvaluator(.01); rep = self.d.measure_lm('C3_LANGUAGE', ev)
        self.assertEqual(ev.seen, prompts); self.assertTrue(rep['passed']); self.assertEqual(rep['probes_sha256'], sha)
        self.assertFalse(self.d.measure_lm('C3_LANGUAGE', FakeEvaluator(.3))['passed'])
        doc = json.loads(drift.PROBE_FILE.read_text()); doc['probes'] = doc['probes'][:3]
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f: f.write(json.dumps(doc))
        try:
            with mock.patch.object(drift, 'PROBE_FILE', Path(f.name)), mock.patch.object(drift, 'APP', Path(f.name).parent):
                with self.assertRaises(ValueError): self.d.lm_probes()
                new = self.d.refreeze('lm', 'shorter set for test'); self.assertNotEqual(new, sha)
                self.assertEqual(len(self.d.lm_probes()[0]), 3)
        finally: Path(f.name).unlink()
        self.assertEqual(self.d.status()['history'][-1]['old_sha256'], sha)
        with self.assertRaises(ValueError): self.d.refreeze('lm', ' ')
        tel = self.s.rows("SELECT metrics FROM telemetry WHERE kind='drift_gate'")
        self.assertEqual(json.loads(tel[0]['metrics'])['measure'], 'LM_KL')

    def test_decision_probes_freeze_and_flip_gate(self):
        with self.assertRaises(ValueError): self.d.decision_probes('route')
        rows = [{'event_id': f'evt_{i}', 'label': 'simple' if i % 2 else 'detail'} for i in range(10)]
        with mock.patch.object(self.d, '_decision_rows', return_value=rows):
            items, sha = self.d.decision_probes('route')
        self.assertEqual(len(items), 10)
        with mock.patch.object(self.d, '_decision_rows', return_value=rows + [{'event_id': 'evt_new', 'label': 'gist'}]):
            self.assertEqual(self.d.decision_probes('route')[1], sha)  # frozen: new labels do not move the bar
        label = {r['event_id']: r['label'] for r in rows}
        ok = self.d.measure_decisions('route', label.get, label.get); self.assertEqual((ok['value'], ok['passed']), (0., True))
        flipped = lambda e: 'both' if e in ('evt_0', 'evt_1') else label[e]
        bad = self.d.measure_decisions('route', label.get, flipped); self.assertEqual(bad['value'], .2); self.assertFalse(bad['passed'])
        with self.assertRaises(ValueError): self.d.decision_probes('output_adapter')

    def test_record_binds_approve_through_envelope(self):
        gen = self.s.generation()['brain_generation_id']; uid = 'upd_' + 'a' * 32
        with self.s.tx() as c:
            c.execute("INSERT INTO updates(id,base_generation,status,path,hash,manifest,created) VALUES (?,?,?,?,?,?,?)",
                      (uid, gen, 'PENDING_APPROVAL', None, None, dumps({'component': 'route', 'commit_eligible': True}), 0.))
        rep = self.d.measure_lm('C3_LANGUAGE', FakeEvaluator(.4)); self.d.record(uid, rep)
        m = json.loads(self.s.one('SELECT manifest FROM updates WHERE id=?', (uid,))['manifest'])
        self.assertEqual(m['drift']['measure'], 'LM_KL')
        with self.assertRaises(ValueError) as cm: self.s.switch_generation(uid, self.r.cfg, self.r.revisions())
        self.assertIn('DRIFT_ABOVE_CAP', str(cm.exception))
        with self.assertRaises(ValueError): self.d.record('upd_missing', rep)

class SDFT(Base):
    def test_dataset_uses_self_teacher_not_correction_target(self):
        src = self.s.source('It is Canberra.', 'TEST_CORRECTION')
        with mock.patch.object(self.s, 'rows', return_value=[{'id': 'fb_1', 'event_id': 'evt_x', 'kind': 'fact', 'value': 'It is Canberra.', 'source_id': src['source_id'], 'hash': src['sha256']}]), \
             mock.patch.object(self.s, 'one', return_value={'text': 'What is the capital of Australia?'}):
            items = self.d.sdft_dataset()
        self.assertEqual(len(items), 1); it = items[0]
        self.assertIsNone(it['target']); self.assertEqual(it['target_policy'], 'SELF_TEACHER_IN_CONTEXT')
        self.assertIn('It is Canberra.', it['teacher_prompt']); self.assertNotIn('Canberra', it['student_prompt'])
        self.assertEqual(it['gate'], 'AG6_RETENTION_REQUIRED')

class Operator(Base):
    def test_operator_command(self):
        from v13.operator import Operator as Op
        out = json.loads(Op(self.r).run(':drift')); self.assertEqual(out['revision'], drift.REVISION)
        self.assertIn('prompts', json.loads(Op(self.r).run(':drift probes')))
        self.assertIn('sha256', json.loads(Op(self.r).run(':drift freeze lm')))
        self.assertEqual(json.loads(Op(self.r).run(':drift sdft')), [])
        with self.assertRaises(ValueError): Op(self.r).run(':drift bogus')

if __name__ == '__main__':
    unittest.main()
