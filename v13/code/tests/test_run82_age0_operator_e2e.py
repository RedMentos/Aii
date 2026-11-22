"""Run82 real Age0 Runtime+Operator lifecycle; no native/model calls."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.operator import Operator
from v13.runtime import Runtime


class TestRun82Age0OperatorLifecycle(unittest.TestCase):
    def test_source_verified_session_export_restart_and_confirmed_forget(self):
        with tempfile.TemporaryDirectory(prefix="v13-run82-age0-") as td:
            home = Path(td)
            question = "What is the budget for Project Elyra?"
            first_session = None
            mid = None
            r = Runtime(home)
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                op = Operator(r)
                status = json.loads(op.run(":status"))
                self.assertEqual(status["learning"], "RECORD_ONLY")
                first_session = status["session"]
                self.assertTrue(first_session)
                self.assertIn(":verified <Frage>", op.run(":help"))
                self.assertIn(first_session, [x["id"] for x in json.loads(op.run(":chats"))])

                e = r.store.event(r.session, "Project Elyra budget")
                mid = r.memory.feedback(e["event_id"], "fact", "615 Euro",
                                        key="Project Elyra budget", permission="record")
                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    source = json.loads(op.run(":verified " + question))
                self.assertEqual(source["status"], "READY")
                self.assertEqual(source["memory_id"], mid)
                self.assertFalse(source["model_called"])
                self.assertEqual(source["native_calls"], 0)
                self.assertNotIn("answer", source)

                exported = Path(op.run(":export chat json"))
                self.assertTrue(exported.is_file())
                self.assertEqual(exported.parent, home / "exports")
                self.assertIsInstance(json.loads(exported.read_text()), list)
                new_session = op.run(":new")
                self.assertNotEqual(new_session, first_session)
                self.assertEqual(json.loads(op.run(":status"))["session"], new_session)
                with self.assertRaisesRegex(ValueError, "Chat-ID unbekannt"):
                    op.run(":open does-not-exist")
                self.assertEqual(op.run(":open " + first_session), first_session)
            finally:
                r.close()

            r = Runtime(home)
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                op = Operator(r)
                self.assertEqual(r.session, first_session)
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    source = json.loads(op.run(":verified " + question))
                self.assertEqual(source["status"], "READY")
                self.assertEqual(source["memory_id"], mid)
                with self.assertRaisesRegex(ValueError, "--confirm"):
                    op.run(":forget " + str(mid))
                op.run(":forget " + str(mid) + " --confirm")
                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    source = json.loads(op.run(":verified " + question))
                self.assertEqual(source["status"], "CLARIFY")
                self.assertEqual(source["native_calls"], 0)
            finally:
                r.close()

            r = Runtime(home)
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                op = Operator(r)
                self.assertEqual(r.session, first_session)
                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    source = json.loads(op.run(":verified " + question))
                self.assertEqual(source["status"], "CLARIFY")
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
