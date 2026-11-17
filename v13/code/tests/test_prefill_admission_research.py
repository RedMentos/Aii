import unittest
from v13.prefill_admission import admit

class AdmissionTests(unittest.TestCase):
    def test_unverified(self):
        self.assertEqual(admit([{'role':'user','content':'hello'}]).status,'UNVERIFIED')
    def test_slow(self):
        self.assertEqual(admit([{'role':'user','content':'x'*630}],measured_tokens_per_second=20,seconds_left=30).status,'REVIEW')
    def test_fast(self):
        self.assertEqual(admit([{'role':'user','content':'hi'}],measured_tokens_per_second=100,seconds_left=30).status,'ADVISORY_PASS')
    def test_preserve(self):
        m=[{'role':'system','content':'source:abc'},{'role':'user','content':'exact'}]
        old=repr(m);admit(m,measured_tokens_per_second=1,seconds_left=2);self.assertEqual(repr(m),old)
    def test_bad_rate(self):
        with self.assertRaises(ValueError):admit([{'role':'user','content':'x'}],measured_tokens_per_second=0,seconds_left=10)
    def test_budget(self):
        self.assertEqual(admit([{'role':'user','content':'abc'}],measured_tokens_per_second=100,seconds_left=10,max_prompt_tokens=2).status,'REVIEW')
