"""Live Memory/session revalidation at the bounded C3 renderer boundary."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.source_consumer import admit, render_messages, verified_recall_messages


class LiveC3RenderRevalidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.query = "What is the budget for Project Elyra?"
        self.row = self.add()

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def add(self, key="Project Elyra budget", value="615 Euro"):
        e = self.r.store.event(self.r.session, key)
        mid = self.r.memory.feedback(e["event_id"], "fact", value,
                                     key=key, permission="record")
        return self.r.memory.candidate(mid, self.r.session)

    def admission(self):
        return admit(self.query, self.r.session, [self.row], self.r.memory)

    def render(self, decision, *, session=None):
        return render_messages(self.r.cfg, self.query, decision,
                               memory=self.r.memory,
                               session=self.r.session if session is None else session)

    def test_actual_live_source_still_renders(self):
        d = self.admission()
        self.assertEqual(d["status"], "ADMITTED")
        self.assertIn("615 Euro", self.render(d)[0]["content"])
        packet = verified_recall_messages(self.r.cfg, self.query, self.r.session, self.r.memory)
        self.assertEqual(packet["decision"]["status"], "ADMITTED")
        self.assertIn("615 Euro", packet["messages"][0]["content"])

    def test_cross_session_replay_rejected(self):
        d = self.admission()
        other = self.r.store.new_session()
        with self.assertRaisesRegex(ValueError, "session mismatch"):
            self.render(d, session=other)

    def test_revoked_after_admission_rejected(self):
        d = self.admission()
        self.r.memory.forget(self.row["id"])
        with self.assertRaisesRegex(ValueError, "authorization changed"):
            self.render(d)
        self.assertIsNone(verified_recall_messages(
            self.r.cfg, self.query, self.r.session, self.r.memory)["messages"])

    def test_new_conflicting_correction_after_admission_rejected(self):
        d = self.admission()
        self.add(key="Project Elyra budgets", value="700 Euro")
        with self.assertRaisesRegex(ValueError, "authorization changed"):
            self.render(d)
        packet = verified_recall_messages(self.r.cfg, self.query, self.r.session, self.r.memory)
        self.assertEqual(packet["decision"]["reason"], "CONFLICTING_AUTHORIZED_SOURCES")
        self.assertIsNone(packet["messages"])

    def test_second_recall_failure_abstains_in_verified_wrapper(self):
        original = self.r.memory.recall
        seen = [0]
        def first_only(*args, **kwargs):
            seen[0] += 1
            return original(*args, **kwargs) if seen[0] == 1 else []
        with patch.object(self.r.memory, "recall", side_effect=first_only):
            packet = verified_recall_messages(self.r.cfg, self.query, self.r.session, self.r.memory)
        self.assertGreaterEqual(seen[0], 2)
        self.assertEqual(packet["decision"]["status"], "CLARIFY")
        self.assertEqual(packet["decision"]["reason"], "SOURCE_REVALIDATION_FAILED")
        self.assertIsNone(packet["messages"])

    def test_both_live_arguments_required_and_forged_dict_still_refused(self):
        d = self.admission()
        for kwargs in ({"memory": self.r.memory}, {"session": self.r.session}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, "required together"):
                    render_messages(self.r.cfg, self.query, d, **kwargs)
        forged = dict(d, source=dict(d["source"], value="999 Euro"))
        with self.assertRaisesRegex(ValueError, "Authenticated"):
            self.render(forged)


if __name__ == "__main__":
    unittest.main()
