"""WP-Z2l runner: whole chain, two bodies vs shared body, chain rescoring."""
import importlib.util
import json
from pathlib import Path
import unittest
from v13.agi import eligibility as E
ROOT=Path(__file__).resolve().parents[1]

def load():
    spec=importlib.util.spec_from_file_location('step2_z2l_test_copy',ROOT/'scripts/step2_z2l_chain.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class Z2l(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.z=load()
    def opts(self,f):return [{k:o[k] for k in ('entity','cost','days','local')} for o in f['oracle']['options']]
    def test_fresh_and_settings(self):
        z=self.z;ids={f['id'] for f in z.FIXTURES}
        import step2_z2j_sources as j, step2_z2k_reader as k
        used={x[0] for m in (z.i,z.h,z.g,z.z,j,k) for x in m.EPISODES}
        self.assertEqual(len(ids),10);self.assertFalse(ids&used);self.assertEqual(z.SEEDS,(41,42,43))
        c=z.z.z2b.settings('CS',41);d=z.z.z2b.settings('DS',41)
        for s in (c,d):self.assertEqual((s['b2_quote_select'],s['b2_quote_choices'],s['b2_quote_slots'],s['b2_context_chars']),('pointer','sources',4,1536))
        self.assertNotEqual(c,d)  # two bodies vs shared body differ only in the Z2 base
    def test_episodes(self):
        for f in self.z.FIXTURES:
            for rule,values in f['superseded_all'].items():
                for v in values:
                    st=f['rules']|{rule:v};self.assertNotEqual(E.recipe(st['budget'],st['deadline'],st['local_only'],self.opts(f))[0],f['oracle']['action'],f['id'])
    def test_chain_rescoring(self):
        z=self.z;f=z.FIX['Baten'];old={'budget':90,'deadline':5,'local_only':False}
        msg=[{'role':'user','content':json.dumps({'current_source':f['current'],'analysts':[{'role':'B2_GIST','verified_quotes':f['history']}]})}]
        tool={'rows':[{'fixture':'Baten','variant':'both_exact','answer':json.dumps({'action':'B'}),'score':{'utility':0.},'tool':{'extracted':{'project':'Baten',**old,'options':self.opts(f)}}}]}
        r=z.chain_rows({'rows':[{'fixture':'Baten','variant':'both_exact','consumer_messages':msg}]},tool)[0]
        self.assertEqual((r['action'],r['oracle']),('NONE','NONE'));self.assertGreater(r['utility'],.9)
        self.assertEqual(z.gate({})['status'],'INCOMPLETE')

if __name__=='__main__':unittest.main()
