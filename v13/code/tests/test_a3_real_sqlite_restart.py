"""Real SQLite source/restart/revocation regression for the opt-in A3 SHADOW bridge.

Host-only test. No Android hardware or teacher model is claimed.
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from v13.a3_online_projector import A3Projector
from v13.a3_store_source import observe_stored_features
from v13.store import Store


class TestA3RealSQLite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / "data" / "db").mkdir(parents=True)
        (self.home / "data" / "blobs").mkdir(parents=True)
        self.store = Store(self.home)
        self.runtime = SimpleNamespace(store=self.store)
        self.projector = A3Projector(2, 1)
        self.ref = self.store.source(
            json.dumps({"features": [0.25, 0.5], "final": True}),
            kind="SYNTHETIC_TEST",
        )

    def tearDown(self):
        if not self.store.closed:
            self.store.close()
        self.tmp.cleanup()

    def observe(self):
        return observe_stored_features(
            self.runtime, self.projector, self.ref, modality="synthetic_audio"
        )

    def test_real_store_then_restart(self):
        first = self.observe()
        self.assertEqual(first["a5"]["status"], "SHADOW_STORE_BACKED")
        self.assertFalse(first["jef"]["android_action_allowed"])
        self.store.close()
        self.store = Store(self.home)
        self.runtime.store = self.store
        second = self.observe()
        self.assertEqual(first["a5"]["embedding"], second["a5"]["embedding"])
        self.assertEqual(second["a5"]["store_source_sha256"], self.ref["sha256"])

    def test_revoke_after_restart(self):
        self.assertEqual(self.observe()["a5"]["status"], "SHADOW_STORE_BACKED")
        self.store.close()
        self.store = Store(self.home)
        self.runtime.store = self.store
        with self.store.tx() as cursor:
            cursor.execute("UPDATE sources SET deleted=1 WHERE id=?", (self.ref["source_id"],))
        with self.assertRaises(ValueError):
            self.observe()

    def test_corrupt_blob_rejected(self):
        blob = self.home / "data" / "blobs" / self.ref["sha256"]
        blob.write_text('{"features":[1,1],"final":true}')
        with self.assertRaises(ValueError):
            self.observe()

    def test_provisional_rejected_in_real_store(self):
        ref = self.store.source(
            json.dumps({"features": [0.25, 0.5], "final": False}),
            kind="SYNTHETIC_TEST",
        )
        with self.assertRaises(PermissionError):
            observe_stored_features(
                self.runtime, self.projector, ref, modality="synthetic_ui"
            )


if __name__ == "__main__":
    unittest.main()
