"""C1 persisted malformed continuity RED: fail closed without losing valid source-bound task."""
import tempfile
import unittest
from pathlib import Path

from v13.config import initialize
from v13.store import Store
from v13.executive import Executive


class MalformedContinuityReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.addCleanup(self.store.close)
        self.session = self.store.new_session()
        self.executive = Executive(self.store)
        self.event = self.store.event(self.session, 'Budget 120 Euro. Berechne die Hälfte.')
        self.executive.begin(self.event, self.session, self.cfg)

    def corrupt(self, **changes):
        key = 'C1_EXEC:' + self.session
        state, version = self.store.state(key, {})
        state.update(changes)
        self.store.set_state(key, state, expected=version)

    def test_nonlist_persisted_fields_fail_closed(self):
        self.corrupt(goal_sequence=None, memory_refs='broken',
                     open_questions=42, salient_B_offer=False)
        view = self.executive.view(self.session)
        self.assertEqual(view['goal_sequence'], [])
        self.assertEqual(view['memory_refs'], [])
        self.assertEqual(view['open_questions'], [])
        self.assertEqual(view['salient_B_offer'], [])
        self.assertEqual(view['goal'], 'Budget 120 Euro. Berechne die Hälfte.')
        self.assertEqual(view['active_task']['exact_task'], view['goal'])
        self.assertEqual(self.executive.report_context(self.session)['task_request']['exact_request'],
                         view['goal'])

    def test_mixed_lists_drop_non_dict_but_keep_valid_source(self):
        good = {'event_id': self.event['event_id'], 'source_ref': self.event['source_ref']}
        self.corrupt(goal_sequence=[None, good, 42, 'text'],
                     memory_refs=[None, False, {'source_ref': {}}],
                     open_questions=['broken', 3, None],
                     salient_B_offer=[None, 4, 'broken'])
        view = self.executive.view(self.session)
        self.assertEqual(view['goal_sequence'], [good])
        self.assertEqual(view['memory_refs'], [])
        self.assertEqual(view['open_questions'], [])
        self.assertEqual(view['salient_B_offer'], [])
        self.assertEqual(view['active_task']['exact_task'], view['goal'])
        next_event = self.store.event(self.session, 'Independent new question')
        state = self.executive.begin(next_event, self.session, self.cfg)
        self.assertEqual(state['goal'], 'Independent new question')


if __name__ == '__main__':
    unittest.main()
