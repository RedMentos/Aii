import unittest
from v13.percept_budget import Envelope, admit, technical_summary

class BudgetTests(unittest.TestCase):
    def test_preserves_mandatory_and_deferred(self):
        e=[Envelope("A5","source-1",40,mandatory=True),
           Envelope("B1","source-2",80,priority=1),
           Envelope("B2","source-3",30,priority=2)]
        r=admit(e,75)
        self.assertEqual([x.source_id for x in r["admitted"]],["source-1","source-3"])
        self.assertEqual([x.source_id for x in r["deferred"]],["source-2"])
        self.assertEqual(technical_summary(r)["remaining_tokens"],5)
        self.assertNotIn("source-1",str(technical_summary(r)))
    def test_fail_closed_required(self):
        r=admit([Envelope("USER","exact",80,mandatory=True)],50)
        self.assertEqual(r["status"],"INSUFFICIENT_REQUIRED_BUDGET")
        self.assertEqual(len(r["admitted"]),0)
        self.assertEqual(r["deferred"][0].source_id,"exact")
    def test_reject_bad(self):
        with self.assertRaises(ValueError):
            admit([Envelope("A5","",5)],20)
        with self.assertRaises(ValueError):
            admit([], -1)
    def test_stable_ties(self):
        e=[Envelope("B1","a",8,priority=1),Envelope("B2","b",8,priority=1)]
        self.assertEqual([x.source_id for x in admit(e,8)["admitted"]],["a"])
if __name__=="__main__":unittest.main()
