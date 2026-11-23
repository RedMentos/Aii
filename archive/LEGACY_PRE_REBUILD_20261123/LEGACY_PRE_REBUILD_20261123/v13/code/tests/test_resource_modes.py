"""§97.2 Redmi resource modes GREEN/YELLOW/ORANGE/RED: thresholds, hysteresis, calibration, policy wiring."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from v13 import resource_modes as rm
from v13 import effort,runners
from v13.resources import ResourceGuard
from v13.runtime import Runtime
from v13.operator import Operator

CFG={'minimum_free_mb':500,'thermal_limit_c':45.}
MB=1048576
def snap(mb=None,temp=None):return {'mem_available_bytes':None if mb is None else int(mb*MB),'battery_temperature_c':temp}

class Modes(unittest.TestCase):
    def test_boot_profile_keeps_legacy_boundaries_and_adds_yellow(self):
        p=rm.boot_profile(CFG);self.assertEqual(p['status'],'UNCALIBRATED')
        self.assertEqual(p['mem_mb'],{'RED':500.,'ORANGE':1000.,'YELLOW':1500.});self.assertEqual(p['temp_c'],{'RED':45.,'ORANGE':42.,'YELLOW':39.})
        for mb,temp,mode in ((4000,30,'GREEN'),(1400,30,'YELLOW'),(4000,40,'YELLOW'),(900,30,'ORANGE'),(4000,43,'ORANGE'),(400,30,'RED'),(4000,45,'RED'),(None,None,'GREEN')):
            self.assertEqual(rm.classify(snap(mb,temp),p)[0],mode,(mb,temp))
        self.assertEqual(rm.classify(snap(900,46),p),('RED',['TEMP_AT_RED']))
        self.assertEqual(rm.classify(snap(400,46),p)[1],['MEM_BELOW_RED','TEMP_AT_RED'])

    def test_guard_maps_modes_to_legacy_states_with_hysteresis(self):
        g=ResourceGuard(CFG)
        self.assertEqual((g.update(snap(1400)),g.mode),('NORMAL','YELLOW'))  # YELLOW is invisible to legacy NORMAL checks
        self.assertEqual((g.update(snap(900)),g.mode),('PRESSURE','ORANGE'))
        self.assertEqual((g.update(snap(1020)),g.mode),('PRESSURE','ORANGE'))  # inside the 5 % margin: no flapping
        self.assertEqual((g.update(snap(1100)),g.mode),('RECOVERY','YELLOW'))
        self.assertEqual((g.update(snap(1100)),g.mode),('NORMAL','YELLOW'))
        self.assertEqual((g.update(snap(400)),g.mode),('CRITICAL','RED'));self.assertEqual(g.reasons,['MEM_BELOW_RED'])
        self.assertEqual((g.update(snap(4000,30)),g.mode),('RECOVERY','GREEN'))
        g.state='PRESSURE';self.assertEqual(g.mode,'ORANGE')  # direct assignment (tests, reflex) is honoured
        self.assertEqual(rm.mode_of(type('G',(),{'state':'CRITICAL'})()),'RED');self.assertEqual(rm.mode_of(None),'GREEN')

    def test_calibration_needs_both_bodies_and_marks_host_numbers(self):
        with self.assertRaisesRegex(ValueError,'B2_GIST'):rm.calibrate(CFG,{'B1_DETAIL':800},{'android':True})
        p=rm.calibrate(CFG,{'B1_DETAIL':800,'B2_GIST':600,'C3_LANGUAGE':300},{'android':False},clock=lambda:7.)
        self.assertEqual(p['status'],'HOST_MEASURED_NOT_REDMI');self.assertEqual(p['thermal_status'],'BOOT_UNMEASURED')
        self.assertEqual(p['mem_mb'],{'RED':500.,'ORANGE':1420.,'YELLOW':2110.});self.assertEqual(p['measured']['body_rss_mb'],{'B1_DETAIL':800.,'B2_GIST':600.})
        d=rm.calibrate(CFG,{'B1_DETAIL':800,'B2_GIST':600},{'android':True},thermal={'RED':44,'ORANGE':41,'YELLOW':38})
        self.assertEqual((d['status'],d['thermal_status'],d['temp_c']['ORANGE']),('DEVICE_MEASURED','DEVICE_MEASURED',41.))
        with self.assertRaises(ValueError):rm.calibrate(CFG,{'B1_DETAIL':800,'B2_GIST':600},{},thermal={'RED':38,'ORANGE':41,'YELLOW':44})
        self.assertEqual(rm.classify(snap(1800),p)[0],'YELLOW');self.assertEqual(rm.classify(snap(1800),rm.boot_profile(CFG))[0],'GREEN')

    def test_policy_follows_canon_table(self):
        self.assertTrue(rm.allows('NORMAL','shadow_learning'));self.assertTrue(rm.allows('YELLOW','replay'))
        self.assertFalse(rm.allows('PRESSURE','shadow_learning'));self.assertFalse(rm.allows('ORANGE','replay'))
        self.assertFalse(rm.allows('CRITICAL','replay'));self.assertFalse(rm.allows('RED','shadow_learning'))
        self.assertEqual(rm.cap_roles(['B1_DETAIL','B2_GIST'],'ORANGE'),['B1_DETAIL']);self.assertEqual(rm.cap_roles(['B1_DETAIL'],'RED'),[])
        self.assertEqual(rm.cap_roles(['B1_DETAIL','B2_GIST'],'YELLOW','background_observers'),['B1_DETAIL'])
        self.assertEqual([rm.scaled(n,'YELLOW','replay_scale') for n in (0,1,3,8,None)],[0,1,2,4,None]);self.assertEqual(rm.scaled(8,'ORANGE','replay_scale'),0)
        self.assertEqual(rm.policy('RED')['preserved'],['response_governor','rules','provenance','cancel'])

    def test_effort_ceiling_per_mode(self):
        s=effort.signals('Vergleiche A und B','both')
        plans={m:effort.decide('max',s,cfg={'max_reentry':1,'focal_slots':8},resource_mode=m) for m in rm.MODES}
        self.assertEqual([plans[m]['wake'] for m in rm.MODES],['both','both',plans['ORANGE']['one_body'],'none'])
        self.assertEqual(plans['ORANGE']['wake_ceiling'],'one');self.assertEqual(effort.cap_wake('gist','one'),'gist');self.assertEqual(effort.cap_wake('both','one','gist'),'gist')
        self.assertGreater(plans['GREEN']['observer_scale'],plans['YELLOW']['observer_scale']);self.assertEqual(plans['RED']['observer_scale'],0.)

class Wired(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off')
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_age_orange_blocks_dream_and_replay(self):
        from v13.age import AgeControl
        a=AgeControl(self.r.store,self.r.cfg)
        self.assertEqual(a.budgets('system','ORANGE')['replay_items'],0);self.assertEqual(a.budgets('system','ORANGE')['dream_seconds'],0)
        self.assertFalse(a.allowed('short_dream',resource_mode='ORANGE'))
        self.assertIn('RESOURCE_ORANGE',effort.decide('max',effort.signals('x'),resource_state='PRESSURE')['constraints'])
    def test_sleep_halves_replay_in_yellow(self):
        cy=self.r.sleep.cycle
        self.r.guard.update(snap(4000,30));green=cy.run('a',resource=lambda:self.r.guard.state)
        self.r.guard.update(snap(1200,30));yellow=cy.run('a',resource=lambda:self.r.guard.state)
        self.assertEqual((green['resource_mode'],yellow['resource_mode']),('GREEN','YELLOW'))
        self.assertEqual(yellow['replay_budget'],rm.scaled(green['replay_budget'],'YELLOW','replay_scale'));self.assertLess(yellow['replay_budget'],green['replay_budget'])
    def test_replay_command_pauses_in_orange(self):
        from v13.common import Limits
        with patch.object(self.r,'resources',lambda:snap(900,30)):
            with self.assertRaisesRegex(Limits,'ORANGE'):self.r._replay(4)
    def test_operator_reports_calibrates_and_profile_survives_restart(self):
        op=Operator(self.r);rep=json.loads(op.run(':resources modes'))
        self.assertEqual(rep['profile']['status'],'UNCALIBRATED');self.assertIn(rep['mode'],rm.MODES)
        self.assertIn('resource_mode',json.loads(op.run(':resources')))
        with self.assertRaisesRegex(ValueError,'B1_DETAIL'):op.run(':resources calibrate')  # no resident bodies: refused, profile unchanged
        self.assertEqual(self.r.guard.profile['status'],'UNCALIBRATED')
        with patch.object(rm,'measure_bodies',lambda r:{'B1_DETAIL':700.,'B2_GIST':500.}):rep=json.loads(op.run(':resources calibrate'))
        self.assertEqual(rep['profile']['mem_mb']['YELLOW'],round(self.r.cfg['minimum_free_mb']+1200*rm.CALIBRATION_MARGIN,1))
        self.r.close();self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off')
        self.assertEqual(self.r.guard.profile['mem_mb']['YELLOW'],rep['profile']['mem_mb']['YELLOW'])
        json.loads(Operator(self.r).run(':resources reset'));self.assertEqual(self.r.guard.profile['status'],'UNCALIBRATED')
        self.r.close();self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off');self.assertEqual(self.r.guard.profile['status'],'UNCALIBRATED')

class FakeRunner:
    alive=set()
    def __init__(self,home,role,model,cfg,purpose='generate'):self.role=role;self.model=model;self.purpose=purpose;self.last_metrics={};FakeRunner.alive.add(id(self))
    def pids(self):return [id(self)] if id(self) in FakeRunner.alive else []
    def unload(self):FakeRunner.alive.discard(id(self));return {'process_reaped':True}
def install(home,key,sha,size_mb):
    p=home/'models'/key/(key+'.gguf');p.parent.mkdir(parents=True,exist_ok=True)
    with open(p,'wb') as f:f.truncate(int(size_mb*2**20))
    return {'model_id':key+'-model','exact_revision':'rev-'+key,'license_id':'x','files':{p.name:{'path':str(p.relative_to(home)),'sha256':sha,'size':p.stat().st_size}},'main_file':p.name,'download_complete':True}

class OrangeBodies(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);r=Runtime(self.home);r.close()
        inst={'body':install(self.home,'body',"a"*64,400),'gist':install(self.home,'gist',"b"*64,300),'language':install(self.home,'language',"c"*64,100)}
        (self.home/'config/models.json').write_text(json.dumps(inst))
        cfg=json.loads((self.home/'config/settings.json').read_text());cfg['body_residency_mb']=5000;(self.home/'config/settings.json').write_text(json.dumps(cfg))
        self.p=patch.object(runners,'LlamaRunner',FakeRunner);self.p.start();self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off')
    def tearDown(self):self.r.close();self.p.stop();self.tmp.cleanup()
    def test_orange_holds_one_observer_body_next_to_c3(self):
        self.r.pool.get('C3_LANGUAGE');self.r.pool.get('B1_DETAIL');self.r.pool.get('B2_GIST')
        self.assertEqual(sorted(self.r.pool.resident_roles()),['B1_DETAIL','B2_GIST','C3_LANGUAGE'])
        self.r.guard.state='PRESSURE';self.r.pool.get('B1_DETAIL')
        self.assertEqual(sorted(self.r.pool.resident_roles()),['B1_DETAIL','C3_LANGUAGE'])  # speaker stays, one observer body

if __name__=='__main__':unittest.main()
