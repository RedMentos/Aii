"""WP-Z2g runner: fresh changed-rule episodes and the paired guard off/on re-decision."""
import importlib.util
import json
from pathlib import Path
import unittest
from v13.agi import eligibility as E
ROOT=Path(__file__).resolve().parents[1]

def load():
    spec=importlib.util.spec_from_file_location('step2_z2g_test_copy',ROOT/'scripts/step2_z2g_recency.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class Z2g(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.z=load()
    def opts(self,f):return [{k:o[k] for k in ('entity','cost','days','local')} for o in f['oracle']['options']]
    def test_fresh_names_and_types(self):
        ids=[f['id'] for f in self.z.FIXTURES]
        self.assertEqual(len(set(ids)),10);self.assertFalse(set(ids)&{'Altair','Electra','Hadar','Izar','Jabbah'})
        self.assertEqual([f['type'] for f in self.z.FIXTURES].count('REVISED'),6)
        self.assertEqual(self.z.SEEDS,(26,27,28));self.assertEqual(set(self.z.ARMS),{'CQ','CQP'})
    def test_every_superseded_value_changes_the_action(self):
        for f in self.z.FIXTURES:
            if f['type']=='CONFIRM':self.assertIsNone(f['superseded']);continue
            for rule,values in f['superseded_all'].items():
                for v in values:
                    stale=f['rules']|{rule:v}
                    self.assertNotEqual(E.recipe(stale['budget'],stale['deadline'],stale['local_only'],self.opts(f))[0],f['oracle']['action'],(f['id'],rule,v))
    def test_guard_on_oracle_quotes(self):
        """Quoting every session source: guard on gives the oracle; quoting only the kickoff gives UNKNOWN (except CONFIRM)."""
        for f in self.z.FIXTURES:
            h=self.z.history_of(f);old=dict(zip(self.z.KEYS,next(x[2] for x in self.z.EPISODES if x[0]==f['id'])))
            self.assertEqual(E.decide(f['rules'],self.opts(f),f['current'],f['history'],history=h)['action'],f['oracle']['action'],f['id'])
            d=E.decide(old,self.opts(f),f['current'],[f['history'][0],f['history'][-1]],history=h)['action']
            self.assertEqual(d,f['oracle']['action'] if f['type']=='CONFIRM' else 'UNKNOWN',f['id'])
            self.assertTrue(all(len(x)<=self.z.EXCERPT for x in f['history'][:-1]))
    def test_redecide_consistency_and_gate(self):
        z=self.z;f=z.FIX['Kochab'];stale={'budget':70,'deadline':5,'local_only':True}
        msg=[{'role':'user','content':json.dumps({'current_source':f['current'],'analysts':[{'role':'B2_GIST','verified_quotes':[f['history'][0],f['history'][-1]]}]})}]
        ex={'project':'Kochab',**stale,'options':self.opts(f)}
        tool={'rows':[{'fixture':'Kochab','variant':'both_exact','answer':json.dumps({'action':'NONE'}),'tool':{'extracted':ex}}]}
        report={'rows':[{'fixture':'Kochab','variant':'both_exact','consumer_messages':msg}]}
        p=z.redecide(report,tool)[0]
        self.assertEqual((p['recorded'],p['off'],p['on'],p['oracle']),('NONE','NONE','UNKNOWN','B'));self.assertEqual(p['superseded_rejections'],['budget:superseded'])
        self.assertEqual(z.gate({})['status'],'INCOMPLETE')
    def test_tool_entry_history(self):
        f=self.z.FIX['Merak'];o=self.opts(f);old=self.z.EPISODES[2][2]
        args=dict(current=f['current'],a_cost=o[0]['cost'],a_days=o[0]['days'],a_local=o[0]['local'],b_cost=o[1]['cost'],b_days=o[1]['days'],b_local=o[1]['local'],
                  quotes='\n'.join([f['history'][0],f['history'][-1]]),budget=old[0],deadline=old[1],local_only=old[2])
        self.assertNotEqual(E.tool(**args)['action'],'UNKNOWN')
        self.assertEqual(E.tool(**args,history='\n'.join(self.z.history_of(f)))['action'],'UNKNOWN')

if __name__=='__main__':unittest.main()
