"""Synthetic A5->C3 prompt admission tests; not Android or tokenizer evidence."""
import unittest
from v13.audio_prompt_admission import admit_audio_shadow

def observation(n=1):
    return {"kind":"A5_AUDIO_OBSERVATION","authority":"SHADOW_ONLY",
            "action_authority":False,"learning_authority":False,
            "semantic_truth_authority":False,"finality":"PROVISIONAL",
            "source_ref":{"source_id":"s","sha256":"a"*64},
            "windows":[{"start_ms":i*20,"end_ms":(i+1)*20,
                        "rms":0.5,"zcr":0.2,"finality":"PROVISIONAL"} for i in range(n)]}

class AdmissionTests(unittest.TestCase):
    def test_full(self):
        r=admit_audio_shadow(observation(),max_utf8_bytes=1024)
        self.assertEqual(r["status"],"FULL")
        self.assertIn("uninterpreted_acoustics",r["prompt_text"])
    def test_summary_not_silent_truncation(self):
        r=admit_audio_shadow(observation(30),max_utf8_bytes=256)
        self.assertEqual(r["status"],"SUMMARY")
        self.assertEqual(r["omitted_windows"],30)
        self.assertLessEqual(r["utf8_bytes"],256)
    def test_tiny_budget_explicit(self):
        r=admit_audio_shadow(observation(),max_utf8_bytes=8)
        self.assertEqual(r["status"],"OMITTED_BUDGET")
        self.assertEqual(r["prompt_text"],"")
    def test_no_consent_or_speaker_leak(self):
        o=observation();o["consent_receipt"]="SECRET";o["speaker"]="PERSON"
        r=admit_audio_shadow(o,max_utf8_bytes=1024)
        self.assertNotIn("SECRET",str(r))
        self.assertNotIn("PERSON",str(r))
    def test_authority_rejected(self):
        o=observation();o["learning_authority"]=True
        with self.assertRaises(PermissionError): admit_audio_shadow(o)
    def test_nan_rejected(self):
        o=observation();o["windows"][0]["rms"]=float("nan")
        with self.assertRaises(ValueError): admit_audio_shadow(o)
    def test_missing_source_rejected(self):
        o=observation();o["source_ref"]["sha256"]="wrong"
        with self.assertRaises(ValueError): admit_audio_shadow(o)
    def test_invalid_budget_rejected(self):
        with self.assertRaises(ValueError): admit_audio_shadow(observation(),max_utf8_bytes=True)
    def test_large_window_count_rejected(self):
        with self.assertRaises(ValueError): admit_audio_shadow(observation(65))

if __name__=="__main__":
    unittest.main()
