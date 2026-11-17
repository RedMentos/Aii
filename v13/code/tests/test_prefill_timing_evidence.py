import unittest
from v13.prefill_timing_evidence import Observation, estimate

class PrefillTimingEvidence(unittest.TestCase):
    def test_unverified_never_admits(self):
        self.assertEqual(estimate('C3',600,30,5,[Observation('C3',600,2,False)])['decision'],'MEASURE_FIRST')
    def test_real_failure_replans(self):
        self.assertEqual(estimate('C3',630,30,5,[Observation('C3',617,28.72,True)])['decision'],'DEFER_OR_REPLAN')
    def test_role_isolation(self):
        self.assertEqual(estimate('B1',60,30,5,[Observation('C3',617,28.72,True)])['decision'],'MEASURE_FIRST')
    def test_no_truncation(self):
        self.assertEqual(estimate('C3',1200,30,5,[Observation('C3',617,28.72,True)])['decision'],'DEFER_OR_REPLAN')
    def test_estimate_only(self):
        self.assertEqual(estimate('C3',40,30,5,[Observation('C3',617,28.72,True)])['decision'],'ADMIT_ESTIMATE_ONLY')
    def test_invalid(self):
        with self.assertRaises(ValueError):estimate('C3',-1,30,5,[])
