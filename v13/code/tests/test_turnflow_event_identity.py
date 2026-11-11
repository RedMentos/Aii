"""A source event must not be rebound to a different JEF body pattern."""
import unittest
from v13 import turnflow


class Store:
    def __init__(self):
        self.value = None
        self.version = 0

    def state(self, key, default=None):
        import copy
        return copy.deepcopy(self.value) if self.value is not None else default, self.version

    def set_state(self, key, value, expected=None):
        import copy
        if expected != self.version:
            raise ValueError("CAS conflict")
        self.value = copy.deepcopy(value)
        self.version += 1


class EventIdentityTests(unittest.TestCase):
    def test_conflicting_role_does_not_rebind_event_or_feedback(self):
        store = Store()
        first = turnflow.plan(store, "source-1", {}, 0, "B1_DETAIL")
        version = store.version
        with self.assertRaisesRegex(ValueError, "different pattern"):
            turnflow.plan(store, "source-1", {}, 0, "B2_GIST")
        self.assertEqual(store.version, version)
        self.assertEqual(turnflow.report(store)["feedback_patterns"], {})
        self.assertEqual(turnflow.observe(store, "source-1", "AFTER_OUTPUT"), "AFTER_OUTPUT")
        rated = turnflow.feedback(store, "source-1", "wasteful")
        self.assertEqual(rated["pattern"], first["pattern"])

    def test_conflicting_preanswer_state_rejected_without_mutation(self):
        store = Store()
        turnflow.plan(store, "source-2", {}, 0, "B1_DETAIL")
        version = store.version
        with self.assertRaises(ValueError):
            turnflow.plan(store, "source-2", {}, 1, "B1_DETAIL")
        self.assertEqual(store.version, version)


if __name__ == "__main__":
    unittest.main()
