"""WP-AG1..AG12 growth infrastructure (v13/agi). No models needed."""
from pathlib import Path
import tempfile
import time
import unittest
from v13.runtime import Runtime
from v13.age import AgeControl
from v13.scheduler import EventScheduler
from v13.agi import hub,job
from v13.agi.generality import GeneralityEval,build_suite,oracle_solver,null_solver,calibration
from v13.agi.weights import WeightConsolidation
from v13.agi.metacog import Metacognition,semantic_entropy
from v13.agi.goals import GoalStore
from v13.agi.curiosity import Curiosity
from v13.agi.tools import ToolRegistry,ToolSpec,calc
from v13.agi.grounding import Grounding
from v13.agi.skills import SkillLibrary
from v13.agi.abstraction import Abstraction,dsl_inducer
from v13.agi.self_improve import SelfImprovement
from v13.agi.teacher import TeacherDistillation
from v13.agi.user_model import UserModel

class Clock:
    def __init__(self,t=1_700_000_000.):self.t=t
    def __call__(self):return self.t

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.r.sleep.cycle.set_policy('tick_seconds','300')
        self.s=self.r.store;self.age=AgeControl(self.s,self.r.cfg)
    def tearDown(self):self.r.close();self.tmp.cleanup()

class G12Eval(Base):
    def test_suite_is_deterministic_and_answers_are_correct(self):
        a,b=build_suite(13),build_suite(13)
        self.assertEqual(a['hash'],b['hash']);self.assertNotEqual(a['hash'],build_suite(14)['hash'])
        self.assertEqual({i['split'] for i in a['items']},{'seen','unseen'})
        add=next(i for i in a['items'] if i['family']=='arith_add');x,y=add['prompt'].split(': ')[1].split(' = ')[0].split(' + ')
        self.assertEqual(int(add['answer']),int(x)+int(y))
        self.assertTrue(add['prompt'].startswith('Compute'))  # English first
        de=build_suite(13,lang='de');self.assertNotEqual(de['hash'],a['hash'])
        self.assertEqual([i['answer'] for i in de['items'] if i['family']=='arith_add'],[i['answer'] for i in a['items'] if i['family']=='arith_add'])
    def test_oracle_vs_null_curves_forgetting_and_holdout_guard(self):
        clock=Clock();g=GeneralityEval(self.s,self.home,clock=clock)
        r1=g.run(oracle_solver(g.suite),'oracle')['summary']
        self.assertEqual(r1['overall'],1.);self.assertEqual(r1['planning_depth'],8);self.assertEqual(r1['calibration']['ece'],0.)
        clock.t+=10;r2=g.run(null_solver,'null')['summary']
        self.assertEqual(r2['overall'],0.);self.assertEqual(r2['forgetting']['rate'],1.)
        self.assertEqual([p['value'] for p in g.curve('overall')],[1.,0.])
        self.assertTrue((self.home/'exports/generality-last.json').exists())
        unseen=next(i for i in g.suite['items'] if i['split']=='unseen')
        with self.assertRaises(ValueError):g.guard_training(['harmlos',unseen['prompt']])
        self.assertTrue(g.guard_training([i['prompt'] for i in g.practice_items()]))
        self.assertFalse(g.due());clock.t+=31*86400;self.assertTrue(g.due())
    def test_solver_errors_count_as_wrong(self):
        g=GeneralityEval(self.s)
        def bad(v):raise RuntimeError('boom')
        self.assertEqual(g.run(bad)['summary']['overall'],0.)
    def test_calibration_metric(self):
        self.assertEqual(calibration([(1.,1)]*5+[(0.,0)]*5)['ece'],0.)
        self.assertAlmostEqual(calibration([(.9,0)]*10)['ece'],.9)

