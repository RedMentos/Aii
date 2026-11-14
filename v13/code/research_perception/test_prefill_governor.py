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
        for tokens in (99,601,1201):
            with self.subTest(tokens=tokens):
                self.assertEqual(admit_prefill(self.samples,**(self.args|{'prompt_tokens':tokens})).status,'EXTRAPOLATION_UNSUPPORTED')
    def test_bad_measurement_rejected(self):
        with self.assertRaises(ValueError): admit_prefill((Sample(10,float('nan'),'c3',2,128,'fixture'),),**self.args)
    def test_bad_deadline_rejected(self):
        with self.assertRaises(ValueError): admit_prefill(self.samples,**(self.args|{'deadline_ms':True}))
    def test_decode_reserve_prevents_false_admission(self):
        args=self.args|{'prompt_tokens':100,'deadline_ms':7500}
        self.assertEqual(admit_prefill(self.samples,**args).status,'ADMITTED')
        self.assertEqual(admit_prefill(self.samples,**args,decode_reserve_ms=1500).status,'PREFILL_DEADLINE_RISK')
    def test_no_admission_on_zero_remaining_decode_budget(self):
        args=self.args|{'prompt_tokens':100,'deadline_ms':6284}
        self.assertEqual(admit_prefill(self.samples,**args,decode_reserve_ms=1).status,'PREFILL_DEADLINE_RISK')
    def test_no_admission_for_nonfinite_factor(self):
        for factor in (float('nan'),float('inf'),0.9,True):
            with self.subTest(factor=factor),self.assertRaises(ValueError):
                admit_prefill(self.samples,**self.args,safety_factor=factor)
    def test_invalid_reserve_rejected(self):
        for value in (True,-1,1.5):
            with self.subTest(value=value),self.assertRaises(ValueError):
                admit_prefill(self.samples,**self.args,decode_reserve_ms=value)
    def test_no_latency_claim_without_two_distinct_lengths(self):
        samples=(self.samples[0],self.samples[0])
        self.assertEqual(admit_prefill(samples,**self.args).status,'INSUFFICIENT_PROFILE')
if __name__=='__main__': unittest.main()
