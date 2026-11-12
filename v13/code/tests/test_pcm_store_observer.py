"""Real V13 SQLite Store integration, synthetic PCM only; no Android proof."""
import json
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from v13.store import Store
from v13.a3_online_projector import A3Projector
from v13.pcm_store_observer import observe_stored_pcm

class PCMStoreA3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / "data" / "db").mkdir(parents=True)
        (self.home / "data" / "blobs").mkdir(parents=True)
        self.store = Store(self.home)
        self.runtime = SimpleNamespace(store=self.store)
        self.projector = A3Projector(2, 2)
        self.projector.train([0.5, 0.5], [0.3, -0.2], trusted=True)
        self.pcm = struct.pack("<320h", *([12000, -12000] * 160))

    def tearDown(self):
        if not self.store.closed:
            self.store.close()
        self.tmp.cleanup()

    def test_real_sqlite_source_and_restart(self):
        result = observe_stored_pcm(self.runtime, self.projector, self.pcm, 16000, consent=True)
        ref = result["source_ref"]
        before = result["observation"]["a5"]
        self.assertEqual(before["status"], "SHADOW_TIMED_AUDIO")
        self.assertFalse(before["android_action_allowed"])
        self.assertIsNone(before["transcript"])
        self.assertEqual(before["a4_salience"]["schema"], "v13.a4.acoustic.salience.v1")
        self.assertEqual(before["a4_salience"]["authority"], "observation_only")
        self.assertIn("pitch_hz", before["a4_salience"]["unmeasured"])
        self.assertEqual(json.loads(self.store.read_source(ref))["end_ms"], 20)
        self.store.close()
        self.store = Store(self.home)
        self.runtime.store = self.store
        from v13.a3_timed_audio import observe_timed_audio
        after = observe_timed_audio(self.runtime, self.projector, ref)["a5"]
        self.assertEqual(before["a3_embedding"], after["a3_embedding"])
        self.assertEqual(before["store_source_sha256"], after["store_source_sha256"])

    def test_revoked_source_fails_closed(self):
        result = observe_stored_pcm(self.runtime, self.projector, self.pcm, 16000, consent=True)
        ref = result["source_ref"]
        with self.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?", (ref["source_id"],))
        from v13.a3_timed_audio import observe_timed_audio
        with self.assertRaises((ValueError, PermissionError)):
            observe_timed_audio(self.runtime, self.projector, ref)

    def test_no_consent_or_provisional_not_stored(self):
        before = self.store.one("SELECT COUNT(*) AS n FROM sources")["n"]
        for opts in ({"consent": False}, {"consent": True, "final": False}):
            with self.assertRaises(PermissionError):
                observe_stored_pcm(self.runtime, self.projector, self.pcm, 16000, **opts)
        self.assertEqual(before, self.store.one("SELECT COUNT(*) AS n FROM sources")["n"])

    def test_wrong_projector_dimension_not_stored(self):
        before = self.store.one("SELECT COUNT(*) AS n FROM sources")["n"]
        incompatible = A3Projector(3, 2)
        with self.assertRaises(ValueError):
            observe_stored_pcm(self.runtime, incompatible, self.pcm, 16000, consent=True)
        self.assertEqual(before, self.store.one("SELECT COUNT(*) AS n FROM sources")["n"])

    def test_missing_projector_not_stored(self):
        before = self.store.one("SELECT COUNT(*) AS n FROM sources")["n"]
        with self.assertRaises(TypeError):
            observe_stored_pcm(self.runtime, object(), self.pcm, 16000, consent=True)
        self.assertEqual(before, self.store.one("SELECT COUNT(*) AS n FROM sources")["n"])

    def test_malformed_pcm_not_stored(self):
        before = self.store.one("SELECT COUNT(*) AS n FROM sources")["n"]
        with self.assertRaises(ValueError):
            observe_stored_pcm(self.runtime, self.projector, bytes([0]), 16000, consent=True)
        self.assertEqual(before, self.store.one("SELECT COUNT(*) AS n FROM sources")["n"])

if __name__ == "__main__":
    unittest.main()