class G6Weights(Base):
    def fact(self,q='Projekt Aurora Budget?',v='120 Euro'):
        e=self.s.event(self.r.session,q);self.r.memory.feedback(e['event_id'],'fact',v);return e['event_id']
    def test_stage_needs_learning_mode_and_replay_pass(self):
        self.fact();w=WeightConsolidation(self.s,self.r.cfg|{'learning_mode':'RECORD_ONLY'})
        self.assertEqual(w.stage()['status'],'SKIPPED_RECORD_ONLY')
        w=WeightConsolidation(self.s,self.r.cfg|{'learning_mode':'SHADOW_UPDATE'})
        self.assertEqual(w.stage()['status'],'NOTHING_TO_STAGE')  # never replay-tested yet
        out=w.stage(require_replay_pass=False);self.assertEqual(out['status'],'STAGED');self.assertEqual(out['items'],1)
        self.assertTrue(w.stage(require_replay_pass=False)['deduplicated'])
    def test_null_trainer_is_honest_and_gate_needs_user(self):
        self.fact();cfg=self.r.cfg|{'learning_mode':'SHADOW_UPDATE'}
        w=WeightConsolidation(self.s,cfg);bid=w.stage(require_replay_pass=False)['batch_id']
        self.assertEqual(w.train(bid)['status'],'NO_TRAINER')
        class Fake:
            method='fake'
            def fit(self,items,base,cancel=None,deadline=None):return {'artifact':'x.gguf','hash':'h','method':'fake','metrics':{'kl_to_base':.01}}
        w=WeightConsolidation(self.s,cfg,trainer=Fake());w.box.mutate(lambda st:st['batches'].clear())
        bid=w.stage(require_replay_pass=False)['batch_id'];w.train(bid)
        base={'overall':.6,'unseen':.4};good={'overall':.61,'unseen':.4,'forgetting':{'rate':0.}}
        bad=w.gate(bid,base,{'overall':.5,'unseen':.4},learned_recall=.9)
        self.assertEqual(bad['status'],'GATE_FAIL');self.assertFalse(bad['gate']['checks']['general_retention'])
        w.box.mutate(lambda st:st['batches'].clear());bid=w.stage(require_replay_pass=False)['batch_id'];w.train(bid)
        p=w.gate(bid,base,good,learned_recall=.9);self.assertEqual(p['status'],'PENDING_USER')
        self.assertEqual(self.s.one('SELECT status FROM requests WHERE id=?',(p['request_id'],))['status'],'PENDING')
        self.assertEqual(w.approve(bid)['status'],'APPROVED');self.assertEqual(w.stage(require_replay_pass=False)['status'],'NOTHING_TO_STAGE')
        w.rollback(bid);self.assertEqual(w.stage(require_replay_pass=False)['status'],'STAGED')
    def test_holdout_prompt_cannot_enter_a_batch(self):
        g=GeneralityEval(self.s);unseen=next(i for i in g.suite['items'] if i['split']=='unseen')
        self.fact(unseen['prompt'],unseen['answer'])
        w=WeightConsolidation(self.s,self.r.cfg|{'learning_mode':'SHADOW_UPDATE'},generality=g)
        with self.assertRaises(ValueError):w.stage(require_replay_pass=False)

class G9Metacog(Base):
    def test_calibrator_is_monotone_and_decides(self):
        m=Metacognition(self.s)
        for i in range(60):m.record('B1',.9,i%10<3)  # overconfident: 30 % right at 0.9
        for i in range(60):m.record('B1',.2,i%10<1)
        self.assertIsNone(Metacognition(self.s).calibrated('B2',.5))
        hi=m.calibrated('B1',.9);lo=m.calibrated('B1',.2)
        self.assertLess(hi,.45);self.assertLessEqual(lo,hi)
        r=m.report('B1')['components']['B1'];self.assertLess(r['calibrated']['ece'],r['raw']['ece'])
        self.assertTrue(m.decide('B1',.2)['abstain']);self.assertTrue(m.decide('B9',.9)['second_attempt'])
    def test_semantic_entropy(self):
        self.assertEqual(semantic_entropy(['Berlin','berlin ','BERLIN'])['entropy'],0.)
        self.assertGreater(semantic_entropy(['a','b','c'])['entropy'],1.)

