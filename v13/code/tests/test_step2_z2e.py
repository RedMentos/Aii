"""WP-Z2e harder episodes for the B2 quote pointer: fixture shape, arms, private module copies."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
import step2_z2e_pointer_hard as z
from v13.agi.eligibility import recipe,stated
from v13.cognition import quote_span

class Fixtures(unittest.TestCase):
    def test_long_rule_note_fits_b2_excerpt_but_not_one_widened_header(self):
        for f in z.FIXTURES:
            if f['type']!='LONG':continue
            note=f['history'][0];self.assertLessEqual(len(note),z.z2.B2_EXCERPT_CHARS)
            self.assertTrue(all(stated(k,v,note) for k,v in f['rules'].items()))
            header=note[:note.index('.')+1];w=note[slice(*quote_span(header,note,200))]
            self.assertFalse(all(stated(k,v,w) for k,v in f['rules'].items()))
    def test_every_revision_changes_the_action(self):
        rev=[f for f in z.FIXTURES if f['type']=='REVISED'];self.assertEqual(len(rev),4)
        for f in rev:
            old=dict(f['rules'])|f['superseded'];opts=[{k:o[k] for k in ('entity','cost','days','local')} for o in f['oracle']['options']]
            self.assertNotEqual(recipe(old['budget'],old['deadline'],old['local_only'],opts)[0],f['oracle']['action'])
            (k,v),=f['superseded'].items();self.assertTrue(stated(k,f['rules'][k],f['history'][1]));self.assertTrue(stated(k,v,f['history'][0]))
    def test_arms_and_isolation(self):
        self.assertEqual(z.settings('CQ',20),z.z2.ARMS['C']|{'seed':20})
        self.assertEqual(z.settings('DQP',21)['b2_control'],'shared_body_dual_state');self.assertEqual(z.settings('CQP',22)['b2_quote_select'],'pointer')
        import step2_z2_timescale as shared, step2_z2b_seeds as shared_b
        self.assertIsNot(shared.FIXTURES,z.FIXTURES);self.assertEqual(shared_b.SEEDS,(14,15,16));self.assertIs(z.z2b.z2,z.z2)
        self.assertEqual(len(z.HARD),8);self.assertEqual(z.gate({})['status'],'INCOMPLETE')

if __name__=='__main__':unittest.main()
