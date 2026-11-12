"""Host-only A3 numeric learning -> checkpoint -> SQLite-backed inference regression.

Synthetic teacher vectors are explicit test fixtures, NOT authenticated A2 evidence.
No native Android, canonical A5, or B/C model inference is claimed.
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from v13.a3_online_projector import A3Projector
from v13.a3_store_source import observe_stored_features
from v13.store import Store


class A3CheckpointStoreRegression(unittest.TestCase):
    def test_numeric_training_survives_checkpoint_and_store_restart(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            (home / "data" / "db").mkdir(parents=True)
            (home / "data" / "blobs").mkdir(parents=True)
            checkpoint = home / "a3-master.json"
            store = Store(home)
            try:
                ref = store.source(json.dumps(
                    {"features": [0.25, 0.5], "final": True}),
                    kind="SYNTHETIC_TEST")
                runtime = SimpleNamespace(store=store)
                projector = A3Projector(2, 1)
                before = observe_stored_features(
                    runtime, projector, ref, modality="synthetic_audio")
                for _ in range(100):
                    projector.train([0.25, 0.5], [0.75], trusted=True)
                after = observe_stored_features(
                    runtime, projector, ref, modality="synthetic_audio")
                self.assertNotEqual(
                    before["a5"]["a3_embedding"], after["a5"]["a3_embedding"])
                self.assertEqual(after["a5"]["a3_training_steps"], 100)
                projector.save(checkpoint)
                store.close()
                store = Store(home)
                runtime.store = store
                restored = A3Projector.load(checkpoint)
                replay = observe_stored_features(
                    runtime, restored, ref, modality="synthetic_audio")
                self.assertEqual(after["a5"]["a3_embedding"],
                                 replay["a5"]["a3_embedding"])
                self.assertEqual(replay["a5"]["a3_training_steps"], 100)
                self.assertFalse(replay["jef"]["android_action_allowed"])
                with store.tx() as db:
                    db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                               (ref["source_id"],))
                with self.assertRaises(ValueError):
                    observe_stored_features(
                        runtime, restored, ref, modality="synthetic_audio")
            finally:
                if not store.closed:
                    store.close()

    def test_invalid_checkpoint_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "bad.json"
            path.write_text(json.dumps({
                "schema": 1, "inputs": 2, "outputs": 1, "lr": 0.02,
                "steps": 3, "weights": [[float("nan"), 0.0]], "bias": [0.0]
            }))
            with self.assertRaises(ValueError):
                A3Projector.load(path)


if __name__ == "__main__":
    unittest.main()
