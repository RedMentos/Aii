import unittest
from v13.synthetic_raw_ear import synthetic_pcm_to_percept as convert

class SyntheticRawEarTests(unittest.TestCase):
    def test_interval_and_lineage(self):
        p=convert([0]*160,source_id="fixture-1",start_ms=100,sample_rate_hz=16000,consent_scope="audio_observation_granted")
        self.assertEqual((p.start_ms,p.end_ms),(100,110))
        self.assertEqual(p.provenance,"raw_ear_derived")
        self.assertNotIn("teacher_text",p.bounded_context())
    def test_energy(self):
        p=convert([1,-1],source_id="fixture-2",start_ms=0,sample_rate_hz=8000,consent_scope="audio_observation_granted")
        self.assertEqual(p.rms,1)
    def test_permission(self):
        with self.assertRaises(PermissionError):
            convert([0],source_id="fixture",start_ms=0,sample_rate_hz=8000,consent_scope="off")
    def test_invalid_pcm(self):
        with self.assertRaises(ValueError):
            convert([float("nan")],source_id="fixture",start_ms=0,sample_rate_hz=8000,consent_scope="audio_observation_granted")
    def test_oversize(self):
        with self.assertRaises(ValueError):
            convert([0]*80001,source_id="fixture",start_ms=0,sample_rate_hz=8000,consent_scope="audio_observation_granted")
if __name__=="__main__": unittest.main()
