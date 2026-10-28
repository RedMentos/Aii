"""Run87 real Age0 emergency-stop backup/restore persistence; Linux software only."""
import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13 import age as agectl
from v13 import prohibitions as P
from v13.backup import restore
from v13.operator import Operator
from v13.runtime import Runtime


class TestRun87StandstillBackupRecovery(unittest.TestCase):
    def _open(self, home):
        r = Runtime(home)
        r.sleep.cycle.set_policy("enabled", "off")
        return r, Operator(r)

    def _source(self, r, op):
        with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            d = json.loads(op.run(":verified What is the budget for Project Elyra?"))
        self.assertEqual(d["status"], "READY")
        self.assertEqual(d["native_calls"], 0)
        self.assertFalse(d["model_called"])
        self.assertNotIn("answer", d)
        return d["memory_id"]

    def _paused_source_refused(self, r, op):
        with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            with self.assertRaisesRegex(ValueError, "RUNTIME_NOT_IDLE"):
                op.run(":verified What is the budget for Project Elyra?")

    def _halted(self, r, op):
        s = json.loads(op.run(":stillstand json"))
        self.assertTrue(s["on"])
        self.assertTrue(s["all_parts_on"])
        self.assertTrue(r.paused)
        self.assertTrue(r.store.queue_paused())
        self.assertTrue(P.report(r.store)["notaus"])
        self.assertTrue(agectl.controller(r).view()["frozen"])
        self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
        return s

    def test_offline_restore_does_not_disarm_emergency_stop(self):
        with tempfile.TemporaryDirectory(prefix="v13-run87-stop-backup-") as td:
            home = Path(td)
            r, op = self._open(home)
            try:
                e = r.store.event(r.session, "Project Elyra budget")
                mid = r.memory.feedback(e["event_id"], "fact", "615 Euro",
                                        key="Project Elyra budget", permission="record")
                self.assertEqual(self._source(r, op), mid)
                self.assertIn("STILLSTAND AN", op.run(":stillstand"))
                self.assertTrue(self._halted(r, op)["confirmed_still"])
                self._paused_source_refused(r, op)
                archive = Path(op.run(":backup"))
                self.assertTrue(archive.is_file())
                self.assertEqual(archive.parent, home / "backups")
                original_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
                with tarfile.open(archive, "r:gz") as tar:
                    members = set(tar.getnames())
                    self.assertIn("backup_manifest.json", members)
                    manifest = json.load(tar.extractfile("backup_manifest.json"))
                    self.assertEqual(manifest["format"], 1)
                    self.assertFalse(manifest["models_included"])
                    self.assertEqual(set(manifest["hashes"]), members - {"backup_manifest.json"})
                    for name, expected in manifest["hashes"].items():
                        self.assertEqual(hashlib.sha256(tar.extractfile(name).read()).hexdigest(),
                                         expected)
            finally:
                r.close()

            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), original_sha)
            safety = restore(home, archive)
            self.assertTrue(Path(safety).is_file())
            self.assertNotEqual(Path(safety), archive)

            r, op = self._open(home)
            try:
                self._halted(r, op)
                self._paused_source_refused(r, op)
                self.assertIn("aufgehoben", op.run(":stillstand aus"))
                self.assertFalse(json.loads(op.run(":stillstand json"))["on"])
                self.assertFalse(r.paused)
                self.assertFalse(P.report(r.store)["notaus"])
                self.assertFalse(agectl.controller(r).view()["frozen"])
                self.assertEqual(self._source(r, op), mid)
            finally:
                r.close()

            r, op = self._open(home)
            try:
                self.assertFalse(json.loads(op.run(":stillstand json"))["on"])
                self.assertEqual(self._source(r, op), mid)
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
