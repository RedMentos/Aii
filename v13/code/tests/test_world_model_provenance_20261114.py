"""Committed T8 producer preserves provenance for group-disjoint evaluation."""
import json
import unittest
from v13 import world_model


class ProvenanceStore:
    def rows(self, sql, params=()):
        if "FROM actions a" in sql:
            return [{
                "id": "action-1", "event_id": "event-1",
                "generation_id": "generation-1", "status": "FINAL",
                "expected": json.dumps({"forecast": {"input_chars": 64}}),
                "outcome": json.dumps({"action_duration_s": 0.5, "characters": 20}),
                "created": 3600.0,
            }]
        if "FROM packets WHERE kind='ActionSelection'" in sql:
            return [{"payload": json.dumps({
                "event_id": "event-1", "brain_generation_id": "generation-1",
                "stage": "COMMIT", "route_hint": "simple",
            })}]
        raise AssertionError("Unexpected SQL")


class ProvenanceContract(unittest.TestCase):
    def test_committed_transition_keeps_event_and_generation(self):
        rows = world_model.transitions(ProvenanceStore())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["action_id"], "action-1")
        self.assertEqual(rows[0]["event_id"], "event-1")
        self.assertEqual(rows[0]["generation_id"], "generation-1")
        self.assertEqual(rows[0]["a"], "simple")

    def test_provenance_is_not_model_training_label(self):
        row = world_model.transitions(ProvenanceStore())[0]
        self.assertEqual(len(row["s"]), 4)
        self.assertEqual(len(row["y"]), 3)


if __name__ == "__main__":
    unittest.main()
