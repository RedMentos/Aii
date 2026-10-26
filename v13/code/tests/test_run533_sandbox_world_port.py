"""Run533 real temp-file and F3/F4 SelfSystem integration tests; no model."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from v13.agi.file_world_port import SandboxWorldPort
from v13.selfmodel import SelfSystem, attribute
from v13.runtime import Runtime


class SandboxWorldPortTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "tool_sandbox"
        self.root.mkdir()

    def test_baseline_external_process_and_no_content(self):
        port = SandboxWorldPort(self.root)
        self.assertEqual(port.poll(), [])
        subprocess.run([sys.executable, "-c",
                        "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('foreign-secret')",
                        str(self.root / "note.txt")], check=True)
        rows = port.poll()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["channel"], "file:note")
        self.assertEqual(rows[0]["value"], hashlib.sha256(b"foreign-secret").hexdigest())
        self.assertEqual(rows[1]["value"], 1)
        self.assertNotIn("foreign-secret", json.dumps(rows))
        self.assertEqual(attribute([], rows[0])["class"], "EXTERNAL")
        self.assertEqual(port.poll(), [])
        self.assertEqual(SandboxWorldPort(self.root).poll(), [])

    def test_explicit_selfsystem_corollary_packet_and_external_overwrite(self):
        home = Path(self.temp.name) / "home"
        runtime = Runtime(home)
        self.addCleanup(runtime.close)
        ev = runtime.store.event(runtime.session, "operator-authorized sandbox test")["event_id"]
        system = SelfSystem(runtime)
        port = SandboxWorldPort(self.root)
        expected = hashlib.sha256(b"own-write").hexdigest()
        system.issue(ev, "own1", "approved-like test write",
                     [{"channel": "file:note", "value": expected}], window_s=20)
        (self.root / "note.txt").write_bytes(b"own-write")
        own = port.observe(system, ev)
        self.assertEqual(own[0]["class"], "SELF")
        self.assertEqual(own[0]["action_ids"], ["own1"])
        self.assertEqual(own[1]["class"], "EXTERNAL")  # unpredicted listing change
        self.assertEqual(port.observe(system, ev), [])
        subprocess.run([sys.executable, "-c",
                        "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('external-overwrite')",
                        str(self.root / "note.txt")], check=True)
        changed = port.observe(system, ev)
        self.assertEqual(len(changed), 1)
        self.assertNotEqual(changed[0]["class"], "SELF")
        counts = system.report()["attribution_counts"]
        self.assertGreaterEqual(counts["SELF"], 1)
        self.assertGreaterEqual(counts["EXTERNAL"] + counts["MIXED"], 1)
        packets = runtime.store.one("SELECT count(*) AS n FROM packets WHERE kind='SelfWorldAttribution'")["n"]
        self.assertGreaterEqual(packets, 3)
        self.assertEqual(runtime.cfg["learning_mode"], "RECORD_ONLY")

    def test_create_delete_directory_and_listing(self):
        port = SandboxWorldPort(self.root)
        (self.root / "a.txt").write_bytes(b"a")
        self.assertEqual([r["channel"] for r in port.poll()], ["file:a", "listing"])
        (self.root / "b.txt").mkdir()
        rows = port.poll()
        self.assertEqual([(r["channel"], r["value"]) for r in rows], [("file:b", "DIR")])
        (self.root / "a.txt").unlink()
        rows = port.poll()
        self.assertEqual([(r["channel"], r["value"]) for r in rows],
                         [("file:a", None), ("listing", 0)])

    def test_symlink_refusal_preserves_baseline(self):
        outside = Path(self.temp.name) / "private.txt"
        outside.write_text("do not read")
        port = SandboxWorldPort(self.root)
        (self.root / "escape.txt").symlink_to(outside)
        with self.assertRaises(ValueError):
            port.poll()
        (self.root / "escape.txt").unlink()
        (self.root / "safe.txt").write_text("okay")
        self.assertEqual([r["channel"] for r in port.poll()], ["file:safe", "listing"])

    def test_root_swap_refused_and_restorable(self):
        port = SandboxWorldPort(self.root)
        moved = Path(self.temp.name) / "moved"
        self.root.rename(moved)
        self.root.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(ValueError):
            port.poll()
        self.root.unlink()
        moved.rename(self.root)
        (self.root / "safe.txt").write_text("okay")
        self.assertEqual(port.poll()[0]["channel"], "file:safe")

    def test_oversize_and_count_fail_closed(self):
        port = SandboxWorldPort(self.root, max_files=1, max_bytes=4)
        (self.root / "a.txt").write_bytes(b"12345")
        with self.assertRaises(ValueError):
            port.poll()
        (self.root / "a.txt").write_bytes(b"1234")
        self.assertEqual(port.poll()[0]["channel"], "file:a")
        (self.root / "b.txt").write_bytes(b"x")
        with self.assertRaises(ValueError):
            port.poll()
        (self.root / "b.txt").unlink()
        (self.root / "a.txt").write_bytes(b"4321")
        self.assertEqual(len(port.poll()), 1)

    def test_bad_name_and_special_file_rejected(self):
        port = SandboxWorldPort(self.root)
        (self.root / "bad name.txt").write_text("x")
        with self.assertRaises(ValueError):
            port.poll()
        (self.root / "bad name.txt").unlink()
        if hasattr(os, "mkfifo"):
            os.mkfifo(self.root / "pipe.txt")
            with self.assertRaises(ValueError):
                port.poll()
            (self.root / "pipe.txt").unlink()
        self.assertEqual(port.poll(), [])

    def test_bad_root_limits_and_timestamp(self):
        with self.assertRaises(ValueError):
            SandboxWorldPort(Path(self.temp.name))
        with self.assertRaises(ValueError):
            SandboxWorldPort(self.root, max_files=True)
        with self.assertRaises(ValueError):
            SandboxWorldPort(self.root, max_bytes=65537)
        port = SandboxWorldPort(self.root)
        for t in (float("nan"), float("inf"), True, "1"):
            with self.assertRaises(ValueError):
                port.poll(t=t)

    def test_no_background_side_effect(self):
        port = SandboxWorldPort(self.root)
        (self.root / "note.txt").write_text("new")
        self.assertEqual(port._previous, ({}, 0))
        self.assertEqual(len(port.poll()), 2)
        self.assertEqual(port._previous[1], 1)


if __name__ == "__main__":
    unittest.main()