class G3Goals(Base):
    def test_tree_progress_wake_and_age_gate(self):
        clock=Clock();sched=EventScheduler(self.s,self.r.cfg,clock,self.age,key='G13_TEST_GROWTH')
        gs=GoalStore(self.s,self.age,sched,clock)
        root=gs.add('Spanisch lernen',steps=['Grundwortschatz'])
        a,b=gs.decompose(root,['Zahlen','Farben'])
        self.assertEqual(gs.next_actionable()['goal']['id'],a)
        gs.set_status(a,'DONE');self.assertAlmostEqual(gs.get(root)['progress'],round(1/3,4))
        gs.set_status(b,'DONE');gs.step_done(root,0);self.assertEqual(gs.get(root)['status'],'DONE')
        with self.assertRaises(PermissionError):gs.add('eigenes Ziel',origin='SELF')
        g2=gs.add('Wiedervorlage',wake_at=clock.t+60);self.assertIsNone(sched.next())
        clock.t+=61;e=sched.next();self.assertEqual(e['action'],'growth_goal')
        self.assertEqual(gs.on_wake(e)['status'],'WOKEN');self.assertEqual(gs.get(g2)['status'],'ACTIVE')
        best=gs.score_plans(g2,['a','bb'],lambda g,p:{'value':len(p),'risk':0});self.assertEqual(best[0]['plan'],'bb')

class G5Curiosity(Base):
    def test_learning_progress_prefers_improving_region(self):
        c=Curiosity(self.s,self.age)
        for i in range(16):c.observe('lernbar',1-i/16);c.observe('rauschen',.5);c.observe('gekonnt',0.)
        v=c.values();self.assertGreater(v['lernbar']['learning_progress'],.3)
        self.assertAlmostEqual(v['rauschen']['learning_progress'],0.);self.assertEqual(c.choose(origin='USER'),'lernbar')
        self.assertIsNone(c.choose(origin='SELF'))  # Age 0: no own exploration
        c.block('lernbar');self.assertNotEqual(c.choose(origin='USER'),'lernbar')

class G10Tools(Base):
    def test_calc_safety_and_policy(self):
        self.assertEqual(calc('2+3*4'),14);self.assertEqual(calc('7/2'),3.5)
        for bad in ('__import__("os")','2**99999','a+1'):
            with self.assertRaises(ValueError):calc(bad)
        g=Grounding(self.s);t=ToolRegistry(self.s,self.age,on_outcome=g.from_tool)
        self.assertEqual(t.call('calc',{'expression':'1+1'})['reason'],'TOOL_NOT_ENABLED_BY_USER')
        t.enable('calc');self.assertEqual(t.call('calc',{'expression':'1+1'})['result'],2)
        self.assertEqual(t.call('calc',{'expression':'1+1'},origin='SELF')['status'],'DENIED')  # Age 0
        t.register(ToolSpec('web',lambda q:q,risk='NETWORK'));t.enable('web')
        tx=t.call('web',{'q':'x'});self.assertEqual(tx['status'],'PROPOSED')
        done=t.approve(tx['id']);self.assertEqual((done['status'],done['result']),('EXECUTED','x'))  # WP-K: per-call approval runs it as a transaction
        self.assertEqual(g.report()['closed'],2)

class G2Grounding(Base):
    def test_prediction_error_drops_with_experience(self):
        g=Grounding(self.s);errs=[]
        for _ in range(5):
            aid,_=g.expect('switch','lampe',{'press':1});errs.append(g.observe(aid,{'status':'ON'})['grounded_error'])
        self.assertEqual(errs[0],1.);self.assertEqual(errs[-1],0.)
        with self.assertRaises(PermissionError):g.expect('look','x',{},modality='camera')
        cf=g.counterfactual('switch','lampe');self.assertEqual((cf['outcome'],cf['authority']),('ON:null','SIMULATION_NOT_FACT'))
        self.assertLess(cf['counterfactual_confidence'],cf['confidence']);self.assertTrue(g.counterfactual('switch','tür')['ood'])

class G4Skills(Base):
    def test_lifecycle_run_and_frontier(self):
        t=ToolRegistry(self.s,self.age);t.enable('calc');sk=SkillLibrary(self.s,self.age,t)
        sk.propose('mwst',[{'tool':'calc','args':{'expression':'{netto}*119/100'}}],trigger='mwst brutto')
        self.assertEqual(sk.run('mwst',{'netto':100})['value'],119)
        for _ in range(3):sk.record('mwst',True,parity=1.)
        self.assertEqual(sk.get('mwst')['stage'],'SHADOW')
        for _ in range(8):sk.record('mwst',True,parity=1.)
        self.assertEqual(sk.get('mwst')['stage'],'TRUSTED');self.assertEqual(sk.select('Was ist brutto mit MwSt?'),['mwst'])
        sk.reopen('mwst');self.assertEqual(sk.get('mwst')['stage'],'SHADOW')
        with self.assertRaises(ValueError):sk.propose('x y',[{'tool':'calc'}])
        items=[{'family':'a','id':1},{'family':'b','id':2}]
        for i in range(10):sk.record('mwst',i<5,family='a');sk.record('mwst',True,family='b')
        self.assertEqual({i['family'] for i in sk.practice(items)},{'a'})

