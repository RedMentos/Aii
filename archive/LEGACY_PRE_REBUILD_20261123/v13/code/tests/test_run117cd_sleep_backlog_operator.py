"""Run117CD operator-visible Sleep catch-up progress, real Store, no model."""
from pathlib import Path
import json
import tempfile
import unittest

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import sleep_offline as S


class SleepOperatorBacklog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.r.sleep.cycle.set_policy("tick_seconds", "300")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def turn(self, i):
        e = self.r.store.event(self.r.session, f"OPERATOR_BACKLOG_{i:03d}")
        self.r.store.message(self.r.session, e["event_id"], "assistant",
                             f"synthetic answer {i:03d}", "FINAL",
                             {"direct_source_copy": True})

    def report(self):
        return json.loads(Operator(self.r).run(":sleep digest"))

    def test_operator_exposes_pending_turn_count_without_fact_authority(self):
        for i in range(70):
            self.turn(i)
        self.assertEqual(S.digest(self.r.store)["turns"], 64)
        first = self.report()
        self.assertEqual(first["pending_final_turns"], 6)
        self.assertTrue(first["catchup_pending"])
        self.assertEqual(first["fact_authority"], 0)
        self.assertNotIn("OPERATOR_BACKLOG_069", first["text"])
        self.assertEqual(S.digest(self.r.store)["turns"], 6)
        second = self.report()
        self.assertEqual(second["pending_final_turns"], 0)
        self.assertFalse(second["catchup_pending"])
        self.assertEqual(second["fact_authority"], 0)
        self.turn(70)
        third = self.report()
        self.assertEqual(third["pending_final_turns"], 1)
        self.assertTrue(third["catchup_pending"])
        self.assertEqual(S.digest(self.r.store)["turns"], 1)
        self.assertEqual(self.report()["pending_final_turns"], 0)


if __name__ == "__main__":
    unittest.main()
