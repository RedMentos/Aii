"""Run117CG: operator must report pending Sleep turns before first digest.

Real Runtime/Store/Operator; diagnostic counts never acquire source authority.
"""
from pathlib import Path
import json
import tempfile
import unittest

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import sleep_offline as S


class SleepPreDigestOperator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.r.sleep.cycle.set_policy("tick_seconds", "300")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def report(self):
        return json.loads(Operator(self.r).run(":sleep digest"))

    def turn(self, marker):
        event = self.r.store.event(self.r.session, "PREDIGEST_" + marker)
        self.r.store.message(self.r.session, event["event_id"], "assistant",
                             "SYNTHETIC_ANSWER_" + marker, "FINAL",
                             {"direct_source_copy": True})
        return event

    def test_pending_count_is_visible_before_first_sleep_without_mutation(self):
        before = self.report()
        self.assertEqual(before["pending_final_turns"], 0)
        self.assertFalse(before["catchup_pending"])
        self.assertEqual(before["fact_authority"], 0)
        self.turn("ALPHA")
        self.turn("BETA")
        result = self.report()
        self.assertEqual(result["entries"], 0)
        self.assertEqual(result["text"], "")
        self.assertEqual(result["pending_final_turns"], 2)
        self.assertTrue(result["catchup_pending"])
        self.assertEqual(result["fact_authority"], 0)
        self.assertIsNone(self.r.store.state(S.KEY, None)[0])
        self.assertEqual(S.digest(self.r.store)["turns"], 2)
        self.assertEqual(self.report()["pending_final_turns"], 0)

    def test_revoked_predigest_source_is_never_displayed_as_fact(self):
        event = self.turn("REVOKED")
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (event["source_ref"]["source_id"],))
        pending = self.report()
        self.assertEqual(pending["pending_final_turns"], 1)
        self.assertEqual(pending["text"], "")
        self.assertEqual(pending["fact_authority"], 0)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        after = self.report()
        self.assertEqual(after["pending_final_turns"], 0)
        self.assertEqual(after["entries"], 0)
        self.assertNotIn("PREDIGEST_REVOKED", after["text"])


if __name__ == "__main__":
    unittest.main()