class G7Abstraction(Base):
    def test_induces_rule_and_checks_holdout(self):
        self.assertEqual(dsl_inducer([('abc','cba'),('xy','yx')])[0][0],'reverse')
        a=Abstraction(self.s)
        eps=[{'id':f'e{i}','input':w,'output':''.join(chr((ord(c)-97+2)%26+97) for c in w),'tags':'geheimschrift'} for i,w in enumerate(['hund','katze','maus','vogel','fisch','baum'])]
        r=a.induce(eps)[0];self.assertEqual((r['program'],r['status'],r['fact_write_authority']),('shift2','VALIDATED',0))
        noisy=[dict(e,id='n'+e['id'],tags='rauschen') for e in eps[:5]]+[{'id':'nx','input':'zebra','output':'falsch','tags':'rauschen'}]
        self.assertEqual(a.induce(noisy,domain='andere')[0]['status'],'REFUTED')
        a.promote(r['id']);self.assertEqual(a.report()['by_status']['APPROVED'],1)

class G8SelfImprove(Base):
    def test_shield_and_human_gate(self):
        si=SelfImprovement(self.s,self.r.cfg,self.age)
        with self.assertRaises(PermissionError):si.propose('knob',{'memory_top_k':4})  # SELF at Age 0
        with self.assertRaises(PermissionError):si.propose('knob',{'user_stage_cap':5},origin='USER')
        with self.assertRaises(ValueError):si.propose('knob',{'memory_top_k':99},origin='USER')
        with self.assertRaises(PermissionError):si.propose('learning_rule',{'base_merge_authority':1.},origin='USER')
        pid=si.propose('knob',{'memory_top_k':4},origin='USER')
        ev=lambda cfg:{'overall':.5,'seen':.6,'unseen':.4} if cfg is None else {'overall':.55,'seen':.6,'unseen':.3}
        self.assertEqual(si.evaluate(pid,ev)['status'],'SHIELD_FAIL')  # unseen regressed
        pid=si.propose('knob',{'memory_top_k':4},origin='USER')
        ev=lambda cfg:{'overall':.5,'seen':.6,'unseen':.4} if cfg is None else {'overall':.55,'seen':.6,'unseen':.41}
        self.assertEqual(si.evaluate(pid,ev)['status'],'PENDING_USER')
        self.assertEqual(si.approve(pid)['settings']['memory_top_k'],4)
        self.assertEqual(self.r.cfg['memory_top_k'],3)  # nothing applied by itself
        self.assertEqual(si.get(si.propose('structural',{'body':'neu'},origin='USER'))['status'],'RECORDED_LOCKED')

class G1Teacher(Base):
    def test_requests_cloud_privacy_dataset_and_reliance(self):
        t=TeacherDistillation(self.s,self.age,GeneralityEval(self.s))
        self.assertIsNone(t.request('frage',origin='SELF'))  # Age 0: no own teacher requests
        t.register('lokal',lambda p:{'answer':'A:'+p,'model':'x'});t.register('wolke',lambda p:{'answer':'C'},'cloud')
        rid=t.request('Was ist 2+2?',own_answer='5');tr=t.fulfil(rid,'lokal')
        self.assertEqual((tr['authority'],tr['own_answer']),('REFERENCE_NOT_FACT','5'))
        self.assertIsNone(t.fulfil(t.request('privat'),'wolke'))  # cloud off by default
        self.assertEqual(t.dataset()[0]['rejected'],'5')
        for _ in range(40):t.trial('language',True,True);t.trial('language',True,False)
        r=t.reliance('language');self.assertTrue(r['removal_ready']);t.remove('language')
        self.assertIsNone(t.request('x',capability='language'))

