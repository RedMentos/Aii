"""Run88 real Age0 human-rule approval rollback across offline backup/restore."""
import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.backup import restore
from v13.operator import Operator
from v13.output_policy import match
from v13.runtime import Runtime


class TestRun88RuleAuthorityRestore(unittest.TestCase):
    def _open(self, home):
        r = Runtime(home)
        r.sleep.cycle.set_policy("enabled", "off")
        return r, Operator(r)

    def _request(self, op, cmd):
        reply = op.run(cmd)
        self.assertIn("; :requests", reply)
        return reply.split(";", 1)[0]

    def _not_active(self, r, op, before, version, query):
        self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
        self.assertEqual(json.loads(op.run(":rules")), before)
        self.assertEqual(r.store.generation()["rule_version"], version)
        self.assertIsNone(match(r.store, query))

    def test_preapproval_snapshot_restore_revokes_rule_until_new_explicit_approval(self):
        with tempfile.TemporaryDirectory(prefix="v13-run88-rule-rollback-") as td:
            home = Path(td)
            query = "What is two plus two?"
            r, op = self._open(home)
            try:
                before = json.loads(op.run(":rules"))
                version = r.store.generation()["rule_version"]
                self._not_active(r, op, before, version, query)
                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    rid = self._request(op, ':rules fixed "What is two plus two?" "4"')
                    self.assertEqual(r.store.one(
                        "SELECT status FROM requests WHERE id=?", (rid,))["status"], "PENDING")
                    self._not_active(r, op, before, version, query)
                    snapshot = Path(op.run(":backup"))
                    self.assertTrue(snapshot.is_file())
                    self.assertEqual(snapshot.parent, home / "backups")
                    snapshot_sha = hashlib.sha256(snapshot.read_bytes()).hexdigest()
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
                    op.run(":approve " + rid)
                    self.assertNotEqual(r.store.generation()["rule_version"], version)
                    answer = match(r.store, query)
                    self.assertEqual(answer["answer"], "4")
                    self.assertFalse(answer["model_generated"])
                    self.assertEqual(answer["output_authority"], "APPROVED_FIXED_RULE")
                    self.assertIsNone(match(r.store, "What is two plus two"))
            finally:
                r.close()

            self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), snapshot_sha)
            safety = restore(home, snapshot)
            self.assertTrue(Path(safety).is_file())
            self.assertNotEqual(Path(safety), snapshot)

            r, op = self._open(home)
            try:
                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    self._not_active(r, op, before, version, query)
                    self.assertEqual(r.store.one(
                        "SELECT status FROM requests WHERE id=?", (rid,))["status"], "PENDING")
                    op.run(":approve " + rid)
                    self.assertEqual(match(r.store, query)["answer"], "4")
                    self.assertIsNone(match(r.store, "What is two plus two"))
            finally:
                r.close()

            r, op = self._open(home)
            try:
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
                answer = match(r.store, query)
                self.assertEqual(answer["answer"], "4")
                self.assertEqual(answer["output_authority"], "APPROVED_FIXED_RULE")
                self.assertIsNone(match(r.store, "What is two plus two"))
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
