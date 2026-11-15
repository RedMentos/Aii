import unittest
from percept_admission import Segment, admit

class AdmissionHardeningTests(unittest.TestCase):
    def test_boolean_token_count_rejected(self):
        with self.assertRaises(ValueError): admit((Segment('x','audio',True,1,True,'x'),),10)
    def test_boolean_budget_rejected(self):
        with self.assertRaises(ValueError): admit((),True)
    def test_noninteger_priority_rejected(self):
        with self.assertRaises(ValueError): admit((Segment('x','ui',1,1.2,True,'x'),),10)
    def test_nonboolean_consent_rejected(self):
        with self.assertRaises(ValueError): admit((Segment('x','ui',1,1,'yes','x'),),10)
    def test_zero_token_nonempty_rejected(self):
        with self.assertRaises(ValueError): admit((Segment('x','text',0,1,True,'x'),),10)
    def test_empty_source_rejected(self):
        with self.assertRaises(ValueError): admit((Segment(' ','text',1,1,True,'x'),),10)
    def test_all_deferred_retained(self):
        xs=(Segment('a','audio',4,1,True,'cue'),Segment('b','ui',2,2,True,'ui'))
        out=admit(xs,0)
        self.assertEqual({x.source_id for x in out.deferred},{x.source_id for x in xs})
        self.assertEqual(out.tokens,0)

if __name__=='__main__': unittest.main()
