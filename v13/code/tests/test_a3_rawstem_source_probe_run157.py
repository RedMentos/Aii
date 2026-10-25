"""Run157 real A3 raw-stem model-free source-group support diagnostics."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from a3_rawstem_source_probe_run157 import probe,corpus,GATES
from v13.student_worker import split

class RawStemProbe(unittest.TestCase):
    def test_source_group_split(self):
        groups,_,_,_=corpus();ti,vi=split(groups)
        self.assertEqual(len(ti)+len(vi),128)
        self.assertEqual(len(set(groups)),128)
        self.assertFalse(set(ti)&set(vi))

    def test_exact_determinism(self):
        self.assertEqual(probe(),probe())

    def test_far_domain_rejection(self):
        r=probe()['far_domain']
        self.assertEqual(r['id_accepted'],r['id_count'])
        self.assertEqual(r['ood_accepted'],0)

    def test_unseen_value_substitution_is_not_truth(self):
        r=probe()['unseen_value_substitution']
        self.assertGreater(r['ood_accepted'],0)
        self.assertFalse(r['threshold_uses_heldout'])

    def test_gates_and_zero_updates(self):
        r=probe();self.assertEqual(r['gates'],GATES)
        self.assertEqual(r['teacher_parameter_updates'],0)
        self.assertEqual(r['student_parameter_updates'],0)
        self.assertEqual(r['gate'],'UNVERIFIED')
        self.assertEqual(r['authority'],'SHADOW_DIAGNOSTIC_NOT_ACTIVE')

if __name__=='__main__':unittest.main()
