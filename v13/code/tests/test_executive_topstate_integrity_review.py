"""C1/JEF independent review: malformed top-level persisted state must not crash continuity."""
import tempfile
import unittest
from pathlib import Path
from v13.config import initialize
from v13.store import Store
from v13.executive import Executive

class TopStateIntegrityReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.addCleanup(self.store.close)
        self.session = self.store.new_session()
        self.executive = Executive(self.store)
        event = self.store.event(self.session, "Original source-bound request")
        self.executive.begin(event, self.session, self.cfg)

    def test_non_dict_top_level_state_abstains_then_new_event_recovers(self):
        key = "C1_EXEC:" + self.session
        for idx, bad in enumerate(([{"untrusted": "text"}], "bad", 42, True)):
            with self.subTest(kind=type(bad).__name__):
                _, version = self.store.state(key, {})
                self.store.set_state(key, bad, expected=version)
                view = self.executive.view(self.session)
                self.assertEqual(view["session_id"], self.session)
                self.assertIsNone(view["active_task"])
                self.assertEqual(view["goal_sequence"], [])
                self.assertEqual(view["memory_refs"], [])
                self.assertEqual(view["open_questions"], [])
                self.assertIsNone(self.executive.report_context(self.session)["task_request"])
                event = self.store.event(self.session, "Fresh request " + str(idx))
                state = self.executive.begin(event, self.session, self.cfg)
                self.assertEqual(state["goal"], "Fresh request " + str(idx))
                self.assertEqual(self.executive.view(self.session)["active_task"]["exact_task"],
                                 "Fresh request " + str(idx))

    def test_valid_current_state_retains_task(self):
        view = self.executive.view(self.session)
        self.assertEqual(view["active_task"]["exact_task"], "Original source-bound request")
        self.assertEqual(self.executive.report_context(self.session)["task_request"]["exact_request"],
                         "Original source-bound request")

if __name__ == "__main__":
    unittest.main()
