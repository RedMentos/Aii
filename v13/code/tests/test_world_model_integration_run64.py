"""Run64: actual production world_model import + synthetic SQLite Store path."""
import json
import math
import sqlite3
import unittest
import numpy as np
from v13 import world_model as W


class Store:
    def __init__(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''CREATE TABLE actions(id TEXT PRIMARY KEY,event_id TEXT,status TEXT,expected TEXT,outcome TEXT,created REAL);
            CREATE TABLE packets(kind TEXT,event_id TEXT,payload TEXT,created REAL);
            CREATE TABLE kv(key TEXT PRIMARY KEY,value TEXT);
            CREATE TABLE logs(kind TEXT,event_id TEXT,payload TEXT);''')
    def rows(self,q,args):return [dict(x) for x in self.db.execute(q,args).fetchall()]
    def one(self,q,args):
        x=self.db.execute(q,args).fetchone()
        return dict(x) if x else None
    def set_state(self,k,v):self.db.execute('INSERT OR REPLACE INTO kv VALUES (?,?)',(k,json.dumps(v)));self.db.commit()
    def state(self,k,default):
        x=self.db.execute('SELECT value FROM kv WHERE key=?',(k,)).fetchone()
        return (json.loads(x['value']) if x else default,0)
    def log(self,k,e,p):self.db.execute('INSERT INTO logs VALUES (?,?,?)',(k,e,json.dumps(p)));self.db.commit()
    def add(self,i,chars=100,duration=1.,output=20,created=1000.,route='simple',latent=None):
        fc={'forecast':{'input_chars':chars,'resource_state':'NORMAL'}}
        if latent is not None:fc['forecast']['learned_latent_prediction']={'latent':latent}
        self.db.execute('INSERT INTO actions VALUES (?,?,?,?,?,?)',(str(i),'e'+str(i),'FINAL',json.dumps(fc),json.dumps({'action_duration_s':duration,'characters':output}),created+i))
        if route is not None:self.db.execute('INSERT INTO packets VALUES (?,?,?,?)',('ActionSelection','e'+str(i),json.dumps({'route_hint':route}),created+i-.01))
        self.db.commit()


def fitted(log_duration=.5,success=.8,log_chars=.3):
    mat=np.zeros((W.ENSEMBLE,9,3));mat[:,0,:]=[log_duration,success,log_chars]
    return {'status':'FITTED','forward':mat.tolist(),'states':{a:[[0.,0.,0.,0.]]*20 for a in W.ACTIONS}}


class WorldRun64(unittest.TestCase):
    def test_valid_sqlite_transition(self):
        s=Store();s.add(1)
        rows=W.transitions(s)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['a'],'simple')
        self.assertTrue(all(math.isfinite(v) for v in rows[0]['s']+rows[0]['y']))

    def test_bad_durations_and_chars_skipped(self):
        s=Store();s.add(1,duration=-1);s.add(2,output=-2);s.add(3,duration=float('nan'))
        self.assertEqual(W.transitions(s),[])

    def test_bad_input_chars_and_created_skipped(self):
        s=Store();s.add(1,chars=float('nan'));s.add(2,chars=-1);s.add(3,created=-10000)
        self.assertEqual(W.transitions(s),[])

    def test_missing_route_skipped(self):
        s=Store();s.add(1,route=None)
        self.assertEqual(W.transitions(s),[])

    def test_malformed_json_skipped(self):
        s=Store();s.add(1)
        s.db.execute('UPDATE actions SET outcome=? WHERE id=?',('{bad','1'));s.db.commit()
        self.assertEqual(W.transitions(s),[])

    def test_bad_latent_does_not_promote(self):
        s=Store();s.add(1,latent=[float('nan')])
        self.assertIsNone(W.transitions(s)[0]['latent'])

    def test_sqlite_fit_with_valid_rows(self):
        s=Store()
        for i in range(24):s.add(i,chars=30+i,duration=.2+i*.02,output=10+i,route=W.ACTIONS[i%4])
        result=W.fit(s,rng_seed=42)
        self.assertEqual(result['status'],'FITTED')
        self.assertEqual(result['n'],24)
        self.assertGreater(result['metrics']['held_out'],0)
        self.assertEqual(W.load(s)['revision'],W.REVISION)

    def test_for_event_bad_observed_state_uncertain(self):
        s=Store();s.add(1,chars=float('nan'))
        r=W.for_event(s,'e1','simple')
        self.assertEqual(r['reason'],'INVALID_OBSERVED_STATE')
        self.assertEqual(r['authority'],'HYPOTHESIS')

    def test_counterfactual_negative_duration_uncertain(self):
        r=W.counterfactual(None,[0.]*4,'simple',fitted(log_duration=-.3))
        self.assertEqual(r['reason'],'IMPOSSIBLE_PREDICTED_OUTCOME')
        self.assertEqual(r['confidence'],0.)
        self.assertIsNone(r['prediction'])

    def test_counterfactual_success_over_one_uncertain(self):
        r=W.counterfactual(None,[0.]*4,'simple',fitted(success=1.2))
        self.assertEqual(r['reason'],'IMPOSSIBLE_PREDICTED_OUTCOME')

    def test_counterfactual_negative_chars_uncertain(self):
        r=W.counterfactual(None,[0.]*4,'simple',fitted(log_chars=-.1))
        self.assertEqual(r['reason'],'IMPOSSIBLE_PREDICTED_OUTCOME')

    def test_valid_supported_prediction_unchanged(self):
        r=W.counterfactual(None,[0.]*4,'simple',fitted())
        self.assertEqual(r['label'],'SIMULATION_SUPPORTED')
        self.assertGreater(r['confidence'],.5)
        self.assertEqual(r['authority'],'HYPOTHESIS')
        self.assertGreaterEqual(r['prediction']['duration_s'],0.)

    def test_nonfinite_model_uncertain(self):
        st=fitted();st['forward'][0][0][0]=float('nan')
        r=W.counterfactual(None,[0.]*4,'simple',st)
        self.assertEqual(r['reason'],'INVALID_MODEL_STATE')

    def test_no_model_uncertain(self):
        r=W.counterfactual(Store(),[0.]*4,'simple',None)
        self.assertEqual(r['reason'],'NO_WORLD_MODEL')


if __name__=='__main__':unittest.main()
