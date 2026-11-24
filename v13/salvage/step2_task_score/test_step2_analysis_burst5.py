import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[1]/'scripts'/'analyze_step2_proof.py'
spec=importlib.util.spec_from_file_location('step2_analysis',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Step2Analysis(unittest.TestCase):
    def test_signal_never_promotes_gate(self):
        p={'proof_kind':'x','status':'ABLATIONS_RECORDED','uses_real_weights':True,'phone_measured':False,'fixtures':[{'id':'f','expected_numbers':[1,2]}],'rows':[
          {'fixture':'f','variant':'b1_only','status':'CHECKS_PASS','lexical_number_coverage':{'final':{'1':True,'2':False}},'measurements':{'turn_s':1.,'sampled_native_peak_rss_bytes':10}},
          {'fixture':'f','variant':'b2_only','status':'CHECKS_PASS','lexical_number_coverage':{'final':{'1':False,'2':True}},'measurements':{'turn_s':2.,'sampled_native_peak_rss_bytes':20}},
          {'fixture':'f','variant':'both_control','status':'CHECKS_PASS','lexical_number_coverage':{'final':{'1':True,'2':True}},'measurements':{'turn_s':3.,'sampled_native_peak_rss_bytes':30}}]}
        o=m.analyze(p)
        self.assertEqual(o['status'],'DIAGNOSTIC_SIGNAL_ONLY');self.assertFalse(o['gate_promotion']);self.assertFalse(o['complementarity_proven'])
        self.assertEqual(o['measurements']['diagnostic_positive_signal_fixtures'],['f'])
    def test_task_bound_score_is_reported_without_gate_promotion(self):
        p={'fixtures':[{'id':'f','expected_numbers':[1]}],'rows':[
          {'fixture':'f','variant':'b1_only','status':'CHECKS_PASS','task_assertions':{'a':True,'b':False},'lexical_number_coverage':{'final':{}},'measurements':{}},
          {'fixture':'f','variant':'both_control','status':'CHECKS_PASS','task_assertions':{'a':True,'b':True},'lexical_number_coverage':{'final':{}},'measurements':{}}]}
        o=m.analyze(p);f=o['fixtures'][0]
        self.assertEqual(f['best_single_task_fraction'],.5);self.assertEqual(f['best_both_task_fraction'],1.)
        self.assertTrue(f['task_bound_positive_combination_signal']);self.assertFalse(o['gate_promotion']);self.assertFalse(o['complementarity_proven'])
    def test_no_signal(self):
        p={'fixtures':[{'id':'f','expected_numbers':[1]}],'rows':[{'fixture':'f','variant':'b1_only','status':'CHECKS_PASS','lexical_number_coverage':{'final':{'1':True}},'measurements':{}},{'fixture':'f','variant':'both_none','status':'CHECKS_PASS','lexical_number_coverage':{'final':{'1':True}},'measurements':{}}]}
        o=m.analyze(p);self.assertEqual(o['status'],'NO_DIAGNOSTIC_COMPLEMENTARITY_SIGNAL');self.assertFalse(o['gate_promotion'])
if __name__=='__main__':unittest.main()
