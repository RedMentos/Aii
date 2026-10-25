"""Run156 A3 synthetic OOD stress checks; no native model/teacher authority."""
import json
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from a3_support_ood_probe_run156 import cohorts,probe,score,SEED,GATES

class A3OODProbe(unittest.TestCase):
    def test_deterministic_aggregate(self):
        self.assertEqual(probe(),probe())

    def test_threshold_independent_of_heldout(self):
        t,h,o=cohorts()['clustered'];a=score(t,h,o)
        b=score(t,np.flip(h,axis=0),np.flip(o,axis=0))
        self.assertEqual(a,b)
        c=score(t,cohorts()['uniform'][1],cohorts()['uniform'][2])
        self.assertEqual(a['support_floor'],c['support_floor'])

    def test_clustered_id_and_ood_are_separated(self):
        a=probe()['results']['clustered']
        self.assertGreater(a['id_accept_rate'],.8)
        self.assertLess(a['ood_false_accept_rate'],.2)

    def test_uniform_clamp_is_detected_not_hidden(self):
        a=probe()['results']['uniform']
        self.assertTrue(a['floor_clamped_min'])
        self.assertEqual(a['id_accepted'],0)
        self.assertEqual(a['ood_accepted'],0)

    def test_nonfinite_heldout_rejected(self):
        t,h,o=cohorts()['clustered'];h=h.copy();h[0,0]=np.nan
        with self.assertRaisesRegex(ValueError,'nonfinite'):score(t,h,o)

    def test_zero_heldout_rejected(self):
        t,h,o=cohorts()['clustered'];o=o.copy();o[0]=0
        with self.assertRaisesRegex(ValueError,'zero_vector'):score(t,h,o)

    def test_gate_and_provenance(self):
        r=probe();self.assertEqual(r['gates'],GATES)
        self.assertEqual(r['authority'],'SHADOW_DIAGNOSTIC_NOT_ACTIVE')
        self.assertEqual(r['gate'],'UNVERIFIED')
        self.assertEqual(r['definition']['seed'],SEED)
        self.assertEqual(len(r['cohort_definition_sha256']),64)

if __name__=='__main__':unittest.main()
