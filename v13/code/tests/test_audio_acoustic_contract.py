"""Run: PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_audio_acoustic_contract.py'"""
import unittest
from v13.audio_acoustic_contract import acoustic_packet


class AcousticContractTests(unittest.TestCase):
    def fixture(self, samples=(0.0, 0.5, -0.5, 1.0), **kw):
        return acoustic_packet(samples, sample_rate_hz=8000, start_ms=1234,
                               source_kind="synthetic_fixture", consent_scope="synthetic_test", **kw)

    def test_timed_nonverbal_packet(self):
        p = self.fixture()
        self.assertEqual((p.start_ms, p.end_ms), (1234, 1235))
        self.assertEqual(p.sample_count, 4)
        self.assertEqual(p.zero_crossing_rate, 1/3)
        self.assertEqual(p.clipped_fraction, .25)
        self.assertIsNone(p.transcript)
        self.assertIsNone(p.speaker_identity)
        self.assertEqual(p.a3_gate, "UNAVAILABLE")

    def test_determinism_and_provisional_final(self):
        a, b = self.fixture(), self.fixture(is_final=True)
        self.assertEqual(a.signal_sha256, b.signal_sha256)
        self.assertFalse(a.is_final)
        self.assertTrue(b.is_final)

    def test_no_unapproved_real_capture(self):
        with self.assertRaises(PermissionError):
            acoustic_packet([0.1], sample_rate_hz=8000, start_ms=0,
                            source_kind="permissioned_microphone", consent_scope="synthetic_test")

    def test_missing_consent(self):
        with self.assertRaises(PermissionError):
            acoustic_packet([0.1], sample_rate_hz=8000, start_ms=0,
                            source_kind="synthetic_fixture", consent_scope="none")

    def test_nonfinite_rejected(self):
        for value in (float("nan"), float("inf"), 1.1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.fixture([value])

    def test_empty_and_invalid_clock(self):
        with self.assertRaises(ValueError):
            self.fixture([])
        with self.assertRaises(ValueError):
            acoustic_packet([0.1], sample_rate_hz=8000, start_ms=-1,
                            source_kind="synthetic_fixture", consent_scope="synthetic_test")

    def test_no_raw_pcm_in_serialized_packet(self):
        p = self.fixture()
        self.assertNotIn("samples", p.to_dict())
        self.assertNotIn("pcm", p.to_dict())


if __name__ == "__main__":
    unittest.main()
