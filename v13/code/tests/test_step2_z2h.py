"""WP-Z2h runner: fresh episodes, slot settings per arm, guarded re-decision reused from WP-Z2g."""
import importlib.util
from pathlib import Path
import unittest
from v13.agi import eligibility as E
ROOT=Path(__file__).resolve().parents[1]

def load():
    spec=importlib.util.spec_from_file_location('step2_z2h_test_copy',ROOT/'scripts/step2_z2h_slots.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class Z2h(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.z=load()
    def opts(self,f):return [{k:o[k] for k in ('entity','cost','days','local')} for o in f['oracle']['options']]
    def test_fresh_and_settings(self):
        z=self.z;ids=[f['id'] for f in z.FIXTURES];used={x[0] for x in z.g.EPISODES}|{x[0] for x in z.z.EPISODES}
        self.assertEqual(len(set(ids)),10);self.assertFalse(set(ids)&used)
        self.assertEqual(z.SEEDS,(29,30,31))
        for arm,n in (('P2',2),('P4',4)):
            s=z.z.z2b.settings(arm,29);self.assertEqual((s['b2_quote_select'],s['b2_quote_slots'],s['b2_context_chars'],s['seed']),('pointer',n,1536,29))
        from v13.config import validate,DEFAULTS
        validate(DEFAULTS|{k:v for k,v in z.z.z2b.settings('P4',29).items() if k in DEFAULTS})
    def test_superseded_values_change_action_and_guard_on_oracle(self):
        for f in self.z.FIXTURES:
            for rule,values in f['superseded_all'].items():
                for v in values:
                    st=f['rules']|{rule:v};self.assertNotEqual(E.recipe(st['budget'],st['deadline'],st['local_only'],self.opts(f))[0],f['oracle']['action'],f['id'])
            h=self.z.g.history_of(f)
            self.assertEqual(E.decide(f['rules'],self.opts(f),f['current'],f['history'],history=h)['action'],f['oracle']['action'],f['id'])
    def test_long_rules_are_separate_sentences(self):
        f=self.z.FIX['Wezen'];self.assertEqual(f['type'],'LONG');self.assertLessEqual(len(f['history'][0]),240)
        self.assertTrue(f['history'][0].endswith('Budget 95 euros. Deadline 4 days. Local-only requirement: true.'))
    def test_gate_incomplete(self):self.assertEqual(self.z.gate({})['status'],'INCOMPLETE')

if __name__=='__main__':unittest.main()
