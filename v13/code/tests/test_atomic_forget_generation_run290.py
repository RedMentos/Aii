"""Run290: forgetting must not race with approval of a newly active weight.

Actual SQLite Store/Memory, synthetic candidate bytes. No native training,
unlearning algorithm, or Redmi proof is claimed.
"""
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest

from v13.common import atomic_write, dumps, file_hash, now, uid
from v13.config import initialize
from v13.memory import Memory
from v13.store import Store


class AtomicForgetGenerationRun290(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.s = Store(self.home)
        self.models = {"C2_CONTROL": "encoder"}
        self.s.ensure_generation_snapshot(self.cfg, self.models)
        self.mem = Memory(self.s, self.cfg)

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def candidate(self):
        source = self.s.source("run290 human reference", kind="HUMAN_OUTPUT_REFERENCE")
        update = uid("upd")
        rel = "checkpoints/head-" + update + ".npz"
        atomic_write(self.home / rel, b"RUN290_SYNTHETIC_HEAD")
        manifest = {"component": "route", "encoder_revision": "encoder",
                    "commit_eligible": True, "source_ids": [source["source_id"]]}
        with self.s.tx() as c:
            c.execute("INSERT INTO updates VALUES (?,?,?,?,?,?,?)",
                      (update, self.s.generation_id, "PENDING_APPROVAL", rel,
                       file_hash(self.home / rel), dumps(manifest), now()))
        return source["source_id"], update, rel

    def test_forget_first_blocks_later_candidate_commit(self):
        sid, update, rel = self.candidate()
        self.mem.forget_output_reference(sid)
        self.assertEqual(self.s.one("SELECT deleted FROM sources WHERE id=?", (sid,))["deleted"], 1)
        self.assertEqual(self.s.one("SELECT status FROM updates WHERE id=?", (update,))["status"], "QUARANTINED")
        with self.assertRaises(ValueError):
            self.s.switch_generation(update, self.cfg, self.models)
        self.assertEqual(self.s.generation()["hashes"], {})
        self.assertEqual(self.s.integrity(True), [])

    def test_committed_weight_blocks_forget_until_rollback(self):
        sid, update, rel = self.candidate()
        self.s.switch_generation(update, self.cfg, self.models)
        with self.assertRaisesRegex(ValueError, "rollback"):
            self.mem.forget_output_reference(sid)
        self.assertEqual(self.s.one("SELECT deleted FROM sources WHERE id=?", (sid,))["deleted"], 0)
        self.assertTrue((self.home / rel).is_file())
        self.assertEqual(self.s.integrity(True), [])

    def test_commit_between_forget_preflight_and_delete_is_refused(self):
        sid, update, rel = self.candidate()
        old = self.s.generation_id
        original_tx = self.s.tx
        commits = []

        @contextmanager
        def concurrent_commit_before_delete():
            # Deterministic second-writer interleaving after the forget
            # preflight but before its BEGIN IMMEDIATE write transaction.
            self.s.tx = original_tx
            commits.append(self.s.switch_generation(update, self.cfg, self.models))
            with original_tx() as c:
                yield c

        self.s.tx = concurrent_commit_before_delete
        try:
            with self.assertRaisesRegex(ValueError, "Generation.*geändert"):
                self.mem.forget_output_reference(sid)
        finally:
            self.s.tx = original_tx

        self.assertEqual(len(commits), 1)
        self.assertNotEqual(self.s.generation_id, old)
        self.assertEqual(self.s.one("SELECT deleted FROM sources WHERE id=?", (sid,))["deleted"], 0)
        self.assertEqual(self.s.one("SELECT status FROM updates WHERE id=?", (update,))["status"], "COMMITTED")
        self.assertTrue((self.home / rel).is_file())
        self.assertEqual(self.s.integrity(True), [])


if __name__ == "__main__":
    unittest.main()
