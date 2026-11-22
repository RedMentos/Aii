"""JEF self-labels must respect an older human RECORD outside 512 recent feedback."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.runtime import Runtime


class JEFHumanRecordWindow(unittest.TestCase):
    def test_old_human_record_remains_a_veto_after_513_newer_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            r = Runtime(home)
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                r.cfg["learning_mode"] = "SHADOW"
                jo.set_mode(r.store, "learn")

                old = r.store.event(r.session, "synthetic older skill context")
                fp.head(r, "skill", old, "skill")
                d = jo._decision(r.store, old["event_id"], "skill")
                self.assertIsNotNone(d)
                key = d["context_ref"]["sha256"]
                self.assertEqual(jo.after_turn(
                    r, old, {"skill": {"name": "synthetic"}},
                    "FINAL", {"coalition": []}), {"skill": "skill"})
                r.memory.feedback(old["event_id"], "skill", "none", "record")

                newer = r.store.event(r.session, "synthetic unrelated skill context")
                fp.head(r, "skill", newer, "skill")
                for i in range(513):
                    # Real HumanDecision packets, source records and feedback;
                    # not synthetic bare rows or a mocked database scan.
                    r.memory.feedback(newer["event_id"], "skill",
                                      "none" if i % 2 else "skill", "record")

                recent = r.store.rows(
                    "SELECT event_id FROM feedback WHERE kind='skill' "
                    "ORDER BY created DESC LIMIT 512")
                self.assertEqual(len(recent), 512)
                self.assertTrue(all(x["event_id"] != old["event_id"]
                                    for x in recent))
                self.assertEqual(len(jo.training_rows(
                    r.store, "skill", d["context_revision"], set())), 0,
                    "Older human RECORD must veto a lower-authority self label")

                # Observe the real caller boundary too, before any optimizer.
                observed = []
                original = jo.training_rows

                def spy(store, component, revision, human_keys):
                    result = original(store, component, revision, human_keys)
                    observed.extend(row[0] for row in result)
                    return result

                with patch.object(jo, "training_rows", side_effect=spy), patch.object(
                        r.guard, "update", return_value="NORMAL"):
                    with self.assertRaisesRegex(ValueError, "Je Klasse"):
                        r.learner.shadow_readout("skill")
                self.assertNotIn(key, observed)
                self.assertEqual(r.pool.pids(), [])
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
