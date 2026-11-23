import unittest
from v13.mobile_prefill_admission import NativeSample, estimate, bounded_source_envelope

class MobileAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.s = [NativeSample("C3_LANGUAGE", 600, 28.0, 20, 4.0, 2, 128)]
    def test_long_prompt_deferred(self):
        r=estimate(self.s,role="C3_LANGUAGE",prompt_tokens=630,output_tokens=20,threads=2,batch=128)
        self.assertEqual(r["decision"],"DEFER_RESTORE")
        self.assertTrue(r["source_preserved"])
    def test_short_prompt_admitted_as_estimate_only(self):
        r=estimate(self.s,role="C3_LANGUAGE",prompt_tokens=40,output_tokens=5,threads=2,batch=128)
        self.assertEqual(r["decision"],"ADMIT_ESTIMATE")
        self.assertIn("ESTIMATE",r["reason"])
    def test_no_cross_configuration_fabrication(self):
        r=estimate(self.s,role="C3_LANGUAGE",prompt_tokens=40,output_tokens=5,threads=4,batch=128)
        self.assertEqual(r["decision"],"UNVERIFIED")
    def test_no_decode_evidence(self):
        s=[NativeSample("B1_DETAIL",100,3.0,0,0.0,2,64)]
        r=estimate(s,role="B1_DETAIL",prompt_tokens=100,output_tokens=10,threads=2,batch=64)
        self.assertEqual(r["decision"],"UNVERIFIED")
    def test_lossless_pointer(self):
        p=[{"source_ref":"raw:1","text":"exact source","estimated_tokens":4},
           {"source_ref":"raw:2","text":"not discarded","estimated_tokens":10}]
        r=bounded_source_envelope(p,4)
        self.assertEqual(r["selected"][0]["text"],"exact source")
        self.assertEqual(r["deferred"][0]["source_ref"],"raw:2")
        self.assertTrue(r["deferred"][0]["restore_required"])
    def test_missing_provenance_rejected(self):
        with self.assertRaises(ValueError):
            bounded_source_envelope([{"text":"unsupported","estimated_tokens":1}],2)
    def test_nonfinite_measurement_rejected(self):
        with self.assertRaises(ValueError):
            estimate([NativeSample("C3_LANGUAGE",100,float("nan"),1,1.,2,64)],
                     role="C3_LANGUAGE",prompt_tokens=10,output_tokens=1,threads=2,batch=64)
if __name__ == "__main__":
    unittest.main()
