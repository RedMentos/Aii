"""RED-first WP-T14 stage-order integrity tests; software only, no phone proof."""
import json
import tempfile
import time
import unittest
from pathlib import Path

from v13 import control_budget as cb
from v13.config import initialize
from v13.store import Store


class MonotonicFabricLatency(unittest.TestCase):
    def test_reversed_stage_marks_cannot_shift_control_time_into_body(self):
        wrong = {'ingress': 0., 'routing': 10., 'native_answer': 1.,
                 'finished': 11.}
        self.assertEqual(cb.durations(wrong), {})
        self.assertAlmostEqual(cb.durations({
            'ingress': 0., 'routing': 1., 'native_answer': 2.,
            'finished': 3.})['routing'], 1.)

    def test_nonfinite_boolean_and_negative_stage_marks_rejected(self):
        valid = {'ingress': 0., 'routing': 1., 'finished': 2.}
        for bad in (float('nan'), float('inf'), float('-inf'), True, -1.):
            with self.subTest(bad=bad):
                marks = dict(valid, routing=bad)
                self.assertEqual(cb.durations(marks), {})
        self.assertEqual(cb.durations(None), {})

    def test_invalid_final_mark_must_not_pass_configured_limit(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            cfg = initialize(home)
            store = Store(home)
            try:
                chat = store.new_session()
                def insert(marks):
                    with store.tx() as db:
                        db.execute(
                            'INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)',
                            (chat, None, 'assistant', 'ok', 'FINAL',
                             json.dumps({'stage_marks_s': marks}), time.time()))
                insert({'ingress': 0., 'routing': .01, 'native_answer': .02, 'finished': .03})
                insert({'ingress': 0., 'routing': 10., 'native_answer': 1., 'finished': 11.})
                lat = cb.latency(store)
                self.assertEqual(lat['turns'], 1)
                self.assertEqual(lat['invalid_stage_marks'], 1)
                rep = cb.report(store, home, cfg | {'control_budget_p95_ms': 10000.})
                self.assertEqual(rep['verdict'], 'INCOMPLETE_EVIDENCE')
                self.assertTrue(rep['limits']['control_p95_ms']['pass'])  # valid subset within cap
                self.assertEqual(rep['latency']['invalid_stage_marks'], 1)
                self.assertEqual(cb.report(store, home, cfg)['verdict'], 'NO_LIMITS')
            finally:
                store.close()


if __name__ == '__main__':
    unittest.main()
