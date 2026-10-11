"""WP-N10: eligibility traces, typed modulator bus, plasticity gate, consolidation tags. No models needed."""
from pathlib import Path
import tempfile
import unittest
from v13.common import dumps,file_hash,uid
from v13.runtime import Runtime
from v13.operator import Operator
from v13.agi.weights import WeightConsolidation
from v13 import neuromod as N
from v13.config import KNOBS

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.n=N.Neuromod(self.r.store)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def ev(self,text='x'):return self.r.store.event(self.r.session,text)['event_id']
    def events(self,k):
        for i in range(k):self.ev('tick '+str(i))

class TraceTests(Base):
    def test_trace_grows_with_activity_and_decays_per_event_on_two_timescales(self):
        e=self.ev();self.n.touch('world_predictor',e)
        g0=self.n.gate('world_predictor');self.assertAlmostEqual(g0['eligibility'],(1-N.SLOW_MIX)*1+N.SLOW_MIX*(1-N.SLOW_DECAY),6)
        self.events(3);g3=self.n.gate('world_predictor')
        fast=N.FAST_DECAY**3;slow=(1-N.SLOW_DECAY)*N.SLOW_DECAY**3
        self.assertAlmostEqual(g3['eligibility'],(1-N.SLOW_MIX)*fast+N.SLOW_MIX*slow,5)
        self.n.touch('world_predictor',e);self.assertGreater(self.n.gate('world_predictor')['eligibility'],g3['eligibility'])
    def test_unknown_path_keeps_only_floor_and_human_label_opens_gate(self):
        self.assertEqual(self.n.gate('route')['factor'],N.FLOOR)
        for i in range(3):self.n.touch('C2_EXTERNAL_ROUTE_HEAD',self.ev('label '+str(i)),authority='EXPLICIT_HUMAN_LEARN')
        g=self.n.gate('route');self.assertEqual(g['path_id'],'route')
        self.assertGreater(g['factor'],.7);self.assertGreater(g['modulator']['epistemic'],.8);self.assertEqual(g['modulator']['instrumental'],0.)
    def test_sync_is_restart_stable_and_counts_each_packet_once(self):
        self.n.touch('route',self.ev());self.n.sync();self.n.sync()
        st=self.r.store.state(N.KEY)[0];self.assertEqual(st['paths']['route']['activations'],1)
        self.assertEqual(N.Neuromod(self.r.store).report('route')['paths']['route']['eligibility'],self.n.gate('route')['eligibility'])
        self.assertEqual(self.r.store.state(N.KEY)[0]['paths']['route']['activations'],1)
    def test_detailed_traces_are_selective(self):
        for i in range(30):self.n.touch('world_predictor',self.ev(str(i)))
        self.n.touch('route',self.ev('h'),authority='EXPLICIT_HUMAN_LEARN')
        self.n.sync();paths=self.r.store.state(N.KEY)[0]['paths']
        self.assertLess(len(paths['world_predictor']['details']),N.MAX_DETAILS)
        self.assertEqual(paths['route']['details'][-1]['class'],'human_feedback')

