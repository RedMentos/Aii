"""Run117BA disjoint-to-AZ validation fixture and strict schema software controls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import run117ba_native_schema_paired as ba

class Run117BAPaired(unittest.TestCase):
    def test_frozen_validation_disjoint_from_az_calibration(self):
        r=ba.rows()
        self.assertEqual(tuple(x['id'] for x in r),ba.IDS)
        self.assertEqual(tuple(x['oracle_action'] for x in r),ba.ACTIONS)
        self.assertEqual(len({x['id'] for x in r}),6)
        self.assertFalse(set(ba.IDS)&set(ba.az.IDS))

    def test_frozen_validation_mutation_refused(self):
        r=ba.p2x.fixtures()
        for x in r:
            if x['id']==ba.IDS[0]:x['current']+=' changed'
        with patch.object(ba.p2x,'fixtures',return_value=r):
            with self.assertRaises((ValueError,AssertionError)):ba.rows()

    def test_synthetic_pair_twelve_source_bound_drafts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertTrue(ba.run(root/'work',None,root/'raw'))
            r=json.loads((root/'raw/report.json').read_text())
            self.assertEqual(r['strict_scores'],{'TOKEN':6,'SCHEMA':6})
            self.assertEqual(r['native_c3_calls'],0)
            self.assertEqual(len(r['rows']),6)
            for i,pair in enumerate(r['rows']):
                self.assertEqual(pair['arm_order'],['TOKEN','SCHEMA'] if i%2==0 else ['SCHEMA','TOKEN'])
                for arm in pair['arms']:
                    self.assertEqual(arm['cli']['status'],'SHADOW_DRAFT_PREFLIGHT_READY')
                    self.assertEqual(arm['store_audit']['live_output_count'],0)
                    self.assertEqual(arm['store_audit']['action_kinds'],['TEXT_REPORT'])

    def test_schema_wrong_action_is_red_without_draft(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);row=ba.rows()[0];home=root/'home'
            ba.initialize(home)
            p=root/'input.json'
            p.write_text(json.dumps({'project':row['id'],'domain':row['domain'],
                 'policy_source':row['policy_source'],'sheet_source':row['sheet_source'],
                 'current':row['current']}))
            r=ba.cli.run(home,p,'synthetic_schema_wrong',operator_opt_in=True,
                         callback_opt_in=True,route_shadow=True)
            self.assertEqual(r['status'],'DRAFT_STAGE_RED')
            self.assertEqual(r['schema_formatter_status'],'SCHEMA_REJECTED_OR_SOURCE_RED')
            audit=ba.az._audit_home(home,row['oracle_action'])
            self.assertEqual(audit['assistant_messages'],0)
            self.assertEqual(audit['action_kinds'],[])

    def test_missing_native_install_red_and_no_calls(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertFalse(ba.run(root/'work',root/'missing',root/'raw',native=True))
            r=json.loads((root/'raw/report.json').read_text())
            self.assertEqual(r['native_c3_calls'],0)
            self.assertEqual(r['status'],'STRUCTURAL_RED_NO_PROMOTION')

if __name__=='__main__':unittest.main()
