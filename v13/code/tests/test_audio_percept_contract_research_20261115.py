"""Synthetic regression for existing A5 RAW EAR contract; no Android hardware claims."""
import hashlib
import unittest

from v13.audio_percept_contract import audio_percept_packet

SHA = hashlib.sha256(b"synthetic-audio-no-raw-content").hexdigest()

def build(**changes):
    kwargs = dict(event_id="synthetic-event", generation_id="g1",
                  source_id="synthetic-audio", source_sha256=SHA,
                  start_ms=100, end_ms=300, rms=0.2, zcr=0.1,
                  finality="PROVISIONAL", consent_receipt="synthetic-test-receipt")
    kwargs.update(changes)
    return audio_percept_packet(**kwargs)

class RawEarContractTests(unittest.TestCase):
    def test_provisional_acoustics_not_asr(self):
        result = build()
        self.assertEqual(result["payload"]["modality"], "audio")
        seg = result["payload"]["segments"][0]
        self.assertEqual(seg["finality"], "PROVISIONAL")
        self.assertIsNone(seg["asr_transcript"])
        self.assertFalse(seg["learning_authority"])
        self.assertFalse(seg["action_authority"])
        self.assertIn("prosody", seg["unmeasured"])

    def test_final_interval(self):
        self.assertEqual(build(finality="FINAL")["payload"]["segments"][0]["finality"], "FINAL")

    def test_missing_consent_denied(self):
        for receipt in (None, "", "  "):
            with self.subTest(receipt=receipt), self.assertRaises(PermissionError):
                build(consent_receipt=receipt)

    def test_reject_invalid_bounds(self):
        for bounds in ((100,100),(300,100),(0,1001),(-1,100)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                build(start_ms=bounds[0], end_ms=bounds[1])

    def test_reject_nonfinite_and_out_of_range(self):
        for bad in (float("nan"), float("inf"), -0.1, 1.1):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                build(rms=bad)

    def test_reject_invalid_hash_and_finality(self):
        with self.assertRaises(ValueError):
            build(source_sha256="not-a-hash")
        with self.assertRaises(ValueError):
            build(finality="UNVERIFIED")

if __name__ == "__main__":
    unittest.main()
