"""WP-KAL: pure helpers of scripts/calibrate_real.py (no model, no server)."""
import importlib.util
import unittest
from pathlib import Path

APP=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('calibrate_real',APP/'scripts/calibrate_real.py')
cal=importlib.util.module_from_spec(spec);spec.loader.exec_module(cal)

class CalibrateRealTest(unittest.TestCase):
    def test_auroc(self):
        self.assertEqual(cal.auroc([.9,.8,.1,.2],[1,1,0,0]),1.)
        self.assertEqual(cal.auroc([.1,.2,.9,.8],[1,1,0,0]),0.)
        self.assertEqual(cal.auroc([.5,.5],[1,0]),.5)
        self.assertIsNone(cal.auroc([.5],[1]))
    def test_threshold(self):
        b=cal.best_threshold([.9,.8,.1,.2],[1,1,0,0]);self.assertEqual((b['tpr'],b['fpr']),(1.,0.))
        t=cal.at_threshold([.9,.1],[1,0],.5);self.assertEqual((t['tpr'],t['fpr'],t['accuracy']),(1.,0.,1.))
    def test_extract_and_contains(self):
        self.assertEqual(cal.extract('The answer is: 42.'),'42')
        self.assertEqual(cal.extract('7 * 8 = 56'),'56')
        self.assertEqual(cal.extract(''),'')
        self.assertEqual(cal.contains('Ben is 27 years old.','27'),1)
        self.assertEqual(cal.contains('Ben is 127 years old.','27'),0)
        self.assertEqual(cal.contains('It arrives at 15:00.','15:00'),1)
    def test_pairs_and_tasks_are_fixed(self):
        self.assertEqual(len(cal.PAIRS),40);self.assertTrue(all(l in (0,1) for _,_,l,_ in cal.PAIRS))
        items=cal.checkable();self.assertEqual(len(items),40);self.assertTrue(all(i['gold'] for i in items))
    def test_mean_prob(self):
        self.assertEqual(cal.mean_prob([]),0.)
        self.assertAlmostEqual(cal.mean_prob([{'token':'a','logprob':0.}]),1.)

if __name__=='__main__':unittest.main()

class CalibrationRegisterTest(unittest.TestCase):
    def test_register_shows_measured_values(self):
        import sys;sys.path.insert(0,str(APP))
        from v13 import register
        cal=register.calibration();self.assertIn('effort.BOOT[min_body_seconds]',cal)
        allowed=set(__import__('json').loads((APP/'specs/calibration.json').read_text())['verdicts'])
        self.assertTrue(all(v['verdict'] in allowed for v in cal.values()))
        self.assertEqual(register.calibration_for(cal,'attention.GAIN[focal]')['verdict'],'NEEDS_LEARNING_RUNS')
        self.assertIsNone(register.calibration_for(cal,None))
        rows=[r for r in register.entries() if r['source']=='BLUEPRINT' and r.get('calibration')]
        self.assertTrue(rows);self.assertEqual(register.summary()['calibrated'],len(rows))
