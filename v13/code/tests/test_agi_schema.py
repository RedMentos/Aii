import unittest
from v13.agi import schema as sc
EP=[{'text':'Items cost 10, 20, 30.','steps':[{'tool':'calc','args':{'expression':'10 + 20 + 30'}}]},
    {'text':'Items cost 5, 6.','steps':[{'tool':'calc','args':{'expression':'5 + 6'}}]},
    {'text':'Items cost 1, 2.','steps':[{'tool':'calc','args':{'expression':'1 - 2'}}]}]
class T(unittest.TestCase):
    def test_induce_merges_and_transports(self):
        s=sc.induce(EP);self.assertEqual(sorted(x['support'] for x in s),[1,2]);g=[x for x in s if x['stage']=='SCHEMA'][0]
        self.assertEqual(sc.instantiate(g,'Items cost 7, 8, 9, 4.')[0]['args']['expression'],'7 + 8 + 9 + 4')
    def test_single_episode_stays_candidate(self):self.assertEqual(sc.induce(EP[:1])[0]['stage'],'CANDIDATE')
    def test_missing_slot_returns_none(self):
        s=sc.induce([EP[1],EP[1]]);self.assertIsNotNone(sc.instantiate(s[0],'a 1 2'))
        s=sc.induce([{'text':'x 1 2','steps':[{'tool':'calc','args':{'expression':'1 - 2 + 1'}}]}]*2);self.assertIsNone(sc.instantiate(s[0],'x 5'))
if __name__=='__main__':unittest.main()
