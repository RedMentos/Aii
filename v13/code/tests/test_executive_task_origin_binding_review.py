"""Independent C1 task-origin RED/GREEN: source hash alone is not authority."""
import tempfile
import unittest
from pathlib import Path

from v13.config import initialize
from v13.store import Store
from v13.executive import Executive


class C1TaskOriginBindingReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.addCleanup(self.store.close)
        self.session = self.store.new_session()
        self.exec = Executive(self.store)
        self.event = self.store.event(self.session, 'Current user request')
        self.exec.begin(self.event, self.session, self.cfg)

    def corrupt_task(self, task):
        key = 'C1_EXEC:' + self.session
        state, version = self.store.state(key, {})
        state['active_task'] = task
        self.store.set_state(key, state, expected=version)

    def test_forged_operator_task_with_valid_unrelated_source_is_rejected(self):
        valid = self.store.source('Unrelated valid source', 'HUMAN_DECISION')
        self.corrupt_task({'source_ref': valid, 'origin': 'EXPLICIT_OPERATOR_TASK',
                           'status': 'UNCONFIRMED'})
        self.assertIsNone(self.exec.view(self.session)['active_task'])
        self.assertIsNone(self.exec.report_context(self.session)['task_request'])
        next_event = self.store.event(self.session, 'Next user request')
        self.exec.begin(next_event, self.session, self.cfg)
        self.assertEqual(self.exec.view(self.session)['active_task']['exact_task'],
                         'Next user request')

    def test_other_session_genuine_human_decision_cannot_be_imported(self):
        other = self.store.new_session()
        other_event = self.store.event(other, 'Other session request')
        self.exec.begin(other_event, other, self.cfg)
        self.exec.task(other, 'Other session pinned task')
        foreign = self.exec.view(other)['active_task']['source_ref']
        self.corrupt_task({'source_ref': foreign, 'origin': 'EXPLICIT_OPERATOR_TASK',
                           'status': 'UNCONFIRMED'})
        self.assertIsNone(self.exec.view(self.session)['active_task'])

    def test_cleared_operator_task_cannot_resurrect_from_persisted_state(self):
        self.exec.task(self.session, 'Operator pinned task')
        prior = self.exec.view(self.session)['active_task']['source_ref']
        self.assertEqual(self.exec.view(self.session)['active_task']['exact_task'],
                         'Operator pinned task')
        self.exec.task(self.session, clear=True)
        self.assertIsNone(self.exec.view(self.session)['active_task'])
        self.corrupt_task({'source_ref': prior, 'origin': 'EXPLICIT_OPERATOR_TASK',
                           'status': 'UNCONFIRMED'})
        self.assertIsNone(self.exec.view(self.session)['active_task'])
        self.assertIsNone(self.exec.report_context(self.session)['task_request'])

    def test_user_task_cannot_reference_prior_event_or_other_source(self):
        prior_ref = self.event['source_ref']
        next_event = self.store.event(self.session, 'New current request')
        self.exec.begin(next_event, self.session, self.cfg)
        self.corrupt_task({'source_ref': prior_ref, 'origin': 'SOURCE_USER_REQUEST',
                           'status': 'UNCONFIRMED'})
        self.assertIsNone(self.exec.view(self.session)['active_task'])
        self.assertIsNone(self.exec.report_context(self.session)['task_request'])

    def test_valid_current_user_and_latest_operator_task_survive(self):
        self.assertEqual(self.exec.view(self.session)['active_task']['exact_task'],
                         'Current user request')
        self.exec.task(self.session, 'Latest real operator task')
        self.assertEqual(self.exec.report_context(self.session)['task_request']['exact_request'],
                         'Latest real operator task')
        next_event = self.store.event(self.session, 'Unrelated next request')
        self.exec.begin(next_event, self.session, self.cfg)
        task = self.exec.view(self.session)['active_task']
        self.assertEqual(task['origin'], 'EXPLICIT_OPERATOR_TASK')
        self.assertEqual(task['exact_task'], 'Latest real operator task')
        self.assertEqual(self.exec.report_context(self.session)['task_request']['exact_request'],
                         'Latest real operator task')


if __name__ == '__main__':
    unittest.main()