class ModulatorTests(Base):
    def test_credit_map_projects_unpathed_modulator_onto_eligible_paths_of_same_event(self):
        e=self.ev();self.n.touch('b1_predictor',e);self.n.touch('memory_retrieval',e)
        self.n.signal(e,source_class='real_deterministic_outcome',world_prediction_error=.8)
        rep=self.n.report()['paths']
        self.assertGreater(rep['b1_predictor']['modulator']['epistemic'],.7)
        self.assertEqual(rep['memory_retrieval']['modulator']['epistemic'],0.)  # knowledge path ignores world error
        self.n.signal(self.ev(),source_class='primary_source',evidence_gain=1.)
        self.n.sync();self.assertEqual(self.r.store.state(N.KEY)[0]['unassigned_modulators'],1)
    def test_existing_learner_packets_feed_the_bus(self):
        from v13.contracts import packet
        e=self.ev();base=self.r.store.generation_id
        self.r.store.add_packet('LearningTrace',packet('LearningTrace','F6_LEARNING',e,base,[],path_id='b2_predictor',activity=1.,eligibility=.95,authority='EXPLICIT_OBSERVATION_LEARN'))
        self.r.store.add_packet('ModulatorPacket',packet('ModulatorPacket','F6_LEARNING',e,base,[],epistemic_evidence=1.,human_correction=0.,task_success=0.,resource_cost=0.,safety_veto=False))
        g=self.n.gate('b2_predictor');self.assertGreater(g['modulator']['epistemic'],0.);self.assertGreater(g['factor'],N.FLOOR)
    def test_epistemic_and_instrumental_stay_separate_and_dream_never_modulates(self):
        e=self.ev();self.n.touch('route',e)
        self.n.signal(e,path='route',task_success=1.,cost_error=.5)
        g=self.n.gate('route');self.assertEqual(g['modulator']['epistemic'],0.);self.assertAlmostEqual(g['modulator']['instrumental'],.8,6)
        e2=self.ev();self.n.touch('world_predictor',e2);self.n.signal(e2,path='world_predictor',source_class='dream',surprise=1.,task_success=1.)
        self.assertEqual(self.n.gate('world_predictor')['modulator']['combined'],0.)
    def test_provisional_counts_half_and_bad_channels_are_rejected(self):
        e=self.ev();self.n.touch('world_predictor',e)
        self.n.signal(e,path='world_predictor',source_class='real_deterministic_outcome',finality='PROVISIONAL',world_prediction_error=1.)
        self.assertAlmostEqual(self.n.gate('world_predictor')['modulator']['epistemic'],N.PROVISIONAL,6)
        with self.assertRaises(ValueError):self.n.signal(e,path='route',reward=1.)
        with self.assertRaises(ValueError):self.n.signal(e,path='route',source_class='oracle',evidence_gain=1.)
        with self.assertRaises(ValueError):self.n.signal(e,path='route',finality='MAYBE',evidence_gain=1.)

class GateTests(Base):
    def shadow_cfg(self):return self.r.cfg|{'learning_mode':'SHADOW_UPDATE'}
    def test_veto_blocks_budget_decays_and_can_be_cleared(self):
        e=self.ev();self.n.touch('route',e,authority='EXPLICIT_HUMAN_LEARN');self.n.signal(e,path='route',safety_veto=True)
        g=self.n.gate('route');self.assertTrue(g['veto']);self.assertEqual(g['factor'],0.)
        with self.assertRaises(ValueError):self.r.learner.plasticity.budget('route',self.shadow_cfg(),uid('upd'),{'base_generation':self.r.store.generation_id},g)
        self.events(10);self.assertFalse(self.n.gate('route')['veto'])  # 0.93^10 < VETO_BLOCK
        self.n.signal(self.ev(),path='route',rule_violation=1.)
        self.assertTrue(self.n.gate('route')['veto']);self.n.clear_veto('route');self.assertFalse(self.n.gate('route')['veto'])
    def test_budget_scales_by_gain_times_factor_and_observe_validates_it(self):
        r=self.r;cfg=self.shadow_cfg();e=self.ev();self.n.touch('route',e,authority='EXPLICIT_HUMAN_LEARN');g=self.n.gate('route')
        id_=uid('upd');manifest={'component':'route','base_generation':r.store.generation_id,'metrics':{'retention_pass':True,'commit_eligible':True,'max_applied_step_norm':.001}}
        eff=r.learner.plasticity.budget('route',cfg,id_,manifest,g);pol=manifest['training_policy']
        self.assertEqual(eff['learning_rate'],max(KNOBS['learning_rate'][2],cfg['learning_rate']*pol['plasticity_gain']*g['factor']))
        self.assertLess(eff['learning_rate'],cfg['learning_rate']);self.assertEqual(pol['neuromodulation']['factor'],g['factor'])
        manifest['metrics'].update(effective_learning_rate=pol['effective_learning_rate'],effective_max_update_norm=pol['effective_max_update_norm'])
        p=r.home/'checkpoints'/('head-'+id_+'.fixture');p.parent.mkdir(exist_ok=True);p.write_bytes(b'fixture')
        with r.store.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(id_,r.store.generation_id,'PENDING_APPROVAL',str(p.relative_to(r.home)),file_hash(p),dumps(manifest),0.))
        self.assertTrue(r.learner.plasticity.observe(id_))
        # Any tampered factor makes the trial non-evidence.
        id2=uid('upd');m2={'component':'route','base_generation':r.store.generation_id,'metrics':{'retention_pass':True,'commit_eligible':True}}
        r.learner.plasticity.budget('route',cfg,id2,m2,g);m2['training_policy']['neuromodulation']['factor']=1.
        m2['metrics'].update(effective_learning_rate=m2['training_policy']['effective_learning_rate'],effective_max_update_norm=m2['training_policy']['effective_max_update_norm'])
        p2=r.home/'checkpoints'/('head-'+id2+'.fixture');p2.write_bytes(b'fixture2')
        with r.store.tx() as c:c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',(id2,r.store.generation_id,'PENDING_APPROVAL',str(p2.relative_to(r.home)),file_hash(p2),dumps(m2),0.))
        self.assertFalse(r.learner.plasticity.observe(id2))
    def test_learner_training_config_uses_gate_and_record_only_stays_closed(self):
        r=self.r;r.cfg['learning_mode']='SHADOW_UPDATE'
        try:
            m={'base_generation':r.store.generation_id};r.learner.training_config('wake',uid('upd'),m)
            self.assertEqual(m['training_policy']['neuromodulation']['path_id'],'wake')
            self.n.signal(self.ev(),path='wake',safety_veto=True)
            with self.assertRaises(ValueError):r.learner.training_config('wake',uid('upd'),{'base_generation':r.store.generation_id})
        finally:r.cfg['learning_mode']='RECORD_ONLY'
        with self.assertRaises(ValueError):r.learner.training_config('route',uid('upd'),{'base_generation':r.store.generation_id})
    def test_retention_failures_reopen_age_plasticity(self):
        from v13.age import AgeControl
        n=N.Neuromod(self.r.store,AgeControl(self.r.store,self.r.cfg))
        e=self.ev();n.touch('world_predictor',e)
        before=n.gate('world_predictor')['repeated_errors']
        n.signal(e,path='world_predictor',source_class='real_deterministic_outcome',retention=-1.)
        g=n.gate('world_predictor');self.assertEqual(g['repeated_errors'],before+1);self.assertEqual(g['age_plasticity'],1.)

