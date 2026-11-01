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
    def test_selector_learns_from_feedback(self):
        sch=[{'steps':[{'tool':'calc','args':{'expression':'{n0} + {n1}'}}],'support':2,'trigger':['total'],'stage':'SCHEMA'},
             {'steps':[{'tool':'calc','args':{'expression':'{n0} - {n1}'}}],'support':2,'trigger':['sum'],'stage':'SCHEMA'}]
        sel=sc.Selector(sch);t='left over from 9 and 4';i=sel.choose(t)
        for _ in range(3):sel.feedback(0,t,True);sel.feedback(1,t,False)
        self.assertEqual(sel.choose(t),0)
if __name__=='__main__':unittest.main()

import tempfile
from pathlib import Path
from v13.runtime import Runtime
from v13.agi import hub
class Lib(unittest.TestCase):
    def test_skill_library_integration(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                hub(r).tools.enable('calc');lib=hub(r).skills;ep=[{'text':'Items cost 10, 20, 30.','steps':[{'tool':'calc','args':{'expression':'10 + 20 + 30'}}]},
                    {'text':'Items cost 5, 6.','steps':[{'tool':'calc','args':{'expression':'5 + 6'}}]},
                    {'text':'Stock 1, 2.','steps':[{'tool':'calc','args':{'expression':'1 - 2'}}]}]
                names=lib.propose_from_episodes('sch',ep);self.assertEqual(len(names),1)
                res=lib.run_text('The bill lists 7, 8, 9, 4.')
                self.assertEqual(res['status'],'DONE');self.assertEqual(float(res['value']),28.)
                lib.record_text(res,True);self.assertIn('sch_0:shape4',lib.report()['families'])
            finally:r.close()

from v13 import skill_consolidation as scon
class Episodes(unittest.TestCase):
    def test_sleep_source_shadow_then_active(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                reg=hub(r).tools;reg.enable('calc');sid=r.store.new_session()
                for text,ex in [('Items cost 10, 20, 30.','10 + 20 + 30'),('Items cost 5, 6.','5 + 6'),('mail me a@b.de, 5, 6','5 + 6')]:
                    e=r.store.event(sid,text);reg.call('calc',{'expression':ex},event_id=e['event_id'])
                rep=scon.run(r);self.assertEqual((rep['mode'],rep['episodes'],rep['schemas'],rep['proposed']),('shadow',2,1,[]))
                r.cfg['skill_schema_mode']='active';rep=scon.run(r);self.assertEqual(len(rep['proposed']),1)
                self.assertEqual(scon.run(r)['proposed'],[])
                self.assertEqual(hub(r).skills.run_text('Sum 1, 2, 3, 4')['value'],10)
            finally:r.close()
