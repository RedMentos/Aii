"""WP-T8: control-grounded world model (forward/inverse/state-align/outcome), coverage-based counterfactuals, live goals/curiosity."""
import json
import math
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock
from v13.runtime import Runtime
from v13 import world_model as WM
from v13 import authority as AU

def synthetic(n=160,seed=0,latent=False):
    rng=random.Random(seed);out=[]
    cost={'simple':.5,'detail':3.,'gist':1.5,'both':4.}
    for i in range(n):
        a=WM.ACTIONS[i%4] if i%5 else 'detail';chars=rng.randint(20,2000);s=WM.state_vec(chars,'NORMAL',rng.uniform(0,24))
        dur=cost[a]*(1+chars/1000)*rng.uniform(.9,1.1);y=[math.log1p(dur),1.,math.log1p(200*cost[a])/8]
        out.append({'action_id':'a%d'%i,'s':s,'a':a,'y':y,'latent':[y[0]+rng.gauss(0,.01),y[2],1.] if latent else None})
    return out

class SyntheticStore:
    """Pure numerical fixture: no source reader, no production persistence."""
    def __init__(self):self.data={}
    def set_state(self,key,payload,expected=None):
        self.data[key]=json.loads(json.dumps(payload))
    def state(self,key,default=None):return self.data.get(key,default),1
    def log(self,kind,event,payload):pass


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled','off')
    def tearDown(self):self.r.close();self.tmp.cleanup()

class Objectives(Base):
    def test_forward_inverse_outcome_and_align_unavailable_without_latent(self):
        synthetic_store=SyntheticStore()
        with mock.patch.object(WM,'transitions',return_value=synthetic()):st=WM.fit(synthetic_store)
        m=st['metrics'];self.assertEqual(st['status'],'FITTED')
        self.assertEqual(st['evidence_scope'],'SYNTHETIC_TEST_ONLY')
        self.assertIsNone(WM.load(self.r.store))
        self.assertLess(m['forward_mae']['log_duration'],.5*m['forward_baseline_mae']['log_duration'])
        self.assertGreater(m['inverse_accuracy'],m['inverse_majority_baseline']+.2);self.assertIn('not a causal claim',m['inverse_note'])
        self.assertEqual(m['state_align']['status'],'UNAVAILABLE')
        with mock.patch.object(WM,'transitions',return_value=synthetic(latent=True)):st=WM.fit(synthetic_store)
        self.assertEqual(st['metrics']['state_align']['status'],'MEASURED');self.assertGreater(st['metrics']['state_align']['r2']['log_duration'],.9)
    def test_too_few_transitions_is_honest(self):
        self.assertEqual(WM.fit(self.r.store)['status'],'TOO_FEW_TRANSITIONS')
        cf=WM.counterfactual(self.r.store,WM.state_vec(100),'detail');self.assertEqual((cf['label'],cf['reason']),('SIMULATION_UNCERTAIN','NO_WORLD_MODEL'))
        self.assertEqual(WM.for_event(self.r.store,'nope','gist')['reason'],'NO_OBSERVED_STATE')

class Counterfactuals(Base):
    def test_confidence_follows_coverage_not_frequency(self):
        data=synthetic()+[{'action_id':'rare','s':WM.state_vec(500,'NORMAL',12.),'a':'both','y':[1.,1.,.5],'latent':None}]
        data=[t for t in data if t['a']!='both' or t['action_id']=='rare']
        synthetic_store=SyntheticStore()
        with mock.patch.object(WM,'transitions',return_value=data):WM.fit(synthetic_store)
        s=WM.state_vec(800,'NORMAL',12.)
        good=WM.counterfactual(synthetic_store,s,'detail');rare=WM.counterfactual(synthetic_store,s,'both')
        far=WM.counterfactual(synthetic_store,WM.state_vec(10**9,'CRITICAL',3.),'detail')
        self.assertEqual(good['label'],'SIMULATION_SUPPORTED');self.assertGreaterEqual(good['confidence'],WM.CF_MIN)
        self.assertEqual(rare['label'],'SIMULATION_UNCERTAIN');self.assertLess(rare['confidence'],good['confidence'])
        self.assertEqual(far['label'],'SIMULATION_UNCERTAIN');self.assertFalse(far['coverage']['in_support'])
        self.assertTrue(all(x['cause']=='SELF_CAUSED' and x['authority']=='HYPOTHESIS' for x in (good,rare,far)))
        self.assertGreater(good['prediction']['duration_s'],WM.counterfactual(synthetic_store,s,'simple')['prediction']['duration_s'])
    def test_dream_route_alternative_carries_counterfactual_and_priority(self):
        e=self.r.store.event(self.r.session,'Erkläre Projekt Aurora genau');self.r.memory.feedback(e['event_id'],'route','detail')
        b=self.r.sleep.cycle.run('b',origin='USER')['phases'][0];h=b['hypotheses'][0]
        p=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='ReplayItem' AND json_extract(payload,'$.replay_id')=? AND json_extract(payload,'$.stage')='QUEUED'",(h['replay_id'],))['payload'])
        self.assertEqual(p['hypothesis']['counterfactual']['label'],'SIMULATION_UNCERTAIN');self.assertEqual(p['priority'],.2)

class LiveGoals(Base):
    def test_unresolved_turn_opens_user_goal_and_later_answer_closes_it(self):
        from v13.agi import live,hub
        e=self.r.store.event(self.r.session,'Plane das Budget für Projekt Aurora im Mai')
        live.goal_turn(self.r,e,{},'ERROR');g=hub(self.r)
        open_=g.goals.tree('OPEN');self.assertEqual(len(open_),1);self.assertEqual(open_[0]['origin'],'USER')
        live.goal_turn(self.r,e,{},'ERROR');self.assertEqual(len(g.goals.tree('OPEN')),1)  # one goal per event
        e2=self.r.store.event(self.r.session,'Plane das Budget für Projekt Aurora im Mai bitte')
        mid=self.r.store.message(self.r.session,e2['event_id'],'assistant','Budgetplan für Aurora erstellt')
        self.r.store.finish_message(mid,'FINAL',{})
        live.goal_turn(self.r,e2,{},'FINAL');self.assertEqual(g.goals.tree('DONE')[0]['id'],open_[0]['id'])
        self.assertEqual(g.curiosity.values()['route:unknown']['error'],0.)
    def test_learn_medium_fits_world_and_keeps_curiosity_age_gated(self):
        out=AU.job(self.r,'learn_medium');self.assertEqual(out['world_model'],'TOO_FEW_TRANSITIONS');self.assertIsNone(out['curiosity'])
        self.assertNotIn('practice_event',out)

if __name__=='__main__':unittest.main()
