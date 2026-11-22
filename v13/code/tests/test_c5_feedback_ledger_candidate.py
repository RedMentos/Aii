import json
import unittest
from v13 import c5_feedback_ledger_candidate as L

class LedgerTests(unittest.TestCase):
    def test_duplicate_is_idempotent(self):
        s=L.record(L.empty(),'e1','simple|low','C3',10)
        self.assertEqual(L.record(s,'e1','simple|low','C3',10),s)
        self.assertEqual(L.aggregate(s)['simple|low|C3']['n'],1)
    def test_correction_retracts_old_credit(self):
        s=L.record(L.empty(),'e1','simple|low','C3',10)
        s=L.record(s,'e1','simple|low','C3',1)
        a=L.aggregate(s)['simple|low|C3']
        self.assertEqual((a['n'],a['human_approval'],a['human_correction']),(1,0,1))
    def test_restart_roundtrip(self):
        s=L.record(L.empty(),'e1','simple|low','C3',4)
        self.assertEqual(L.aggregate(json.loads(json.dumps(s))),L.aggregate(s))
    def test_action_rebind_rejected(self):
        s=L.record(L.empty(),'e1','simple|low','C3',10)
        with self.assertRaises(ValueError):L.record(s,'e1','detail|low','C3',1)
    def test_invalid_values_rejected(self):
        for score in (float('nan'),float('inf'),True,0,11):
            with self.subTest(score=score),self.assertRaises(ValueError):L.record(L.empty(),'e','c','a',score)
    def test_distinct_events_count(self):
        s=L.empty()
        for i in range(3):s=L.record(s,'e'+str(i),'c','a',10)
        self.assertEqual(L.aggregate(s)['c|a']['n'],3)

if __name__=='__main__':unittest.main()
