"""Run262: actual-Store source-bound WorldModel load/counterfactual scaling.

Linux software with synthetic action outcomes; never native model/Redmi proof.
No production source edits and no perf/utility gate promotion.
"""
import hashlib
import json
from pathlib import Path
import statistics
import tempfile
import time

from v13.runtime import Runtime
from v13 import world_model as W


def median_ms(fn, n=5):
    samples = []
    for _ in range(n):
        t0 = time.perf_counter()
        value = fn()
        samples.append((time.perf_counter()-t0)*1000)
    return round(statistics.median(samples), 4), value


def cohort(count):
    with tempfile.TemporaryDirectory(prefix='v13-run262-') as home:
        r = Runtime(Path(home))
        try:
            r.sleep.cycle.set_policy('enabled', 'off')
            ids = []
            for i in range(count):
                text = f'Synthetic observed digital action {i} (no model inference)'
                event = r.store.event(r.session, text)
                eid = event['event_id']
                generation = event['brain_generation_id']
                route = W.ACTIONS[i % len(W.ACTIONS)]
                with r.store.tx() as c:
                    c.execute('INSERT INTO packets VALUES (?,?,?,?,?,?)',
                              (f'run262-select-{i}', 'ActionSelection', eid,
                               generation, json.dumps({'route_hint':route}), time.time()))
                aid = r.store.start_action(
                    eid, generation,
                    forecast={'input_chars':len(text),
                              'resource_state':'NORMAL',
                              'profile':{'role':'C3_LANGUAGE'}})
                r.store.finish_action(
                    aid, 'FINAL',
                    {'action_duration_s':0.2+i*0.0001,
                     'characters':20+i%7, 'role':'C3_LANGUAGE'})
                ids.append(event['source_ref']['source_id'])
            t0 = time.perf_counter()
            fitted = W.fit(r.store, rng_seed=17)
            fit_ms = round((time.perf_counter()-t0)*1000,4)
            assert fitted['status']=='FITTED', fitted['status']
            assert fitted['n']==count
            assert fitted['evidence_scope']=='SOURCE_BOUND_STORE'
            load_ms, loaded = median_ms(lambda: W.load(r.store))
            assert loaded is not None
            state = W.state_vec(50)
            cf_ms, cf = median_ms(lambda: W.counterfactual(r.store,state,'simple'))
            assert cf['authority']=='HYPOTHESIS'
            with r.store.tx() as c:
                c.execute('UPDATE sources SET deleted=1 WHERE id=?',(ids[-1],))
            rev_ms, revoked = median_ms(lambda: W.load(r.store),3)
            assert revoked is None, 'revoked source remained usable'
            explicit = W.counterfactual(r.store,state,'simple',st=fitted)
            assert explicit['prediction'] is None
            assert explicit['reason']=='TRAINING_SOURCE_UNVERIFIED'
            return {'rows':count,'fit_ms':fit_ms,'load_median_ms':load_ms,
                    'counterfactual_median_ms':cf_ms,'revoked_load_median_ms':rev_ms,
                    'rejection_after_revocation':True,
                    'counterfactual_label_before_revocation':cf['label']}
        finally:
            r.close()


def main():
    path=Path(__file__)
    source=Path(__file__).resolve().parents[1]/'v13'/'world_model.py'
    print(json.dumps({'scope':'LINUX_ACTUAL_STORE_SYNTHETIC_ACTIONS',
                      'no_native_model':True,'no_redmi':True,
                      'script_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                      'world_model_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                      'revision':W.REVISION},sort_keys=True),flush=True)
    for n in (16,128,512,1024):
        print(json.dumps(cohort(n),sort_keys=True),flush=True)


if __name__=='__main__':
    main()
