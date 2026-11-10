"""Human-labelled JEF veto must retain bounded opportunities for new evidence."""
import hashlib
import unittest
from v13 import turnflow


class HumanExplorationTest(unittest.TestCase):
    def test_active_human_veto_keeps_deterministic_probe(self):
        pattern = "pre0/no_focal/B1_DETAIL"
        state = {"mode": "active", "patterns": {pattern: {
            "useful": 0, "wasteful": 12, "on_time": 0, "too_late": 12}}}
        probe = next("event-" + str(i) for i in range(100)
                     if hashlib.sha256(("event-" + str(i)).encode()).digest()[0] % 4 == 0)
        nonprobe = next("event-" + str(i) for i in range(100)
                        if hashlib.sha256(("event-" + str(i)).encode()).digest()[0] % 4 != 0)
        yes = turnflow.decide(state, pattern, True, True, probe)
        no = turnflow.decide(state, pattern, True, True, nonprobe)
        self.assertTrue(yes["start_optional_observer"])
        self.assertTrue(yes["exploration_turn"])
        self.assertEqual(yes["adaptive_reason"], "HUMAN_FEEDBACK_EXPLORATION")
        self.assertFalse(no["start_optional_observer"])
        self.assertEqual(no["adaptive_reason"], "HUMAN_FEEDBACK")
        self.assertEqual(yes["human_feedback_n"], 12)
        self.assertEqual(no["human_feedback_n"], 12)

    def test_probe_never_bypasses_residency_or_eligibility(self):
        pattern = "pre0/no_focal/B2_GIST"
        state = {"mode": "active", "patterns": {pattern: {
            "useful": 0, "wasteful": 9, "on_time": 0, "too_late": 0}}}
        probe = next("probe-" + str(i) for i in range(100)
                     if hashlib.sha256(("probe-" + str(i)).encode()).digest()[0] % 4 == 0)
        for eligible, resident in ((False, True), (True, False)):
            result = turnflow.decide(state, pattern, eligible, resident, probe)
            self.assertFalse(result["start_optional_observer"])
            self.assertFalse(result["proposed_concurrency"])
        self.assertFalse(turnflow.decide(state, pattern, True, True, "")["start_optional_observer"])


if __name__ == "__main__":
    unittest.main()
