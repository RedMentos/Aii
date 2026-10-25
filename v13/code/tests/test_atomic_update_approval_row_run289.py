"""Run289: a preflighted update row must still be identical at SQLite commit.

These are actual SQLite Store transactions with synthetic artifacts. No native
weights, Redmi execution, STEP2/B3 success, or learned utility is claimed.
"""
import json
from pathlib import Path
import tempfile
import unittest

from v13.common import atomic_write, dumps, file_hash, now, uid
from v13.config import initialize
from v13.store import Store


class AtomicUpdateApprovalRowRun289(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.s = Store(self.home)
        self.models = {"C2_CONTROL": "encoder"}
        self.s.ensure_generation_snapshot(self.cfg, self.models)

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def candidate(self):
        source = self.s.source("run289 authorized human training input")
        update = uid("upd")
        path = "checkpoints/head-" + update + ".npz"
        atomic_write(self.home / path, b"RUN289_SYNTHETIC_CANDIDATE")
        manifest = {
            "component": "route", "encoder_revision": "encoder",
            "commit_eligible": True, "source_ids": [source["source_id"]],
        }
        with self.s.tx() as c:
            c.execute("INSERT INTO updates VALUES (?,?,?,?,?,?,?)",
                      (update, self.s.generation_id, "PENDING_APPROVAL", path,
                       file_hash(self.home / path), dumps(manifest), now()))
        return update, manifest

    def mutate_after_preflight(self, update, change):
        """Deterministically emulate a second writer between preflight and BEGIN."""
        before = self.s.generation_id
        original = self.s.validate_artifacts
        invoked = []
        def intercept(artifacts):
            original(artifacts)
            self.s.validate_artifacts = original
            invoked.append(True)
            with self.s.tx() as c:
                change(c)
        self.s.validate_artifacts = intercept
        try:
            with self.assertRaisesRegex(ValueError, "Update.*(geändert|veraltet|freigabefähig)"):
                self.s.switch_generation(update, self.cfg, self.models)
        finally:
            self.s.validate_artifacts = original
        self.assertEqual(invoked, [True])
        self.assertEqual(self.s.generation_id, before)
        self.assertEqual(self.s.generation()["hashes"], {})
        self.assertEqual(self.s.integrity(True), [])

    def test_status_revoked_after_preflight_cannot_be_committed(self):
        update, _ = self.candidate()
        self.mutate_after_preflight(
            update, lambda c: c.execute(
                "UPDATE updates SET status='ABORTED' WHERE id=?", (update,)))
        self.assertEqual(self.s.one("SELECT status FROM updates WHERE id=?", (update,))["status"], "ABORTED")

    def test_manifest_retention_gate_changed_after_preflight_cannot_commit(self):
        update, manifest = self.candidate()
        manifest["commit_eligible"] = False
        self.mutate_after_preflight(
            update, lambda c: c.execute(
                "UPDATE updates SET manifest=? WHERE id=?", (dumps(manifest), update)))
        self.assertEqual(json.loads(self.s.one(
            "SELECT manifest FROM updates WHERE id=?", (update,))["manifest"])["commit_eligible"], False)

    def test_artifact_pointer_changed_after_preflight_cannot_commit(self):
        update, _ = self.candidate()
        new_path = "checkpoints/head-" + uid("upd") + ".npz"
        atomic_write(self.home / new_path, b"RUN289_DIFFERENT_CANDIDATE")
        new_hash = file_hash(self.home / new_path)
        self.mutate_after_preflight(
            update, lambda c: c.execute(
                "UPDATE updates SET path=?,hash=? WHERE id=?", (new_path, new_hash, update)))

    def test_source_lineage_changed_after_preflight_cannot_commit(self):
        update, manifest = self.candidate()
        revoked = self.s.source("run289 forgotten source")
        with self.s.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?", (revoked["source_id"],))
        manifest["source_ids"] = [revoked["source_id"]]
        self.mutate_after_preflight(
            update, lambda c: c.execute(
                "UPDATE updates SET manifest=? WHERE id=?", (dumps(manifest), update)))

    def test_unchanged_update_still_commits_and_rolls_back(self):
        update, _ = self.candidate()
        before = self.s.generation_id
        committed = self.s.switch_generation(update, self.cfg, self.models)
        self.assertNotEqual(committed, before)
        self.assertEqual(self.s.one(
            "SELECT status FROM updates WHERE id=?", (update,))["status"], "COMMITTED")
        self.s.rollback(update)
        self.assertEqual(self.s.generation()["hashes"], {})
        self.assertEqual(self.s.integrity(True), [])


if __name__ == "__main__":
    unittest.main()
