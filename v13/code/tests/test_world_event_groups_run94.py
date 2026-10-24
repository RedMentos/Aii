"""Run94: world-model held-out validation must separate whole event groups.

Synthetic digital transitions, real NumPy/SQLite state; no native models,
causal claims or real-world action authority.
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_world_model import synthetic
from v13 import world_model as WM
from v13.runtime import Runtime


class WorldEventGroupsRun94(unittest.TestCase):
    def test_repeated_event_rows_never_cross_train_test_boundary(self):
        transitions = synthetic(160, seed=12)
        for i, row in enumerate(transitions):
            row["event_id"] = "evt-%03d" % (i // 2)
        train, test, info = WM._split_grouped(transitions)
        self.assertTrue(train)
        self.assertTrue(test)
        train_events = {transitions[i]["event_id"] for i in train}
        test_events = {transitions[i]["event_id"] for i in test}
        self.assertTrue(train_events.isdisjoint(test_events))
        self.assertEqual(info["mode"], "EVENT_GROUP_HASHED")
        self.assertEqual(info["event_overlap"], 0)
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            try:
                with mock.patch.object(WM, "transitions",
                                       return_value=transitions):
                    fitted = WM.fit(runtime.store)
                self.assertEqual(fitted["status"], "FITTED")
                self.assertEqual(fitted["metrics"]["split"]["event_overlap"], 0)
                self.assertEqual(
                    fitted["metrics"]["split"]["mode"],
                    "EVENT_GROUP_HASHED")
            finally:
                runtime.close()

    def test_many_rows_from_only_two_events_are_not_valid_holdout(self):
        transitions = synthetic(32, seed=13)
        for i, row in enumerate(transitions):
            row["event_id"] = "evt-" + str(i % 2)
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            try:
                with mock.patch.object(WM, "transitions",
                                       return_value=transitions):
                    fitted = WM.fit(runtime.store)
                self.assertEqual(fitted["status"], "TOO_FEW_EVENT_GROUPS")
                self.assertEqual(fitted["metrics"]["split"]["mode"],
                                 "TOO_FEW_EVENT_GROUPS")
                self.assertNotIn("forward", fitted)
            finally:
                runtime.close()

    def test_legacy_synthetic_without_event_id_is_not_misrepresented(self):
        transitions = synthetic(160, seed=14)
        self.assertTrue(all("event_id" not in t for t in transitions))
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            try:
                with mock.patch.object(WM, "transitions",
                                       return_value=transitions):
                    fitted = WM.fit(runtime.store)
                self.assertEqual(fitted["status"], "FITTED")
                self.assertEqual(fitted["metrics"]["split"]["mode"],
                                 "LEGACY_INDEX_NO_EVENT_ID")
                self.assertIsNone(
                    fitted["metrics"]["split"]["event_overlap"])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
