"""Software-only shape/negative-gate guards; no fake native acceptance."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import c2_c3_body_auto_native_smoke_20261030 as m

class AutoNativeSmokeSoftware(unittest.TestCase):
    def make(self, source='NATIVE_C2_ADVISORY', offers=True):
        audit={'checks':{'source_refs_valid':True,'final_output':True},
               'source_errors':[],'output':'A visible native answer',
               'offers':([{'role':'B1_DETAIL'},{'role':'B2_GIST'}] if offers else []),
               'output_metadata':{'route':{'source':source},
                                  'c2_packet':{'route':'both'},
                                  'runner':{'role':'C3_LANGUAGE'},
                                  'model_generated':True}}
        return audit,{'query_ref':{'source_id':'src_test'}}

    def test_seed47_frozen_fixture_hash(self):
        self.assertEqual(m.SEED,47)
        self.assertEqual(m.fixture_hash(),'74818535a13819a65d4d32801d704fecd7716ea99c112b33c3bca248f3442c36')
        self.assertTrue(m.validate_fixtures())
        self.assertEqual(len(m.FIXTURES),3)

    def test_no_expected_remainder_in_prompt(self):
        for f in m.FIXTURES:
            text=m.prompt(f)
            self.assertIn(f['project'],text)
            self.assertIn('no cloud',text)
            self.assertNotIn(str(f['budget']-f['a_cost'])+' Euro',text)
            self.assertNotIn(str(f['budget']-f['b_cost'])+' Euro',text)

    def test_native_invoked_and_selected_are_distinct(self):
        audit,ctx=self.make(source='BOOT_SCAFFOLD')
        with patch.object(m,'valid_control_evidence',return_value=True):
            f=m.evidence_flags(audit,ctx,'chat_x','evt_x','source',True)
        self.assertTrue(f['native_invocation'])
        self.assertFalse(f['native_selected'])
        self.assertTrue(f['full_body_path'])

    def test_native_advisory_selected_only_with_genuine_invocation(self):
        audit,ctx=self.make()
        with patch.object(m,'valid_control_evidence',return_value=True):
            yes=m.evidence_flags(audit,ctx,'chat_x','evt_x','source',True)
            no=m.evidence_flags(audit,ctx,'chat_x','evt_x','source',False)
        self.assertTrue(yes['native_selected'])
        self.assertFalse(no['native_selected'])
        self.assertFalse(no['native_invocation'])

    def test_no_body_path_when_no_offers(self):
        audit,ctx=self.make(offers=False)
        with patch.object(m,'valid_control_evidence',return_value=True):
            f=m.evidence_flags(audit,ctx,'chat_x','evt_x','source',True)
        self.assertTrue(f['native_output'])
        self.assertFalse(f['full_body_path'])

    def test_invalid_final_checks_veto_output(self):
        audit,ctx=self.make()
        audit['checks']['source_refs_valid']=False
        with patch.object(m,'valid_control_evidence',return_value=True):
            f=m.evidence_flags(audit,ctx,'chat_x','evt_x','source',True)
        self.assertFalse(f['native_output'])
        self.assertFalse(f['full_body_path'])

    def test_source_control_invalid_cannot_be_native(self):
        audit,ctx=self.make()
        with patch.object(m,'valid_control_evidence',return_value=False):
            f=m.evidence_flags(audit,ctx,'chat_x','evt_x','source',True)
        self.assertFalse(f['native_invocation'])
        self.assertFalse(f['native_selected'])

    def test_existing_output_directory_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileExistsError):m.run(Path(td),Path(td))

if __name__=='__main__':unittest.main()
