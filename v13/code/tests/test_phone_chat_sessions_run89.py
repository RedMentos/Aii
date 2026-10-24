"""Run89 real SQLite multi-chat source and export isolation in extracted ZIP.

No native models or learned utility; see preregistration for claim scope.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path

from v13.operator import Operator
from v13.runtime import Runtime


def wait_idle(runtime, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if runtime.idle():
            return
        time.sleep(0.02)
    raise AssertionError("Runtime failed bounded idle wait")


class PhoneChatSessionsRun89(unittest.TestCase):
    def test_two_chat_exports_exact_sources_and_selected_chat_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            runtime = Runtime(home)
            try:
                op = Operator(runtime)
                chat_a = runtime.session
                text_a = "Kopiere exakt: 100% A"
                event_a = op.run(text_a)
                wait_idle(runtime)
                self.assertEqual(runtime.last_answer()["text"], "100% A")
                chat_b = op.run(":new")
                self.assertNotEqual(chat_a, chat_b)
                text_b = "Kopiere exakt: 100 percent B"
                event_b = op.run(text_b)
                wait_idle(runtime)
                self.assertEqual(runtime.last_answer()["text"], "100 percent B")

                exported_b = json.loads(Path(op.run(":export chat json")).read_text())
                self.assertEqual(
                    [x["text"] for x in exported_b],
                    [text_b, "100 percent B"])
                self.assertEqual(op.run(":open " + chat_a), chat_a)
                exported_a = json.loads(Path(op.run(":export chat json")).read_text())
                self.assertEqual(
                    [x["text"] for x in exported_a],
                    [text_a, "100% A"])
                sessions = json.loads(op.run(":chats"))
                self.assertEqual({row["id"] for row in sessions},
                                 {chat_a, chat_b})
                matches = json.loads(op.run(':search "100%"'))
                self.assertTrue(matches)
                self.assertEqual({row["session_id"] for row in matches},
                                 {chat_a})
            finally:
                runtime.close()

            runtime = Runtime(home)
            try:
                self.assertEqual(runtime.session, chat_a)
                self.assertEqual(runtime.store.queue_stats()["count"], 0)
                for event_id, original, session in (
                    (event_a, text_a, chat_a), (event_b, text_b, chat_b)):
                    row = runtime.store.one(
                        "SELECT session_id,packet FROM events WHERE id=?",
                        (event_id,))
                    self.assertEqual(row["session_id"], session)
                    ref = json.loads(row["packet"])["source_ref"]
                    self.assertEqual(runtime.store.read_source(ref), original)
                self.assertEqual(runtime.store.rows(
                    "SELECT session_id,text,status FROM messages "
                    "WHERE role='assistant' ORDER BY id"), [
                    {"session_id": chat_a, "text": "100% A", "status": "FINAL"},
                    {"session_id": chat_b, "text": "100 percent B",
                     "status": "FINAL"}])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
