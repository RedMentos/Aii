"""JEF event retry must not revise a committed schedule or training evidence."""
import copy
import unittest
from v13 import turnflow


class Store:
    def __init__(self):
        self.value = None
        self.version = 0

    def state(self, key, default=None):
        return copy.deepcopy(self.value) if self.value is not None else default, self.version

    def set_state(self, key, value, expected=None):
        if expected != self.version:
            raise ValueError("CAS conflict")
        self.value = copy.deepcopy(value)
        self.version += 1


class ReplayTests(unittest.TestCase):
    def test_same_event_returns_exact_original_decision_without_write(self):
        store = Store()
        first = turnflow.plan(store, "one", {}, 0, "B1_DETAIL")
        before = store.version
        again = turnflow.plan(store, "one", {}, 0, "B1_DETAIL", eligible=False)
        self.assertEqual(again, first)
        self.assertEqual(store.version, before)
        turnflow.set_mode(store, "active", "OPERATOR_TTY")
        before = store.version
        self.assertEqual(turnflow.plan(store, "one", {}, 0, "B1_DETAIL"), first)
        self.assertEqual(store.version, before)

    def test_old_unsnapshotted_event_fails_closed_without_mutation(self):
        store = Store()
        turnflow.plan(store, "old", {}, 0, "B2_GIST")
        store.value["events"]["old"].pop("decision")
        before = store.version
        with self.assertRaisesRegex(ValueError, "lacks replayable decision"):
            turnflow.plan(store, "old", {}, 0, "B2_GIST")
        self.assertEqual(store.version, before)

    def test_observer_and_feedback_not_reset_by_retry(self):
        store = Store()
        first = turnflow.plan(store, "rated", {}, 0, "B1_DETAIL")
        turnflow.observe(store, "rated", "AFTER_OUTPUT")
        turnflow.feedback(store, "rated", "useful")
        before = turnflow.report(store)["feedback_patterns"]
        self.assertEqual(turnflow.plan(store, "rated", {}, 0, "B1_DETAIL"), first)
        self.assertEqual(turnflow.report(store)["feedback_patterns"], before)


    def test_concurrent_first_writer_wins_without_duplicate_record(self):
        store = Store()
        class RacingStore(Store):
            def __init__(self):
                super().__init__()
                self.injected = False
            def set_state(self, key, value, expected=None):
                if not self.injected and "race" in value["events"]:
                    self.injected = True
                    # Simulate a different first writer committing before CAS.
                    winner = turnflow.plan(store, "race", {}, 0, "B1_DETAIL",
                                           eligible=False)
                    self.value = copy.deepcopy(store.value)
                    self.version = store.version
                return super().set_state(key, value, expected)
        racing = RacingStore()
        losing = turnflow.plan(racing, "race", {}, 0, "B1_DETAIL",
                               eligible=True)
        self.assertEqual(losing["schedule"], "SPEAK_ONLY")
        self.assertEqual(racing.version, 1)
        self.assertEqual(len(racing.value["last"]), 1)
        self.assertEqual(racing.value["events"]["race"]["decision"], losing)

    def test_concurrent_different_pattern_fails_closed(self):
        store = Store()
        class RacingStore(Store):
            def set_state(self, key, value, expected=None):
                if self.version == 0:
                    winning = turnflow.plan(store, "race", {}, 1, "B2_GIST")
                    self.value = copy.deepcopy(store.value)
                    self.version = store.version
                return super().set_state(key, value, expected)
        racing = RacingStore()
        with self.assertRaisesRegex(ValueError, "different pattern"):
            turnflow.plan(racing, "race", {}, 0, "B1_DETAIL")
        self.assertEqual(racing.version, 1)
        self.assertEqual(racing.value["events"]["race"]["pattern"], "pre1/no_focal/B2_GIST")


if __name__ == "__main__":
    unittest.main()
