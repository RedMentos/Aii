"""WP-T13: BodyPort lifecycle in the RunnerPool, live IH-H21 bridge-key check, online body swap with rollback (no native weights)."""
import json
import unittest
from unittest import mock
from pathlib import Path
from test_bodies import Base,FakeRunner
from v13.runtime import Runtime
from v13.bodyport import BodySwap,bridge_key,direction_roles
from v13.operator import Operator

OLD_EVAL={'overall':.6,'seen':.7,'unseen':.5};NEW_EVAL={'overall':.62,'seen':.7,'unseen':.51}

class Swap(Base):
    budget=1300
    def gguf(self,name='cand.gguf',size=4096):
        p=Path(self.tmp.name)/'incoming'/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b'GGUF'+bytes(size));return p
    def swap(self,probe_ok=True):
        sw=BodySwap(self.r,probe=lambda role:{'ok':probe_ok,**({} if probe_ok else {'error':'no health'})})
        out=sw.propose('B2_GIST',self.gguf());self.assertEqual(out['stage'],'SHADOW')
        self.assertEqual(sw.parity('B2_GIST',OLD_EVAL,NEW_EVAL)['stage'],'PARITY_PASS')
        steps=[sw.ramp('B2_GIST') for _ in range(3)]
        return sw,out,steps
    def model(self,role='B2_GIST'):return Path(str(self.r.pool.get(role).model)).name

class LifecycleTests(Swap):
    def test_pool_reports_assigned_and_released_with_bridge_key(self):
        self.r.pool.get('B1_DETAIL');rep=self.r.bodies.ports.report()['ports']['B1_DETAIL']
        self.assertEqual((rep['state'],rep['revision'],rep['loads']),('ASSIGNED','rev-body',1));self.assertEqual(len(rep['bridge_key']),64)
        self.r.pool.get('B1_DETAIL');self.assertEqual(self.r.bodies.ports.report()['ports']['B1_DETAIL']['loads'],1)  # a hit is not a load
        self.r.pool.unload('B1_DETAIL');self.assertEqual(self.r.bodies.ports.report()['ports']['B1_DETAIL']['state'],'RELEASED')
    def test_bridge_key_changes_with_any_identity_field(self):
        s={'model_id':'m','revision':'r1','sha256':'a'*64,'capabilities':['CAN_NATIVE_DECODE']}
        k=bridge_key('B2_GIST',s)
        for change in ({'revision':'r2'},{'sha256':'b'*64},{'capabilities':['CAN_EMBED']},{'dims':896}):self.assertNotEqual(bridge_key('B2_GIST',s|change),k,change)
        self.assertNotEqual(bridge_key('B1_DETAIL',s),k);self.assertEqual(direction_roles('B1_TO_B2'),('B1_DETAIL','B2_GIST'))

