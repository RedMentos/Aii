"""Run92 JEF outcome self-labels cannot train out-of-vocabulary actions.

Real SQLite, source and decision packets; no native models or training.
"""
import tempfile
import unittest
from pathlib import Path

from v13 import fastpolicy, jefoutcome
from v13.operator import Operator
from v13.runtime import Runtime


CASES = (
    ("wake", "both", {"wake_decision": {"action": "both"}},
     [{"source_kind": "B1_DETAIL", "item_id": "o1"}], "detail"),
    ("memory", "recall", {"memory_ids": ["m1"]}, [], "skip"),
    ("skill", "skill", {"skill": {"name": "weekly_plan"}}, [], "skill"),
)


class JefOutcomeVocabularyRun92(unittest.TestCase):
    def test_invalid_matching_self_label_source_cannot_train_any_head(self):
        for component, baseline, meta, coalition, expected in CASES:
            with self.subTest(component=component):
                with tempfile.TemporaryDirectory() as directory:
                    runtime = Runtime(Path(directory))
                    try:
                        event = runtime.store.event(
                            runtime.session, "JEF source bound " + component)
                        fastpolicy.head(runtime, component, event, baseline)
                        got = jefoutcome.after_turn(
                            runtime, event, meta, "FINAL",
                            {"coalition": coalition})
                        self.assertEqual(got.get(component), expected)
                        decision = jefoutcome._decision(
                            runtime.store, event["event_id"], component)
                        revision = decision["context_revision"]
                        self.assertEqual(
                            jefoutcome.training_rows(
                                runtime.store, component, revision, set()), [])
                        Operator(runtime).run(":fastpolicy outcomes learn")
                        self.assertEqual(len(jefoutcome.training_rows(
                            runtime.store, component, revision, set())), 1)

                        # Simulate a corrupted self-label ledger AND matching
                        # authority-typed source: hashes alone do not make an
                        # arbitrary string a valid head action.
                        invalid = runtime.store.source(
                            "teleport", "OUTCOME_SELF_LABEL")
                        state, version = runtime.store.state(jefoutcome.KEY)
                        label = next(
                            x for x in state["labels"]
                            if x["event_id"] == event["event_id"]
                            and x["component"] == component)
                        label["value"] = "teleport"
                        label["source_id"] = invalid["source_id"]
                        runtime.store.set_state(
                            jefoutcome.KEY, state, expected=version)
                        self.assertEqual(
                            jefoutcome.training_rows(
                                runtime.store, component, revision, set()), [])
                    finally:
                        runtime.close()


if __name__ == "__main__":
    unittest.main()
