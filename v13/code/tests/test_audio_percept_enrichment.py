import unittest
from v13.audio_percept_contract import audio_percept_packet
from v13.audio_percept_enrichment import enrich_audio_percept

def fixture():
    return audio_percept_packet(event_id="fixture", generation_id="fixture-gen",
        source_id="fixture-source", source_sha256="a"*64, start_ms=0, end_ms=20,
        rms=.2, zcr=.1, consent_receipt="synthetic-only")

class AcousticEnrichmentTests(unittest.TestCase):
    def test_nonverbal_without_asr(self):
        p=enrich_audio_percept(fixture(), pitch_hz=120, voiced_probability=.75)
        self.assertEqual(p["segments"][0]["acoustic"]["pitch_hz"],120)
        self.assertIsNone(p["segments"][0]["asr_transcript"])
        self.assertFalse(p["segments"][0]["learning_authority"])
    def test_teacher_not_promoted(self):
        p=enrich_audio_percept(fixture(), teacher_text="hello", teacher_source="fixture-asr")
        self.assertFalse(p["segments"][0]["teacher_asr"]["trusted"])
    def test_no_mutation(self):
        original=fixture()
        enrich_audio_percept(original,pitch_hz=130)
        self.assertNotIn("pitch_hz",original["segments"][0]["acoustic"])
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            enrich_audio_percept(fixture(),voiced_probability=float("nan"))
    def test_missing_teacher_source(self):
        with self.assertRaises(ValueError):
            enrich_audio_percept(fixture(),teacher_text="hello")
    def test_consent_rechecked(self):
        p=fixture()
        p["segments"][0]["consent_receipt_ref"]=None
        with self.assertRaises(PermissionError):
            enrich_audio_percept(p,pitch_hz=120)
if __name__=="__main__":
    unittest.main()