class OnlineSwapTests(Swap):
    def test_swap_takes_effect_without_restart_and_survives_one(self):
        self.assertEqual(self.model(),'gist.gguf')
        sw,out,steps=self.swap()
        self.assertEqual([s['stage'] for s in steps],['RAMP','RAMP','ACTIVE']);self.assertTrue(steps[-1]['probe']['ok'])
        self.assertTrue(self.model().startswith(out['candidate'][:16]))  # same process, next get serves the new file
        self.assertEqual(self.r.models.revision('B2_GIST'),out['candidate']);self.assertEqual(self.r.models.revision('B1_DETAIL'),'rev-body')
        port=self.r.bodies.ports.report()['ports']['B2_GIST'];self.assertEqual(port['changes'],1);self.assertEqual(port['revision'],out['candidate'])
        self.r.close();self.r=Runtime(self.home)
        self.assertEqual(self.r.models.revision('B2_GIST'),out['candidate']);self.assertTrue(self.model().startswith(out['candidate'][:16]))
    def test_ramp_share_routes_turns_by_key(self):
        sw=BodySwap(self.r,probe=lambda role:{'ok':True});out=sw.propose('B2_GIST',self.gguf());sw.parity('B2_GIST',OLD_EVAL,NEW_EVAL);sw.ramp('B2_GIST');sw.ramp('B2_GIST')  # share .5
        seen=set()
        for i in range(24):
            self.r.bodies.begin_turn('evt%d'%i);seen.add(self.model().startswith(out['candidate'][:16]))
        self.assertEqual(seen,{True,False})
    def test_failed_probe_rolls_back_automatically(self):
        sw,out,steps=self.swap(probe_ok=False)
        self.assertEqual(steps[-1]['stage'],'ROLLED_BACK');self.assertEqual(self.model(),'gist.gguf');self.assertEqual(self.r.models.revision('B2_GIST'),'rev-gist')
        self.assertEqual(self.r.bodies.ports.report()['ports']['B2_GIST']['failures'],1)
    def test_user_rollback_after_active(self):
        sw,out,_=self.swap();self.assertTrue(self.model().startswith(out['candidate'][:16]))
        res=json.loads(Operator(self.r).run(':body rollback B2_GIST'));self.assertEqual(res['serving'],'rev-gist')
        self.assertEqual(self.model(),'gist.gguf');self.assertEqual(self.r.models.revision('B2_GIST'),'rev-gist')
    def test_own_swap_needs_age_right_and_non_gguf_is_refused(self):
        sw=BodySwap(self.r)
        with self.assertRaises(PermissionError):sw.propose('B2_GIST',self.gguf(),origin='SYSTEM')
        bad=Path(self.tmp.name)/'x.bin';bad.write_bytes(b'ELF0')
        with self.assertRaises(ValueError):sw.propose('B2_GIST',bad)

class BridgeKeyTests(Swap):
    def test_bridges_for_the_old_body_go_stale_before_the_new_one_serves(self):
        d=self.home/'b3';d.mkdir(exist_ok=True)
        ports=self.r.bodies.ports
        (d/'B1_TO_B2.json').write_text(json.dumps({'direction':'B1_TO_B2',**ports.bridge_binding('B1_TO_B2')}))
        (d/'B2_TO_B1.json').write_text(json.dumps({'direction':'B2_TO_B1',**ports.bridge_binding('B2_TO_B1')}))
        self.r.bodies.slots.register_asset('B2_GIST','prefix_bridge','latent_path')
        self.assertTrue(ports.bridge_valid('B1_TO_B2'));self.model()
        sw,out,_=self.swap();self.model()  # the model change happens at this get
        keys=ports.report()['bridge_keys']['B2_GIST']
        self.assertEqual(set(keys['stale']),{'B1_TO_B2','B2_TO_B1','B2_GIST:prefix_bridge'})
        self.assertNotEqual(keys['key'],keys['previous_key'])
        self.assertFalse(ports.bridge_valid('B1_TO_B2'));self.assertFalse(ports.bridge_valid('missing'))
        self.assertEqual(self.r.bodies.slots.box.load()[0]['assets']['B2_GIST:prefix_bridge']['authority'],'SHADOW_RECALIBRATE')
        self.assertIn('B2_GIST',json.loads(Operator(self.r).run(':body bridges')))

