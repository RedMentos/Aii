"""Regression: human ratings are distinct from observer timeliness evidence."""
import unittest

from v13 import turnflow


class MemoryState:
    def __init__(self):
        self.value = None
        self.version = 0

    def state(self, key, default):
        assert key == turnflow.KEY
        import copy
        return copy.deepcopy(self.value), self.version

    def set_state(self, key, value, expected):
        assert key == turnflow.KEY
        if expected != self.version:
            raise ValueError("stale")
        import copy
        self.value = copy.deepcopy(value)
        self.version += 1


class FeedbackCountTest(unittest.TestCase):
    def test_human_n_does_not_count_observer_timeliness(self):
        store = MemoryState()
        for i in range(7):
            eid = "event-" + str(i)
            turnflow.plan(store, eid, {}, 0, "B1_DETAIL")
            self.assertEqual(turnflow.observe(store, eid, "AFTER_OUTPUT"), "AFTER_OUTPUT")
        first = turnflow.feedback(store, "event-0", "wasteful")
        self.assertEqual(first["n"], 1)
        second = turnflow.feedback(store, "event-1", "useful")
        self.assertEqual(second["n"], 2)
        counts = turnflow.report(store)["feedback_patterns"][first["pattern"]]
        self.assertEqual(counts["too_late"], 7)
        self.assertEqual(counts["useful"], 1)
        self.assertEqual(counts["wasteful"], 1)

    def test_duplicate_human_feedback_does_not_increase_count(self):
        store = MemoryState()
        turnflow.plan(store, "event", {}, 0, "B2_GIST")
        turnflow.observe(store, "event", "AGREES")
        self.assertEqual(turnflow.feedback(store, "event", "useful")["n"], 1)
        with self.assertRaises(ValueError):
            turnflow.feedback(store, "event", "wasteful")
        self.assertEqual(turnflow.report(store)["feedback_patterns"]["pre0/no_focal/B2_GIST"]["useful"], 1)


if __name__ == "__main__":
    unittest.main()
