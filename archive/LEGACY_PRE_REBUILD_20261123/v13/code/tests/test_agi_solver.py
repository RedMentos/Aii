"""WP-AG12 step 2 body solvers + WP-AG1 teacher backends (fake runners, no models)."""
from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import threading
import unittest
from v13.runtime import Runtime
from v13.common import Unavailable
from v13.agi import hub,job,operator_command
from v13.agi import solver as sv
from v13.agi import teacher_backends as tb
from v13.agi.generality import GeneralityEval

class FakeRunner:
    """Answers correctly for roles in `good`, else a fixed wrong answer; token confidence per role."""
    def __init__(self,role,gold,good,conf):self.role=role;self.gold=gold;self.good=good;self.conf=conf;self.last_metrics={};self.calls=[]
    def generate(self,messages,cancel,deadline,max_tokens=None,schema=None,seed=13,first_token_bias=None,confidence_field='summary'):
        self.calls.append((messages[-1]['content'],schema is not None,confidence_field));cancel.wait(0)
        ans=self.gold[messages[-1]['content']] if self.good else 'zzz'
        self.last_metrics={'token_confidence':{'field':confidence_field,'field_min_prob':self.conf}}
        yield json.dumps({'answer':ans})[:5];yield json.dumps({'answer':ans})[5:]

class FakePool:
    def __init__(self,runners):self.runners=runners;self.order=[]
    def get(self,role):
        self.order.append(role);return self.runners[role]
    def unload(self,role=None):return {'process_reaped':True}
    def pids(self):return []

class FakeModels:
    def __init__(self,roles):self.roles=roles
    def path_for(self,role):
        if role not in self.roles:raise Unavailable('missing '+role)
        return Path('/x')
    def revision(self,role):return 'rev-'+role

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.g=hub(self.r)
        self.gold={i['prompt']:i['answer'] for i in self.g.eval.suite['items']}
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def fake(self,good=('B1_DETAIL','C3_LANGUAGE'),installed=('B1_DETAIL','B2_GIST','C3_LANGUAGE'),conf=None):
        conf=conf or {'B1_DETAIL':.9,'B2_GIST':.4,'C3_LANGUAGE':.7}
        runners={r:FakeRunner(r,self.gold,r in good,conf[r]) for r in ('B1_DETAIL','B2_GIST','C3_LANGUAGE')}
        self.r.pool=FakePool(runners);self.r.models=FakeModels(installed);return runners

class Solver(Base):
    def test_extract_and_combine(self):
        self.assertEqual(sv.extract('{"answer": " 42 "}'),'42')
        self.assertEqual(sv.extract('{"answer": "elppa'),'elppa')  # cut-off JSON
        self.assertEqual(sv.extract('42\nbecause'),'42')
        c=sv.combine([{'answer':'42','confidence':.9},{'answer':'41','confidence':.4},{'answer':' 42','confidence':.7}])
        self.assertEqual(c['answer'],'42');self.assertEqual(c['agree'],2);self.assertAlmostEqual(c['confidence'],1.6/3,3)
        self.assertEqual(sv.combine([])['confidence'],0.)
    def test_single_body_run_uses_grammar_answer_confidence_and_no_store_writes(self):
        runners=self.fake();before=self.r.store.one('SELECT COUNT(*) n FROM events')['n']
        out=sv.run(self.g,self.r,'b1')
        self.assertEqual(out['status'],'DONE');self.assertEqual(out['overall'],1.);self.assertEqual(out['roles'],['B1_DETAIL'])
        prompt,grammar,field=runners['B1_DETAIL'].calls[0]
        self.assertTrue(grammar);self.assertEqual(field,'answer')
        self.assertEqual(self.r.store.one('SELECT COUNT(*) n FROM events')['n'],before)  # holdout prompts never become events
        self.assertEqual(self.g.metacog.report('ag12:b1')['components']['ag12:b1']['n'],88)  # AG9 gets (confidence, correct) only
    def test_batch_loads_each_body_once_in_a_row(self):
        self.fake();sv.run(self.g,self.r,'v13')
        order=self.r.pool.order;switches=sum(1 for a,b in zip(order,order[1:]) if a!=b)
        self.assertEqual(switches,2)  # B1 for all items, then B2, then C3
    def test_ensemble_votes_and_per_solver_curves(self):
        self.fake(good=('B1_DETAIL','C3_LANGUAGE'))
        v=sv.run(self.g,self.r,'v13');b2=sv.run(self.g,self.r,'b2')
        self.assertEqual(v['overall'],1.);self.assertEqual(b2['overall'],0.)
        self.assertEqual([p['value'] for p in self.g.eval.curve('overall','v13')],[1.])
        self.assertEqual([p['value'] for p in self.g.eval.curve('overall','b2')],[0.])
        # forgetting is per solver: a weak b2 run after a strong v13 run is not "forgetting" of v13
        again=self.g.eval.run(sv.make_solver(self.r,'v13'),solver_name='v13')
        self.assertEqual(again['summary']['forgetting']['rate'],0.)
        self.assertEqual(set(self.g.eval.report()['solvers']),{'v13','b2'})
    def test_missing_models_are_skipped_or_no_solver(self):
        self.fake(installed=('C3_LANGUAGE',))
        self.assertEqual(sv.make_solver(self.r,'v13').roles,('C3_LANGUAGE',))
        self.assertEqual(sv.run(self.g,self.r,'b1')['status'],'NO_SOLVER')
        with self.assertRaises(ValueError):sv.make_solver(self.r,'gpt')
    def test_runner_error_counts_wrong_and_cancel_interrupts(self):
        runners=self.fake()
        def boom(*a,**k):raise RuntimeError('native down');yield
        runners['B1_DETAIL'].generate=boom
        out=sv.run(self.g,self.r,'b1');self.assertEqual(out['status'],'ERROR');self.assertEqual(out['stats']['B1_DETAIL']['errors'],88)
        self.assertEqual(self.g.eval.curve('overall','b1')[-1]['value'],None)  # broken runner is no 0 % curve point
        ev=threading.Event();ev.set()
        self.assertEqual(sv.run(self.g,self.r,'c3',cancel=ev)['status'],'INTERRUPTED')
    def test_scheduler_job_and_operator(self):
        self.fake()
        msg=operator_command(self.r,['eval','run','c3']);self.assertIn('c3',msg)
        e=next(x for x in self.r.sleep.scheduler._load()[0]['events'] if x['action']=='growth_eval')
        self.assertEqual(e['payload'],{'solver':'c3'})
        res=job(self.r.sleep,e);self.assertEqual(res['status'],'DONE');self.assertEqual(res['overall'],1.)
        self.assertIn('"solver":"c3"',operator_command(self.r,['eval','curve','c3']))
        with self.assertRaises(ValueError):operator_command(self.r,['eval','run','nope'])

