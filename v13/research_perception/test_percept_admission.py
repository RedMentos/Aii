import unittest
from percept_admission import Segment, admit

class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.a=Segment('raw-a','audio',9,3,True,'nonverbal cue')
        self.b=Segment('ui-b','ui',5,2,True,'screen')
    def test_priority_and_budget(self):
        x=admit((self.b,self.a),12,2)
        self.assertEqual([s.source_id for s in x.accepted],['raw-a'])
        self.assertEqual(x.tokens,9)
        self.assertEqual(x.status,'PARTIAL')
    def test_no_consent(self):
        x=admit((Segment('x','visual',1,99,False,'secret'),),10)
        self.assertFalse(x.accepted)
        self.assertEqual(x.status,'NO_ADMISSION')
    def test_no_truncation(self):
        x=admit((self.a,),8)
        self.assertEqual(x.deferred[0].text,self.a.text)
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): admit((self.a,self.a),50)
    def test_invalid_budget(self):
        with self.assertRaises(ValueError): admit((self.a,),3,4)
    def test_deterministic(self):
        self.assertEqual(admit((self.a,self.b),20),admit((self.b,self.a),20))
    def test_all_modalities(self):
        for m in ('text','audio','visual','ui'):
            self.assertEqual(admit((Segment('id',m,1,1,True,'x'),),1).status,'FULL')

if __name__=='__main__': unittest.main()
