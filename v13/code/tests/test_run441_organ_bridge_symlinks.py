"""Run441 RED-first: organ checkpoint bridges must never follow external symlinks.

Model-free Runtime fixtures, no native weights and no real device claims.
"""
import tempfile
import unittest
from pathlib import Path

from tests.test_organ import Base
from v13 import organ as O


class Run441OrganBridgeSymlinkIntegrity(Base):
    def outside(self, data=b'{"outside":"keep"}'):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        p = Path(t.name) / "outside.json"
        p.write_bytes(data)
        self.assertFalse(p.is_relative_to(self.r.home))
        return p

    def test_snapshot_rejects_bridge_file_symlink(self):
        self.bridge("B1_TO_B2.json", '{"v":1}')
        link = self.r.home / "b3/B1_TO_B2.json"
        link.unlink()
        external = self.outside(b'{"v":1}')
        link.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "BRIDGE.*SYMLINK|SYMLINK.*BRIDGE"):
            O.snapshot(self.r, "B1_DETAIL")
        self.assertEqual(external.read_bytes(), b'{"v":1}')

    def test_snapshot_rejects_bridge_directory_symlink(self):
        d = self.r.home / "b3"
        d.mkdir(exist_ok=True)
        d.rmdir()
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        d.symlink_to(Path(t.name), target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "BRIDGE.*SYMLINK|SYMLINK.*BRIDGE"):
            O.snapshot(self.r, "B1_DETAIL")

    def test_restore_rejects_external_bridge_destination_before_generation(self):
        self.bridge("B1_TO_B2.json", '{"v":1}')
        snapshot = O.snapshot(self.r, "B1_DETAIL")
        self.bridge("B1_TO_B2.json", '{"v":2}')
        link = self.r.home / "b3/B1_TO_B2.json"
        link.unlink()
        external = self.outside()
        link.symlink_to(external)
        before = self.r.store.generation_id
        with self.assertRaisesRegex(ValueError, "BRIDGE.*SYMLINK|SYMLINK.*BRIDGE"):
            O.restore(self.r, snapshot["id"])
        self.assertEqual(external.read_bytes(), b'{"outside":"keep"}')
        self.assertEqual(self.r.store.generation_id, before)

    def test_backup_bridge_symlink_does_not_count_as_intact(self):
        self.bridge("B1_TO_B2.json", '{"v":1}')
        snapshot = O.snapshot(self.r, "B1_DETAIL")
        backup = self.r.home / "organs/B1_DETAIL" / snapshot["id"] / "files/B1_TO_B2.json"
        original = backup.read_bytes()
        backup.unlink()
        external = self.outside(original)
        backup.symlink_to(external)
        status = O.check(self.r, snapshot["id"])
        self.assertFalse(status["backup_intact"])
        self.assertFalse(status["restorable"])
        before = self.r.store.generation_id
        with self.assertRaisesRegex(RuntimeError, "beschädigt"):
            O.restore(self.r, snapshot["id"])
        self.assertEqual(self.r.store.generation_id, before)


if __name__ == "__main__":
    unittest.main()
