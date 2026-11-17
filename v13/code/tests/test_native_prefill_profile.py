"""Synthetic contract checks; no claim of Redmi verification."""
import unittest
from v13.native_prefill_profile import Sample, estimate

class NativeProfile(unittest.TestCase):
    def setUp(self):
        self.samples=[Sample("redmi","c3-rev",2,128,2,n,t,True)
                      for n,t in ((40,1),(120,3.5),(300,8))]
        self.kw=dict(device="redmi",model_revision="c3-rev",threads=2,
                     batch=128,concurrent=2,prompt_tokens=600,remaining_s=30)
    def test_admission(self):
        self.assertFalse(estimate(self.samples,**self.kw)["admit"])
        self.assertTrue(estimate(self.samples,**(self.kw|{"prompt_tokens":40}))["admit"])
    def test_no_profile_transfer(self):
        for key,val in (("device","linux"),("model_revision","other"),("threads",4),("concurrent",1)):
            self.assertEqual(estimate(self.samples,**(self.kw|{key:val}))["reason"],
                             "NO_MATCHING_COMPLETED_NATIVE_PROFILE")
    def test_failed_prefill_is_not_positive_profile(self):
        bad=Sample("redmi","c3-rev",2,128,2,630,28.7,False)
        self.assertEqual(estimate([bad]*5,**self.kw)["samples"],0)
    def test_invalid_budget(self):
        self.assertEqual(estimate(self.samples,**(self.kw|{"prompt_tokens":0}))["reason"],"INVALID_BUDGET")
if __name__=="__main__":unittest.main()