class G11UserModel(Base):
    def test_beliefs_need_evidence_and_protected_are_refused(self):
        clock=Clock();u=UserModel(self.s,clock)
        with self.assertRaises(ValueError):u.observe('preference','antwortlänge','kurz',None)
        with self.assertRaises(PermissionError):u.observe('knowledge','Religion','x','ref1')
        u.observe('preference','antwortlänge','kurz','ref1');b=u.observe('preference','antwortlänge','kurz','ref2')
        self.assertGreater(b['confidence'],.5)
        b=u.observe('preference','antwortlänge','lang','ref3');self.assertEqual(b['replaced']['value'],'kurz')
        clock.t+=180*86400;self.assertLess(u.beliefs()[0]['confidence'],.2)
        self.assertEqual(u.forget(),1);self.assertEqual(u.beliefs(),[])

class AG0Slots(Base):
    def test_swap_keeps_portable_and_relearns_bound_state(self):
        from v13.agi.slots import ModelSlots
        m=ModelSlots(self.s,self.age);old=m.spec('LFM2.5-1.2B','rev1',('CAN_NATIVE_DECODE','CAN_LAYER_TAP'),dims=2048,tokenizer='lfm')
        m.install('B1_DETAIL',old)
        m.register_asset('B1_DETAIL','gedaechtnis','memory');m.register_asset('B1_DETAIL','lora_tag1','lora',dataset_ref='g6b_x')
        m.register_asset('B1_DETAIL','alt_lora','adapter');m.register_asset('B1_DETAIL','callosum','bridge');m.register_asset('B1_DETAIL','route','route_head')
        with self.assertRaises(PermissionError):m.propose_swap('B1_DETAIL',m.spec('Qwen3.5-0.8B','rev2'),origin='SELF')  # Age 0
        plan=m.propose_swap('B1_DETAIL',m.spec('Qwen3.5-0.8B','rev2',('CAN_NATIVE_DECODE',),dims=1024,tokenizer='qwen'))
        acts={p['asset'].split(':')[1]:p['action'] for p in plan['assets']}
        self.assertEqual(acts,{'gedaechtnis':'PORTABLE','lora_tag1':'REDISTILL','alt_lora':'REDISTILL_NO_DATA','callosum':'SHADOW','route':'REFIT'})
        self.assertEqual(plan['lost_capabilities'],['CAN_LAYER_TAP'])
        m.start_shadow('B1_DETAIL');self.assertEqual(m.route('B1_DETAIL','turn1'),'rev1')
        self.assertEqual(m.parity('B1_DETAIL',{'overall':.6},{'overall':.5})['stage'],'PARITY_FAIL')
        m.rollback('B1_DETAIL');m.propose_swap('B1_DETAIL',m.spec('Qwen3.5-0.8B','rev2',dims=1024));m.start_shadow('B1_DETAIL')
        m.parity('B1_DETAIL',{'overall':.6,'unseen':.3},{'overall':.61,'unseen':.31})
        m.ramp('B1_DETAIL');routes={m.route('B1_DETAIL',i) for i in range(200)};self.assertEqual(routes,{'rev1','rev2'})
        m.ramp('B1_DETAIL');self.assertEqual(m.ramp('B1_DETAIL')['stage'],'ACTIVE');self.assertEqual(m.route('B1_DETAIL','x'),'rev2')
        self.assertEqual(m.usable_assets('B1_DETAIL','rev2'),['gedaechtnis'])  # old LoRA never applied to the new model
        m.mark_relearned('B1_DETAIL','lora_tag1','rev2');self.assertIn('lora_tag1',m.usable_assets('B1_DETAIL','rev2'))
        m.rollback('B1_DETAIL');self.assertEqual(m.route('B1_DETAIL','x'),'rev1');self.assertIn('alt_lora',m.usable_assets('B1_DETAIL','rev1'))
    def test_export_import_goes_through_swap_gates(self):
        from v13.agi.slots import ModelSlots
        a=ModelSlots(self.s);a.install('B2_GIST',a.spec('gist','r1',dims=8));a.register_asset('B2_GIST','skills','skill');a.register_asset('B2_GIST','lora','lora',dataset_ref='d1')
        h1=a.manifest_fields()['slots_hash'];b=a.export_bundle('B2_GIST',home=self.home)
        self.assertTrue(Path(b['path']).exists());self.assertEqual(b['manifest_slots_hash'],h1)
        bad=dict(b,slot='B1_DETAIL')
        with self.assertRaises(ValueError):a.import_bundle(bad)
        a.box.mutate(lambda st:st.update(slots={},assets={}))
        a.install('B2_GIST',a.spec('gist','r0'))
        out=a.import_bundle(b);self.assertFalse(out['installed_directly'])
        self.assertEqual(a.route('B2_GIST','x'),'r0')  # import never activates itself
        self.assertEqual(a.box.load()[0]['assets']['B2_GIST:lora']['authority'],'IMPORTED_NEEDS_CHECK')
        self.assertNotEqual(a.manifest_fields()['slots_hash'],h1)

