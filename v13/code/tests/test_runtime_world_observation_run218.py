"""Run218: actual Runtime C5 action/outcome -> WorldModel observed transition.

Real Runtime/SQLite with deterministic C3 double. No native model, fitted
world model, JEPA, Redmi, or acceptance-gate promotion.
"""
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from v13.backup import backup, restore
from v13.runtime import Runtime
from v13 import world_model


class RuntimeWorldObservationRun218(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.wire()

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def wire(self):
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.cfg.update(observer_mode='off', route_override='simple',
                          history_turns=0)
        fake = SimpleNamespace(
            role='C3_LANGUAGE', last_metrics={'test_seam': True},
            generate=lambda messages, *args, **kwargs: iter(['RUN218_C3_DOUBLE']),
        )
        self.r.pool.get = Mock(return_value=fake)
        self.r.learner.output_delta = Mock(return_value=None)

    def ask(self, text):
        eid = self.r.submit(text)
        deadline = time.monotonic() + 20
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.r.idle(), 'Runtime did not complete')
        answer = self.r.last_answer()
        self.assertEqual(answer['status'], 'FINAL', answer)
        self.assertEqual(answer['event_id'], eid)
        self.assertEqual(answer['text'], 'RUN218_C3_DOUBLE')
        return eid

    def test_actual_final_turn_yields_observed_not_invented_world_transition(self):
        eid = self.ask('RUN218_SOURCE observed action')
        rows = world_model.transitions(self.r.store)
        self.assertEqual(len(rows), 1, 'C5 final action must yield observed WorldModel row')
        row = rows[0]
        self.assertEqual(row['a'], 'simple')
        self.assertEqual(row['y'][1], 1.)
        self.assertIsNone(row['latent'], 'Synthetic C3 must not invent JEPA latent')
        self.assertEqual(self.r.store.one('SELECT event_id FROM actions WHERE id=?',
                                          (row['action_id'],))['event_id'], eid)
        cf = world_model.for_event(self.r.store, eid, 'simple')
        self.assertEqual(cf['authority'], 'HYPOTHESIS')
        self.assertEqual(cf['reason'], 'NO_WORLD_MODEL')
        self.assertIsNone(cf['prediction'])

    def test_backup_restores_exact_observed_actions_without_post_snapshot_rows(self):
        self.ask('RUN218_ALPHA before backup')
        before = world_model.transitions(self.r.store)
        self.assertEqual(len(before), 1)
        snapshot = backup(self.r.store)
        self.ask('RUN218_BETA after backup')
        self.assertEqual(len(world_model.transitions(self.r.store)), 2)
        self.r.close()
        self.r = None
        restore(self.home, snapshot)
        self.r = Runtime(self.home)
        self.wire()
        self.assertEqual(world_model.transitions(self.r.store), before)
        self.assertIsNone(world_model.load(self.r.store))


if __name__ == '__main__':
    unittest.main()
