"""WorldModel fitted parameters must not outlive their source evidence.

Actual production Store + synthetic actions. No native model, JEPA or Redmi.
"""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest

from v13.runtime import Runtime
from v13.store import Store
from v13 import world_model as W


class FittedWorldSourceLineage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off')
        self.actions = []
        self.sources = []
        for i in range(24):
            text = f'World observation question {i}: deterministic source?'
            event = self.r.store.event(self.r.session, text)
            eid = event['event_id']
            generation = event['brain_generation_id']
            route = W.ACTIONS[i % 4]
            with self.r.store.tx() as c:
                c.execute('INSERT INTO packets VALUES (?,?,?,?,?,?)',
                          (f'synthetic-action-selection-{i}','ActionSelection',eid,
                           generation,json.dumps({'route_hint':route}),time.time()))
            aid = self.r.store.start_action(
                eid,generation,forecast={'input_chars':len(text),
                                          'resource_state':'NORMAL',
                                          'profile':{'role':'C3_LANGUAGE'}})
            self.r.store.finish_action(
                aid,'FINAL',{'action_duration_s':0.5+i*0.08,
                             'characters':30+i,'role':'C3_LANGUAGE'})
            self.actions.append(aid)
            self.sources.append(event['source_ref']['source_id'])

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def fitted(self):
        st = W.fit(self.r.store,rng_seed=17)
        self.assertEqual(st['status'],'FITTED',st)
        self.assertEqual(st['n'],24)
        self.assertIsNotNone(W.load(self.r.store))
        return st

    def test_actual_store_fit_is_bound_and_survives_restart(self):
        st = self.fitted()
        self.assertEqual(st['revision'],W.REVISION)
        self.assertEqual(len(st['training_bindings']),24)
        self.assertTrue(all(b['action_sha256'] for b in st['training_bindings']))
        # The production Store enforces a single-writer home lock; restart
        # means closing the original Runtime before opening the same home.
        self.r.close()
        self.r = None
        fresh = Store(self.home)
        try:
            self.assertIsNotNone(W.load(fresh))
        finally:
            fresh.close()

    def test_deleted_source_invalidates_fitted_state_and_explicit_st(self):
        st = self.fitted()
        with self.r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?',(self.sources[0],))
        self.assertIsNone(W.load(self.r.store))
        r = W.counterfactual(self.r.store,W.state_vec(80),'simple')
        self.assertIsNone(r['prediction'])
        self.assertEqual(r['label'],'SIMULATION_UNCERTAIN')
        explicit = W.counterfactual(self.r.store,W.state_vec(80),'simple',st=st)
        self.assertIsNone(explicit['prediction'])
        self.assertEqual(explicit['reason'],'TRAINING_SOURCE_UNVERIFIED')

    def test_action_outcome_tamper_invalidates_fitted_state(self):
        self.fitted()
        with self.r.store.tx() as c:
            c.execute('UPDATE actions SET outcome=? WHERE id=?',
                      (json.dumps({'action_duration_s':999,'characters':1,
                                   'role':'C3_LANGUAGE'}),self.actions[0]))
        self.assertIsNone(W.load(self.r.store))

    def test_action_selection_route_tamper_invalidates_fitted_state(self):
        self.fitted()
        # The selected route is part of the learned action input, but lives
        # in ActionSelection rather than in the actions row.
        with self.r.store.tx() as c:
            c.execute(
                "UPDATE packets SET payload=? WHERE kind='ActionSelection' "
                "AND event_id=(SELECT event_id FROM actions WHERE id=?)",
                (json.dumps({'route_hint':'both'}),self.actions[0]))
        self.assertIsNone(W.load(self.r.store))

    def test_model_weight_tamper_invalidates_fitted_state(self):
        self.fitted()
        payload,_ = self.r.store.state(W.KEY)
        payload['forward'][0][0][0] += .125
        self.r.store.set_state(W.KEY,payload)
        self.assertIsNone(W.load(self.r.store))

    def test_old_unbound_revision_is_not_loaded(self):
        self.fitted()
        payload,_ = self.r.store.state(W.KEY)
        payload['revision']='t8-world-model-v1'
        self.r.store.set_state(W.KEY,payload)
        self.assertIsNone(W.load(self.r.store))


if __name__=='__main__':
    unittest.main()
