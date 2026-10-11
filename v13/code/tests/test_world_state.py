"""State/forecast semantics; fixture durations are not hardware measurements."""
import json
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime

class WorldTests(unittest.TestCase):
    def test_restart_repairs_both_action_and_materialized_view_crash_windows(self):
        self.action(2.)
        e=self.r.store.event(self.r.session,'Testfall für die lokale Ausgabe');f=self.r.world.forecast(e,'C3_LANGUAGE');a=self.r.store.start_action(e['event_id'],self.r.store.generation_id,forecast=f)
        self.r.store.finish_action(a,'FINAL',{'action_duration_s':3.,'role':'C3_LANGUAGE'})
        # Simulated termination after durable outcome but before derived state.
        self.r.close();self.r=Runtime(self.home);self.assertEqual(self.r.world.world_state()['observed_action_count'],2)
        with self.r.store.tx() as c:c.execute("DELETE FROM states WHERE key LIKE 'WORLD_STATE:%'")
        self.r.close();self.r=Runtime(self.home);self.assertEqual(self.r.world.world_state()['observed_action_count'],2)
        self.assertEqual(len(self.r.store.rows("SELECT id FROM packets WHERE kind='PredictionOutcome'")),2)
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def action(self,duration,status='FINAL',text='Testfall für die lokale Ausgabe'):
        r=self.r;e=r.store.event(r.session,text);f=r.world.forecast(e,'C3_LANGUAGE');a=r.store.start_action(e['event_id'],r.store.generation_id,forecast=f)
        r.store.finish_action(a,status,{'action_duration_s':duration,'role':'C3_LANGUAGE','model_generated':False})
        outcome=r.world.observe(a);return e,f,a,outcome
    def test_forecast_is_prior_action_bound_and_restart_persistent(self):
        for seconds in [2.,3.,4.]:self.action(seconds)
        e,f,a,o=self.action(5.)
        self.assertEqual(f['sample_count'],3);self.assertEqual(f['duration_median_s'],3.);self.assertEqual(o['timing_error_s'],2.)
        self.assertNotIn(a,f['sample_action_ids']);self.assertFalse(o['causal_claim']);self.assertIsNone(o['semantic_success'])
        state=self.r.world.world_state();self.assertEqual(state['observed_action_count'],4)
        self.r.world.observe(a);self.assertEqual(self.r.world.world_state()['observed_action_count'],4)
        generation=self.r.store.generation();self.r.close();self.r=Runtime(self.home)
        self.assertEqual(self.r.world.world_state(),state);self.assertEqual(self.r.store.generation(),generation)
        self.assertEqual(self.r.world.self_state()['learning']['active_artifact_count'],0)
    def test_failed_and_ood_data_never_become_supported_forecast(self):
        for seconds in [2.,3.,4.]:self.action(seconds,status='DEADLINE')
        e,f,a,o=self.action(2.)
        self.assertEqual(f['failed_action_count'],3);self.assertEqual(f['sample_count'],0);self.assertIsNone(f['duration_median_s'])
        for seconds in [2.,3.,4.]:self.action(seconds)
        e,f,a,o=self.action(3.,text='x'*1500)
        self.assertFalse(f['covered']);self.assertIsNone(f['duration_median_s']);self.assertFalse(o['scored'])
    def test_model_config_and_session_profiles_do_not_mix(self):
        for seconds in [2.,3.,4.]:self.action(seconds)
        self.r.cfg['answer_tokens']+=1
        self.assertEqual(self.action(2.)[1]['sample_count'],0)
        self.r.cfg['answer_tokens']-=1;self.r.session=self.r.store.new_session()
        self.assertEqual(self.action(2.)[1]['sample_count'],0)
    def test_corollary_forecast_precedes_observation(self):
        e,_,a,_=self.action(2.)
        rows=self.r.store.rows('SELECT kind FROM packets WHERE event_id=? ORDER BY created',(e['event_id'],));k=[x['kind'] for x in rows]
        self.assertLess(k.index('ActionPrediction'),k.index('CorollaryCopy'));self.assertLess(k.index('CorollaryCopy'),k.index('PredictionOutcome'))
        self.assertEqual(self.r.store.integrity(True),[])

if __name__=='__main__':unittest.main()
