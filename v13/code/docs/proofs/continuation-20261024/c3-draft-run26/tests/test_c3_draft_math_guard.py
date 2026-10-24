import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import c3_draft_math_guard as guard

class DraftMathGuard(unittest.TestCase):
    def test_explicit_correct(self):
        self.assertEqual(guard.assess('87 + 51 + 66 = 204 euros')['findings'],[])
    def test_explicit_incorrect(self):
        self.assertEqual(guard.assess('57 + 19 + 38 = 94 euros')['findings'][0]['calculated'],114)
    def test_total_correct(self):
        self.assertEqual(guard.assess('The correct total is 171 euros (75 + 42 + 54).')['findings'],[])
    def test_total_incorrect(self):
        self.assertEqual(guard.assess('The correct total is **133 euros** (23 + 56 + 14).')['findings'][0]['calculated'],93)
    def test_difference_correct(self):
        self.assertEqual(guard.assess('The difference is 436 mm (722 - 286).')['findings'],[])
    def test_difference_incorrect(self):
        self.assertEqual(guard.assess('The difference is 112 mm (689 - 476).')['findings'][0]['calculated'],213)
    def test_order_inversion(self):
        r=guard.assess('Lyon has the highest rainfall 302 mm, Graz the lowest 775 mm.')
        self.assertEqual(r['findings'][0]['kind'],'ORDER_INVERSION')
    def test_no_claim_on_unsupported_text(self):
        r=guard.assess('The latest note says 33 members, 5 March.')
        self.assertEqual(r['status'],'NO_ARITHMETIC_CONTRADICTION_FOUND')
        self.assertFalse(r['correctness_proven'])
    def test_bound_and_type(self):
        for x in (None,{},'a'*8193):
            with self.assertRaises(ValueError):guard.assess(x)
    def test_input_schema_and_duplicate_id(self):
        with self.assertRaises(ValueError):guard.audit_records([{'fixture':'a','draft':'ok','extra':1}])
        with self.assertRaises(ValueError):guard.audit_records([{'fixture':'a','draft':'x'},{'fixture':'a','draft':'y'}])
    def test_durable_report_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'in.json';out=root/'out.json'
            src.write_text(json.dumps([{'fixture':'x','draft':'1 + 2 = 4'}]))
            h=guard.write_closed_report(src,out)
            self.assertEqual(len(h),64)
            self.assertEqual(json.loads(out.read_text())['rows'][0]['status'],'NEEDS_VERIFICATION')
            with self.assertRaises(FileExistsError):guard.write_closed_report(src,out)
    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'in.json'
            src.write_text('[{"fixture":"x","draft":"1+2=4","draft":"ok"}]')
            with self.assertRaisesRegex(ValueError,'duplicate'):
                guard.write_closed_report(src,root/'out.json')

    def test_large_input_rejected_without_full_read(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'in.json'
            src.write_bytes(b' '*(16*1024*1024+2))
            with self.assertRaisesRegex(ValueError,'too large'):
                guard.write_closed_report(src,root/'out.json')

    def test_dangling_output_symlink_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'in.json';out=root/'out.json'
            src.write_text('[{"fixture":"x","draft":"1+2=4"}]')
            out.symlink_to(root/'missing.json')
            with self.assertRaises(FileExistsError):
                guard.write_closed_report(src,out)
            self.assertTrue(out.is_symlink())

    def test_no_action_authority(self):
        r=guard.assess('1 + 2 = 4')
        self.assertEqual(r['authority'],'SHADOW_NO_ACTION')
        self.assertNotIn('wake',r)

if __name__=='__main__':unittest.main()
