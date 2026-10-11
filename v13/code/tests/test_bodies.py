"""WP-N11: two distinct bodies through AG0 slots + AG13 residency in the RunnerPool (no native weights)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from v13.runtime import Runtime
from v13 import bodies,runners
from v13.cognition import offer_schema
from v13.agi.slots import ModelSlots

class FakeRunner:
    alive=set()
    def __init__(self,home,role,model,cfg,purpose='generate'):self.role=role;self.model=model;self.purpose=purpose;self.last_metrics={};FakeRunner.alive.add(id(self))
    def pids(self):return [id(self)] if id(self) in FakeRunner.alive else []
    def unload(self):FakeRunner.alive.discard(id(self));return {'process_reaped':True}

def install(home,key,sha,size_mb):
    p=home/'models'/key/(key+'.gguf');p.parent.mkdir(parents=True,exist_ok=True)
    with open(p,'wb') as f:f.truncate(int(size_mb*2**20))
    return {'model_id':key+'-model','exact_revision':'rev-'+key,'license_id':'x','files':{p.name:{'path':str(p.relative_to(home)),'sha256':sha,'size':p.stat().st_size}},'main_file':p.name,'download_complete':True}

class Base(unittest.TestCase):
    budget=1000
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);r=Runtime(self.home);r.close()
        inst={'body':install(self.home,'body',"a"*64,400),'gist':install(self.home,'gist',"b"*64,300),'language':install(self.home,'language',"c"*64,100)}
        (self.home/'config/models.json').write_text(json.dumps(inst))
        cfg=json.loads((self.home/'config/settings.json').read_text());cfg['body_residency_mb']=self.budget;(self.home/'config/settings.json').write_text(json.dumps(cfg))
        self.p=patch.object(runners,'LlamaRunner',FakeRunner);self.p.start();self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off')
    def tearDown(self):self.r.close();self.p.stop();self.tmp.cleanup()

class TwoBodies(Base):
    budget=1300  # B1 536 + B2 426 + C3 206 MB estimated
    def test_distinct_bodies_and_slots_mirror_installed_models(self):
        rep=self.r.bodies.report()
        self.assertTrue(rep['distinct_bodies']);self.assertEqual(rep['bodies']['B2_GIST']['model'],'gist-model')
        self.assertEqual(set(rep['slots']),{'B1_DETAIL','B2_GIST','C3_LANGUAGE'})
        self.r.models.b2_control='shared_body_dual_state';self.assertFalse(bodies.distinct_bodies(self.r.models))

    def test_both_bodies_stay_resident_within_budget_and_c3_is_pinned(self):
        b1=self.r.pool.get('B1_DETAIL');b2=self.r.pool.get('B2_GIST')
        self.assertEqual(sorted(self.r.pool.resident_roles()),['B1_DETAIL','B2_GIST'])
        self.assertIs(self.r.pool.get('B1_DETAIL'),b1)  # HIT: no reload
        self.r.pool.get('C3_LANGUAGE');self.assertEqual(len(self.r.pool.pids()),3)
        self.assertIn('C3_LANGUAGE',self.r.bodies.residency.report()['resident'])
        self.r.pool.unload();self.assertEqual(self.r.pool.pids(),[]);self.assertEqual(len(self.r.pool.release_history),3)

class TightBudget(Base):
    budget=900
    def test_over_budget_evicts_the_least_used_body(self):
        self.r.pool.get('B1_DETAIL');self.r.pool.get('B1_DETAIL');self.r.pool.get('B2_GIST')
        self.assertEqual(self.r.pool.resident_roles(),['B2_GIST'])  # B1 (bigger) had to leave for B2
        self.assertEqual(self.r.pool.release_history[-1]['role'],'B1_DETAIL')

    def test_memory_pressure_never_holds_two_bodies(self):
        self.r.guard.state='CRITICAL';self.r.pool.get('C3_LANGUAGE');self.r.pool.get('B2_GIST')
        self.assertEqual(self.r.pool.resident_roles(),['B2_GIST'])

class OldPool(Base):
    budget=0
    def test_zero_budget_keeps_one_process_at_a_time(self):
        self.r.pool.get('B1_DETAIL');self.r.pool.get('B2_GIST');self.assertEqual(self.r.pool.resident_roles(),['B2_GIST'])

class SlotRouting(Base):
    def test_ramp_candidate_gets_its_share_of_turns(self):
        cand=install(self.home,'gist2',"d"*64,300)
        s=self.r.bodies.slots;s.propose_swap('B2_GIST',ModelSlots.from_installed(cand));s.start_shadow('B2_GIST')
        s.parity('B2_GIST',{'overall':.5},{'overall':.5});s.ramp('B2_GIST')
        picked=set()
        for k in range(60):
            self.r.bodies.begin_turn('evt%d'%k);picked.add(self.r.models.path_for('B2_GIST').name)
        self.assertEqual(picked,{'gist.gguf','gist2.gguf'})
        s.rollback('B2_GIST');self.r.bodies.begin_turn('evt1');self.assertEqual(self.r.models.path_for('B2_GIST').name,'gist.gguf')

class Schema(unittest.TestCase):
    def test_offer_schema_fits_the_token_budget(self):
        s=offer_schema(96);pr=s['properties']
        worst=pr['summary']['maxLength']+pr['uncertainty']['maxLength']+pr['quotes']['maxItems']*pr['quotes']['items']['maxLength']
        self.assertLessEqual(worst/2.2+30,96*1.05);self.assertGreater(offer_schema(256)['properties']['summary']['maxLength'],pr['summary']['maxLength'])

class Taps(unittest.TestCase):
    def test_b2_tap_spec_and_predictor_accept_qwen_width(self):
        self.assertEqual(runners.TAP_SPECS['gist'],('qwen35.result_norm.final.v1',1024))
        from v13.predictor_worker import normalize
        self.assertEqual(normalize(np.ones((3,1024))).shape,(3,1024))
        with self.assertRaises(ValueError):normalize(np.ones((3,768)))

if __name__=='__main__':unittest.main()