class AG13Residency(Base):
    def test_experts_load_evict_and_learn_only_when_resident(self):
        from v13.agi.residency import ExpertResidency
        r=ExpertResidency(self.s,budget_mb=1000)
        r.register('router',100,shared=True)
        for n in 'abc':r.register(n,400)
        self.assertEqual(r.request('a')['status'],'LOADED');self.assertEqual(r.request('a')['status'],'HIT')
        self.assertEqual(r.request('b')['status'],'LOADED')
        out=r.request('c');self.assertEqual((out['status'],out['evict']),('LOADED',['b']))  # a used more often stays
        self.assertTrue(r.can_learn('a'));self.assertFalse(r.can_learn('b'));self.assertFalse(r.can_learn('router'))
        r.defer_update('b','upd1');self.assertEqual(r.request('b')['replay_updates'],['upd1'])
        self.assertIn('router',r.report()['resident'])
        ev=r.set_mode('RED');self.assertTrue(ev);self.assertLessEqual(r.report()['used_mb'],300)
        self.assertEqual(r.request('a')['status'],'REFUSED')

class AgeEvidence(Base):
    def test_metrics_come_from_measurements_and_estimate_names_blockers(self):
        g=hub(self.r);out=g.age_evidence()
        self.assertIsNone(out['metrics']['competence']);self.assertIn('competence',out['next_stage']['blockers'])
        g.eval.run(oracle_solver(g.eval.suite))
        for i in range(30):g.metacog.record('B1',.9 if i%10 else .1,i%10!=0)
        m=g.age_evidence()['metrics'];self.assertEqual(m['competence'],1.);self.assertEqual(m['memory_health'],1.)
        from v13.agi.maturity import estimate
        e=estimate({'experience':20},0);self.assertEqual(e['experience']['days_at_rate']['10'],3)
        rec=g.age_evidence(record=True)['recorded'];self.assertEqual(rec['system']['stage'],0);self.assertIn('language',rec)  # build ceiling 0: no silent promotion

class SchedulerHooks(Base):
    def test_growth_actions_run_through_sleep_runtime(self):
        g=hub(self.r);self.assertIs(hub(self.r),g)
        gid=g.goals.add('Test')
        e={'id':'x','action':'growth_goal','origin':'USER','payload':{'goal_id':gid}}
        self.assertEqual(job(self.r.sleep,e)['status'],'WOKEN')
        self.assertEqual(job(self.r.sleep,dict(e,action='growth_eval'))['status'],'NO_SOLVER')
        self.assertEqual(job(self.r.sleep,dict(e,action='growth_practice'))['status'],'DONE')
        self.assertIn(job(self.r.sleep,dict(e,action='growth_consolidate'))['status'],{'SKIPPED_RECORD_ONLY','NOTHING_TO_STAGE'})
        eid=self.r.sleep.scheduler.post('TIMER',origin='USER',action='growth_consolidate')
        self.assertIsNotNone(eid)
        rep=g.report();self.assertEqual(sorted(rep,key=lambda k:int(k[2:])),[f'AG{i}' for i in range(0,14)])
        self.assertFalse(any('error' in v for v in rep.values()),rep)
    def test_operator_growth_command(self):
        from v13.operator import Operator
        op=Operator(self.r)
        self.assertIn('AG12',op.run(':growth'))
        self.assertTrue(op.run(':growth goal Mehr lesen').startswith('Ziel angelegt'))
        op.run(':growth enable calc');self.assertIn('"result":42',op.run(':growth calc 6*7'))

if __name__=='__main__':unittest.main()
