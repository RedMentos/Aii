"""WP-N13: AG modules hooked into the live turn. Model-free (exact-copy turns, synthetic labels)."""
from pathlib import Path
import tempfile
import unittest
from v13.agi import hub
from v13.agi import live
from v13 import inputs
from v13.runtime import Runtime

SIG={'uncertainty':.2,'route_hint':'simple'}

class LiveHooks(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.g=hub(self.r)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def ev(self,text='Budget Aurora?'):return self.r.store.event(self.r.session,text)
    def test_metacog_raises_effort_only_when_calibrated(self):
        e=self.ev();meta={}
        self.assertEqual(live.before_effort(self.r,e,meta,SIG)['uncertainty'],.2);self.assertEqual(meta['metacognition']['answer']['reason'],'UNCALIBRATED')
        for i in range(40):self.g.metacog.record(live.ANSWER_QUALITY,.8,i%2==0)
        meta={};out=live.before_effort(self.r,e,meta,SIG);self.assertEqual(out['uncertainty'],.6);self.assertNotIn('metacog_abstain',meta)
        for _ in range(512):self.g.metacog.record(live.ANSWER_GROUNDED,.8,False)
        meta={};out=live.before_effort(self.r,e,meta,SIG);self.assertEqual(out['uncertainty'],.8);self.assertTrue(meta['metacog_abstain'])
    def test_trusted_route_skill_sets_route_candidate_does_not(self):
        e=self.ev('please summarize the plan');self.g.skills.propose('summary_gist',[{'route':'gist'}],trigger='summarize plan')
        meta={};self.assertEqual(live.skill_route(self.r,e,'please summarize the plan','simple',False,meta),'simple')
        self.g.skills.set_stage('summary_gist','TRUSTED');meta={}
        self.assertEqual(live.skill_route(self.r,e,'please summarize the plan','simple',False,meta),'gist');self.assertEqual(meta['skill']['prior_route'],'simple')
        self.assertEqual(live.skill_route(self.r,e,'please summarize the plan','simple',True,{}),'simple')
        live.after_turn(self.r,e,{},'FINAL');self.assertEqual(self.g.skills.get('summary_gist')['uses'],1)
    def test_feedback_labels_and_user_beliefs(self):
        e=self.ev();live.before_effort(self.r,e,{},SIG)
        self.r.memory.feedback(e['event_id'],'fact','120 Euro',key='Budget Aurora?')
        self.assertEqual(self.g.metacog.box.load()[0]['components'][live.ANSWER_GROUNDED]['pairs'],[[.8,0]])
        self.r.memory.feedback(e['event_id'],'preference','short answers',key='answer length')
        self.assertEqual([b['value'] for b in self.g.users.beliefs()],['short answers'])
        self.r.memory.feedback(e['event_id'],'preference','no meat',key='health diet')
        self.assertEqual(len(self.g.users.beliefs()),1)
        meta={};live.before_effort(self.r,e,meta,SIG);self.assertEqual(meta['user_model']['beliefs'],1)
    def test_rating_becomes_metacog_label(self):
        e=self.ev();live.before_effort(self.r,e,{},SIG);mid=self.r.store.message(self.r.session,e['event_id'],'assistant','ok');self.r.store.finish_message(mid,'FINAL',{})
        inputs.record_rating(self.r.store,e['event_id'],9,'EXPLICIT_NOTE');inputs.record_rating(self.r.store,e['event_id'],5,'IMPLICIT_CHAT')
        self.assertEqual(self.g.metacog.box.load()[0]['components'][live.ANSWER_QUALITY]['pairs'],[[.8,1]])
    def test_slots_mirror_installed_models_and_propose_on_new_revision(self):
        entry={'model_id':'m','exact_revision':'r1','license_id':'x','files':{'a.gguf':{'path':'models/language/a.gguf'}},'main_file':'a.gguf','download_complete':True}
        self.r.models.installed['language']=entry;self.assertEqual(live.sync_slots(self.r),[('C3_LANGUAGE','INSTALL')])
        self.assertEqual(live.sync_slots(self.r),[])
        self.r.models.installed['language']=dict(entry,exact_revision='r2');self.assertEqual(live.sync_slots(self.r),[('C3_LANGUAGE','PROPOSE')])
        self.assertEqual(self.g.slots.box.load()[0]['slots']['C3_LANGUAGE']['stage'],'CANDIDATE')
    def test_real_turn_grounds_the_action_without_errors(self):
        for t in ['Copy exactly: one','Copy exactly: two']:self.r._turn(self.ev(t))
        rep=self.g.grounding.report();self.assertEqual(rep['closed'],2);self.assertEqual(rep['error_rate']['answer:SOURCE_COPY'],.5)
        self.assertIsNone(self.r.store.one("SELECT id FROM telemetry WHERE kind IN ('agi_live_unavailable','episodes_unavailable')"))
        self.assertIn('hooks',live.report(self.r))

if __name__=='__main__':unittest.main()

class ClarifyAndUserModel(unittest.TestCase):
    """WP-N13 rest: AG9 abstain -> C5 ASK_USER (ACTIVE only by explicit human), AG11 beliefs -> C1 + answer context."""
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.g=hub(self.r)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_abstain_asks_user_only_when_active(self):
        from v13.focal import ActionGate
        e=self.r.store.event(self.r.session,'Budget Aurora?');meta={'metacog_abstain':True}
        c=live.clarify(self.r,meta);self.assertEqual((c['mode'],c['apply']),('SHADOW',False))
        sel=ActionGate(self.r.store).select(e,route='simple',direct=False,resource_state='NORMAL',clarify=c)
        self.assertEqual(sel['role'],'C3_LANGUAGE');self.assertIn('ASK_USER',[x['action_id'] for x in sel['suppressed']])
        with self.assertRaises(PermissionError):live.set_ask_mode(self.r.store,'ACTIVE')
        live.set_ask_mode(self.r.store,'ACTIVE','EXPLICIT_HUMAN');c=live.clarify(self.r,meta)
        self.assertEqual(ActionGate(self.r.store).select(e,route='simple',direct=False,resource_state='NORMAL',clarify=c)['role'],'ASK_USER')
        self.assertEqual(ActionGate(self.r.store).select(e,route='simple',direct=True,resource_state='NORMAL',clarify=c)['role'],'SOURCE_COPY')
        self.assertIsNone(live.clarify(self.r,{}))
        self.assertEqual(live.operator_command(self.r,['ask','shadow']),{'ask':'SHADOW'})
    def test_user_beliefs_reach_exec_state_but_not_constraints(self):
        e=self.r.store.event(self.r.session,'Budget Aurora?')
        self.r.memory.feedback(e['event_id'],'preference','short answers',key='answer length')
        for _ in range(3):self.g.users.observe('preference','answer length','short answers','src:x')
        meta={};live.before_effort(self.r,e,meta,SIG)
        self.assertEqual(live.user_layer(meta),[{'aspect':'preference','topic':'answer length','value':'short answers'}])
        self.r.executive.begin(e,self.r.session,self.r.cfg,{},'NORMAL');self.r.executive.update(e,self.r.session,user_beliefs=meta['user_beliefs'])
        v=self.r.executive.control_view(self.r.session,e)
        self.assertEqual(v['user_beliefs'][0]['authority'],'BELIEF_NOT_FACT');self.assertEqual(v['constraints'],self.r.store.rules())
        self.assertIsNone(live.user_layer({}))
