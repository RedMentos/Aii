import unittest
from prefill_governor import Sample, admit_prefill

class GovernorTests(unittest.TestCase):
    def setUp(self):
        self.samples=(Sample(100,3000,'c3',2,128,'fixture'),Sample(600,29000,'c3',2,128,'fixture'))
        self.args=dict(prompt_tokens=600,deadline_ms=30000,model_revision='c3',threads=2,batch=128,device='fixture')
    def test_measured_risk(self):
        self.assertEqual(admit_prefill(self.samples,**self.args).status,'PREFILL_DEADLINE_RISK')
    def test_shorter_prompt(self):
        self.assertEqual(admit_prefill(self.samples,**(self.args|{'prompt_tokens':100})).status,'ADMITTED')
    def test_mismatched_device_refused(self):
        self.assertEqual(admit_prefill(self.samples,**(self.args|{'device':'other'})).status,'INSUFFICIENT_PROFILE')
    def test_mismatched_batch_refused(self):
        self.assertEqual(admit_prefill(self.samples,**(self.args|{'batch':64})).status,'INSUFFICIENT_PROFILE')
    def test_extrapolation_refused(self):
        self.assertEqual(admit_prefill(self.samples,**(self.args|{'prompt_tokens':1201})).status,'EXTRAPOLATION_UNSUPPORTED')
    def test_bad_measurement_rejected(self):
        with self.assertRaises(ValueError): admit_prefill((Sample(10,float('nan'),'c3',2,128,'fixture'),),**self.args)
    def test_bad_deadline_rejected(self):
        with self.assertRaises(ValueError): admit_prefill(self.samples,**(self.args|{'deadline_ms':True}))
if __name__=='__main__': unittest.main()
