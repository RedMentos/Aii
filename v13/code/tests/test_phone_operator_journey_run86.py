"""Run86: model-free operator journey from the *extracted* phone ZIP.

Real Runtime/Operator/SQLite paths; no model weights, inference, tool effects,
training, Redmi, or canonical gate promotion. See Run86 PREREG.md.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path

from v13.operator import Operator
from v13.runtime import Runtime
from v13 import standstill


def wait_idle(runtime, timeout=8.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if runtime.idle():
            return
        time.sleep(0.02)
    raise AssertionError("Bounded wait: Runtime never became idle")


class PhoneOperatorJourneyRun86(unittest.TestCase):
    def test_paused_fifo_exact_sources_export_and_second_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            first_text = "Kopiere exakt: Alpha from the source ZIP"
            second_text = "Kopiere exakt: Beta after restart"
            runtime = Runtime(home)
            try:
                op = Operator(runtime)
                self.assertEqual(op.run(":pause"), "Pausiert")
                first = op.run(first_text)
                second = op.run(second_text)
                session = runtime.session
                self.assertEqual(runtime.store.queue_stats()["count"], 2)
                self.assertEqual(runtime.store.rows(
                    "SELECT text FROM messages WHERE role='assistant'"), [])
                for event_id, text in ((first, first_text), (second, second_text)):
                    event = runtime.store.one(
                        "SELECT packet FROM events WHERE id=?", (event_id,))
                    source = json.loads(event["packet"])["source_ref"]
                    self.assertEqual(runtime.store.read_source(source), text)
            finally:
                runtime.close()

            runtime = Runtime(home)
            try:
                op = Operator(runtime)
                self.assertEqual(runtime.session, session)
                self.assertTrue(json.loads(op.run(":status"))["paused"])
                self.assertEqual(runtime.store.queue_stats()["count"], 2)
                self.assertEqual(op.run(":resume"), "Fortgesetzt")
                wait_idle(runtime)
                rows = runtime.store.rows(
                    "SELECT event_id,text,status FROM messages "
                    "WHERE role='assistant' ORDER BY id")
                self.assertEqual(rows, [
                    {"event_id": first, "text": "Alpha from the source ZIP",
                     "status": "FINAL"},
                    {"event_id": second, "text": "Beta after restart",
                     "status": "FINAL"}])
                export_path = Path(op.run(":export chat json"))
                self.assertTrue(export_path.is_file())
                exported = json.loads(export_path.read_text())
                self.assertTrue(any(
                    item["text"] == "Beta after restart"
                    for item in exported))
                self.assertIn("Alpha from the source ZIP", op.run(":search Alpha"))
            finally:
                runtime.close()

            runtime = Runtime(home)
            try:
                wait_idle(runtime)
                self.assertEqual(runtime.store.rows(
                    "SELECT event_id,text,status FROM messages "
                    "WHERE role='assistant' ORDER BY id"), rows)
                self.assertEqual(runtime.store.queue_stats()["count"], 0)
            finally:
                runtime.close()

    def test_standstill_persists_and_blocks_turn_until_local_release(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            runtime = Runtime(home)
            try:
                op = Operator(runtime)
                self.assertIn("STILLSTAND AN", op.run(":stillstand"))
                event_id = op.run("Kopiere exakt: Only after local release")
                self.assertEqual(runtime.store.queue_stats()["count"], 1)
                self.assertIsNone(runtime.last_answer())
            finally:
                runtime.close()

            runtime = Runtime(home)
            try:
                op = Operator(runtime)
                state = standstill.status(runtime)
                self.assertTrue(state["on"] and state["all_parts_on"])
                self.assertTrue(runtime.paused)
                self.assertEqual(runtime.store.queue_stats()["count"], 1)
                self.assertIsNone(runtime.last_answer())
                self.assertIn("aufgehoben", op.run(":stillstand aus"))
                wait_idle(runtime)
                self.assertEqual(runtime.store.rows(
                    "SELECT event_id,text,status FROM messages "
                    "WHERE role='assistant' ORDER BY id"), [
                    {"event_id": event_id,
                     "text": "Only after local release", "status": "FINAL"}])
                self.assertFalse(standstill.status(runtime)["on"])
            finally:
                runtime.close()

    def test_local_operator_origin_and_record_only_default(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            try:
                op = Operator(runtime)
                before = json.loads(op.run(":status"))
                self.assertEqual(before["learning"], "RECORD_ONLY")
                with self.assertRaisesRegex(ValueError, "lokale Operator"):
                    op.run(":status", origin="REMOTE_API")
                after = json.loads(op.run(":status"))
                self.assertEqual(after["learning"], "RECORD_ONLY")
                self.assertEqual(after["queued"], 0)
                self.assertEqual(runtime.store.rows(
                    "SELECT * FROM requests"), [])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
