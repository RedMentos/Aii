import unittest
from prefill_admission import Envelope, Profile, admit

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

if __name__ == "__main__":
    unittest.main()
