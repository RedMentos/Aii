"""Operator :help must disclose Context OS exact-source audit without authority changes."""
import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import context_os as C


class ContextSourceHelp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_help_exposes_read_only_current_chat_source_command(self):
        help_text = self.op.run(":help")
        self.assertIn(":ctxos source <Event-ID>", help_text)
        self.assertIn("nur aktueller Chat", help_text)
        self.assertIn("nur lesen", help_text)

    def test_help_and_exact_source_command_do_not_change_context_mode(self):
        original = "Wörtlich: Äpfel, 123.45 EUR; `x=7` 😀\n"
        event = self.r.store.event(self.r.session, original)
        context = C.ContextOS(self.r.store, self.r.cfg)
        before = context.report()["mode"]
        self.assertEqual(before, "SHADOW")
        self.op.run(":help")
        restored = json.loads(self.op.run(":ctxos source " + event["event_id"]))
        self.assertEqual(restored["text"], original)
        self.assertEqual(restored["authority"], "SOURCE_EXACT_READ_ONLY")
        self.assertFalse(restored["context_applied"])
        self.assertEqual(context.report()["mode"], before)


if __name__ == "__main__":
    unittest.main()
