"""WP-T14 thin-control-fabric budget (§22.2.3): stage split, P95, state/checkpoint bytes, limits and :fabric."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from v13 import control_budget as cb
from v13.config import initialize
from v13.store import Store

class Budget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.home = Path(self.tmp.name); self.cfg = initialize(self.home); self.store = Store(self.home); self.chat = self.store.new_session()
    def tearDown(self): self.store.close(); self.tmp.cleanup()

    def turn(self, ctrl, body, status='FINAL'):
        """Marks for a turn whose control stages take ctrl seconds in total and body stages body seconds."""
        c = ctrl/7; marks = {}; t = 0.
        for s in cb.STAGES:
            marks[s] = t
            if s == 'finished': break
            t += body/2 if s in cb.BODY else c
        with self.store.tx() as db:
            db.execute('INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)',
                       (self.chat, None, 'assistant', 'a', status, json.dumps({'stage_marks_s': marks}), time.time()))

    def test_durations_split_control_from_body(self):
        d = cb.durations({'ingress': 0., 'routing': .1, 'native_answer': .3, 'finished': 1.3, 'bogus': .2})
        self.assertAlmostEqual(d['ingress'], .1); self.assertAlmostEqual(d['routing'], .2); self.assertAlmostEqual(d['native_answer'], 1.)
        self.assertNotIn('finished', d); self.assertEqual(cb.durations(None), {})
        self.assertNotIn('native_answer', cb.CONTROL); self.assertIn('routing', cb.CONTROL)

    def test_latency_report_and_limits(self):
        for i in range(19): self.turn(.07, 1.)
        self.turn(.7, 1.); self.turn(5., 5., status='CANCELLED')  # cancelled turns are not counted
        lat = cb.latency(self.store)
        self.assertEqual(lat['turns'], 20); self.assertAlmostEqual(lat['control_mean_ms'], 1000*(19*.07+.7)/20, places=1)
        self.assertAlmostEqual(lat['control_p95_ms'], 70., places=1); self.assertAlmostEqual(lat['control_share'], (19*.07+.7)/(19*.07+.7+20.), places=3)
        self.assertEqual(lat['inline_observer_rate'], 1.)
        rep = cb.report(self.store, self.home, self.cfg); self.assertEqual(rep['verdict'], 'NO_LIMITS'); self.assertEqual(rep['limits'], {})
        rep = cb.report(self.store, self.home, self.cfg | {'control_budget_p95_ms': 100.}); self.assertEqual(rep['verdict'], 'PASS')
        rep = cb.report(self.store, self.home, self.cfg | {'control_budget_p95_ms': 50., 'control_budget_state_mb': 100.}); self.assertEqual(rep['verdict'], 'FAIL')
        self.assertFalse(rep['limits']['control_p95_ms']['pass']); self.assertTrue(rep['limits']['state_mb']['pass'])

    def test_state_and_checkpoint_bytes(self):
        self.store.set_state('BIG', {'x': 'y'*5000}); st = cb.state_bytes(self.store)
        self.assertEqual(st['largest'][0]['key'], 'BIG'); self.assertGreater(st['bytes'], 5000)
        ck = self.home/'checkpoints'/'route-u1.npz'; ck.parent.mkdir(exist_ok=True); ck.write_bytes(b'0'*4096)
        (self.home/'models').mkdir(exist_ok=True); (self.home/'models'/'body.gguf').write_bytes(b'1'*10)
        fake = type('S', (), {'generation': lambda s: {'components': {'route': {'path': str(ck)}, 'body': 'models/body.gguf', 'gone': 'checkpoints/missing.npz'}}})()
        out = cb.checkpoints(fake, self.home)
        self.assertEqual([c['path'] for c in out], ['checkpoints/route-u1.npz']); self.assertEqual(out[0]['bytes'], 4096)
        self.assertIsInstance(cb.checkpoints(self.store, self.home), list)

    def test_operator_record(self):
        self.turn(.07, 1.); rt = type('R', (), {'store': self.store, 'home': self.home, 'cfg': self.cfg})()
        rep = cb.operator_command(rt, ['record']); self.assertEqual(rep['verdict'], 'NO_LIMITS')
        self.assertEqual(self.store.state(cb.KEY)[0]['verdict'], 'NO_LIMITS'); self.assertEqual(rep['energy_thermal'][:10], 'UNMEASURED')
        with self.assertRaises(ValueError): cb.operator_command(rt, ['bogus'])

if __name__ == '__main__':
    unittest.main()
