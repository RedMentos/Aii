import unittest
from prefill_admission import Envelope, Profile, admit, plan

class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.sources = (Envelope("A5","user:1",80), Envelope("B1","offer:1",300,False), Envelope("C3","header:1",40))
        self.fixture = Profile(20,2,4,True)  # synthetic only; never claim device measurement
    def test_unknown_refuses(self):
        self.assertEqual(admit(self.sources,None,30),(False,None,()))
    def test_optional_source_deferred(self):
        self.assertEqual(admit(self.sources,self.fixture,15),(True,12.0,("offer:1",)))
    def test_required_not_truncated(self):
        self.assertEqual(admit(self.sources,self.fixture,7)[0],False)
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): admit((self.sources[0],self.sources[0]),self.fixture,30)
    def test_invalid_rate(self):
        with self.assertRaises(ValueError): admit(self.sources,Profile(0,2,4,True),30)
    def test_all_sources_fit(self):
        self.assertEqual(admit(self.sources,self.fixture,60)[2],())

    def test_explicit_kept_sources(self):
        p = plan(self.sources,self.fixture,15)
        self.assertEqual(p.kept_source_ids,("user:1","header:1"))
        self.assertEqual(p.deferred_source_ids,("offer:1",))
        self.assertEqual(p.reason,"ESTIMATE_FITS")
    def test_no_profile_preserves_ids(self):
        p = plan(self.sources,None,30)
        self.assertFalse(p.admitted)
        self.assertEqual(p.kept_source_ids,tuple(e.source_id for e in self.sources))
        self.assertEqual(p.reason,"NO_REDMI_PROFILE")
    def test_bad_token_and_required_types(self):
        for bad in (True,1.5,-1,"10"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                plan((Envelope("A5","bad",bad),),self.fixture,30)
        with self.assertRaises(ValueError):
            plan((Envelope("A5","bad",1,"false"),),self.fixture,30)
    def test_nonfinite_and_boolean_deadline(self):
        for bad in (True,float("nan"),float("inf"),0):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                plan(self.sources,self.fixture,bad)
    def test_malformed_profile_and_no_mutation(self):
        with self.assertRaises(ValueError):
            plan(self.sources,Profile(float("nan"),2,4,True),30)
        before = tuple(self.sources)
        plan(self.sources,self.fixture,15)
        self.assertEqual(self.sources,before)

if __name__ == "__main__":
    unittest.main()
