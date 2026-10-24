"""Run29: actual SQLite data path with synthetic digital actions, no LLM/device."""
import importlib.util
import json
import math
from pathlib import Path
import random
import sqlite3
import sys
import tempfile
import types
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
pkg=types.ModuleType('run29_isolated');pkg.__path__=[str(SCRIPTS)];sys.modules[pkg.__name__]=pkg
common=types.ModuleType('run29_isolated.common');common.now=lambda:0.;sys.modules[common.__name__]=common
spec=importlib.util.spec_from_file_location('run29_isolated.world_model',SCRIPTS/'world_model.py')
W=importlib.util.module_from_spec(spec);sys.modules[spec.name]=W;spec.loader.exec_module(W)

class SQLiteStore:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,event_id TEXT,status TEXT,expected TEXT,outcome TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS packets(kind TEXT,event_id TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS logs(kind TEXT,event_id TEXT,payload TEXT);''')
    def rows(self,sql,args):return [dict(x) for x in self.db.execute(sql,args).fetchall()]
    def one(self,sql,args):
        x=self.db.execute(sql,args).fetchone()
        return dict(x) if x else None
    def set_state(self,key,value):
        self.db.execute('INSERT OR REPLACE INTO kv(key,value) VALUES (?,?)',(key,json.dumps(value,allow_nan=False)))
        self.db.commit()
    def state(self,key,default):
        r=self.db.execute('SELECT value FROM kv WHERE key=?',(key,)).fetchone()
        return (json.loads(r['value']) if r else default,None)
    def log(self,kind,event_id,payload):
        self.db.execute('INSERT INTO logs(kind,event_id,payload) VALUES (?,?,?)',(kind,event_id,json.dumps(payload)))
        self.db.commit()
    def add(self,aid,route,input_chars,duration,characters,created,latent=None,raw_expected=None):
        forecast={'input_chars':input_chars,'resource_state':'NORMAL',
                  'learned_latent_prediction':{'latent':latent}}
        expected=raw_expected if raw_expected is not None else json.dumps({'forecast':forecast})
        self.db.execute('INSERT INTO actions VALUES (?,?,?,?,?,?)',(aid,aid,'FINAL',expected,
                       json.dumps({'action_duration_s':duration,'characters':characters}),created))
        self.db.execute('INSERT INTO packets VALUES (?,?,?)',('ActionSelection',aid,json.dumps({'route_hint':route})))
        self.db.commit()
    def close(self):self.db.close()

class WorldSQLiteIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'v13.sqlite'
        self.store=SQLiteStore(self.path)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def populate(self,n=160,latent=False):
        rng=random.Random(123)
        for i in range(n):
            route=W.ACTIONS[i%4]
            chars=rng.randint(50,500)
            dur=(1.+i%4)*(1+chars/1000)
            target=[math.log1p(dur),1.,math.log1p(100+i)/8]
            lat=target if latent else None
            self.store.add(f'event-{i}',route,chars,dur,100+i,1700000000+i*3600,lat)
    def test_real_sqlite_fit_persists_and_reloads(self):
        self.populate()
        state=W.fit(self.store,rng_seed=17)
        self.assertEqual(state['status'],'FITTED')
        self.assertEqual(state['n'],160)
        self.assertGreater(state['metrics']['held_out'],0)
        self.assertEqual(state['metrics']['state_align']['status'],'UNAVAILABLE')
        self.store.close();self.store=SQLiteStore(self.path)
        loaded=W.load(self.store)
        self.assertEqual(loaded['n'],160)
        q=W.counterfactual(self.store,W.state_vec(250,'NORMAL',12),'detail')
        self.assertEqual(q['authority'],'HYPOTHESIS')
        self.assertTrue(0<=q['confidence']<=1)
        self.assertTrue(math.isfinite(q['prediction']['duration_s']))
    def test_malformed_rows_are_not_training_examples(self):
        self.populate(n=80)
        self.store.add('bad-duration','detail',100,-2,10,1700000000)
        self.store.add('bad-input','gist',float('nan'),2,10,1700000001)
        self.store.add('bad-json','both',100,2,10,1700000002,raw_expected='{"forecast":oops}')
        state=W.fit(self.store,rng_seed=1)
        self.assertEqual(state['n'],80)
        self.assertEqual(sum(state['counts'].values()),80)
        self.assertTrue(all(math.isfinite(v) for v in state['metrics']['forward_mae'].values()))
    def test_latent_probe_only_with_actual_latent_rows(self):
        self.populate(n=80,latent=True)
        state=W.fit(self.store)
        self.assertEqual(state['metrics']['state_align']['status'],'MEASURED')
        self.assertTrue(all(math.isfinite(v) for v in state['metrics']['state_align']['r2'].values()))
    def test_for_event_rejects_corrupt_sqlite_state(self):
        self.store.add('bad-event','detail',-20,2,10,1700000000)
        r=W.for_event(self.store,'bad-event','detail')
        self.assertEqual(r['reason'],'INVALID_OBSERVED_STATE')
        self.assertEqual(r['authority'],'HYPOTHESIS')
    def test_recovery_after_reopen_without_fit(self):
        self.populate(n=2)
        state=W.fit(self.store)
        self.assertEqual(state['status'],'TOO_FEW_TRANSITIONS')
        self.store.close();self.store=SQLiteStore(self.path)
        r=W.counterfactual(self.store,W.state_vec(100),'gist')
        self.assertEqual(r['reason'],'NO_WORLD_MODEL')
        self.assertEqual(r['confidence'],0.)

    def test_corrupt_persisted_weights_never_supported(self):
        self.populate(n=80)
        st=W.fit(self.store)
        st['forward'][0][0][0]=float('nan')
        # JSON layer used by V13 may persist legacy NaN: readout must refuse it.
        self.store.db.execute('UPDATE kv SET value=? WHERE key=?',(json.dumps(st),W.KEY))
        self.store.db.commit()
        self.store.close();self.store=SQLiteStore(self.path)
        r=W.counterfactual(self.store,W.state_vec(200),'detail')
        self.assertEqual(r['label'],'SIMULATION_UNCERTAIN')
        self.assertEqual(r['reason'],'INVALID_MODEL_STATE')
        self.assertEqual(r['confidence'],0.)

    def test_valid_for_event_prediction_is_hypothesis(self):
        self.populate(n=80)
        W.fit(self.store)
        r=W.for_event(self.store,'event-11','detail')
        self.assertEqual(r['authority'],'HYPOTHESIS')
        self.assertIn(r['label'],('SIMULATION_SUPPORTED','SIMULATION_UNCERTAIN'))
        self.assertIsNotNone(r['prediction'])

if __name__=='__main__':unittest.main()
