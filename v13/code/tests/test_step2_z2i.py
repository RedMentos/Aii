"""WP-Z2i runner: fresh episodes, choice-list setting per arm, pick-source counting."""
import importlib.util
from pathlib import Path
import unittest
from v13.agi import eligibility as E
ROOT=Path(__file__).resolve().parents[1]

def load():
    spec=importlib.util.spec_from_file_location('step2_z2i_test_copy',ROOT/'scripts/step2_z2i_choices.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class Z2i(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.z=load()
    def opts(self,f):return [{k:o[k] for k in ('entity','cost','days','local')} for o in f['oracle']['options']]
    def test_fresh_and_settings(self):
        z=self.z;ids={f['id'] for f in z.FIXTURES};used={x[0] for x in z.h.EPISODES}|{x[0] for x in z.g.EPISODES}|{x[0] for x in z.z.EPISODES}
        self.assertEqual(len(ids),10);self.assertFalse(ids&used);self.assertEqual(z.SEEDS,(32,33,34))
        from v13.config import validate,DEFAULTS
        for arm,c in (('A4','all'),('E4','earlier'),('N4','earlier_newest')):
            s=z.z.z2b.settings(arm,32);self.assertEqual((s['b2_quote_select'],s['b2_quote_slots'],s['b2_quote_choices'],s['b2_context_chars']),('pointer',4,c,1536))
            validate(DEFAULTS|{k:v for k,v in s.items() if k in DEFAULTS})
    def test_superseded_change_action_guard_gives_oracle(self):
        for f in self.z.FIXTURES:
            for rule,values in f['superseded_all'].items():
                for v in values:
                    st=f['rules']|{rule:v};self.assertNotEqual(E.recipe(st['budget'],st['deadline'],st['local_only'],self.opts(f))[0],f['oracle']['action'],f['id'])
            self.assertEqual(E.decide(f['rules'],self.opts(f),f['current'],f['history'],history=self.z.g.history_of(f))['action'],f['oracle']['action'],f['id'])
    def test_picked_kinds(self):
        f=self.z.FIX['Hamal'];q=[f['history'][0].split('. ')[1]+'.',f['history'][1].split('. ')[2]+'.','Project Hamal.']
        rep={'rows':[{'fixture':'Hamal','variant':'both_exact','offers':[{'role':'B2_GIST','offer':{'quotes':q}}]},
                     {'fixture':'Hamal','variant':'prompt_only_dual','offers':[{'role':'B2_GIST','offer':{'quotes':['Project Hamal.']}}]}]}
        self.assertEqual(self.z.picked_kinds(rep),{'current':1,'kickoff':1,'note':1,'sheet':0,'other':0})
        self.assertEqual(self.z.gate({})['status'],'INCOMPLETE')

if __name__=='__main__':unittest.main()
