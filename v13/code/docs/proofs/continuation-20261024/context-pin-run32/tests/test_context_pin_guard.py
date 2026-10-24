from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import context_pin_guard as C

class ContextPinTests(unittest.TestCase):
    def plan(self,items,planned=100,limit=200):
        return {'items':items,'budget':{'planned_chars':planned,'chars':limit}}
    def test_pinned_compressed_rejected(self):
        r=C.validate(self.plan([{'item_id':'e1','layer':'COMPRESSED','form':'COMPRESSED','pinned':True}]))
        self.assertEqual(r['status'],'REJECT_ACTIVE')
        self.assertIn('PIN_NOT_RAW:e1',r['violations'])
    def test_pinned_pointer_rejected(self):
        r=C.validate(self.plan([{'item_id':'e1','layer':'SOURCE_LINKS','form':'POINTER','pinned':True}]))
        self.assertEqual(r['status'],'REJECT_ACTIVE')
    def test_restored_pointer_rejected(self):
        r=C.validate(self.plan([{'item_id':'e1','layer':'SOURCE_LINKS','form':'POINTER','restored':True}]))
        self.assertIn('RESTORED_NOT_RAW:e1',r['violations'])
    def test_valid_pinned_raw_accepted_only_as_invariant(self):
        r=C.validate(self.plan([{'item_id':'e1','layer':'RAW_HISTORY','form':'RAW','pinned':True}]))
        self.assertEqual(r['status'],'PASS_INVARIANTS')
        self.assertFalse(r['source_restoration_proven'])
    def test_overbudget_rejected(self):
        r=C.validate(self.plan([],planned=201,limit=200))
        self.assertIn('OVER_BUDGET',r['violations'])
    def test_duplicate_item_rejected(self):
        r=C.validate(self.plan([{'item_id':'x','layer':'RAW_HISTORY'}, {'item_id':'x','layer':'RAW_HISTORY'}]))
        self.assertIn('DUPLICATE_ITEM',r['violations'])
    def test_pinned_never_compressed_under_pressure(self):
        r=C.choose_budget_forms([('old',300,False,False),('recent',200,True,False)],250,50,50,{'old':100,'recent':10})
        self.assertEqual(r['forms']['recent'],'RAW')
        self.assertEqual(r['forms']['old'],'POINTER')
        self.assertEqual(r['status'],'NO_PLAN_PINNED_BUDGET')
    def test_unpinned_can_compress_and_fit(self):
        r=C.choose_budget_forms([('old',300,False,False),('recent',100,True,False)],250,20,20,{'old':80})
        self.assertEqual(r['status'],'READY')
        self.assertEqual(r['forms']['old'],'COMPRESSED')
        self.assertEqual(r['forms']['recent'],'RAW')
    def test_restored_unpinned_cannot_drop(self):
        r=C.choose_budget_forms([('old',300,False,True)],200,20,20,{'old':10})
        self.assertEqual(r['status'],'NO_PLAN_PINNED_BUDGET')
        self.assertEqual(r['forms']['old'],'RAW')
    def test_no_authority(self):
        r=C.validate(self.plan([]))
        self.assertEqual(r['authority'],'SHADOW_GUARD_NO_RUNTIME_ACTION')
        self.assertFalse(r['canonical_gate_pass'])

if __name__=='__main__':unittest.main()
