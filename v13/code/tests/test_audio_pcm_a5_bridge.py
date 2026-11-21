"""RAW EAR PCM -> existing canonical A5 contract; synthetic only."""
import unittest
from v13.audio_percept import acoustic_window, canonical_packet
from v13.contracts import validate

SRC={"source_id":"fixture-source","sha256":"a"*64}

class PCMToA5(unittest.TestCase):
    def test_pcm_features_and_provisional(self):
        p=acoustic_window([.5,-.5,.5,-.5],8000,SRC,100,consent=True)
        self.assertEqual(p["end_ms"],100.5)
        self.assertEqual(p["features"]["rms"],.5)
        self.assertEqual(p["features"]["zero_crossing_rate"],1)
        self.assertIsNone(p["provenance"]["transcript"])
        self.assertEqual(p["learning_authority"],"NONE")
    def test_consent_and_invalid_pcm(self):
        with self.assertRaises(PermissionError):
            acoustic_window([0],8000,SRC,0)
        for samples in ([float("nan")],[2.0],[],[0]*16001):
            with self.subTest(length=len(samples)):
                with self.assertRaises(ValueError):
                    acoustic_window(samples,8000,SRC,0,consent=True)
    def test_existing_a5_contract(self):
        p=canonical_packet([.5,-.5]*80,8000,SRC,100,
                           consent_receipt="synthetic-local-receipt",
                           event_id="synthetic-event",generation_id="synthetic-generation")
        validate("PerceptPacket",p)
        self.assertEqual(p["segments"][0]["finality"],"PROVISIONAL")
        self.assertFalse(p["segments"][0]["learning_authority"])
        self.assertIsNone(p["segments"][0]["asr_transcript"])
    def test_short_window_rejected(self):
        with self.assertRaises(ValueError):
            canonical_packet([0],8000,SRC,0,consent_receipt="synthetic",
                             event_id="e",generation_id="g")
if __name__=="__main__":
    unittest.main()
