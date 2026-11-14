import unittest
from percept_admission import Percept, admit

def p(source, text, consent=True, final=True, end=10, modality='text'):
    return Percept(source, modality, text, consent, final, 0, end)

class AdmissionTests(unittest.TestCase):
    def test_current_user_priority(self):
        yes, no = admit([p('old','12345678'),p('now','abc')],max_chars=4,current_user_source='now')
        self.assertEqual([x.source_id for x in yes],['now'])
        self.assertEqual(no,[('old','BUDGET_EXCEEDED')])
    def test_no_truncation(self):
        with self.assertRaises(ValueError):
            admit([p('now','long')],max_chars=3,current_user_source='now')
    def test_consent_and_provisional(self):
        yes,no=admit([p('now','yes'),p('mic','raw',False,True,modality='audio'),p('asr','guess',True,False,modality='audio')],max_chars=20,current_user_source='now')
        self.assertEqual(len(yes),1)
        self.assertEqual(set(r for _,r in no),{'NO_CONSENT','PROVISIONAL'})
    def test_duplicate(self):
        yes,no=admit([p('now','a'),p('now','a')],max_chars=2,current_user_source='now')
        self.assertEqual(len(yes),1)
        self.assertEqual(no[0][1],'DUPLICATE_SOURCE')
    def test_bad_interval(self):
        with self.assertRaises(ValueError):
            Percept('x','audio','',True,True,5,4)
    def test_bad_confidence(self):
        with self.assertRaises(ValueError):
            Percept('x','ui','',True,True,0,1,1.1)
    def test_negative_budget(self):
        with self.assertRaises(ValueError):
            admit([p('now','a')],max_chars=-1,current_user_source='now')

if __name__=='__main__':
    unittest.main()
