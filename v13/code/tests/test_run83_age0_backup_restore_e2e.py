"""Run83 real Age0 backup/restore and source recall across process lifecycles."""
import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.backup import restore
from v13.operator import Operator
from v13.runtime import Runtime


class TestRun83Age0BackupRestore(unittest.TestCase):
    def _open(self, home):
        r = Runtime(home)
        r.sleep.cycle.set_policy("enabled", "off")
        return r, Operator(r)

    def _verified(self, r, op, project):
        with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            result = json.loads(op.run(":verified What is the budget for Project " + project + "?"))
        self.assertEqual(result["native_calls"], 0)
        self.assertFalse(result["model_called"])
        return result

    def _add(self, r, project, value):
        key = "Project " + project + " budget"
        e = r.store.event(r.session, key)
        return r.memory.feedback(e["event_id"], "fact", value,
                                 key=key, permission="record")

    def test_backup_invalid_restore_refusal_and_confirmed_offline_restore(self):
        with tempfile.TemporaryDirectory(prefix="v13-run83-backup-") as td:
            home = Path(td)
            r, op = self._open(home)
            try:
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
                mid = self._add(r, "Elyra", "615 Euro")
                self.assertEqual(self._verified(r, op, "Elyra")["memory_id"], mid)
                snapshot = Path(op.run(":backup"))
                self.assertTrue(snapshot.is_file())
                self.assertEqual(snapshot.parent, home / "backups")
                archive_sha = hashlib.sha256(snapshot.read_bytes()).hexdigest()
                with tarfile.open(snapshot, "r:gz") as tar:
                    names = set(tar.getnames())
                    self.assertIn("backup_manifest.json", names)
                    manifest = json.load(tar.extractfile("backup_manifest.json"))
                    self.assertEqual(manifest["format"], 1)
                    self.assertFalse(manifest["models_included"])
                    self.assertEqual(set(manifest["hashes"]), names - {"backup_manifest.json"})
                    for name, expected in manifest["hashes"].items():
                        self.assertEqual(hashlib.sha256(tar.extractfile(name).read()).hexdigest(),
                                         expected)
                self._add(r, "Dovan", "700 Euro")
                self.assertEqual(self._verified(r, op, "Dovan")["status"], "READY")
            finally:
                r.close()

            invalid = home / "invalid-restore.tar.gz"
            invalid.write_bytes(b"not a valid tar archive")
            with self.assertRaises((tarfile.ReadError, ValueError)):
                restore(home, invalid)
            r, op = self._open(home)
            try:
                self.assertEqual(self._verified(r, op, "Dovan")["status"], "READY")
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
            finally:
                r.close()

            self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), archive_sha)
            safety = restore(home, snapshot)
            self.assertTrue(Path(safety).is_file())
            self.assertNotEqual(Path(safety), snapshot)
            r, op = self._open(home)
            try:
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
                self.assertEqual(self._verified(r, op, "Elyra")["memory_id"], mid)
                self.assertEqual(self._verified(r, op, "Dovan")["status"], "CLARIFY")
            finally:
                r.close()

            r, op = self._open(home)
            try:
                self.assertEqual(self._verified(r, op, "Elyra")["status"], "READY")
                self.assertEqual(self._verified(r, op, "Dovan")["status"], "CLARIFY")
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
