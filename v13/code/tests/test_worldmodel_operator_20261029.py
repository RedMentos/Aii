"""Read-only operator lane for observed World-Model status and own-session event counterfactuals."""
import json
import tempfile
import unittest
from pathlib import Path
from v13.runtime import Runtime
from v13.operator import Operator
from v13.contracts import packet
from v13 import world_model as WM


class WorldModelOperatorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.r=Runtime(Path(self.temp.name))
        self.op=Operator(self.r)
    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def test_status_is_readonly_without_fit(self):
        before=self.r.store.state(WM.KEY)
        result=json.loads(self.op.run(':worldmodel status'))
        self.assertEqual(result['status'],'NOT_FITTED')
        self.assertEqual(self.r.store.state(WM.KEY),before)
        self.assertEqual(self.r.cfg['learning_mode'],'RECORD_ONLY')

    def test_existing_action_outcome_is_read_only_hypothesis(self):
        event=None
        for i in range(48):
            route=WM.ACTIONS[i%4]
            e=self.r.store.event(self.r.session,'Observed route '+str(i))
            self.r.store.add_packet('ActionSelection',packet('ActionSelection','C5_ACTION_GATE',
                e['event_id'],e['brain_generation_id'],[e['source_ref']],
                selected={'action_id':'TEXT_REPORT','action_type':'TEXT_REPORT',
                          'score':0.,'permission_class':'local_text_only','focal_support':0.},
                candidates=[],suppressed=[],permission_class='local_text_only',route_hint=route))
            aid=self.r.store.start_action(e['event_id'],e['brain_generation_id'],
                forecast={'input_chars':100+5*i,'resource_state':'NORMAL'})
            self.r.store.finish_action(aid,'FINAL',{'action_duration_s':1+i/100,'characters':80+2*i})
            if i==4:event=e['event_id']
        st=WM.fit(self.r.store,rng_seed=17)
        self.assertEqual(st['status'],'FITTED')
        state_before=self.r.store.state(WM.KEY)
        packets_before=self.r.store.one('SELECT COUNT(*) AS n FROM packets')['n']
        actions_before=self.r.store.one('SELECT COUNT(*) AS n FROM actions')['n']
        report=json.loads(self.op.run(':worldmodel'))
        self.assertEqual(report['status'],'FITTED')
        result=json.loads(self.op.run(':worldmodel event '+event+' simple'))
        self.assertEqual(result['authority'],'HYPOTHESIS')
        self.assertEqual(result['cause'],'SELF_CAUSED')
        self.assertIsNotNone(result['prediction'])
        compared=json.loads(self.op.run(':worldmodel compare '+event))
        self.assertEqual(compared['status'],'READ_ONLY_COUNTERFACTUALS')
        self.assertEqual(compared['authority'],'HYPOTHESIS')
        self.assertFalse(compared['decision_authority'])
        self.assertFalse(compared['ranked'])
        self.assertNotIn('selection',compared)
        self.assertEqual(set(compared['routes']),set(WM.ACTIONS))
        self.assertEqual(compared['routes']['simple'],result)
        for route,forecast in compared['routes'].items():
            self.assertEqual(forecast['action'],route)
            self.assertEqual(forecast['authority'],'HYPOTHESIS')
            self.assertEqual(forecast['cause'],'SELF_CAUSED')
        self.assertEqual(self.r.store.state(WM.KEY),state_before)
        self.assertEqual(self.r.store.one('SELECT COUNT(*) AS n FROM packets')['n'],packets_before)
        self.assertEqual(self.r.store.one('SELECT COUNT(*) AS n FROM actions')['n'],actions_before)
        self.assertEqual(self.r.cfg['learning_mode'],'RECORD_ONLY')
        self.assertEqual(self.r.pool.pids(),[])

    def test_unknown_or_foreign_event_is_not_revealed(self):
        other=self.r.store.new_session()
        e=self.r.store.event(other,'Foreign session event')
        for eid in ('not-an-event',e['event_id']):
            with self.subTest(eid=eid),self.assertRaisesRegex(ValueError,'aktuellen Chat'):
                self.op.run(':worldmodel event '+eid+' detail')
            with self.subTest(eid=eid),self.assertRaisesRegex(ValueError,'aktuellen Chat'):
                self.op.run(':worldmodel compare '+eid)
        with self.assertRaises(ValueError):self.op.run(':worldmodel event '+e['event_id']+' bad')
        with self.assertRaises(ValueError):self.op.run(':worldmodel nope')


    def test_unfitted_same_session_comparison_never_invents_support(self):
        e=self.r.store.event(self.r.session,'Observed but not trained')
        aid=self.r.store.start_action(
            e['event_id'],e['brain_generation_id'],
            forecast={'input_chars':25,'resource_state':'NORMAL'})
        self.r.store.finish_action(
            aid,'FINAL',{'action_duration_s':1.0,'characters':40})
        before=self.r.store.state(WM.KEY)
        result=json.loads(self.op.run(':worldmodel compare '+e['event_id']))
        self.assertEqual(set(result['routes']),set(WM.ACTIONS))
        for cf in result['routes'].values():
            self.assertEqual(cf['reason'],'NO_WORLD_MODEL')
            self.assertEqual(cf['label'],'SIMULATION_UNCERTAIN')
            self.assertIsNone(cf['prediction'])
            self.assertEqual(cf['confidence'],0.)
        self.assertEqual(self.r.store.state(WM.KEY),before)
        self.assertEqual(self.r.pool.pids(),[])


if __name__=='__main__':unittest.main()
