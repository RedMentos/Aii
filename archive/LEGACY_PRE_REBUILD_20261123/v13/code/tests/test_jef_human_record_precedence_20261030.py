"""JEF WP-U1: explicit human RECORD must suppress lower-authority self-label training."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.runtime import Runtime


class JEFHumanRecordPrecedence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.r.cfg["learning_mode"] = "SHADOW"
        jo.set_mode(self.r.store, "learn")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def labelled_event(self, text):
        e = self.r.store.event(self.r.session, text)
        fp.head(self.r, "skill", e, "skill")
        self.assertEqual(jo.after_turn(
            self.r, e, {"skill": {"name": "synthetic_skill"}},
            "FINAL", {"coalition": []}), {"skill": "skill"})
        d = jo._decision(self.r.store, e["event_id"], "skill")
        self.assertIsNotNone(d)
        return e, d

    def actual_shadow_readout_human_keys(self):
        observed = []
        original = jo.training_rows

        def capture(store, component, revision, human_keys):
            observed.append(set(human_keys))
            return original(store, component, revision, human_keys)

        # All class minima are intentionally unsatisfied. This test observes
        # the real learning caller BEFORE any optimizer, native model or write.
        with patch.object(jo, "training_rows", side_effect=capture), patch.object(
                self.r.guard, "update", return_value="NORMAL"):
            with self.assertRaisesRegex(ValueError, "Je Klasse"):
                self.r.learner.shadow_readout("skill")
        self.assertEqual(len(observed), 1)
        return observed[0]

    def test_human_record_blocks_self_label_on_same_context(self):
        e, d = self.labelled_event("synthetic skill action alpha")
        key = d["context_ref"]["sha256"]
        self.assertEqual(len(jo.training_rows(
            self.r.store, "skill", d["context_revision"], set())), 1)
        self.r.memory.feedback(e["event_id"], "skill", "none", "record")
        self.assertIn(key, self.actual_shadow_readout_human_keys())
        self.assertEqual(jo.training_rows(
            self.r.store, "skill", d["context_revision"], {key}), [])
        self.assertEqual(self.r.pool.pids(), [])

    def test_later_record_revokes_previous_human_learn_without_self_reentry(self):
        e, d = self.labelled_event("synthetic skill action beta")
        self.r.memory.feedback(e["event_id"], "skill", "skill", "learn")
        self.r.memory.feedback(e["event_id"], "skill", "none", "record")
        self.assertIn(d["context_ref"]["sha256"],
                      self.actual_shadow_readout_human_keys())
        self.assertEqual(self.r.pool.pids(), [])

    def test_unlabelled_context_keeps_self_outcome_available(self):
        e, d = self.labelled_event("synthetic skill action gamma")
        self.assertEqual(self.actual_shadow_readout_human_keys(), set())
        rows = jo.training_rows(
            self.r.store, "skill", d["context_revision"], set())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1]["authority"], jo.AUTHORITY)
        self.assertEqual(rows[0][1]["value"], "skill")


if __name__ == "__main__":
    unittest.main()
