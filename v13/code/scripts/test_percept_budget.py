import unittest
from percept_budget import Percept, admit

class TestAdmission(unittest.TestCase):
    def p(self, source, salience=.5, tokens=4, consent=True):
        return Percept(source, "audio_raw", 0, 100, salience, tokens, consent)
    def test_priority_and_deferred(self):
        result=admit([self.p("low",.2),self.p("high",.9)],4)
        self.assertEqual([x["source_id"] for x in result["selected"]],["high"])
        self.assertEqual([x["source_id"] for x in result["deferred"]],["low"])
    def test_no_consent(self):
        result=admit([self.p("private",1,1,False)],10)
        self.assertEqual(result["selected"],[])
        self.assertEqual(result["consent_denied_count"],1)
    def test_provenance(self):
        self.assertEqual(admit([self.p("a")],4)["selected"][0]["provenance"],"source_exact")
    def test_zero_budget(self):
        self.assertEqual(len(admit([self.p("a")],0)["deferred"]),1)
    def test_invalid_timing(self):
        with self.assertRaises(ValueError):
            admit([Percept("a","ui",5,4,.5,2,True)],5)
    def test_invalid_provenance(self):
        with self.assertRaises(ValueError):
            admit([Percept("a","ui",0,4,.5,2,True,"latent_learned")],5)
    def test_negative_budget(self):
        with self.assertRaises(ValueError): admit([], -1)
    def test_deterministic_tie(self):
        self.assertEqual(admit([self.p("b"),self.p("a")],4)["selected"][0]["source_id"],"a")

if __name__ == "__main__": unittest.main()
