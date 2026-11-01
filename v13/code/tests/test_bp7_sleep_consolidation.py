"""WP-BP7: Sleep-D checklist (FS6) and retrieval reconsolidation (FS8). Synthetic software tests, no model."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from v13.runtime import Runtime
from v13.ssgm import Checklist,private_hits,value_leaks,spans_missing
from v13.reconsolidation import Reconsolidation,DAY
from v13.agi.weights import WeightConsolidation

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off')
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def fact(self,q,v,kind='fact'):
        e=self.r.store.event(self.r.session,q);fid=self.r.memory.feedback(e['event_id'],kind,v,'learn');return e['event_id']
    def mem(self,key_part):
        return next(m for m in self.r.store.rows("SELECT * FROM memories WHERE active=1") if key_part in m['key_text'])

class Checks(Base):
    def test_private_patterns(self):
        for t,name in (('mail me at anna.k@example.org','email'),('Tel +49 170 1234567','phone'),('DE89 3704 0044 0532 0130 00','iban'),('passwort: hunter2','secret_word'),('sk-abcdef1234567890','key')):
            self.assertIn(name,private_hits(t),t)
        self.assertEqual(private_hits('Projekt Aurora hat 120 Euro Budget'),[])
    def test_private_fact_never_reaches_weight_batch(self):
        self.fact('Projekt Aurora Budget?','120 Euro');self.fact('Kontakt Aurora Mail?','anna.k@example.org')
        items=[{'memory_id':self.mem('Aurora Budget')['id'],'kind':'fact','prompt':'Projekt Aurora Budget?','target':'120 Euro'},
               {'memory_id':self.mem('Kontakt')['id'],'kind':'fact','prompt':'Kontakt Aurora Mail?','target':'anna.k@example.org'}]
        kept,rep=Checklist(self.r.store,{'sleep_d_checklist':'active'}).run(items)
        self.assertEqual([i['target'] for i in kept],['120 Euro']);self.assertEqual(rep['by_check']['PRIVATE'],1)
        self.assertNotIn('anna.k',json.dumps(rep))  # report does not copy the private string
    def test_shadow_reports_but_keeps_and_off_skips(self):
        items=[{'kind':'fact','prompt':'x?','target':'mail a@b.de'}]
        kept,rep=Checklist(self.r.store,{}).run(items,mode='shadow');self.assertEqual(len(kept),1);self.assertEqual(rep['hard_failures'],1);self.assertEqual(rep['dropped'],0)
        kept,rep=Checklist(self.r.store,{}).run(items,mode='off');self.assertEqual((len(kept),rep['checked']),(1,0))
    def test_dream_fact_leak_and_policy_only(self):
        self.fact('Projekt Aurora Budget?','120 Euro')
        leak={'kind':'dream_para','origin':'dream','prompt':'Wie hoch ist das Budget?','target':'Das Budget ist 120 Euro'}
        policy={'kind':'dream_policy','origin':'dream','prompt':'Du bist unsicher. Was tust du?','target':'Quelle nennen oder nachfragen, nichts erfinden'}
        kept,rep=Checklist(self.r.store,{}).run([leak,policy],mode='active')
        self.assertEqual(kept,[policy]);self.assertEqual(rep['by_check'].get('FACT_LEAK'),1)
    def test_dream_as_fact_target_dropped(self):
        kept,rep=Checklist(self.r.store,{}).run([{'kind':'fact','origin':'dream','prompt':'p?','target':'t'}],mode='active')
        self.assertEqual(kept,[]);self.assertEqual(rep['by_check']['DREAM_AS_FACT'],1)
    def test_superseded_memory_is_conflict(self):
        self.fact('Projekt Aurora Budget?','120 Euro');old=self.mem('Aurora Budget');time.sleep(.01)
        self.fact('Projekt Aurora Budget?','90 Euro')
        it={'memory_id':old['id'],'kind':'fact','prompt':'Projekt Aurora Budget?','target':'120 Euro'}
        kept,rep=Checklist(self.r.store,{}).run([it],mode='active');self.assertEqual(kept,[]);self.assertEqual(rep['by_check']['CONFLICT'],1)
    def test_batch_disagreement_and_summary_drift(self):
        a={'kind':'fact','prompt':'Budget?','target':'120'};b={'kind':'fact','prompt':'Budget?','target':'90'}
        kept,rep=Checklist(self.r.store,{}).run([a,b],mode='active');self.assertEqual(kept,[])
        self.assertEqual(spans_missing('Budget 120 und 77','Budget 120'),['77'])
        d={'kind':'ttt','origin':'self','prompt':'p','target':'t','summary_depth':2}
        kept,rep=Checklist(self.r.store,{}).run([d],mode='active');self.assertEqual(kept,[])
    def test_aged_is_soft(self):
        self.fact('Projekt Aurora Budget?','120 Euro');m=self.mem('Aurora Budget')
        it={'memory_id':m['id'],'kind':'fact','prompt':'Projekt Aurora Budget?','target':'120 Euro'}
        c=Checklist(self.r.store,{},clock=lambda:time.time()+400*DAY)
        kept,rep=c.run([it],mode='active');self.assertEqual(len(kept),1);self.assertEqual(rep['by_check']['AGED'],1)
    def test_stage_uses_checklist_and_invalid_mode_rejected(self):
        self.r.cfg['learning_mode']='SHADOW_UPDATE'
        self.fact('Projekt Aurora Budget?','120 Euro');self.fact('Kontakt Aurora Mail?','anna.k@example.org')
        out=WeightConsolidation(self.r.store,self.r.cfg,age=None).stage(origin='USER',require_replay_pass=False)
        self.assertEqual(out['status'],'STAGED');self.assertEqual(out['sleep_d']['by_check'],{'PRIVATE':1})
        b=WeightConsolidation(self.r.store,self.r.cfg).batch(out['batch_id']);self.assertEqual([i['target'] for i in b['items']],['120 Euro'])
        with self.assertRaises(ValueError):Checklist(self.r.store,{'sleep_d_checklist':'maybe'}).mode()

class Recon(Base):
    def verdict(self,eid,mid,label):
        self.r.memory.retrieval_feedback(eid,mid,label)
    def test_weights_move_but_value_never_and_default_order_unchanged(self):
        self.fact('Projekt Aurora Budget?','120 Euro');self.fact('Projekt Borealis Budget?','80 Euro')
        a=self.mem('Aurora');b=self.mem('Borealis');q=self.r.store.event(self.r.session,'Projekt Aurora Budget Info?')['event_id']
        before=self.r.store.rows('SELECT id,key_text,value,active FROM memories')
        for _ in range(3):self.verdict(q,a['id'],'relevant')
        for _ in range(3):self.verdict(q,b['id'],'irrelevant')
        rc=Reconsolidation(self.r.store,self.r.cfg);rep=rc.sleep();self.assertEqual(rep['new_outcomes'],6);self.assertEqual(rep['fact_write_authority'],0)
        w=rc.weights();self.assertGreater(w[a['id']],1.);self.assertLess(w[b['id']],1.)
        self.assertEqual(before,self.r.store.rows('SELECT id,key_text,value,active FROM memories'))
        self.assertEqual(rc.sleep()['new_outcomes'],0)  # idempotent
        self.assertEqual([x['memory_id'] for x in rc.review_list()],[b['id']])
    def test_decay_and_modes(self):
        self.fact('Projekt Aurora Budget?','120 Euro');a=self.mem('Aurora');q=self.r.store.event(self.r.session,'Projekt Aurora Budget Info?')['event_id']
        for _ in range(4):self.verdict(q,a['id'],'irrelevant')
        rc=Reconsolidation(self.r.store,self.r.cfg);rc.update()
        w_now=rc.weights()[a['id']];w_later=rc.weights(time.time()+120*DAY)[a['id']]
        self.assertLess(w_now,w_later);self.assertLess(w_later,1.)
        self.r.cfg['reconsolidation']='off';self.assertEqual(rc.sleep(),{'status':'OFF'})
        with self.assertRaises(ValueError):Reconsolidation(self.r.store,{'reconsolidation':'x'}).mode()
    def test_active_mode_reorders_recall_only_by_weight(self):
        self.fact('Projekt Aurora Budget Plan?','120 Euro');self.fact('Projekt Aurora Budget Notiz?','80 Euro')
        a=self.mem('Plan');b=self.mem('Notiz');q=self.r.store.event(self.r.session,'Projekt Aurora Budget?')['event_id']
        for _ in range(5):self.verdict(q,a['id'],'irrelevant');self.verdict(q,b['id'],'relevant')
        Reconsolidation(self.r.store,self.r.cfg).sleep()
        self.r.cfg['memory_threshold']=.1;self.r.cfg['reconsolidation']='shadow'
        base=[m['id'] for m in self.r.memory.recall('Projekt Aurora Budget',self.r.session,top_k=8)]
        self.r.cfg['reconsolidation']='active'
        act=self.r.memory.recall('Projekt Aurora Budget',self.r.session,top_k=8)
        self.assertEqual(set(base),{m['id'] for m in act});self.assertEqual(act[0]['id'],b['id'])
    def test_sleep_c_reports_reconsolidation(self):
        rep=self.r.sleep.cycle.run('c',origin='USER')['phases'][0];self.assertEqual(rep['reconsolidation']['status'],'DONE')
if __name__=='__main__':unittest.main()
