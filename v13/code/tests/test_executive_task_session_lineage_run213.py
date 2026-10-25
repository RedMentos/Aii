"""Run213: JEF active_task must be bound to current event or own human decision.

Actual Store/Executive, two sessions and synthetic persisted-state tampering.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.config import initialize
from v13.store import Store
from v13.executive import Executive


class ExecutiveTaskSessionLineageRun213(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.s = Store(self.home)
        self.a = self.s.new_session()
        self.b = self.s.new_session()
        self.x = Executive(self.s)
        self.ea = self.s.event(self.a, 'Run213 ALPHA own task')
        self.eb = self.s.event(self.b, 'Run213 BETA foreign task')
        self.x.begin(self.ea, self.a, self.cfg)
        self.x.begin(self.eb, self.b, self.cfg)

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def inject_task(self, task):
        key = 'C1_EXEC:' + self.a
        st, version = self.s.state(key, {})
        st['active_task'] = task
        self.s.set_state(key, st, expected=version)

    def test_foreign_implicit_task_cannot_reach_view_report_or_control(self):
        self.inject_task({'source_ref':self.eb['source_ref'],
                          'origin':'SOURCE_USER_REQUEST', 'status':'UNCONFIRMED'})
        view = self.x.view(self.a)
        self.assertIsNone(view['active_task'])
        self.assertNotIn('BETA', json.dumps(self.x.report_context(self.a)))
        self.assertNotIn('BETA', json.dumps(self.x.control_view(self.a, self.ea)))

    def test_foreign_explicit_operator_task_cannot_cross_sessions(self):
        self.x.task(self.a, 'Run213 ALPHA explicit decision')
        self.x.task(self.b, 'Run213 BETA explicit decision')
        foreign = self.x.view(self.b)['active_task']['source_ref']
        self.inject_task({'source_ref':foreign,
                          'origin':'EXPLICIT_OPERATOR_TASK', 'status':'UNCONFIRMED'})
        self.assertIsNone(self.x.view(self.a)['active_task'])
        self.assertNotIn('BETA', json.dumps(self.x.report_context(self.a)))

    def test_valid_explicit_operator_task_survives_later_turn(self):
        self.x.task(self.a, 'Run213 ALPHA explicit decision')
        later = self.s.event(self.a, 'Run213 unrelated question')
        self.x.begin(later, self.a, self.cfg)
        view = self.x.view(self.a)
        self.assertEqual(view['active_task']['exact_task'], 'Run213 ALPHA explicit decision')
        self.assertEqual(view['active_task']['origin'], 'EXPLICIT_OPERATOR_TASK')


if __name__ == '__main__':
    unittest.main()
