"""Run365: organ checkpoint user strings cannot escape the snapshot namespace.

Actual Runtime/Store SQLite; no models or network. These tests were committed
before the production fix to preserve the expected RED counterexamples.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import organ as O
from v13.common import digest, dumps


class OrganPathSafetyRun365(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_role_traversal_refused_before_external_directory_creation(self):
        outside = self.root / "escaped"
        with self.assertRaises(ValueError):
            O.snapshot(self.r, "../../escaped")
        self.assertFalse(outside.exists())
        with self.assertRaises(ValueError):
            O.members(self.r, "../B1_DETAIL")
        with self.assertRaises(ValueError):
            O.snapshot(self.r, "NOT_A_MODEL_ROLE")

    def test_snapshot_id_wildcard_and_parent_segments_refused(self):
        legitimate = O.snapshot(self.r, "B1_DETAIL")
        self.assertEqual(O.check(self.r, legitimate["id"])["role"], "B1_DETAIL")
        for invalid in ("*", "../B1_DETAIL", "organ_" + "a" * 31 + "*"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    O.check(self.r, invalid)

    def test_hash_consistent_manifest_cannot_change_its_own_identity(self):
        legitimate = O.snapshot(self.r, "B1_DETAIL")
        manifest = self.home / "organs" / "B1_DETAIL" / legitimate["id"] / "manifest.json"
        data = json.loads(manifest.read_text())
        data["role"] = "C2_CONTROL"
        data["hash"] = digest(dumps({k: v for k, v in data.items() if k != "hash"}))
        manifest.write_text(dumps(data))
        with self.assertRaises((ValueError, RuntimeError)):
            O.check(self.r, legitimate["id"])

    def test_symlinked_organ_root_must_not_write_outside_runtime_home(self):
        outside = self.root / "external"
        outside.mkdir()
        organ_root = self.home / "organs"
        self.assertFalse(organ_root.exists(), "test requires an unused organ root")
        organ_root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            O.snapshot(self.r, "B1_DETAIL")
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
