import unittest
from v13.audio_percept_contract import audio_percept_packet
from v13.audio_percept_enrichment import enrich_audio_percept
from v13.canonical_audio_admission import admit_canonical_audio

def fixture():
    return audio_percept_packet(event_id="synthetic",generation_id="synthetic",
        source_id="private-raw",source_sha256="a"*64,start_ms=0,end_ms=20,
        rms=.2,zcr=.1,consent_receipt="synthetic-only")

class CanonicalAdmissionTests(unittest.TestCase):
    def test_real_contract_to_jef_envelope(self):
        p=enrich_audio_percept(fixture(),pitch_hz=140,voiced_probability=.8,
                               teacher_text="private transcript",teacher_source="teacher")
        result=admit_canonical_audio(p,consent=True)
        self.assertEqual(result["modality"],"audio")
        self.assertTrue(result["requires_source_lookup"])
        self.assertNotIn("private transcript",str(result))
        self.assertNotIn("private-raw",str(result))
        self.assertFalse(result["learning_authority"])
    def test_no_consent(self):
        with self.assertRaises(PermissionError): admit_canonical_audio(fixture())
    def test_revoked_receipt(self):
        p=fixture();p["segments"][0]["consent_receipt_ref"]=None
        with self.assertRaises(PermissionError): admit_canonical_audio(p,consent=True)
    def test_injected_authority(self):
        p=fixture();p["segments"][0]["learning_authority"]=True
        with self.assertRaises(PermissionError): admit_canonical_audio(p,consent=True)
    def test_provisional(self):
        p=fixture();p["segments"][0]["finality"]="PROVISIONAL"
        self.assertEqual(admit_canonical_audio(p,consent=True)["status"],"PROVISIONAL")
    def test_invalid_time_bool(self):
        p=fixture();p["segments"][0]["start_ms"]=True
        with self.assertRaises(ValueError): admit_canonical_audio(p,consent=True)

if __name__=="__main__": unittest.main()
