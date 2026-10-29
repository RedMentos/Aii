"""Real Store ActionSelection -> CorollaryCopy -> ActionOutcome -> WorldModel fit.

Software-only integration; no model calls or permission to learn at Age 0.
"""
import tempfile
import unittest
from pathlib import Path
from v13.runtime import Runtime
from v13.contracts import packet
from v13 import world_model as WM


class WorldModelObservedStoreIntegration(unittest.TestCase):
    def test_actual_action_packets_are_fitted_and_persisted(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                self.assertEqual(r.cfg['learning_mode'],'RECORD_ONLY')
                actions=WM.ACTIONS
                for i in range(48):
                    a=actions[i%len(actions)]
                    e=r.store.event(r.session,'Synthetic route observation '+str(i))
                    r.store.add_packet('ActionSelection',packet(
                        'ActionSelection','C5_ACTION_GATE',e['event_id'],e['brain_generation_id'],
                        [e['source_ref']],selected={'action_id':'TEXT_REPORT','action_type':'TEXT_REPORT',
                        'score':0.,'permission_class':'local_text_only','focal_support':0.},
                        candidates=[],suppressed=[],permission_class='local_text_only',route_hint=a))
                    aid=r.store.start_action(e['event_id'],e['brain_generation_id'],forecast={
                        'input_chars':100+5*i,'resource_state':'NORMAL'})
                    r.store.finish_action(aid,'FINAL',{'action_duration_s':1.0+i/100,
                                                      'characters':80+2*i})
                T=WM.transitions(r.store)
                self.assertEqual(len(T),48)
                self.assertEqual({a:sum(t['a']==a for t in T) for a in actions},
                                 {a:12 for a in actions})
                st=WM.fit(r.store,rng_seed=17)
                self.assertEqual(st['status'],'FITTED')
                self.assertEqual(st['n'],48)
                self.assertEqual(st['metrics']['held_out'],len(WM._split(48)[1]))
                self.assertEqual(WM.load(r.store)['forward'],st['forward'])
                self.assertEqual(sum(st['train_counts'].values()),len(WM._split(48)[0]))
                self.assertEqual(st['support_scope'],'TRAIN_SPLIT_ONLY_HELDOUT_EXCLUDED')
                cf=WM.counterfactual(r.store,T[4]['s'],T[4]['a'])
                self.assertEqual(cf['authority'],'HYPOTHESIS')
                self.assertEqual(cf['cause'],'SELF_CAUSED')
                self.assertIsNotNone(cf['prediction'])
                self.assertEqual(r.cfg['learning_mode'],'RECORD_ONLY')
            finally:
                r.close()
            reopened=Runtime(Path(d))
            try:
                self.assertEqual(WM.load(reopened.store)['forward'],st['forward'])
                self.assertEqual(len(WM.transitions(reopened.store)),48)
                self.assertEqual(reopened.cfg['learning_mode'],'RECORD_ONLY')
            finally:
                reopened.close()


if __name__=='__main__':unittest.main()
