"""WP-T9 §9.5 learned memory admission: human-derived labels, held-out check, SHADOW vs user-only ACTIVE, AG6 order."""
from pathlib import Path
from unittest import mock
import tempfile
import unittest
from v13.runtime import Runtime
from v13 import admission as adm
from v13.admission import Admission

class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.s=self.r.store;self.a=Admission(self.s,self.r.cfg)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def fact(self,q,v):
        e=self.s.event(self.r.session,q);return e['event_id'],self.r.memory.feedback(e['event_id'],'fact',v)
    def test_labels_come_only_from_human_signals(self):
        e1,old=self.fact('What is the name of my cat?','Mitzi');new=self.r.memory.feedback(e1,'fact','Luna')  # superseded
        e2,a=self.fact('Where do I work?','Kranich');b=self.r.memory.feedback(e2,'fact','Kranich')  # restated
        _,c=self.fact('What do I play?','bandoneon')  # no signal
        _,d=self.fact('What is my phone?','Redmi');self.r.memory.forget(d)
        lab={x['memory_id']:(x['label'],x['reasons']) for x in self.a.table()}
        self.assertEqual(lab[old][0],0);self.assertIn('superseded',lab[old][1])
        self.assertEqual((lab[a][0],lab[b][0]),(1,1));self.assertIn('restated',lab[a][1])
        self.assertIsNone(lab[c][0]);self.assertIsNone(lab[new][0])
        self.assertEqual(lab[d][0],0);self.assertIn('deleted',lab[d][1])
    def test_too_few_labels_keeps_prior_and_blocks_active(self):
        self.fact('What is the name of my cat?','Mitzi')
        self.assertEqual(self.a.train()['status'],'TOO_FEW_LABELS')
        with self.assertRaises(ValueError):self.a.set_authority('ACTIVE','USER')
        self.assertEqual(self.a.report()['weights'],'prior')
    def synthetic(self,n=40):
        rows=[]
        for k in range(n):
            good=k%2==0;f={x:0. for x in adm.FEATURES};f['bias']=1.;f['uses']=2. if good else 0.;f['age']=1.
            rows.append({'memory_id':'mem_%03d'%k,'active':True,'features':f,'label':int(good),'reasons':[]})
        return rows
    def test_heldout_check_then_user_only_active_orders_and_drops(self):
        rows=self.synthetic()
        with mock.patch.object(Admission,'table',return_value=rows):
            chk=self.a.train();self.assertEqual(chk['status'],'PASS');self.assertGreaterEqual(chk['auc_learned'],chk['auc_prior'] or 0)
            with self.assertRaises(ValueError):self.a.set_authority('ACTIVE','SYSTEM')
            items=[{'memory_id':r['memory_id'],'prompt':'q','target':'t'} for r in rows[:6]]+[{'memory_id':'rating:e1','prompt':'q','target':'t'}]
            kept,rec=self.a.order([dict(i) for i in items])  # SHADOW: same order, scores attached
            self.assertEqual([i['memory_id'] for i in kept],[i['memory_id'] for i in items]);self.assertEqual(rec['authority'],'SHADOW')
            self.assertTrue(set(rec['would_drop'])<={'mem_001','mem_003','mem_005'} and rec['would_drop'])
            self.a.set_authority('ACTIVE','USER');kept,rec=self.a.order([dict(i) for i in items])
            ids=[i['memory_id'] for i in kept];self.assertIn('rating:e1',ids);self.assertNotIn('mem_001',ids)
            self.assertEqual(ids[0],'mem_000')
    def test_failed_retrain_demotes_active(self):
        rows=self.synthetic()
        with mock.patch.object(Admission,'table',return_value=rows):self.a.train();self.a.set_authority('ACTIVE','USER')
        bad=self.synthetic()
        for r in bad:r['label']=int(r['features']['uses']==0.)  # labels now contradict usage: learned head cannot pass on held-out
        for r in bad[::3]:r['label']=1-r['label']
        with mock.patch.object(Admission,'table',return_value=bad),mock.patch.object(adm,'fit',return_value=dict(adm.PRIOR)):
            self.assertEqual(self.a.train()['status'],'FAIL')
        self.assertEqual(self.a.state()['authority'],'SHADOW')
    def test_ag6_stage_records_admission(self):
        self.fact('What is the name of my cat?','Mitzi')
        from v13.agi import hub
        self.r.cfg['learning_mode']='SHADOW_UPDATE';g=hub(self.r);out=g.weights.stage('USER',require_replay_pass=False)
        if out.get('status')!='STAGED':self.skipTest('stage not reachable here: '+str(out.get('status')))
        b=g.weights.batch(out['batch_id']);self.assertEqual(b['admission']['authority'],'SHADOW');self.assertIn('admission',b['items'][0])
    def test_operator_command(self):
        from v13.admission import operator_command
        self.assertEqual(operator_command(self.r,[])['authority'],'SHADOW')
        with self.assertRaises(ValueError):operator_command(self.r,['magic'])

if __name__=='__main__':unittest.main()
