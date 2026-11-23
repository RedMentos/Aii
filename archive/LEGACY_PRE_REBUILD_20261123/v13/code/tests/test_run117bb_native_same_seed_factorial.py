"""Run117BB frozen 2x2 native candidate and model-free 24-arm controls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import run117bb_native_same_seed_factorial as bb

class Run117BBFactorial(unittest.TestCase):
    def test_frozen_new_validation_disjoint_from_ba_and_az(self):
        rows=bb.rows()
        self.assertEqual(tuple(r['id'] for r in rows),bb.IDS)
        self.assertEqual(tuple(r['oracle_action'] for r in rows),bb.ACTIONS)
        self.assertFalse(set(bb.IDS)&set(bb.az.IDS))
        from scripts import run117ba_native_schema_paired as ba
        self.assertFalse(set(bb.IDS)&set(ba.IDS))

    def test_mutated_source_fails_closed(self):
        r=bb.p2x.fixtures()
        for x in r:
            if x['id']==bb.IDS[0]:x['current']+=' corrupted'
        with patch.object(bb.p2x,'fixtures',return_value=r):
            with self.assertRaises((ValueError,AssertionError)):bb.rows()

    def test_real_24_synthetic_drafts_four_arms_balanced(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertTrue(bb.run(root/'work',None,root/'raw'))
            r=json.loads((root/'raw/report.json').read_text())
            self.assertEqual(r['status'],'STRUCTURAL_GREEN_NO_PROMOTION')
            self.assertEqual(r['native_c3_calls'],0)
            self.assertEqual(r['strict_scores'],{f'{kind}_S{seed}':6 for kind,seed in bb.ARMS})
            self.assertEqual(len(r['rows']),6)
            for i,pair in enumerate(r['rows']):
                self.assertEqual(pair['arm_order'],[f'{kind}_S{seed}' for kind,seed in bb.ARMS[i%4:]+bb.ARMS[:i%4]])
                for a in pair['arms']:
                    self.assertEqual(a['cli']['status'],'SHADOW_DRAFT_PREFLIGHT_READY')
                    self.assertEqual(a['store_audit']['live_output_count'],0)
                    self.assertEqual(a['store_audit']['action_kinds'],['TEXT_REPORT'])

    def test_missing_native_binding_no_calls(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertFalse(bb.run(root/'work',root/'missing',root/'raw',native=True))
            r=json.loads((root/'raw/report.json').read_text())
            self.assertEqual(r['native_c3_calls'],0)
            self.assertEqual(r['status'],'STRUCTURAL_RED_NO_PROMOTION')

if __name__=='__main__':unittest.main()
