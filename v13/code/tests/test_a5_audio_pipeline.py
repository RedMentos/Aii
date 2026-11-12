"""Real V13 SQLite Store integration, synthetic PCM; native Android unverified."""
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from v13.store import Store
from v13.a3_online_projector import A3Projector
from v13.a5_audio_pipeline import observe_pcm_checked, checked_projector_audio_view


class AudioPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        (self.home / 'data' / 'db').mkdir(parents=True)
        (self.home / 'data' / 'blobs').mkdir(parents=True)
        self.store = Store(self.home)
        self.runtime = SimpleNamespace(store=self.store)
        self.projector = A3Projector(2, 2)
        self.projector.train([0.5, 0.5], [0.3, -0.2], trusted=True)
        self.pcm = struct.pack('<320h', *([12000, -12000] * 160))

    def tearDown(self):
        if not self.store.closed:
            self.store.close()
        self.temp.cleanup()

    def run_pipeline(self):
        return observe_pcm_checked(self.runtime, self.projector, self.pcm, 16000, consent=True)

    def test_real_sqlite_to_shadow_view(self):
        result = self.run_pipeline()
        self.assertEqual(result['candidate']['status'], 'SHADOW')
        self.assertEqual(result['view']['schema'], 'v13.audio.b_source_view.shadow.v1')
        self.assertTrue(result['view']['a3_recomputed'])
        self.assertFalse(result['view']['projector_revision_authenticated'])
        self.assertFalse(result['view']['body_inference_executed'])
        self.assertFalse(result['view']['android_action_allowed'])
        self.assertIsNone(result['candidate']['transcript'])
        self.assertIn('pitch_hz', result['candidate']['raw_ear']['unmeasured'])

    def test_sqlite_restart_revalidates(self):
        result = self.run_pipeline()
        self.store.close()
        self.store = Store(self.home)
        self.runtime.store = self.store
        after = checked_projector_audio_view(self.store, self.projector, result['candidate'], result['source_ref'])
        self.assertEqual(after['feature_sha256'], result['view']['feature_sha256'])

    def test_source_revocation_blocks_consumption(self):
        result = self.run_pipeline()
        with self.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (result['source_ref']['source_id'],))
        with self.assertRaises((PermissionError, ValueError)):
            checked_projector_audio_view(self.store, self.projector, result['candidate'], result['source_ref'])

    def test_no_consent_or_provisional_does_not_store(self):
        before = self.store.one('SELECT COUNT(*) AS n FROM sources')['n']
        with self.assertRaises(PermissionError):
            observe_pcm_checked(self.runtime, self.projector, self.pcm, 16000)
        with self.assertRaises(PermissionError):
            observe_pcm_checked(self.runtime, self.projector, self.pcm, 16000, consent=True, final=False)
        self.assertEqual(before, self.store.one('SELECT COUNT(*) AS n FROM sources')['n'])

    def test_bad_projector_does_not_store(self):
        before = self.store.one('SELECT COUNT(*) AS n FROM sources')['n']
        with self.assertRaises(ValueError):
            observe_pcm_checked(self.runtime, A3Projector(3, 2), self.pcm, 16000, consent=True)
        self.assertEqual(before, self.store.one('SELECT COUNT(*) AS n FROM sources')['n'])

    def test_tampered_embedding_rejected(self):
        result = self.run_pipeline()
        result['candidate']['a3']['embedding'] = [0.99, -0.99]
        with self.assertRaises(ValueError):
            checked_projector_audio_view(self.store, self.projector, result['candidate'], result['source_ref'])

    def test_changed_projector_rejected(self):
        result = self.run_pipeline()
        other = A3Projector(2, 2)
        with self.assertRaises(ValueError):
            checked_projector_audio_view(self.store, other, result['candidate'], result['source_ref'])

    def test_nonfinite_projector_prediction_rejected(self):
        result = self.run_pipeline()
        class BadProjector:
            def predict(self, features):
                return [float('nan'), 0.0]
        with self.assertRaises(ValueError):
            checked_projector_audio_view(self.store, BadProjector(), result['candidate'], result['source_ref'])

    def test_mutating_projector_prediction_rejected(self):
        result = self.run_pipeline()
        original = self.projector
        class MutableProjector:
            def __init__(self):
                self.calls = 0
            def predict(self, features):
                self.calls += 1
                base = original.predict(features)
                return base if self.calls == 1 else [base[0] + 0.01, base[1]]
        with self.assertRaises(PermissionError):
            checked_projector_audio_view(self.store, MutableProjector(), result['candidate'], result['source_ref'])


if __name__ == '__main__':
    unittest.main()
