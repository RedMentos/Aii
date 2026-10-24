"""Run103: explicit Memory feedback must respect fixed user LEARN/WRITE rules.
Actual Runtime/SQLite; no models, no tool execution, no global-learning claim.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13 import userrules as U


TABLES = ("sources", "feedback", "memories", "replay", "packets")


class MemoryUserRuleGateRun103(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self):
        return self.r.store.event(self.r.session, "Project Orion budget?")

    def counts(self):
        return {t: self.r.store.one("SELECT COUNT(*) AS n FROM " + t)["n"] for t in TABLES}

    def rule(self, text):
        result = U.add(self.r.store, text, "USER_TYPED")
        self.assertEqual(len(result), 1)
        return result[0]

    def refused(self, text, permission="record"):
        e = self.event()
        self.rule(text)
        before = self.counts()
        with self.assertRaises(PermissionError):
            self.r.memory.feedback(e["event_id"], "fact", "120 Euro",
                                   permission=permission, key="Project Orion budget")
        self.assertEqual(self.counts(), before)

    def test_no_remember_rule_blocks_record_and_learn(self):
        for permission in ("record", "learn"):
            with self.subTest(permission=permission):
                # New independent Runtime to avoid state from earlier subcase.
                self.r.close()
                self.r = Runtime(self.home / permission)
                self.r.sleep.cycle.set_policy("enabled", "off")
                self.refused("Don't remember my chats.", permission)

    def test_no_learn_conversation_blocks_feedback(self):
        self.refused("Don't learn from our conversation.")

    def test_no_train_messages_blocks_feedback(self):
        self.refused("Don't train on my messages.")

    def test_no_store_personal_details_blocks_feedback(self):
        self.refused("Never store my personal details.")

    def test_ask_first_never_auto_approves_memory_write(self):
        self.refused("Ask me before you remember anything.")

    def test_retrieval_feedback_refused_without_side_effects(self):
        e = self.event()
        mid = self.r.memory.feedback(e["event_id"], "fact", "120 Euro",
                                     key="Project Orion budget")
        query = self.event()
        self.rule("Don't learn from our conversation.")
        before = self.counts()
        with self.assertRaises(PermissionError):
            self.r.memory.retrieval_feedback(query["event_id"], mid, "relevant", "learn")
        self.assertEqual(self.counts(), before)

    def test_rule_survives_restart_and_still_blocks(self):
        self.rule("Don't remember my chats.")
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        e = self.event()
        before = self.counts()
        with self.assertRaises(PermissionError):
            self.r.memory.feedback(e["event_id"], "fact", "120 Euro",
                                   key="Project Orion budget")
        self.assertEqual(self.counts(), before)

    def test_unreadable_rule_state_fails_closed(self):
        e = self.event()
        before = self.counts()
        with patch.object(U, "box", side_effect=RuntimeError("synthetic state read failure")):
            with self.assertRaises(PermissionError):
                self.r.memory.feedback(e["event_id"], "fact", "120 Euro",
                                       key="Project Orion budget")
        self.assertEqual(self.counts(), before)

    def test_no_rule_still_allows_explicit_feedback(self):
        e = self.event()
        mid = self.r.memory.feedback(e["event_id"], "fact", "120 Euro",
                                     key="Project Orion budget")
        self.assertTrue(self.r.store.one("SELECT id FROM memories WHERE id=?", (mid,)))

    def test_unrelated_send_rule_does_not_block_memory_feedback(self):
        self.rule("Never send my notes.")
        e = self.event()
        mid = self.r.memory.feedback(e["event_id"], "fact", "120 Euro",
                                     key="Project Orion budget")
        self.assertTrue(self.r.store.one("SELECT id FROM memories WHERE id=?", (mid,)))

    def test_explicitly_switched_off_rule_allows_feedback(self):
        r = self.rule("Don't remember my chats.")
        U.set_status(self.r.store, r["id"], "OFF")
        e = self.event()
        mid = self.r.memory.feedback(e["event_id"], "fact", "120 Euro",
                                     key="Project Orion budget")
        self.assertTrue(self.r.store.one("SELECT id FROM memories WHERE id=?", (mid,)))

    def test_forget_remains_available_under_no_learn_rule(self):
        e = self.event()
        mid = self.r.memory.feedback(e["event_id"], "fact", "120 Euro",
                                     key="Project Orion budget")
        self.rule("Don't remember my chats.")
        self.r.memory.forget(mid)
        self.assertEqual(self.r.store.one("SELECT active FROM memories WHERE id=?", (mid,))["active"], 0)


if __name__ == "__main__":
    unittest.main()
