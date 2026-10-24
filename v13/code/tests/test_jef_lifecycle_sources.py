import copy
import json
import unittest
from v13.jef_lifecycle_sources import matching_updates


def update(i, manifest):return {'id':i,'status':'ACTIVE','manifest':manifest if isinstance(manifest,str) else json.dumps(manifest)}


class LifecycleSources(unittest.TestCase):
    def test_exact_match(self):
        r=update('u1',{'source_ids':['src1','src2']})
        self.assertEqual(matching_updates([r],['src1']),[r])

    def test_substring_collision_not_match(self):
        self.assertEqual(matching_updates([update('u',{'source_ids':['src10']})],['src1']),[])

    def test_unrelated_manifest_text_not_match(self):
        self.assertEqual(matching_updates([update('u',{'source_ids':['x'],'note':'src1'})],['src1']),[])

    def test_malformed_json_ignored(self):
        self.assertEqual(matching_updates([update('u','{bad')],['src1']),[])

    def test_nonmapping_manifest_ignored(self):
        self.assertEqual(matching_updates([update('u','["src1"]')],['src1']),[])

    def test_nonlist_source_ids_ignored(self):
        for bad in ['src1',None,{'src1':True},1]:
            with self.subTest(bad=repr(bad)):
                self.assertEqual(matching_updates([update('u',{'source_ids':bad})],['src1']),[])

    def test_mixed_nonstring_source_ids_ignored(self):
        self.assertEqual(matching_updates([update('u',{'source_ids':['src1',1]})],['src1']),[])

    def test_duplicate_ids_one_update(self):
        r=update('u',{'source_ids':['src1','src1']})
        self.assertEqual(matching_updates([r],['src1','src1']),[r])

    def test_empty_source_ids_no_matches(self):
        self.assertEqual(matching_updates([update('u',{'source_ids':['src1']})],[]),[])

    def test_empty_string_source_ref_ignored(self):
        self.assertEqual(matching_updates([update('u',{'source_ids':['src1']})],['']),[])

    def test_input_unchanged(self):
        rows=[update('u',{'source_ids':['src1']})];before=copy.deepcopy(rows)
        matching_updates(rows,['src1']);self.assertEqual(rows,before)

    def test_multiple_updates_exact_subset(self):
        rows=[update('a',{'source_ids':['src10']}),update('b',{'source_ids':['src1']}),update('c',{'source_ids':['other']})]
        self.assertEqual([r['id'] for r in matching_updates(rows,['src1'])],['b'])


if __name__=='__main__':unittest.main()
