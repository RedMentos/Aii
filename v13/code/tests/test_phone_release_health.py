"""Offline installed-runtime health tests; no model or database contents read."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from v13 import phone_release_health as h
from v13 import runtime_deploy as d


class PhoneHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "v13"
        self.private = self.root / "private"
        self.builds = self.root / "builds"
        self.private.mkdir()
        self.builds.mkdir()
        (self.home / "bin").mkdir(parents=True)
        self.launcher = self.home / "bin/v13"
        self.launcher.write_bytes(b"#!/bin/sh\necho safe\n")
        self.code = self.builds / "v13-deadbeef" / "code"
        for rel in d.REQUIRED:
            p = self.code / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("fixture")
        self.marker = self.private / d.MARKER_NAME
        self.marker.write_text(json.dumps({
            "code": str(self.code),
            "launcher_sha256": hashlib.sha256(self.launcher.read_bytes()).hexdigest()
        }))
        self.marker.chmod(0o600)

    def check(self):
        return h.inspect(home=self.home, private=self.private, builds=self.builds)

    def test_complete_installed_snapshot(self):
        self.assertEqual(self.check()["status"], "READY")
        self.assertFalse(self.check()["database_contents_read"])

    def test_corrupt_launcher_and_deleted_module(self):
        self.launcher.write_bytes(b"tampered")
        self.assertEqual(self.check()["launcher"], "MISMATCH")
        self.launcher.write_bytes(b"#!/bin/sh\necho safe\n")
        (self.code / "v13/runtime.py").unlink()
        self.assertEqual(self.check()["snapshot"], "INCOMPLETE")

    def test_marker_cannot_redirect_to_outside_builds(self):
        other = self.root / "outside" / "v13-fake" / "code"
        for rel in d.REQUIRED:
            p = other / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("fixture")
        marker = json.loads(self.marker.read_text())
        marker["code"] = str(other)
        self.marker.write_text(json.dumps(marker))
        self.assertEqual(self.check()["status"], "INVALID")

    def test_symlink_and_world_readable_marker_fail_closed(self):
        self.marker.chmod(0o644)
        self.assertEqual(self.check()["marker"], "UNSAFE")
        self.marker.unlink()
        self.marker.symlink_to(self.code / d.REQUIRED[0])
        self.assertEqual(self.check()["status"], "NOT_INSTALLED")


if __name__ == "__main__":
    unittest.main()
