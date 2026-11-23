"""Offline regression for canonical audio packet; no native Android claim."""
import unittest
from v13.audio_percept_contract import audio_percept_packet
from v13.contracts import validate

BASE = dict(event_id="synthetic-event",generation_id="synthetic-generation",
            source_id="synthetic-source",source_sha256="a"*64,
            start_ms=0,end_ms=20,rms=0.2,zcr=0.1,
            consent_receipt="synthetic-consent-reference")

class AudioPerceptContractTests(unittest.TestCase):
    def test_canonical(self):
        p=audio_percept_packet(**BASE)
        validate("PerceptPacket",p)
        self.assertEqual(p["modality"],"audio")
        self.assertFalse(p["segments"][0]["action_authority"])
        self.assertFalse(p["segments"][0]["learning_authority"])
        self.assertIsNone(p["segments"][0]["asr_transcript"])
    def test_missing_receipt(self):
        with self.assertRaises(PermissionError):
            audio_percept_packet(**{**BASE,"consent_receipt":None})
    def test_nonfinite(self):
        with self.assertRaises(ValueError):
            audio_percept_packet(**{**BASE,"rms":float("nan")})
    def test_invalid_hash(self):
        with self.assertRaises(ValueError):
            audio_percept_packet(**{**BASE,"source_sha256":"A"*64})
    def test_invalid_interval(self):
        with self.assertRaises(ValueError):
            audio_percept_packet(**{**BASE,"end_ms":0})
    def test_oversized_interval(self):
        with self.assertRaises(ValueError):
            audio_percept_packet(**{**BASE,"end_ms":1001})
    def test_provisional(self):
        p=audio_percept_packet(**{**BASE,"finality":"PROVISIONAL"})
        self.assertEqual(p["segments"][0]["finality"],"PROVISIONAL")

if __name__=="__main__":
    unittest.main()
