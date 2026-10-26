"""Run542 real sandbox F3/F4 observation retry integrity (Linux software only)."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from v13.agi.approved_sandbox_world import ApprovedSandboxWorldSession
from v13.agi.file_world_port import SandboxWorldPort
from v13.runtime import Runtime
from v13.selfmodel import KEY


class SelfWorldRetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.r = Runtime(Path(self.tmp.name) / "home")
        self.addCleanup(self.r.close)
        self.root = self.r.store.home / "data" / "tool_sandbox"
        self.root.mkdir(parents=True, exist_ok=True)

    def test_corrupt_self_state_does_not_lose_real_approved_file_observation(self):
        event = self.r.store.event(self.r.session, "approved retry test")["event_id"]
        session = ApprovedSandboxWorldSession(self.r, event)
        session.registry.enable("sandbox_note")
        tx = session.propose("note", "actual bytes")
        done = session.registry.approve(tx["id"])
        self.assertEqual(done["status"], "EXECUTED")
        self.assertEqual((self.root / "note.txt").read_bytes(), b"actual bytes")
        original, _ = session.selfsys._load()
        self.r.store.set_state(KEY, {"revision": "invalid"})
        with self.assertRaisesRegex(ValueError, "revision mismatch"):
            session.collect(done)
        self.assertEqual(
            self.r.store.one("SELECT count(*) AS n FROM packets WHERE kind='SelfWorldAttribution'")["n"], 0)
        self.r.store.set_state(KEY, original)
        report = session.collect(done)
        rows = {o["channel"]: o for o in report["observations"]}
        self.assertEqual(rows["file:note"]["class"], "SELF")
        self.assertEqual(rows["status:note"]["class"], "SELF")
        self.assertEqual(rows["file:note"]["action_ids"], [done["action_tx"]])
        self.assertEqual(rows["status:note"]["action_ids"], [done["action_tx"]])
        self.assertEqual(len(rows), 3)  # file, listing, action status
        self.assertFalse(report["learning_authorized"])
        self.assertFalse(report["age_reopen_authorized"])
        with self.assertRaisesRegex(ValueError, "already collected"):
            session.collect(done)

    def test_observer_exception_retains_pending_file_scan_until_success(self):
        port = SandboxWorldPort(self.root)
        (self.root / "a.txt").write_bytes(b"real")
        class Flaky:
            def __init__(self):
                self.calls = 0
            def observe(self, event, rows, close):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("synthetic pre-write observer failure")
                return [{"channel": row["channel"], "class": "EXTERNAL",
                         "reason": "test", "action_ids": []} for row in rows]
        observer = Flaky()
        with self.assertRaisesRegex(RuntimeError, "pre-write"):
            port.observe(observer, "event", t=123.0)
        rows = port.observe(observer, "event", t=124.0)
        self.assertEqual([r["channel"] for r in rows], ["file:a", "listing"])
        self.assertEqual(port.observe(observer, "event", t=125.0), [])
        self.assertEqual(observer.calls, 2)

    def test_failed_preaction_hook_does_not_borrow_old_corollary(self):
        event = self.r.store.event(self.r.session, "no hook")["event_id"]
        session = ApprovedSandboxWorldSession(self.r, event)
        session.registry.enable("sandbox_note")
        session.selfsys.issue(
            event, "unrelated", "unrelated",
            [{"channel": "file:note", "value": hashlib.sha256(b"same").hexdigest()}])
        def reject(_tx):
            raise RuntimeError("test hook")
        session.registry.on_pre_execute = reject
        tx = session.propose("note", "same")
        report = session.approve(tx["id"], origin="OPERATOR_TTY")
        self.assertEqual(report["status"], "EXECUTED")
        self.assertFalse(report["corollary_issued"])
        file_obs = next(o for o in report["observations"] if o["channel"] == "file:note")
        self.assertEqual((file_obs["class"], file_obs["reason"], file_obs["action_ids"]),
                         ("UNCLEAR", "no_current_corollary", []))
        self.assertEqual(
            self.r.store.one("SELECT count(*) AS n FROM packets WHERE kind='SelfWorldAttribution'")["n"], 0)


if __name__ == "__main__":
    unittest.main()
