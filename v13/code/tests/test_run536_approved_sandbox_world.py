"""Run536 real WP-K approved sandbox_note -> F3/F4 Self/World integration."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from v13.agi.approved_sandbox_world import ApprovedSandboxWorldSession
from v13.runtime import Runtime


class ApprovedSandboxWorldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.r = Runtime(Path(self.temp.name) / "home")
        self.addCleanup(self.r.close)
        self.root = self.r.store.home / "data" / "tool_sandbox"
        self.root.mkdir(parents=True, exist_ok=True)
        self.event = self.r.store.event(self.r.session, "test operator-approved local note")["event_id"]
        self.session = ApprovedSandboxWorldSession(self.r, self.event)

    def enable(self):
        self.session.registry.enable("sandbox_note")

    def test_real_approval_creates_corollary_before_effect_and_observes_own(self):
        self.enable()
        tx = self.session.propose("note", "own real bytes")
        self.assertEqual(tx["status"], "PROPOSED")
        self.assertFalse((self.root / "note.txt").exists())
        self.assertEqual(self.r.store.one("SELECT count(*) AS n FROM packets WHERE kind='SelfCorollary'")["n"], 0)
        report = self.session.approve(tx["id"], origin="OPERATOR_TTY")
        self.assertEqual(report["status"], "EXECUTED")
        self.assertTrue(report["corollary_issued"])
        self.assertEqual((self.root / "note.txt").read_text(), "own real bytes")
        by_channel = {o["channel"]: o for o in report["observations"]}
        self.assertEqual(by_channel["file:note"]["class"], "SELF")
        self.assertEqual(by_channel["status:note"]["class"], "SELF")
        self.assertIn(by_channel["listing"]["class"], ("UNCLEAR", "EXTERNAL"))
        self.assertEqual(by_channel["file:note"]["action_ids"], [report["action_tx"]])
        self.assertEqual(self.r.store.one("SELECT count(*) AS n FROM packets WHERE kind='SelfCorollary'")["n"], 1)
        self.assertFalse(report["learning_authorized"])
        self.assertFalse(report["age_reopen_authorized"])
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")
        self.assertNotIn("own real bytes", json.dumps(report))

    def test_independent_world_overwrite_before_collect_is_not_self(self):
        self.enable()
        tx = self.session.propose("note", "own bytes")
        done = self.session.registry.approve(tx["id"])
        self.assertEqual(done["status"], "EXECUTED")
        subprocess.run([sys.executable, "-c",
                        "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('world bytes')",
                        str(self.root / "note.txt")], check=True)
        report = self.session.collect(done)
        file_obs = next(o for o in report["observations"] if o["channel"] == "file:note")
        self.assertNotEqual(file_obs["class"], "SELF")
        self.assertTrue(report["corollary_issued"])
        self.assertEqual((self.root / "note.txt").read_text(), "world bytes")

    def test_no_enable_or_no_approval_never_writes(self):
        tx = self.session.propose("note", "not authorized")
        self.assertNotEqual(tx["status"], "EXECUTED")
        self.assertFalse((self.root / "note.txt").exists())
        self.enable()
        tx2 = self.session.propose("note", "needs human")
        self.assertEqual(tx2["status"], "PROPOSED")
        with self.assertRaisesRegex(ValueError, "local operator"):
            self.session.approve(tx2["id"], origin="API")
        self.assertFalse((self.root / "note.txt").exists())

    def test_invalid_name_failed_action_gets_no_false_self_corollary(self):
        self.enable()
        tx = self.session.propose("../escape", "bad")
        self.assertEqual(tx["status"], "PROPOSED")
        report = self.session.approve(tx["id"], origin="OPERATOR_TTY")
        self.assertEqual(report["status"], "FAILED")
        self.assertFalse(report["corollary_issued"])
        self.assertEqual(report["observations"], [])
        self.assertFalse((Path(self.temp.name) / "escape.txt").exists())

    def test_real_failed_approved_write_is_mixed_not_false_self(self):
        self.enable()
        (self.root / "blocked.txt").mkdir()
        tx = self.session.propose("blocked", "will fail")
        self.assertEqual(tx["status"], "PROPOSED")
        report = self.session.approve(tx["id"], origin="OPERATOR_TTY")
        self.assertEqual(report["status"], "FAILED")
        self.assertTrue(report["corollary_issued"])
        status = next(o for o in report["observations"] if o["channel"] == "status:blocked")
        self.assertEqual(status["class"], "MIXED")
        self.assertNotIn("will fail", json.dumps(report))

    def test_failed_pre_effect_hook_cannot_borrow_unrelated_self_corollary(self):
        self.enable()
        digest = hashlib.sha256(b"own bytes").hexdigest()
        self.session.selfsys.issue(
            self.event, "unrelated-old", "old prediction",
            [{"channel": "file:note", "value": digest}], window_s=30)
        def fail_pre(_tx):
            raise RuntimeError("test-only pre-effect failure")
        self.session.registry.on_pre_execute = fail_pre
        tx = self.session.propose("note", "own bytes")
        report = self.session.approve(tx["id"], origin="OPERATOR_TTY")
        self.assertEqual(report["status"], "EXECUTED")
        self.assertFalse(report["corollary_issued"])
        file_obs = next(o for o in report["observations"] if o["channel"] == "file:note")
        self.assertEqual((file_obs["class"], file_obs["reason"], file_obs["action_ids"]),
                         ("UNCLEAR", "no_current_corollary", []))
        self.assertEqual(
            self.r.store.one("SELECT count(*) AS n FROM packets WHERE kind='SelfWorldAttribution'")["n"], 0)

    def test_duplicate_collect_and_forged_transaction_refused(self):
        self.enable()
        tx = self.session.propose("note", "hello")
        done = self.session.registry.approve(tx["id"])
        self.session.collect(done)
        with self.assertRaisesRegex(ValueError, "already collected"):
            self.session.collect(done)
        fake = dict(done, action_tx="forged")
        with self.assertRaisesRegex(ValueError, "unverified"):
            self.session.collect(fake)

    def test_wrong_event_and_wrong_tool_refused(self):
        self.enable()
        other = self.r.store.event(self.r.session, "another event")["event_id"]
        tx = self.session.registry.call("sandbox_note", {"name": "other", "text": "x"},
                                        origin="USER", event_id=other)
        done = self.session.registry.approve(tx["id"])
        with self.assertRaisesRegex(ValueError, "wrong event/tool"):
            self.session.collect(done)
        self.session.registry.enable("calc")
        calc = self.session.registry.call("calc", {"expression": "2+2"}, event_id=self.event)
        with self.assertRaisesRegex(ValueError, "wrong event/tool"):
            self.session.collect(calc)

    def test_requires_existing_real_sandbox_and_current_event(self):
        with self.assertRaises(ValueError):
            ApprovedSandboxWorldSession(self.r, "fake-event")
        self.root.rmdir()
        with self.assertRaises(ValueError):
            ApprovedSandboxWorldSession(self.r, self.event)


if __name__ == "__main__":
    unittest.main()