class ExactBridgeIdentityTests(Swap):
    def manifest(self,direction='B1_TO_B2'):
        d=self.home/'b3';d.mkdir(exist_ok=True)
        ports=self.r.bodies.ports
        p=d/(direction+'.json')
        man={'direction':direction,**ports.bridge_binding(direction)}
        p.write_text(json.dumps(man))
        return p,man

    def test_legacy_revision_only_manifest_fails_closed(self):
        p,man=self.manifest()
        self.assertTrue(self.r.bodies.ports.bridge_valid('B1_TO_B2'))
        del man['sender_bridge_key']
        p.write_text(json.dumps(man))
        self.assertFalse(self.r.bodies.ports.bridge_valid('B1_TO_B2'))
        del man['receiver_bridge_key']
        p.write_text(json.dumps(man))
        self.assertFalse(self.r.bodies.ports.bridge_valid('B1_TO_B2'))

    def test_same_revision_changed_sha_invalidates_exact_bridge(self):
        p,man=self.manifest()
        ports=self.r.bodies.ports
        self.assertTrue(ports.bridge_valid('B1_TO_B2'))
        old=ports.spec('B2_GIST');new=old|{'sha256':'e'*64}
        self.assertEqual(old['revision'],new['revision'])
        with mock.patch.object(ports,'spec',side_effect=lambda role: new if role=='B2_GIST' else
                               ports.__class__.spec(ports,role)):
            self.assertFalse(ports.bridge_valid('B1_TO_B2'))
        stale=ports.check_bridges('B2_GIST',old,new)['stale']
        self.assertEqual({x['bridge'] for x in stale if 'bridge' in x},{'B1_TO_B2'})
        self.assertFalse(stale[0]['bridge_key_match'])

    def test_same_revision_changed_capabilities_invalidates(self):
        p,man=self.manifest()
        ports=self.r.bodies.ports
        old=ports.spec('B2_GIST');new=old|{'capabilities':['CAN_EMBED']}
        self.assertEqual(old['revision'],new['revision'])
        self.assertNotEqual(bridge_key('B2_GIST',old),bridge_key('B2_GIST',new))
        stale=ports.check_bridges('B2_GIST',old,new)['stale']
        self.assertIn('B1_TO_B2',{x['bridge'] for x in stale if 'bridge' in x})

    def test_same_revision_identity_change_demotes_slot_asset(self):
        ports=self.r.bodies.ports
        self.r.bodies.slots.register_asset('B2_GIST','old_bridge','latent_path')
        old=ports.spec('B2_GIST');new=old|{'sha256':'f'*64}
        stale=ports.check_bridges('B2_GIST',old,new)['stale']
        self.assertIn('B2_GIST:old_bridge',{x['asset'] for x in stale if 'asset' in x})
        asset=self.r.bodies.slots.box.load()[0]['assets']['B2_GIST:old_bridge']
        self.assertEqual(asset['authority'],'SHADOW_RECALIBRATE')

    def test_exact_same_identity_keeps_bound_manifest_and_slot(self):
        p,man=self.manifest()
        ports=self.r.bodies.ports
        old=ports.spec('B2_GIST')
        self.assertTrue(ports.bridge_valid('B1_TO_B2'))
        self.assertEqual(ports.check_bridges('B2_GIST',old,dict(old))['stale'],[])
        self.assertTrue(ports.bridge_valid('B1_TO_B2'))

    def test_unknown_or_swapped_direction_fails_closed(self):
        p,man=self.manifest()
        ports=self.r.bodies.ports
        self.assertFalse(ports.bridge_valid('B2_TO_B1'))
        self.assertFalse(ports.bridge_valid('../B1_TO_B2'))
        with self.assertRaises(ValueError):ports.bridge_binding('unknown')
        man['direction']='B2_TO_B1'
        p.write_text(json.dumps(man))
        self.assertFalse(ports.bridge_valid('B1_TO_B2'))

    def test_invalid_live_sha_cannot_create_or_accept_bridge(self):
        p,man=self.manifest()
        ports=self.r.bodies.ports
        old=ports.spec('B2_GIST')
        with mock.patch.object(ports,'spec',side_effect=lambda role: old|{'sha256':None}
                               if role=='B2_GIST' else ports.__class__.spec(ports,role)):
            with self.assertRaisesRegex(ValueError,'unbound'):
                ports.bridge_binding('B1_TO_B2')
            self.assertFalse(ports.bridge_valid('B1_TO_B2'))

    def test_key_fields_reject_wrong_side_even_when_revision_matches(self):
        p,man=self.manifest()
        man['sender_bridge_key'],man['receiver_bridge_key']=man['receiver_bridge_key'],man['sender_bridge_key']
        p.write_text(json.dumps(man))
        self.assertFalse(self.r.bodies.ports.bridge_valid('B1_TO_B2'))


if __name__=='__main__':unittest.main()
