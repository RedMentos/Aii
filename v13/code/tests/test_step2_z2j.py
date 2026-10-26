"""WP-Z2j runner: fresh episodes, arms all / earlier_oldest / sources."""
import importlib.util
from pathlib import Path
import unittest
from v13.agi import eligibility as E
ROOT=Path(__file__).resolve().parents[1]

def load():
    spec=importlib.util.spec_from_file_location('step2_z2j_test_copy',ROOT/'scripts/step2_z2j_sources.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class Z2j(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.z=load()
    def opts(self,f):return [{k:o[k] for k in ('entity','cost','days','local')} for o in f['oracle']['options']]
    def test_fresh_and_settings(self):
        z=self.z;ids={f['id'] for f in z.FIXTURES}
        used={x[0] for m in (z.i,z.h,z.g,z.z) for x in m.EPISODES}
        self.assertEqual(len(ids),10);self.assertFalse(ids&used);self.assertEqual(z.SEEDS,(35,36,37))
        from v13.config import validate,DEFAULTS
        for arm,c in (('A4','all'),('O4','earlier_oldest'),('S4','sources')):
            s=z.z.z2b.settings(arm,35);self.assertEqual((s['b2_quote_select'],s['b2_quote_slots'],s['b2_quote_choices'],s['b2_context_chars'],s['seed']),('pointer',4,c,1536,35))
            validate(DEFAULTS|{k:v for k,v in s.items() if k in DEFAULTS})
        self.assertEqual(z.i.CANDIDATES,('O4','S4'))
    def test_superseded_change_action_guard_gives_oracle(self):
        for f in self.z.FIXTURES:
            for rule,values in f['superseded_all'].items():
                for v in values:
                    st=f['rules']|{rule:v};self.assertNotEqual(E.recipe(st['budget'],st['deadline'],st['local_only'],self.opts(f))[0],f['oracle']['action'],f['id'])
            self.assertEqual(E.decide(f['rules'],self.opts(f),f['current'],f['history'],history=self.z.g.history_of(f))['action'],f['oracle']['action'],f['id'])
    def test_whole_source_quotes_are_classified(self):
        f=self.z.FIX['Alcor'];rep={'rows':[{'fixture':'Alcor','variant':'both_exact','offers':[{'role':'B2_GIST','offer':{'quotes':[f['history'][0],f['history'][1],f['history'][2][:240]]}}]}]}
        self.assertEqual(self.z.i.picked_kinds(rep),{'current':0,'kickoff':1,'note':1,'sheet':1,'other':0})
        self.assertEqual(self.z.i.gate({})['status'],'INCOMPLETE')

if __name__=='__main__':unittest.main()
