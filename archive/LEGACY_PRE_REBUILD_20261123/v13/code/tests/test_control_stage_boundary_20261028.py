"""RED-first WP-T14 FINAL latency boundary integrity; software-only."""
import json
from pathlib import Path
import tempfile
import time
import unittest

from v13 import control_budget as cb
from v13.config import initialize
from v13.store import Store


class ControlStageBoundary(unittest.TestCase):
    def test_final_without_start_or_finish_has_no_closed_duration(self):
        valid = {'ingress': 0., 'routing': .01,
                 'native_answer': .02, 'finished': .03}
        self.assertTrue(cb.durations(valid))
        self.assertEqual(cb.durations({k: v for k, v in valid.items()
                                       if k != 'finished'}), {})
        self.assertEqual(cb.durations({k: v for k, v in valid.items()
                                       if k != 'ingress'}), {})
        # Sparse interior stages are a documented historical compatibility path.
        self.assertEqual(cb.durations({'ingress': 0., 'finished': .03}),
                         {'ingress': .03})

    def test_incomplete_final_boundaries_never_pass_configured_control_limit(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            cfg = initialize(home)
            store = Store(home)
            try:
                chat = store.new_session()
                marks = [
                    {'ingress': 0., 'routing': .01,
                     'native_answer': .02, 'finished': .03},
                    {'ingress': 0., 'routing': .01, 'native_answer': .02},
                    {'routing': .01, 'native_answer': .02, 'finished': .03},
                ]
                for m in marks:
                    with store.tx() as db:
                        db.execute(
                            'INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)',
                            (chat, None, 'assistant', 'ok', 'FINAL',
                             json.dumps({'stage_marks_s': m}), time.time()))
                lat = cb.latency(store)
                self.assertEqual(lat['turns'], 1)
                self.assertEqual(lat['invalid_stage_marks'], 2)
                report = cb.report(store, home,
                                   cfg | {'control_budget_p95_ms': 10000.})
                self.assertEqual(report['verdict'], 'INCOMPLETE_EVIDENCE')
                self.assertTrue(report['limits']['control_p95_ms']['pass'])
                self.assertEqual(cb.report(store, home, cfg)['verdict'],
                                 'NO_LIMITS')
            finally:
                store.close()


if __name__ == '__main__':
    unittest.main()