class ConsolidationTagTests(Base):
    def test_single_surprise_never_tags_and_confirmations_plus_stability_do(self):
        e=self.ev();self.n.touch('weights',e)
        self.n.signal(e,path='weights',source_class='real_deterministic_outcome',surprise=1.,retention=1.)
        self.assertEqual(self.n.tags(),{})
        for i in range(N.TAG_CONFIRMATIONS-1):self.n.signal(self.ev(str(i)),path='weights',source_class='human_correction',human_correction=1.)
        self.assertEqual(self.n.tags(),{'weights':'CONFIRMED_STABLE'})
        self.n.signal(self.ev(),path='weights',source_class='real_deterministic_outcome',retention=-1.)
        self.assertEqual(self.n.tags(),{})
    def test_provisional_or_dream_confirmations_do_not_count(self):
        for i in range(5):
            self.n.signal(self.ev(str(i)),path='weights',source_class='dream',evidence_gain=1.,retention=1.)
            self.n.signal(self.ev('p'+str(i)),path='weights',source_class='human_correction',finality='PROVISIONAL',human_correction=1.)
        self.assertEqual(self.n.tags(),{})

class SleepAndHookTests(Base):
    def test_sleep_ends_fast_traces_keeps_tags_and_prunes_dead_paths(self):
        e=self.ev();self.n.touch('route',e);self.n.touch('halt',e)
        for i in range(3):self.n.signal(self.ev(str(i)),path='weights',source_class='human_correction',human_correction=1.,retention=1.)
        self.assertIn('weights',self.n.tags())
        out=self.n.sleep();st=self.r.store.state(N.KEY)[0]
        self.assertEqual(st['paths']['route']['fast'],0.);self.assertIn('weights',out['tagged'])
        for _ in range(60):self.n.sleep()
        self.assertNotIn('route',self.r.store.state(N.KEY)[0]['paths']);self.assertIn('weights',self.n.tags())
    def test_sleep_c_reports_neuromodulation_and_operator_command(self):
        self.n.touch('route',self.ev())
        cyc=self.r.sleep.cycle;rep=cyc.sleep_c(cyc.queue.load()[0],cyc.policy())
        self.assertEqual(rep['status'],'DONE');self.assertIn('paths',rep['neuromodulation'])
        op=Operator(self.r);self.assertIn('n10-neuromod-v1',op.run(':neuromod status'));self.assertIn('"route"',op.run(':neuromod path route'))
    def test_ag6_stage_traces_veto_blocks_and_gate_failure_reopens_path(self):
        class Trainer:
            method='fixture'
            def fit(self,items,base,cancel=None,deadline=None):return {'artifact':'x','hash':'h','method':'fixture','metrics':{'kl_to_base':.5}}
        w=WeightConsolidation(self.r.store,self.r.cfg|{'learning_mode':'SHADOW_UPDATE'},trainer=Trainer(),home=self.home)
        ref={'source_id':'s','sha256':'0'*64,'char_start':0,'char_end':1,'modality':'text'}
        w.candidates=lambda require_replay_pass=True,**kw:[{'memory_id':'m1','event_id':'e1','kind':'fact','prompt':'p','target':'t','source_ref':ref}]
        st=w.stage('USER');self.assertEqual(st['status'],'STAGED')
        self.assertGreater(self.n.gate('weights')['eligibility'],.5);self.assertIn('neuromodulation',w.batch(st['batch_id']))
        w.train(st['batch_id']);w.gate(st['batch_id'],{'overall':.8},{'overall':.8},learned_recall=.9)  # drift .5 fails
        self.assertEqual(w.batch(st['batch_id'])['status'],'GATE_FAIL');self.assertEqual(self.n.gate('weights')['repeated_errors'],1)
        self.n.signal(self.ev(),path='weights',safety_veto=True)
        w.candidates=lambda require_replay_pass=True,**kw:[{'memory_id':'m2','event_id':'e2','kind':'fact','prompt':'q','target':'u','source_ref':ref}]
        self.assertEqual(w.stage('USER')['status'],'SKIPPED_MODULATOR_VETO')

