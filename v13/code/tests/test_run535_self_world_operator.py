"""Run535 local manual Self/World operator integration; no model or tool action."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from v13.operator import Operator
from v13.runtime import Runtime
from v13.selfmodel import SelfSystem


class SelfWorldOperatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.r = Runtime(self.home)
        self.addCleanup(self.r.close)
        self.op = Operator(self.r)
        self.root = self.home / "data" / "tool_sandbox"

    def start(self):
        self.root.mkdir(parents=True, exist_ok=True)
        return json.loads(self.op.run(":self world start"))

    def test_off_no_directory_does_not_create_and_help(self):
        status = json.loads(self.op.run(":self world status"))
        self.assertFalse(status["active"])
        self.assertFalse(status["sandbox_ready"])
        self.assertIn("world status|start|poll|stop", self.op.run(":help"))
        with self.assertRaises(ValueError):
            self.op.run(":self world start")
        self.assertFalse(self.root.exists())

    def test_external_subprocess_poll_readonly_no_content(self):
        self.assertEqual(self.start()["status"], "BASELINED")
        self.assertEqual(json.loads(self.op.run(":self world poll"))["total"], 0)
        before = self.r.store.one("SELECT count(*) AS n FROM packets")["n"]
        subprocess.run([sys.executable, "-c",
                        "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('private-local-text')",
                        str(self.root / "n.txt")], check=True)
        data = json.loads(self.op.run(":self world poll"))
        after = self.r.store.one("SELECT count(*) AS n FROM packets")["n"]
        self.assertEqual(before, after)
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["recent"][0]["class"], "EXTERNAL")
        self.assertEqual(data["packets_written"], 0)
        self.assertNotIn("private-local-text", json.dumps(data))
        self.assertFalse(data["learning_authorized"])
        self.assertFalse(data["tool_authorized"])

    def test_matching_existing_corollary_is_self_without_new_packets(self):
        self.start()
        system = SelfSystem(self.r)
        event = self.r.store.event(self.r.session, "local self/world diagnostic")["event_id"]
        expected = hashlib.sha256(b"known-own").hexdigest()
        system.issue(event, "own-action", "approved-like local write",
                     [{"channel": "file:n", "value": expected}], window_s=30)
        before = self.r.store.one("SELECT count(*) AS n FROM packets")["n"]
        (self.root / "n.txt").write_bytes(b"known-own")
        data = json.loads(self.op.run(":self world poll"))
        self.assertEqual(data["recent"][0]["class"], "SELF")
        self.assertEqual(data["recent"][0]["action_ids"], ["own-action"])
        self.assertEqual(self.r.store.one("SELECT count(*) AS n FROM packets")["n"], before)

    def test_last_eight_bounded_and_stop(self):
        self.start()
        for n in range(12):
            (self.root / ("f%02d.txt" % n)).write_text(str(n))
        data = json.loads(self.op.run(":self world poll"))
        self.assertEqual(data["total"], 13)
        self.assertEqual(len(data["recent"]), 8)
        self.assertFalse(json.loads(self.op.run(":self world stop"))["active"])
        with self.assertRaises(ValueError):
            self.op.run(":self world poll")
        self.assertFalse(json.loads(self.op.run(":self world status"))["active"])

    def test_multiple_operator_instances_share_explicit_runtime_port(self):
        self.start()
        another = Operator(self.r)
        (self.root / "a.txt").write_text("x")
        self.assertEqual(json.loads(another.run(":self world poll"))["total"], 2)
        self.assertEqual(json.loads(self.op.run(":self world poll"))["total"], 0)

    def test_symlink_root_rejected(self):
        outside = Path(self.tmp.name) / "other"
        outside.mkdir()
        self.root.parent.mkdir(parents=True, exist_ok=True)
        self.root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.op.run(":self world start")
        self.assertFalse(json.loads(self.op.run(":self world status"))["sandbox_ready"])

    def test_local_only_and_other_self_views_unchanged(self):
        self.start()
        with self.assertRaisesRegex(ValueError, "Nur lokale Operator"):
            self.op.run(":self world poll", origin="API")
        self.assertIn("mode", json.loads(self.op.run(":self correction")))
        self.assertEqual(json.loads(self.op.run(":self arithmetic"))["status"], "SHADOW_ONLY")

    def test_corrupt_self_state_cannot_consume_scan_baseline(self):
        from v13.selfmodel import KEY, empty
        self.start()
        (self.root / "new.txt").write_text("visible after recovery")
        self.r.store.set_state(KEY, {"revision": "broken"})
        with self.assertRaisesRegex(ValueError, "revision mismatch"):
            self.op.run(":self world poll")
        self.r.store.set_state(KEY, empty())
        data = json.loads(self.op.run(":self world poll"))
        self.assertEqual(data["total"], 2)

    def test_restart_defaults_off_without_replay(self):
        self.start()
        self.r.close()
        r2 = Runtime(self.home)
        self.addCleanup(r2.close)
        op2 = Operator(r2)
        self.assertFalse(json.loads(op2.run(":self world status"))["active"])
        self.assertEqual(json.loads(op2.run(":self world start"))["status"], "BASELINED")
        self.assertEqual(json.loads(op2.run(":self world poll"))["total"], 0)


if __name__ == "__main__":
    unittest.main()