class FakeClaude:
    def __init__(self,stop='end_turn',text='ANSWER: 56\nREASONING: 7*8 is 56.'):
        self.kw=None;self.stop=stop;self.text=text
        self.beta=SimpleNamespace(messages=SimpleNamespace(create=self.create))
    def create(self,**kw):
        self.kw=kw
        return SimpleNamespace(stop_reason=self.stop,stop_details=SimpleNamespace(category='cyber'),model=kw['model'],
                               content=[SimpleNamespace(type='thinking',thinking=''),SimpleNamespace(type='text',text=self.text)])

class Teacher(Base):
    def test_split(self):
        self.assertEqual(tb.split('ANSWER: 56\nREASONING: because'),('56','because'))
        self.assertEqual(tb.split('plain'),('plain',''))
    def test_claude_backend_request_shape_and_refusal(self):
        fc=FakeClaude();out=tb.claude_backend(client=fc)('What is 7*8?')
        self.assertEqual(out,{'answer':'56','reasoning':'7*8 is 56.','model':'claude-opus-5-5'})
        self.assertEqual(fc.kw['model'],'claude-opus-5-5');self.assertEqual(fc.kw['fallbacks'],'default')
        self.assertEqual(fc.kw['betas'],['server-side-fallback-2026-07-01']);self.assertNotIn('thinking',fc.kw)
        with self.assertRaises(Unavailable):tb.claude_backend(client=FakeClaude(stop='refusal'))('x')
    def test_cloud_needs_user_permission_and_local_runs(self):
        t=self.g.teacher;t.backends['claude']=(tb.claude_backend(client=FakeClaude()),'cloud')
        rid=t.request('What is 7*8?')
        self.assertEqual(tb.fulfil_open(self.g,self.r)['status'],'NO_TEACHER')  # no local teacher, cloud not allowed
        res=tb.fulfil_open(self.g,self.r,'claude');self.assertEqual(res['denied_cloud'],1)
        self.assertEqual(t.box.load()[0]['requests'][rid]['status'],'DENIED_CLOUD')
        operator_command(self.r,['teacher','cloud','on']);rid2=t.request('What is 7*8?')
        res=tb.fulfil_open(self.g,self.r);self.assertEqual((res['backend'],res['done']),('claude',1))
        self.assertEqual(t.dataset()[0]['target'],'56');self.assertEqual(t.dataset()[0]['authority'],'REFERENCE_NOT_FACT')
        # local TEACHER runner preferred once enabled + installed
        self.r.cfg['teacher_enabled']=True
        runner=FakeRunner('TEACHER',{},True,.9)
        def gen(messages,cancel,deadline,max_tokens=None,**k):yield 'ANSWER: Paris\nREASONING: capital.'
        runner.generate=gen;self.r.pool=FakePool({'TEACHER':runner});self.r.models=FakeModels(('TEACHER',))
        t.request('Capital of France?');res=tb.fulfil_open(self.g,self.r)
        self.assertEqual((res['backend'],res['done']),('local',1))
        self.assertEqual(t.dataset()[-1]['target'],'Paris')
    def test_holdout_prompt_cannot_enter_teacher_dataset(self):
        t=self.g.teacher;t.backends['claude']=(tb.claude_backend(client=FakeClaude()),'cloud');t.allow_cloud(True)
        unseen=next(i for i in self.g.eval.suite['items'] if i['split']=='unseen')
        t.request(unseen['prompt']);tb.fulfil_open(self.g,self.r,'claude')
        with self.assertRaises(ValueError):t.dataset()
    def test_operator_teacher_and_job(self):
        self.assertIn('treq_',operator_command(self.r,['teacher','ask','Why','is','the','sky','blue?']))
        operator_command(self.r,['teacher','run'])
        e=next(x for x in self.r.sleep.scheduler._load()[0]['events'] if x['action']=='growth_teacher')
        self.assertEqual(job(self.r.sleep,e)['status'],'NO_TEACHER')
        self.assertIn('claude',operator_command(self.r,['teacher']))

if __name__=='__main__':unittest.main()