if __name__=='__main__':unittest.main()

class LocalErrorAndMeta(unittest.TestCase):
    """WP-T12: signed per-sample δ (r - r̂), mapped error level, §68 metaplasticity rule + learned head (SHADOW)."""
    def test_delta_meta_and_modes(self):
        import tempfile
        from pathlib import Path
        from v13.config import initialize
        from v13.store import Store
        from v13 import neuromod as N
        with tempfile.TemporaryDirectory() as t:
            initialize(Path(t));s=Store(Path(t));n=N.Neuromod(s);sess=s.new_session()
            try:
                eid=lambda i:s.event(sess,'x'+str(i))['event_id']
                e=eid(0);n.touch('route',e);n.signal(e,path='route',source_class='real_deterministic_outcome',task_success=1.)
                up=n.local_update('route');self.assertGreater(up['delta'],0);self.assertGreater(up['scale'],0)
                e=eid(1);n.touch('route',e);n.signal(e,path='route',source_class='real_deterministic_outcome',task_success=0.)
                down=n.local_update('route');self.assertLess(down['delta'],0);self.assertLess(down['scale'],0)
                self.assertEqual(n.local_update('route',delta=.5)['delta'],.5)
                e=eid(2);n.signal(e,path='world_predictor',source_class='real_deterministic_outcome',world_prediction_error=.8)
                self.assertGreater(n.gate('world_predictor')['error_level'],0)
                g=n.gate('route');self.assertEqual(g['meta']['mode'],'SHADOW');self.assertIsNone(g['meta']['learned_p_help'])
                f=dict(g['meta']['features']);hi=N.Neuromod.meta_rule(f|{'stability':1.,'novelty':0.,'repeated_errors':0.});lo=N.Neuromod.meta_rule(f|{'stability':0.,'novelty':1.,'repeated_errors':1.})
                self.assertLess(hi,lo)
                with self.assertRaises(PermissionError):n.set_meta_mode('ACTIVE')
                factor_shadow=g['factor'];n.set_meta_mode('ACTIVE','EXPLICIT_HUMAN')
                self.assertLessEqual(n.gate('route')['factor'],max(factor_shadow,N.EPS))
                # learned head: features snapshotted at the trace, labelled by the next retention result
                for i in range(10):
                    e=eid(10+i);n.touch('weights',e)
                    s.add_packet('PlasticityState',N.packet('PlasticityState','F7_PLASTICITY',e,s.generation_id,[],component='weights',consolidation_ready=False,retention_pass=i%3!=0,**{k:v for k,v in N_extra().items()}))
                n.sync();self.assertIsNotNone(n.gate('weights')['meta']['learned_p_help'])
            finally:s.close()

def N_extra():
    return {'update_id':'u','trials':1,'plasticity_gain':1.,'stability_score':.5,'saturation':None,'semantic_truth_authority':False}
